"""Detección de pose humana con MediaPipe.

La salida está desacoplada de MediaPipe para que las siguientes etapas
(calibración, filtrado y retargeting Genesis) no dependan directamente
de la API del detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import mediapipe as mp
import numpy as np


@dataclass(frozen=True)
class PoseLandmark:
    """Punto corporal normalizado producido por MediaPipe."""

    index: int
    name: str
    x: float
    y: float
    z: float
    visibility: float
    presence: float


@dataclass(frozen=True)
class PoseFrame:
    """Resultado de pose correspondiente a un frame."""

    frame_index: int
    width: int
    height: int
    landmarks: tuple[PoseLandmark, ...]

    @property
    def detected(self) -> bool:
        return bool(self.landmarks)

    def by_name(self, name: str) -> PoseLandmark | None:
        """Busca un landmark por nombre de MediaPipe."""

        return next((item for item in self.landmarks if item.name == name), None)


class PoseDetector:
    """Detector MediaPipe Pose reutilizable para imagen o vídeo."""

    def __init__(
        self,
        *,
        static_image_mode: bool = False,
        model_complexity: int = 0,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        if model_complexity not in (0, 1, 2):
            raise ValueError("model_complexity debe ser 0, 1 o 2")

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, image_bgr: np.ndarray, *, frame_index: int = 0) -> PoseFrame:
        """Detecta una pose en una imagen BGR de OpenCV."""

        if image_bgr is None or image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise ValueError("image_bgr debe ser una imagen BGR de 3 canales")

        height, width = image_bgr.shape[:2]
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        result = self._pose.process(image_rgb)

        if result.pose_landmarks is None:
            return PoseFrame(
                frame_index=frame_index,
                width=width,
                height=height,
                landmarks=(),
            )

        landmarks = tuple(
            PoseLandmark(
                index=index,
                name=_landmark_name(index),
                x=float(landmark.x),
                y=float(landmark.y),
                z=float(landmark.z),
                visibility=float(landmark.visibility),
                presence=float(getattr(landmark, "presence", 0.0)),
            )
            for index, landmark in enumerate(result.pose_landmarks.landmark)
        )

        return PoseFrame(
            frame_index=frame_index,
            width=width,
            height=height,
            landmarks=landmarks,
        )

    def close(self) -> None:
        """Libera el modelo y sus recursos."""

        self._pose.close()

    def __enter__(self) -> "PoseDetector":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _landmark_name(index: int) -> str:
    """Devuelve el nombre estable del enum PoseLandmark."""

    members: Sequence[object] = tuple(mp.solutions.pose.PoseLandmark)
    try:
        return members[index].name
    except IndexError:
        return f"LANDMARK_{index}"
