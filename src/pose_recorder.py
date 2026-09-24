import json
from pathlib import Path


class PoseRecorder:

    def __init__(self, fps=30):

        self.fps = fps
        self.frames = []

    # ========================================================
    # AGREGAR FRAME
    # ========================================================

    def add(self, packet):

        if packet is None:
            return

        self.frames.append(packet)

    # ========================================================
    # CANTIDAD
    # ========================================================

    def frame_count(self):

        return len(self.frames)

    # ========================================================
    # GUARDAR
    # ========================================================

    def save(self, path):

        path = Path(path)

        data = {
            "fps": self.fps,
            "frame_count": len(self.frames),
            "frames": self.frames,
        }

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2
            )

        print(
            f"Poses guardadas: {path}"
        )

        print(
            f"Frames: {len(self.frames)}"
        )