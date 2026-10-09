"""Entrada de imagen y vídeo para la primera etapa del MOCAP.

Esta capa solo se ocupa de leer datos. No contiene lógica de Blender,
retargeting ni generación de keyframes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(frozen=True)
class VideoFrame:
    """Frame de vídeo junto con su índice y tiempo."""

    index: int
    timestamp_ms: float
    image_bgr: np.ndarray


def load_image(path: str | Path) -> np.ndarray:
    """Carga una imagen como BGR.

    Raises:
        FileNotFoundError: si la ruta no existe.
        ValueError: si OpenCV no puede decodificar la imagen.
    """

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"No existe la imagen: {source}")

    if source.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Formato de imagen no soportado: {source.suffix}. "
            f"Permitidos: {sorted(SUPPORTED_IMAGE_EXTENSIONS)}"
        )

    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"OpenCV no pudo leer la imagen: {source}")

    return image


def iter_video(path: str | Path) -> Iterator[VideoFrame]:
    """Lee un vídeo frame por frame sin cargarlo completo en memoria."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"No existe el vídeo: {source}")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"OpenCV no pudo abrir el vídeo: {source}")

    try:
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            timestamp_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC))
            yield VideoFrame(
                index=index,
                timestamp_ms=timestamp_ms,
                image_bgr=frame,
            )
            index += 1
    finally:
        capture.release()
