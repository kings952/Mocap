import json
from pathlib import Path


class PoseRecorder:

    def __init__(self):

        self.frames = []

    def reset(self):

        self.frames.clear()

    def add(self, packet):

        self.frames.append(packet)

    def __len__(self):

        return len(self.frames)

    def save(self, path):

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "version": 2,

            "fps": 10,

            "frames": self.frames,
        }

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
            )