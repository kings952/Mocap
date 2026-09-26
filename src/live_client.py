import time

from live_renderer import render
from retarget import build_live_targets
from config import LIVE_FPS


class LivePreviewClient:
    """Live preview completamente local: no inicia Blender ni toca archivos."""

    def __init__(self):
        self.connected = False
        self.last_error = ""
        self.last_send = 0.0
        self.sent_frames = 0
        self.dropped_frames = 0
        self.last_target_count = 0
        self.preview = None
        self.interval = 1.0 / max(float(LIVE_FPS), 1.0)

    def start(self):
        self.stop()
        self.connected = True
        self.last_error = ""
        self.preview = None
        print(
            "[LIVE] Preview local activo: Python/OpenCV; "
            "Blender fuera del loop.",
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

            # El retarget se sigue calculando para validar la relacion
            # humano -> rig, pero ya no necesita un proceso Blender para el LIVE.
            self.last_target_count = len(targets)
            self.preview = render(keypoints)
            self.last_send = now
            self.sent_frames += 1
            return True

        except Exception as exc:
            self.last_error = f"Error preview local: {exc}"
            print(
                f"[LIVE] {self.last_error}",
                flush=True,
            )
            return False

    def stop(self):
        self.connected = False
        self.preview = None
