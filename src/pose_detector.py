from pathlib import Path

import numpy as np
from ultralytics import YOLO

from config import (
    FALLBACK_MODEL_PATH,
    MODEL_PATH,
    MODEL_NAME,
    POSE_DETECTION_CONFIDENCE,
    POSE_IOU,
    POSE_TRACKER,
    YOLO_IMAGE_SIZE,
)
from skeleton import KEYPOINT_NAMES


class PoseDetector:
    def __init__(self):
        self.model_path = MODEL_PATH
        self.model_name = MODEL_NAME
        self.tracking_ready = True

        print(
            f"[YOLO] Modelo live: {MODEL_NAME}",
            flush=True,
        )

        try:
            self.model = YOLO(str(MODEL_PATH))
        except Exception as exc:
            print(
                f"[YOLO] No se pudo cargar {MODEL_PATH}: {exc}",
                flush=True,
            )

            if not Path(FALLBACK_MODEL_PATH).exists():
                raise RuntimeError(
                    "No se pudo cargar el modelo YOLO26n y tampoco existe "
                    f"el fallback: {FALLBACK_MODEL_PATH}"
                ) from exc

            self.model_path = FALLBACK_MODEL_PATH
            self.model_name = FALLBACK_MODEL_PATH.name
            print(
                f"[YOLO] Usando fallback local: {self.model_name}",
                flush=True,
            )
            self.model = YOLO(str(FALLBACK_MODEL_PATH))

        # Warm-up real: source=None provoca el warning
        # "'source' is missing" en Ultralytics.
        try:
            dummy = np.zeros(
                (
                    YOLO_IMAGE_SIZE,
                    YOLO_IMAGE_SIZE,
                    3,
                ),
                dtype=np.uint8,
            )
            self.model.predict(
                source=dummy,
                imgsz=YOLO_IMAGE_SIZE,
                conf=POSE_DETECTION_CONFIDENCE,
                verbose=False,
            )
        except Exception as exc:
            print(
                f"[YOLO] Warm-up omitido: {exc}",
                flush=True,
            )

    def detect(self, frame):
        try:
            results = self.model.track(
                source=frame,
                persist=True,
                tracker=POSE_TRACKER,
                imgsz=YOLO_IMAGE_SIZE,
                conf=POSE_DETECTION_CONFIDENCE,
                iou=POSE_IOU,
                max_det=1,
                verbose=False,
            )
        except Exception as exc:
            print(
                f"[YOLO] Tracker no disponible, usando predict: {exc}",
                flush=True,
            )

            results = self.model.predict(
                source=frame,
                imgsz=YOLO_IMAGE_SIZE,
                conf=POSE_DETECTION_CONFIDENCE,
                iou=POSE_IOU,
                max_det=1,
                verbose=False,
            )

        if not results:
            return None

        result = results[0]

        if (
            result.keypoints is None
            or len(result.keypoints.xy) == 0
        ):
            return None

        index = self._best_person_index(result)
        points = result.keypoints.xy[index].cpu().numpy()

        if result.keypoints.conf is not None:
            confidences = (
                result.keypoints.conf[index]
                .cpu()
                .numpy()
            )
        else:
            confidences = [1.0] * len(points)

        keypoints = {}

        for i, name in enumerate(KEYPOINT_NAMES):
            if i >= len(points):
                continue

            keypoints[name] = {
                "x": float(points[i][0]),
                "y": float(points[i][1]),
                "confidence": float(confidences[i]),
            }

        return keypoints

    @staticmethod
    def _best_person_index(result):
        if (
            result.boxes is None
            or len(result.boxes.conf) == 0
        ):
            return 0

        confidences = (
            result.boxes.conf
            .cpu()
            .numpy()
        )
        return int(confidences.argmax())
