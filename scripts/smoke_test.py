"""Comprueba las dependencias principales sin abrir cámara ni Blender."""

from __future__ import annotations

import sys
from pathlib import Path

# Permite ejecutar el diagnóstico desde el checkout sin instalar el paquete.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    print(f"Python: {sys.version.split()[0]} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")

    if sys.version_info[:2] != (3, 12):
        print("ERROR: este conjunto de dependencias está fijado para Python 3.12.x.")
        print("Crea el entorno con: py -3.12 -m venv .venv")
        return 1

    try:
        import numpy as np
        import scipy
        import cv2
        import mediapipe as mp
        import PySide6
        from mocap.config import DEFAULT_CONFIG

        print(f"NumPy: {np.__version__}")
        print(f"SciPy: {scipy.__version__}")
        print(f"OpenCV: {cv2.__version__}")
        print(f"MediaPipe: {getattr(mp, '__version__', 'desconocida')}")
        print(f"PySide6: {PySide6.__version__}")
        print(
            "Cámara configurada: "
            f"{DEFAULT_CONFIG.camera_width}x{DEFAULT_CONFIG.camera_height} "
            f"@ {DEFAULT_CONFIG.camera_fps} FPS"
        )
    except Exception as exc:
        print("\nERROR: el entorno no está listo.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print("\nOK: dependencias importadas correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
