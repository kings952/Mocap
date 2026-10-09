"""Verify that the development environment is ready."""

from __future__ import annotations

import sys


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")

    try:
        import numpy as np
        print(f"NumPy: {np.__version__}")

        import scipy
        print(f"SciPy: {scipy.__version__}")

        import cv2
        print(f"OpenCV: {cv2.__version__}")

        import mediapipe as mp
        print(f"MediaPipe: {getattr(mp, '__version__', 'unknown')}")

        import PySide6
        print(f"PySide6: {PySide6.__version__}")

        from mocap.config import DEFAULT_CONFIG
        print(f"Camera: {DEFAULT_CONFIG.camera_width}x{DEFAULT_CONFIG.camera_height} @ {DEFAULT_CONFIG.camera_fps} FPS")

    except Exception as exc:
        print()
        print("ERROR: el entorno no esta listo.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print()
    print("OK: entorno MOCAP preparado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
