"""Comprueba el entorno base sin abrir cámara ni Blender."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    version = sys.version_info[:2]
    bits = "64-bit" if sys.maxsize > 2**32 else "32-bit"

    print(f"Python: {sys.version.split()[0]} ({bits})")

    if version != (3, 10):
        print("ERROR: esta base está fijada para Python 3.10.x.")
        print("Crea el entorno con: py -3.10 -m venv .venv")
        return 1

    if bits != "64-bit":
        print("ERROR: se requiere Python de 64 bits.")
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
