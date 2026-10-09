"""Modelo de keyframes independiente de Blender y serialización JSON."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from .pose import PoseFrame

@dataclass(frozen=True)
class PoseKeyframe:
    frame: int
    pose: PoseFrame
    score: float
    reason: str

class KeyframeStore:
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
    def to_dict(self) -> dict:
        return {"keyframes": [_item_dict(item) for item in self._items]}
    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return target

def _item_dict(item: PoseKeyframe) -> dict:
    return {"frame": item.frame, "score": item.score, "reason": item.reason,
            "pose": {"width": item.pose.width, "height": item.pose.height,
                     "landmarks": [
                         {"index": p.index, "name": p.name, "x": p.x, "y": p.y, "z": p.z,
                          "visibility": p.visibility, "presence": p.presence}
                         for p in item.pose.landmarks]}}
def image_keyframe(pose: PoseFrame) -> PoseKeyframe:
    return PoseKeyframe(1, pose, 1.0, "imagen")
