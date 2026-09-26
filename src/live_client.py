import time

from live_3d_renderer import Live3DRenderer
from retarget import build_live_targets
from config import LIVE_FPS


class LivePreviewClient:
    """Tracker 3D local: calcula IK y renderiza un proxy 3D sin Blender."""

    def __init__(self):
        self.connected = False
        self.last_error = ""
        self.last_send = 0.0
        self.sent_frames = 0
        self.dropped_frames = 0
        self.last_target_count = 0
        self.preview = None
        self.interval = 1.0 / max(float(LIVE_FPS), 1.0)
        self.renderer = Live3DRenderer()

    def start(self):
        self.stop()
        self.connected = True
        self.last_error = ""
        self.preview = None
        self.last_send = 0.0
        self.sent_frames = 0
        self.dropped_frames = 0
        self.last_target_count = 0
        print(
            "[LIVE] Tracker 3D local activo: Python/OpenCV; Blender fuera del loop.",
            flush=True,
        )
        return True

    def send(self, keypoints, calibration, frame_id, timestamp):
        if not self.connected:
            return False

        now = time.perf_counter()
        if (
            self.last_send > 0.0
            and now - self.last_send < self.interval
        ):
            self.dropped_frames += 1
            return False

        try:
            targets = build_live_targets(
                keypoints,
                calibration,
            )
            self.last_target_count = len(targets)
            self.preview = self.renderer.render(
                keypoints,
                calibration,
            )
            self.last_send = now
            self.sent_frames += 1
            return True
        except Exception as exc:
            self.last_error = f"Error tracker 3D: {exc}"
            print(
                f"[LIVE] {self.last_error}",
                flush=True,
            )
            return False

    def stop(self):
        self.connected = False
        self.preview = None
