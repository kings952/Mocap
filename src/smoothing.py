import math

from config import (
    SMOOTHING_ALPHA,
    SMOOTHING_HOLD_FRAMES,
    SMOOTHING_MAX_JUMP_RATIO,
)


class PoseSmoother:
    """
    Suavizado temporal con:
    - EMA suave.
    - limite de salto por frame proporcional al ancho de hombros.
    - retencion breve cuando YOLO pierde un keypoint.

    Esto evita que un solo frame malo mande un IK a una posicion absurda.
    """

    def __init__(
        self,
        alpha=SMOOTHING_ALPHA,
        max_jump_ratio=SMOOTHING_MAX_JUMP_RATIO,
        hold_frames=SMOOTHING_HOLD_FRAMES,
    ):
        self.alpha = float(alpha)
        self.max_jump_ratio = float(max_jump_ratio)
        self.hold_frames = int(hold_frames)
        self.previous = None
        self.missing = {}

    def reset(self):
        self.previous = None
        self.missing = {}

    def update(self, keypoints):
        if not keypoints:
            return self._copy(self.previous) if self.previous else {}

        if self.previous is None:
            self.previous = self._copy(keypoints)
            self.missing = {name: 0 for name in keypoints}
            return self._copy(self.previous)

        shoulder_width = self._shoulder_width(keypoints)
        max_jump = max(3.0, shoulder_width * self.max_jump_ratio)

        result = {}
        all_names = set(self.previous) | set(keypoints)

        for name in all_names:
            current = keypoints.get(name)
            previous = self.previous.get(name)

            if current is None:
                if previous is None:
                    continue

                count = self.missing.get(name, 0) + 1
                self.missing[name] = count

                if count <= self.hold_frames:
                    held_confidence = float(previous.get("confidence", 0.0)) * 0.85
                    result[name] = {
                        "x": float(previous["x"]),
                        "y": float(previous["y"]),
                        "confidence": held_confidence,
                    }
                continue

            self.missing[name] = 0

            if previous is None:
                result[name] = dict(current)
                continue

            dx = float(current["x"]) - float(previous["x"])
            dy = float(current["y"]) - float(previous["y"])
            distance = math.hypot(dx, dy)

            if distance > max_jump and distance > 0.0001:
                ratio = max_jump / distance
                limited_x = float(previous["x"]) + dx * ratio
                limited_y = float(previous["y"]) + dy * ratio
            else:
                limited_x = float(current["x"])
                limited_y = float(current["y"])

            alpha = self.alpha
            result[name] = {
                "x": float(previous["x"]) * (1.0 - alpha)
                + limited_x * alpha,
                "y": float(previous["y"]) * (1.0 - alpha)
                + limited_y * alpha,
                "confidence": float(current.get("confidence", 0.0)),
            }

        self.previous = self._copy(result)
        return result

    @staticmethod
    def _shoulder_width(keypoints):
        left = keypoints.get("left_shoulder")
        right = keypoints.get("right_shoulder")

        if not left or not right:
            return 120.0

        return max(
            abs(float(left["x"]) - float(right["x"])),
            20.0,
        )

    @staticmethod
    def _copy(keypoints):
        return {
            name: {
                "x": float(point["x"]),
                "y": float(point["y"]),
                "confidence": float(point.get("confidence", 0.0)),
            }
            for name, point in keypoints.items()
        }
