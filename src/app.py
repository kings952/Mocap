import time

from PySide6.QtCore import QObject, QThread, Signal

from camera import Camera
from pose_detector import PoseDetector
from smoothing import PoseSmoother
from sampler import FixedRateSampler
from calibration import CalibrationManager
from recorder import PoseRecorder
from retarget import build_packet
from gui import MocapGUI
from calibration_ui import draw_calibration_overlay
from live_client import LivePreviewClient
from config import SMOOTHING_ALPHA, RECORDING_FPS, RECORDINGS_DIR, ensure_directories


class MocapWorker(QObject):
    frame_ready = Signal(object, object, object)
    finished = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.calibration = CalibrationManager()
        self.smoother = PoseSmoother(SMOOTHING_ALPHA)
        self.sampler = FixedRateSampler(RECORDING_FPS)
        self.recorder = PoseRecorder()
        self.camera = None
        self.detector = None
        self.live = LivePreviewClient()
        self.recording = False
        self.last_time = time.perf_counter()
        self.camera_fps = 0.0
        self.yolo_fps = 0.0
        self.frames_counter = 0
        self.live_frame_id = 0

    def run(self):
        try:
            self.camera = Camera()
            self.detector = PoseDetector()

            if not self.live.start():
                print(f"[LIVE] {self.live.last_error}")

            while self.running:
                frame = self.camera.read()
                if frame is None:
                    continue

                now = time.perf_counter()
                delta = now - self.last_time
                self.last_time = now
                if delta > 0:
                    fps = 1.0 / delta
                    self.camera_fps = self.camera_fps * 0.9 + fps * 0.1

                start = time.perf_counter()
                keypoints = self.detector.detect(frame)
                inference_time = time.perf_counter() - start
                if inference_time > 0:
                    fps = 1.0 / inference_time
                    self.yolo_fps = self.yolo_fps * 0.9 + fps * 0.1

                if keypoints:
                    keypoints = self.smoother.update(keypoints)

                if self.calibration.active:
                    done = self.calibration.process(keypoints or {})

                    display = draw_calibration_overlay(
                        frame,
                        self.calibration.progress(),
                        self.calibration.last_score,
                        self.calibration.last_reason,
                    )

                    metrics = self._metrics(keypoints)
                    metrics.update({
                        "state": (
                            "CALIBRADO"
                            if done
                            else f"CALIBRANDO {self.calibration.stable_frames}/{self.calibration.required_frames}"
                        ),
                        "calibration_progress": self.calibration.progress(),
                        "calibration_score": self.calibration.last_score,
                        "calibration_reason": self.calibration.last_reason,
                        "live_connected": self.live.connected,
                        "live_error": self.live.last_error,
                    })
                    self.frame_ready.emit(display, keypoints, metrics)

                    if done:
                        self.recording = True
                        self.sampler.reset()
                        self.recorder.reset()

                    if self.calibration.calibration and keypoints:
                        self._send_live(keypoints, now)
                    continue

                if keypoints:
                    if self.recording:
                        sample = self.sampler.update()
                        if sample:
                            packet = build_packet(
                                keypoints,
                                sample["frame_id"],
                                sample["time"],
                            )
                            self.recorder.add(packet)
                            self.frames_counter = len(self.recorder.frames)

                    self._send_live(keypoints, now)
                    state = "LIVE"
                else:
                    state = "NO PERSON"

                metrics = self._metrics(keypoints)
                metrics.update({
                    "state": state,
                    "live_connected": self.live.connected,
                    "live_error": self.live.last_error,
                })
                self.frame_ready.emit(frame, keypoints, metrics)

        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            if self.camera:
                self.camera.release()
            self.live.stop()
            self.finished.emit()

    def _send_live(self, keypoints, timestamp):
        if not self.calibration.calibration:
            return
        self.live.send(
            keypoints,
            self.calibration.calibration,
            self.live_frame_id,
            timestamp,
        )
        self.live_frame_id += 1

    def _metrics(self, keypoints):
        metrics = {}
        if keypoints:
            metrics = build_packet(keypoints, 0, 0.0)["metrics"]
        metrics["camera_fps"] = self.camera_fps
        metrics["yolo_fps"] = self.yolo_fps
        metrics["recorded_frames"] = self.frames_counter
        return metrics

    def start_calibration(self):
        self.calibration.start()
        self.recording = False
        self.recorder.reset()
        self.sampler.reset()
        self.frames_counter = 0

    def stop(self):
        self.running = False

    def save_recording(self):
        if len(self.recorder) == 0:
            return None
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = RECORDINGS_DIR / f"mocap_{timestamp}.json"
        self.recorder.save(path)
        return path


class MocapApplication:
    def __init__(self):
        ensure_directories()
        self.gui = MocapGUI()
        self.thread = QThread()
        self.worker = MocapWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.frame_ready.connect(self._frame)
        self.worker.error.connect(self._error)

        self.gui.on_calibrate = self.worker.start_calibration
        self.gui.on_reset = self.worker.start_calibration

        self.thread.start()
        self.gui.show()

    def _frame(self, frame, keypoints, metrics):
        self.gui.set_camera(frame, keypoints)
        self.gui.set_state(metrics.get("state", "IDLE"))
        self.gui.update_metrics(metrics)

    def _error(self, message):
        print(f"[ERROR] {message}")
        self.gui.set_state("ERROR")

    def close(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
