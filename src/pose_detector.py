from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO

from config import (
    FALLBACK_MODEL_NAME, FALLBACK_MODEL_PATH,
    MODEL_PATH, MODEL_NAME,
    POSE_DETECTION_CONFIDENCE, POSE_IOU,
    YOLO_DEVICE, YOLO_HALF, YOLO_IMAGE_SIZE,
    YOLO_MAX_DET, YOLO_TRACKER,
)
from skeleton import KEYPOINT_NAMES


class PoseDetector:
    def __init__(self):
        self.device = YOLO_DEVICE if torch.cuda.is_available() else "cpu"
        self.half = bool(YOLO_HALF and self.device != "cpu")
        self.model_path = MODEL_PATH
        self.model_name = MODEL_NAME
        self.tracking_ready = True
        self.track_id = None

        print(
            f"[YOLO] Modelo: {MODEL_NAME} | device={self.device} | half={self.half}",
            flush=True,
        )
        self.model = self._load_model()

        try:
            self.model.to(self.device)
        except Exception:
            pass
        try:
            self.model.fuse()
        except Exception:
            pass
        self._warmup()

    def _load_model(self):
        candidates = []
        candidates.append((MODEL_PATH if Path(MODEL_PATH).exists() else MODEL_NAME, MODEL_NAME))
        candidates.append((FALLBACK_MODEL_PATH if Path(FALLBACK_MODEL_PATH).exists() else FALLBACK_MODEL_NAME, FALLBACK_MODEL_NAME))

        last_error = None
        for source, name in candidates:
            try:
                model = YOLO(str(source))
                self.model_path = Path(source) if Path(str(source)).exists() else Path(str(source))
                self.model_name = name
                print(f"[YOLO] Cargado: {name}", flush=True)
                return model
            except Exception as exc:
                last_error = exc
                print(f"[YOLO] Fallo cargando {name}: {exc}", flush=True)

        raise RuntimeError(
            "No se pudo cargar YOLO26s-pose ni YOLO26n-pose."
        ) from last_error

    def _warmup(self):
        try:
            dummy = np.zeros(
                (YOLO_IMAGE_SIZE, YOLO_IMAGE_SIZE, 3),
                dtype=np.uint8,
            )
            self.model.predict(
                source=dummy,
                imgsz=YOLO_IMAGE_SIZE,
                conf=POSE_DETECTION_CONFIDENCE,
                device=self.device,
                half=self.half,
                max_det=YOLO_MAX_DET,
                verbose=False,
            )
            print("[YOLO] Warm-up completado.", flush=True)
        except Exception as exc:
            print(f"[YOLO] Warm-up omitido: {exc}", flush=True)

    def detect(self, frame):
        try:
            results = self.model.track(
                source=frame,
                persist=True,
                tracker=YOLO_TRACKER,
                imgsz=YOLO_IMAGE_SIZE,
                conf=POSE_DETECTION_CONFIDENCE,
                iou=POSE_IOU,
                max_det=YOLO_MAX_DET,
                device=self.device,
                half=self.half,
                verbose=False,
            )
        except Exception as exc:
            self.tracking_ready = False
            print(f"[YOLO] Track fallo; usando predict: {exc}", flush=True)
            results = self.model.predict(
                source=frame,
                imgsz=YOLO_IMAGE_SIZE,
                conf=POSE_DETECTION_CONFIDENCE,
                iou=POSE_IOU,
                max_det=YOLO_MAX_DET,
                device=self.device,
                half=self.half,
                verbose=False,
            )

        if not results:
            self.track_id = None
            return None

        result = results[0]
        if result.keypoints is None or len(result.keypoints.xy) == 0:
            self.track_id = None
            return None

        index = self._best_person_index(result)
        if result.boxes is not None and getattr(result.boxes, "id", None) is not None:
            ids = result.boxes.id
            if len(ids) > index:
                self.track_id = int(ids[index].item())

        points = result.keypoints.xy[index].cpu().numpy()
        if result.keypoints.conf is not None:
            confidences = result.keypoints.conf[index].cpu().numpy()
        else:
            confidences = np.ones(len(points), dtype=np.float32)

        return {
            name: {
                "x": float(points[i][0]),
                "y": float(points[i][1]),
                "confidence": float(confidences[i]),
            }
            for i, name in enumerate(KEYPOINT_NAMES)
            if i < len(points)
        }

    @staticmethod
    def _best_person_index(result):
        if result.boxes is None or len(result.boxes.conf) == 0:
            return 0
        return int(result.boxes.conf.cpu().numpy().argmax())
