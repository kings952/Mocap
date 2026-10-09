"""Captura de cámara y dibujo del esqueleto detectado."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .inputs import VideoFrame
from .pose import PoseFrame


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30


class CameraCapture:
    """Context manager para cámara local con liberación determinista."""

    def __init__(self, config: CameraConfig | None = None) -> None:
        self.config = config or CameraConfig()
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self._capture is not None:
            return
        capture = cv2.VideoCapture(self.config.index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"No se pudo abrir la cámara {self.config.index}.")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        capture.set(cv2.CAP_PROP_FPS, self.config.fps)
        self._capture = capture

    def read(self, index: int) -> VideoFrame | None:
        if self._capture is None:
            raise RuntimeError("La cámara no está abierta.")
        ok, frame = self._capture.read()
        if not ok:
            return None
        timestamp = float(self._capture.get(cv2.CAP_PROP_POS_MSEC))
        return VideoFrame(index=index, timestamp_ms=timestamp, image_bgr=frame)

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "CameraCapture":
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


POSE_CONNECTIONS = (
    ("NOSE", "LEFT_SHOULDER"), ("NOSE", "RIGHT_SHOULDER"),
    ("LEFT_SHOULDER", "LEFT_ELBOW"), ("LEFT_ELBOW", "LEFT_WRIST"),
    ("RIGHT_SHOULDER", "RIGHT_ELBOW"), ("RIGHT_ELBOW", "RIGHT_WRIST"),
    ("LEFT_SHOULDER", "LEFT_HIP"), ("RIGHT_SHOULDER", "RIGHT_HIP"),
    ("LEFT_HIP", "RIGHT_HIP"),
    ("LEFT_HIP", "LEFT_KNEE"), ("LEFT_KNEE", "LEFT_ANKLE"),
    ("RIGHT_HIP", "RIGHT_KNEE"), ("RIGHT_KNEE", "RIGHT_ANKLE"),
    ("LEFT_ANKLE", "LEFT_HEEL"), ("LEFT_HEEL", "LEFT_FOOT_INDEX"),
    ("RIGHT_ANKLE", "RIGHT_HEEL"), ("RIGHT_HEEL", "RIGHT_FOOT_INDEX"),
)


def draw_pose(frame_bgr: np.ndarray, pose: PoseFrame) -> np.ndarray:
    """Dibuja landmarks y conexiones sobre una copia del frame."""
    output = frame_bgr.copy()
    points = {
        item.name: (int(item.x * pose.width), int(item.y * pose.height))
        for item in pose.landmarks if item.visibility >= 0.4
    }
    for first, second in POSE_CONNECTIONS:
        if first in points and second in points:
            cv2.line(output, points[first], points[second], (0, 255, 0), 2)
    for point in points.values():
        cv2.circle(output, point, 4, (0, 0, 255), -1)
    return output
