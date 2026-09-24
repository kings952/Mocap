import time
from pathlib import Path

import cv2

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
)

from camera import Camera
from pose_detector import PoseDetector
from smoothing import PoseSmoother
from sampler import FixedRateSampler
from calibration import CalibrationManager
from recorder import PoseRecorder
from retarget import build_packet
from keyframe_reducer import KeyframeReducer
from gui import MocapGUI
from config import (
    SMOOTHING_ALPHA,
    RECORDING_FPS,
    RECORDINGS_DIR,
    ensure_directories,
)


class MocapWorker(QObject):

    frame_ready = Signal(
        object,
        object,
        object,
    )

    finished = Signal()

    error = Signal(str)

    def __init__(self):

        super().__init__()

        self.running = True

        self.calibration = (
            CalibrationManager()
        )

        self.smoother = PoseSmoother(
            SMOOTHING_ALPHA
        )

        self.sampler = FixedRateSampler(
            RECORDING_FPS
        )

        self.recorder = PoseRecorder()

        self.camera = None
        self.detector = None

        self.recording = False

        self.last_time = time.perf_counter()

        self.camera_fps = 0.0
        self.yolo_fps = 0.0

        self.frames_counter = 0

    def run(self):

        try:

            self.camera = Camera()

            self.detector = PoseDetector()

            while self.running:

                frame = self.camera.read()

                if frame is None:
                    continue

                now = time.perf_counter()

                delta = (
                    now
                    - self.last_time
                )

                self.last_time = now

                if delta > 0:

                    current_fps = (
                        1.0 / delta
                    )

                    self.camera_fps = (
                        self.camera_fps * 0.9
                        + current_fps * 0.1
                    )

                inference_start = (
                    time.perf_counter()
                )

                keypoints = (
                    self.detector.detect(
                        frame
                    )
                )

                inference_time = (
                    time.perf_counter()
                    - inference_start
                )

                if inference_time > 0:

                    current_yolo_fps = (
                        1.0
                        / inference_time
                    )

                    self.yolo_fps = (
                        self.yolo_fps * 0.9
                        + current_yolo_fps * 0.1
                    )

                if keypoints:

                    keypoints = (
                        self.smoother.update(
                            keypoints
                        )
                    )

                    # ------------------------------------------------
                    # CALIBRATION
                    # ------------------------------------------------

                    if (
                        self.calibration.active
                    ):

                        done = (
                            self.calibration.process(
                                keypoints
                            )
                        )

                        state = (
                            f"CALIBRANDO "
                            f"{self.calibration.stable_frames}/"
                            f"{self.calibration.required_frames}"
                        )

                        self.frame_ready.emit(
                            frame,
                            keypoints,
                            {
                                "state": state,
                            },
                        )

                        if done:

                            self.recording = True

                            self.sampler.reset()

                            self.recorder.reset()

                            self.frame_ready.emit(
                                frame,
                                keypoints,
                                {
                                    "state":
                                        "RECORDING",
                                },
                            )

                        continue

                    # ------------------------------------------------
                    # RECORDING
                    # ------------------------------------------------

                    if self.recording:

                        sample = (
                            self.sampler.update()
                        )

                        if sample:

                            packet = build_packet(
                                keypoints,
                                sample["frame_id"],
                                sample["time"],
                            )

                            self.recorder.add(
                                packet
                            )

                            self.frames_counter = (
                                len(
                                    self.recorder.frames
                                )
                            )

                        state = "RECORDING"

                    else:

                        state = "IDLE"

                else:

                    state = "NO PERSON"

                metrics = {}

                if keypoints:

                    packet = build_packet(
                        keypoints,
                        0,
                        0.0,
                    )

                    metrics = packet[
                        "metrics"
                    ]

                metrics[
                    "camera_fps"
                ] = self.camera_fps

                metrics[
                    "yolo_fps"
                ] = self.yolo_fps

                metrics[
                    "recorded_frames"
                ] = self.frames_counter

                metrics[
                    "state"
                ] = state

                self.frame_ready.emit(
                    frame,
                    keypoints,
                    metrics,
                )

        except Exception as exc:

            self.error.emit(
                str(exc)
            )

        finally:

            if self.camera:
                self.camera.release()

            self.finished.emit()

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

        timestamp = (
            time.strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        path = (
            RECORDINGS_DIR
            / f"mocap_{timestamp}.json"
        )

        self.recorder.save(
            path
        )

        return path


class MocapApplication:

    def __init__(self):

        ensure_directories()

        self.gui = MocapGUI()

        self.thread = QThread()

        self.worker = MocapWorker()

        self.worker.moveToThread(
            self.thread
        )

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.frame_ready.connect(
            self._frame
        )

        self.worker.error.connect(
            self._error
        )

        self.gui.on_calibrate = (
            self.worker.start_calibration
        )

        self.gui.on_reset = (
            self.worker.start_calibration
        )

        self.thread.start()

        self.gui.show()

    def _frame(
        self,
        frame,
        keypoints,
        metrics,
    ):

        self.gui.set_camera(
            frame,
            keypoints,
        )

        self.gui.set_state(
            metrics.get(
                "state",
                "IDLE",
            )
        )

        self.gui.update_metrics(
            metrics
        )

    def _error(self, message):

        print(
            f"[ERROR] {message}"
        )

        self.gui.set_state(
            "ERROR"
        )

    def close(self):

        self.worker.stop()

        self.thread.quit()

        self.thread.wait()