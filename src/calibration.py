import json
import time
from pathlib import Path

import numpy as np

from config import (
    CALIBRATION_FRAMES,
    CALIBRATION_MIN_CONFIDENCE,
)


# La calibracion NO depende de las piernas.
# Solo necesitamos torso superior + brazos.
CALIBRATION_POINTS = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
]


class CalibrationManager:
    def __init__(self):
        self.active = False
        self.stable_frames = 0
        self.required_frames = CALIBRATION_FRAMES
        self.samples = []
        self.calibration = None
        self.last_score = 0.0
        self.last_reason = "Pulsa CALIBRAR"

    def start(self):
        self.active = True
        self.stable_frames = 0
        self.samples = []
        self.calibration = None
        self.last_score = 0.0
        self.last_reason = "Colocate dentro de la guia"

    def reset(self):
        self.active = False
        self.stable_frames = 0
        self.samples = []
        self.calibration = None
        self.last_score = 0.0
        self.last_reason = "Pulsa CALIBRAR"

    def process(self, keypoints):
        if not self.active:
            return False

        score, reason = self._pose_score(keypoints)
        self.last_score = score
        self.last_reason = reason

        if score < 0.70:
            self.stable_frames = 0
            self.samples.clear()
            return False

        self.samples.append(self._copy(keypoints))
        self.stable_frames += 1

        if self.stable_frames >= self.required_frames:
            self._finish()
            return True

        return False

    def progress(self):
        return min(
            1.0,
            self.stable_frames / max(self.required_frames, 1),
        )

    def _pose_score(self, p):
        if not self._valid(p, "left_shoulder") or not self._valid(
            p, "right_shoulder"
        ):
            return 0.0, "Muestra ambos hombros"

        ls = p["left_shoulder"]
        rs = p["right_shoulder"]

        shoulder_width = abs(ls["x"] - rs["x"])
        if shoulder_width < 20:
            return 0.0, "Acercate un poco a la camara"

        score = 0.25

        arm_points = [
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
        ]

        visible_arms = [
            name for name in arm_points if self._valid(p, name)
        ]

        if len(visible_arms) >= 4:
            lw = p["left_wrist"]
            rw = p["right_wrist"]

            left_horizontal = abs(lw["y"] - ls["y"]) / shoulder_width
            right_horizontal = abs(rw["y"] - rs["y"]) / shoulder_width

            if left_horizontal <= 0.65 and right_horizontal <= 0.65:
                score += 0.50
            else:
                return score, "Levanta los brazos aproximadamente en T"

            if lw["x"] < ls["x"] and rw["x"] > rs["x"]:
                score += 0.25
            else:
                return score, "Abre los brazos hacia los lados"

        elif len(visible_arms) >= 2:
            score += 0.35
            return score, "Mantente quieto; faltan puntos de un brazo"

        else:
            return score, "Muestra al menos los brazos"

        return score, "Correcto: manten la pose"

    def _valid(self, p, name):
        point = p.get(name)
        return (
            point is not None
            and float(point.get("confidence", 0.0))
            >= CALIBRATION_MIN_CONFIDENCE
        )

    def _finish(self):
        if not self.samples:
            return

        calibration = {}
        names = self.samples[0].keys()

        for name in names:
            values = [
                [sample[name]["x"], sample[name]["y"]]
                for sample in self.samples
                if name in sample
            ]

            if not values:
                continue

            mean = np.mean(np.asarray(values), axis=0)
            calibration[name] = {
                "x": float(mean[0]),
                "y": float(mean[1]),
            }

        ls = calibration["left_shoulder"]
        rs = calibration["right_shoulder"]

        center = [
            (ls["x"] + rs["x"]) / 2.0,
            (ls["y"] + rs["y"]) / 2.0,
        ]

        shoulder_width = max(
            abs(ls["x"] - rs["x"]),
            1.0,
        )

        # Store normalized-space information explicitly. The live retarget
        # uses this instead of assuming a fixed camera resolution.
        self.calibration = {
            "version": 3,
            "timestamp": time.time(),
            "keypoints": calibration,
            "center": center,
            "body_scale": float(shoulder_width),
            "space": {
                "type": "shoulder_normalized_2d",
                "reference_width_px": float(shoulder_width),
            },
        }

        self.active = False
        self.last_score = 1.0
        self.last_reason = "CALIBRACION COMPLETA"

    def save(self, path):
        if self.calibration is None:
            return

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.calibration, file, indent=2)

    def _copy(self, points):
        return {
            name: {
                "x": float(value["x"]),
                "y": float(value["y"]),
                "confidence": float(value.get("confidence", 0.0)),
            }
            for name, value in points.items()
        }
