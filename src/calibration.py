import json
import time
from pathlib import Path

import numpy as np

from config import (
    CALIBRATION_FRAMES,
    CALIBRATION_MIN_CONFIDENCE,
)


REQUIRED_POINTS = [
    "left_shoulder",
    "right_shoulder",

    "left_elbow",
    "right_elbow",

    "left_wrist",
    "right_wrist",

    "left_hip",
    "right_hip",

    "left_knee",
    "right_knee",

    "left_ankle",
    "right_ankle",
]


class CalibrationManager:

    def __init__(self):

        self.active = False

        self.stable_frames = 0

        self.required_frames = CALIBRATION_FRAMES

        self.samples = []

        self.calibration = None

    def start(self):

        self.active = True

        self.stable_frames = 0

        self.samples = []

        self.calibration = None

    def reset(self):

        self.active = False

        self.stable_frames = 0

        self.samples = []

        self.calibration = None

    def process(self, keypoints):

        if not self.active:
            return False

        if not self._valid(keypoints):
            self.stable_frames = 0
            self.samples.clear()

            return False

        if not self._is_t_pose(keypoints):
            self.stable_frames = 0
            self.samples.clear()

            return False

        self.samples.append(
            self._copy(keypoints)
        )

        self.stable_frames += 1

        if self.stable_frames >= self.required_frames:

            self._finish()

            return True

        return False

    def _valid(self, keypoints):

        for name in REQUIRED_POINTS:

            point = keypoints.get(name)

            if point is None:
                return False

            if (
                point["confidence"]
                < CALIBRATION_MIN_CONFIDENCE
            ):
                return False

        return True

    def _is_t_pose(self, p):

        ls = p["left_shoulder"]
        rs = p["right_shoulder"]

        le = p["left_elbow"]
        re = p["right_elbow"]

        lw = p["left_wrist"]
        rw = p["right_wrist"]

        # Brazos aproximadamente horizontales.

        left_arm_y = abs(
            lw["y"] - ls["y"]
        )

        right_arm_y = abs(
            rw["y"] - rs["y"]
        )

        shoulder_width = abs(
            ls["x"] - rs["x"]
        )

        if shoulder_width < 20:
            return False

        if left_arm_y > shoulder_width * 0.35:
            return False

        if right_arm_y > shoulder_width * 0.35:
            return False

        # Las muñecas deben estar hacia afuera.

        if not (
            lw["x"] < ls["x"]
            and rw["x"] > rs["x"]
        ):
            return False

        # Piernas aproximadamente verticales.

        lh = p["left_hip"]
        rh = p["right_hip"]

        la = p["left_ankle"]
        ra = p["right_ankle"]

        if not (
            la["y"] > lh["y"]
            and ra["y"] > rh["y"]
        ):
            return False

        return True

    def _finish(self):

        if not self.samples:
            return

        calibration = {}

        names = self.samples[0].keys()

        for name in names:

            values = [
                [
                    sample[name]["x"],
                    sample[name]["y"],
                ]
                for sample in self.samples
                if name in sample
            ]

            if not values:
                continue

            mean = np.mean(
                np.asarray(values),
                axis=0,
            )

            calibration[name] = {
                "x": float(mean[0]),
                "y": float(mean[1]),
            }

        ls = calibration["left_shoulder"]
        rs = calibration["right_shoulder"]

        center = [
            (
                ls["x"]
                + rs["x"]
            ) / 2.0,

            (
                ls["y"]
                + rs["y"]
            ) / 2.0,
        ]

        shoulder_width = abs(
            ls["x"] - rs["x"]
        )

        self.calibration = {
            "timestamp": time.time(),

            "keypoints": calibration,

            "center": center,

            "body_scale": float(
                max(shoulder_width, 1.0)
            ),
        }

        self.active = False

    def save(self, path):

        if self.calibration is None:
            return

        path = Path(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                self.calibration,
                file,
                indent=2,
            )

    def _copy(self, points):

        return {
            name: {
                "x": float(value["x"]),
                "y": float(value["y"]),
                "confidence": float(
                    value["confidence"]
                ),
            }
            for name, value in points.items()
        }