import json
import time
from pathlib import Path

import numpy as np

from config import (
    CALIBRATION_FRAMES,
    CALIBRATION_MIN_CONFIDENCE,
)


# La calibracion es una POSE NEUTRA, no una T obligatoria.
# Funciona con I-pose (brazos/piernas juntos) y evita imponer
# una geometria que luego no coincide con el punto cero del usuario.
CALIBRATION_POINTS = [
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
        self.last_score = 0.0
        self.last_reason = "Pulsa CALIBRAR"

    def start(self):
        self.active = True
        self.stable_frames = 0
        self.samples = []
        self.calibration = None
        self.last_score = 0.0
        self.last_reason = "Colocate en tu pose neutra (I-pose recomendada)"

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

    def _pose_score(self, points):
        required = [
            name
            for name in CALIBRATION_POINTS
            if self._valid(points, name)
        ]

        visibility = len(required) / max(len(CALIBRATION_POINTS), 1)

        if not self._valid(points, "left_shoulder") or not self._valid(
            points, "right_shoulder"
        ):
            return 0.0, "Muestra ambos hombros"

        shoulder_width = abs(
            points["left_shoulder"]["x"]
            - points["right_shoulder"]["x"]
        )

        if shoulder_width < 20:
            return 0.0, "Acercate un poco a la camara"

        if visibility < 0.70:
            return (
                visibility,
                "Muestra cuerpo completo y manten la pose quieta",
            )

        # No se exige que brazos o piernas esten abiertos.
        # I-pose, A-pose o T-pose pueden servir como neutral siempre
        # que la persona mantenga la misma pose durante la captura.
        return (
            min(1.0, 0.75 + visibility * 0.25),
            "Pose neutra detectada; mantenla quieta",
        )

    def _valid(self, points, name):
        point = points.get(name)
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
            (ls["x"] + rs["x"]) / 2.0,
            (ls["y"] + rs["y"]) / 2.0,
        ]

        shoulder_width = max(
            abs(ls["x"] - rs["x"]),
            1.0,
        )

        self.calibration = {
            "version": 4,
            "timestamp": time.time(),
            "keypoints": calibration,
            "center": center,
            "body_scale": float(shoulder_width),
            "neutral_pose": "I",
            "space": {
                "type": "shoulder_normalized_2d",
                "reference_width_px": float(shoulder_width),
            },
        }

        self.active = False
        self.last_score = 1.0
        self.last_reason = "CALIBRACION COMPLETA • NEUTRA"

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
                    value.get("confidence", 0.0)
                ),
            }
            for name, value in points.items()
        }
