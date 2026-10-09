"""Prueba manual de imagen o vídeo.

Ejemplos:
    python scripts\\pose_test.py --image ruta\\persona.jpg
    python scripts\\pose_test.py --video ruta\\movimiento.mp4 --max-frames 120
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mocap.inputs import iter_video, load_image
from mocap.pose import PoseDetector


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba MediaPipe Pose")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path)
    group.add_argument("--video", type=Path)
    parser.add_argument("--max-frames", type=int, default=120)
    args = parser.parse_args()

    if args.image:
        with PoseDetector(
            static_image_mode=True,
            model_complexity=0,
        ) as detector:
            result = detector.detect(load_image(args.image), frame_index=1)

        print(f"Imagen: {args.image}")
        print(f"Resolución: {result.width}x{result.height}")
        print(f"Pose detectada: {result.detected}")
        print(f"Landmarks: {len(result.landmarks)}")
        return 0

    processed = 0
    detected = 0

    with PoseDetector(model_complexity=0) as detector:
        for frame in iter_video(args.video):
            result = detector.detect(frame.image_bgr, frame_index=frame.index)
            processed += 1
            detected += int(result.detected)

            if processed >= args.max_frames:
                break

    print(f"Vídeo: {args.video}")
    print(f"Frames procesados: {processed}")
    print(f"Frames con pose: {detected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
