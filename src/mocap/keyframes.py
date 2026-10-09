"""Modelo de keyframes independiente de Blender."""

from __future__ import annotations

from dataclasses import dataclass

from .pose import PoseFrame


@dataclass(frozen=True)
class PoseKeyframe:
    frame: int
    pose: PoseFrame
    score: float
    reason: str


class KeyframeStore:
    """Almacena únicamente poses aceptadas por el filtro."""

    def __init__(self) -> None:
        self._items: list[PoseKeyframe] = []

    @property
    def items(self) -> tuple[PoseKeyframe, ...]:
        return tuple(self._items)

    def clear(self) -> None:
        self._items.clear()

    def add(self, pose: PoseFrame, *, frame: int, score: float = 0.0, reason: str = "") -> PoseKeyframe:
        frame = max(1, int(frame))
        if self._items and frame < self._items[-1].frame:
            raise ValueError("Los keyframes deben estar ordenados por frame.")
        item = PoseKeyframe(frame, pose, float(score), reason)
        self._items.append(item)
        return item

    def add_if_accepted(self, pose: PoseFrame, *, frame: int, accepted: bool, score: float, reason: str) -> PoseKeyframe | None:
        if not accepted:
            return None
        return self.add(pose, frame=frame, score=score, reason=reason)

    def frames(self) -> tuple[int, ...]:
        return tuple(item.frame for item in self._items)

    def __len__(self) -> int:
        return len(self._items)


def image_keyframe(pose: PoseFrame) -> PoseKeyframe:
    """RF-008: una imagen siempre se representa en el frame 1."""
    return PoseKeyframe(1, pose, 1.0, "imagen")
