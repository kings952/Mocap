"""Calibración, suavizado y selección de keyframes del MOCAP.

La comparación de movimiento se hace contra el último keyframe aceptado,
no contra el frame inmediatamente anterior. Así los micro-movimientos no
se acumulan hasta convertirse accidentalmente en un keyframe.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import hypot, sqrt
from typing import Iterable
from .pose import PoseFrame, PoseLandmark

class CaptureState(str, Enum):
    IDLE = "idle"
    CALIBRATING = "calibrating"
    READY = "ready"
    RECORDING = "recording"

@dataclass(frozen=True)
class MotionConfig:
    min_visibility: float = 0.55
    calibration_samples: int = 15
    calibration_stability_threshold: float = 0.025
    movement_threshold: float = 0.035
    min_keyframe_gap: int = 2
    smoothing_alpha: float = 0.45

@dataclass(frozen=True)
class Calibration:
    reference: tuple[PoseLandmark, ...]
    center_x: float
    center_y: float
    scale: float

@dataclass(frozen=True)
class MotionDecision:
    accepted: bool
    score: float
    reason: str
    pose: PoseFrame | None = None

class MotionProcessor:
    def __init__(self, config: MotionConfig | None = None) -> None:
        self.config = config or MotionConfig()
        self.state = CaptureState.IDLE
        self._samples: list[PoseFrame] = []
        self._calibration: Calibration | None = None
        self._last_smoothed: PoseFrame | None = None
        self._last_keyframe_pose: PoseFrame | None = None
        self._last_keyframe: int | None = None

    @property
    def calibration(self) -> Calibration | None:
        return self._calibration

    @property
    def calibrated(self) -> bool:
        return self._calibration is not None

    @property
    def calibration_progress(self) -> float:
        return min(1.0, len(self._samples) / self.config.calibration_samples)

    @property
    def last_keyframe(self) -> int | None:
        return self._last_keyframe

    def reset(self) -> None:
        self.state = CaptureState.IDLE
        self._samples.clear()
        self._calibration = None
        self._last_smoothed = None
        self._last_keyframe_pose = None
        self._last_keyframe = None

    def start_calibration(self) -> None:
        self._samples.clear()
        self._calibration = None
        self._last_smoothed = None
        self._last_keyframe_pose = None
        self._last_keyframe = None
        self.state = CaptureState.CALIBRATING

    def add_calibration_sample(self, pose: PoseFrame) -> bool:
        if self.state != CaptureState.CALIBRATING:
            raise RuntimeError("La captura no está en estado CALIBRATING.")
        if not _usable(pose, self.config.min_visibility):
            return False
        self._samples.append(pose)
        if len(self._samples) < self.config.calibration_samples:
            return False
        normalized = [_normalize_pose(p, _build_calibration(self._samples, self.config.min_visibility))
                      for p in self._samples]
        if _pose_spread(normalized) > self.config.calibration_stability_threshold:
            self._samples = self._samples[-max(3, self.config.calibration_samples // 3):]
            return False
        self._calibration = _build_calibration(self._samples, self.config.min_visibility)
        self._samples.clear()
        self.state = CaptureState.READY
        return True

    def begin_recording(self) -> None:
        if not self.calibrated:
            raise RuntimeError("No se puede grabar sin calibración.")
        self.state = CaptureState.RECORDING
        self._last_smoothed = None
        self._last_keyframe_pose = None
        self._last_keyframe = None

    def evaluate(self, pose: PoseFrame, frame_index: int | None = None) -> MotionDecision:
        if self.state != CaptureState.RECORDING:
            return MotionDecision(False, 0.0, "captura_no_activa")
        if self._calibration is None:
            return MotionDecision(False, 0.0, "sin_calibracion")
        if not _usable(pose, self.config.min_visibility):
            return MotionDecision(False, 0.0, "pose_no_valida")
        normalized = PoseFrame(pose.frame_index, pose.width, pose.height,
                               _normalize_pose(pose, self._calibration))
        current = smooth_pose(self._last_smoothed, normalized, self.config.smoothing_alpha)
        self._last_smoothed = current
        index = max(1, pose.frame_index if frame_index is None else frame_index)
        if self._last_keyframe_pose is None:
            self._last_keyframe_pose = current
            self._last_keyframe = index
            return MotionDecision(True, 1.0, "primer_keyframe", current)
        score = _pose_distance(self._last_keyframe_pose, current)
        gap_ok = index - self._last_keyframe >= self.config.min_keyframe_gap
        if score >= self.config.movement_threshold and gap_ok:
            self._last_keyframe_pose = current
            self._last_keyframe = index
            return MotionDecision(True, score, "movimiento_significativo", current)
        return MotionDecision(False, score, "movimiento_pequeno", current)

def _usable(pose: PoseFrame, minimum: float) -> bool:
    return bool(pose.landmarks) and sum(p.visibility >= minimum for p in pose.landmarks) >= 8

def _build_calibration(samples: Iterable[PoseFrame], minimum_visibility: float) -> Calibration:
    samples = tuple(samples)
    names = {p.name for pose in samples for p in pose.landmarks if p.visibility >= minimum_visibility}
    reference = []
    for name in sorted(names):
        points = [p for pose in samples for p in pose.landmarks
                  if p.name == name and p.visibility >= minimum_visibility]
        if points:
            reference.append(PoseLandmark(points[0].index, name,
                sum(p.x for p in points) / len(points),
                sum(p.y for p in points) / len(points),
                sum(p.z for p in points) / len(points),
                min(p.visibility for p in points), min(p.presence for p in points)))
    center_x, center_y, scale = _body_geometry(reference)
    return Calibration(tuple(reference), center_x, center_y, scale)

def _body_geometry(landmarks: Iterable[PoseLandmark]) -> tuple[float, float, float]:
    points = tuple(landmarks)
    if not points:
        return 0.5, 0.5, 1.0
    center_x = sum(p.x for p in points) / len(points)
    center_y = sum(p.y for p in points) / len(points)
    scale = max(hypot(p.x - center_x, p.y - center_y) for p in points)
    return center_x, center_y, max(scale, 1e-6)

def _normalize_pose(pose: PoseFrame, calibration: Calibration) -> tuple[PoseLandmark, ...]:
    return tuple(PoseLandmark(p.index, p.name,
        (p.x - calibration.center_x) / calibration.scale,
        (p.y - calibration.center_y) / calibration.scale,
        p.z / calibration.scale, p.visibility, p.presence) for p in pose.landmarks)

def _pose_distance(first: PoseFrame, second: PoseFrame) -> float:
    a, b = {p.name: p for p in first.landmarks}, {p.name: p for p in second.landmarks}
    common = a.keys() & b.keys()
    if not common:
        return 0.0
    return sum(sqrt((a[n].x-b[n].x)**2 + (a[n].y-b[n].y)**2 + (a[n].z-b[n].z)**2)
               for n in common) / len(common)

def _pose_spread(poses: Iterable[PoseFrame]) -> float:
    poses = tuple(poses)
    if len(poses) < 2:
        return 0.0
    reference = poses[0]
    return max(_pose_distance(reference, p) for p in poses[1:])

def smooth_pose(previous: PoseFrame | None, current: PoseFrame, alpha: float = 0.45) -> PoseFrame:
    alpha = min(1.0, max(0.0, alpha))
    if previous is None:
        return current
    old = {p.name: p for p in previous.landmarks}
    result = []
    for point in current.landmarks:
        before = old.get(point.name)
        if before is None:
            result.append(point)
        else:
            result.append(PoseLandmark(point.index, point.name,
                before.x + alpha*(point.x-before.x),
                before.y + alpha*(point.y-before.y),
                before.z + alpha*(point.z-before.z),
                point.visibility, point.presence))
    return PoseFrame(current.frame_index, current.width, current.height, tuple(result))
