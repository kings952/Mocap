import json
import math
from pathlib import Path

from config import (
    ALWAYS_KEEP_FIRST,
    ALWAYS_KEEP_LAST,
    KEYFRAME_TOLERANCE,
)


class PoseRecorder:
    """
    Guarda keyframes por cambio real de pose, no por cada muestra.

    La comparacion usa unidades normalizadas por el ancho de hombros.
    Un keyframe nuevo entra cuando algun keypoint valido cambia mas de
    KEYFRAME_TOLERANCE respecto al ultimo keyframe guardado.

    Esto mantiene el procesamiento LIVE continuo, pero evita llenar el
    JSON con 10 frames casi identicos por segundo.
    """

    def __init__(
        self,
        tolerance=KEYFRAME_TOLERANCE,
        always_keep_first=ALWAYS_KEEP_FIRST,
        always_keep_last=ALWAYS_KEEP_LAST,
    ):
        self.tolerance = float(tolerance)
        self.always_keep_first = bool(always_keep_first)
        self.always_keep_last = bool(always_keep_last)
        self.frames = []
        self._latest_packet = None

    def reset(self):
        self.frames.clear()
        self._latest_packet = None

    def add(self, packet):
        return self.add_if_changed(packet)

    def add_if_changed(self, packet):
        self._latest_packet = packet

        if not self.frames:
            if self.always_keep_first:
                self.frames.append(packet)
                return True

            self.frames.append(packet)
            return True

        if self._pose_change(self.frames[-1], packet) > self.tolerance:
            self.frames.append(packet)
            return True

        return False

    def finalize(self):
        if (
            self.always_keep_last
            and self._latest_packet is not None
            and self.frames
            and self.frames[-1] is not self._latest_packet
        ):
            self.frames.append(self._latest_packet)

    def __len__(self):
        return len(self.frames)

    def save(self, path):
        self.finalize()

        path = Path(path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "version": 3,
            "fps": 10,
            "keyframe_tolerance": self.tolerance,
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

    def _pose_change(self, previous_packet, current_packet):
        previous = previous_packet.get("keypoints", {})
        current = current_packet.get("keypoints", {})

        if not previous or not current:
            return float("inf")

        previous_scale = float(
            previous_packet.get("metrics", {}).get(
                "body_scale",
                1.0,
            )
            or 1.0
        )

        current_scale = float(
            current_packet.get("metrics", {}).get(
                "body_scale",
                previous_scale,
            )
            or previous_scale
        )

        scale = max(
            (previous_scale + current_scale) * 0.5,
            1.0,
        )

        maximum_change = 0.0

        for name, point in current.items():
            old = previous.get(name)

            if old is None:
                continue

            confidence = min(
                float(point.get("confidence", 0.0)),
                float(old.get("confidence", 0.0)),
            )

            if confidence < 0.35:
                continue

            dx = float(point["x"]) - float(old["x"])
            dy = float(point["y"]) - float(old["y"])

            normalized = math.hypot(dx, dy) / scale
            maximum_change = max(
                maximum_change,
                normalized,
            )

        return maximum_change
