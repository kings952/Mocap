from ultralytics import YOLO

from config import (
    MODEL_PATH,
    YOLO_IMAGE_SIZE,
)


class PoseDetector:

    def __init__(self):

        print(f"[YOLO] Cargando: {MODEL_PATH}")

        self.model = YOLO(str(MODEL_PATH))

    def detect(self, frame):

        results = self.model.predict(
            source=frame,
            imgsz=YOLO_IMAGE_SIZE,
            verbose=False,
            conf=0.25,
        )

        if not results:
            return None

        result = results[0]

        if result.keypoints is None:
            return None

        if len(result.keypoints.xy) == 0:
            return None

        # Persona con mayor confianza.
        index = 0

        if result.boxes is not None:
            if len(result.boxes.conf) > 0:
                confidence = result.boxes.conf.cpu().numpy()

                index = int(confidence.argmax())

        points = result.keypoints.xy[index].cpu().numpy()

        if result.keypoints.conf is not None:
            confidences = (
                result.keypoints.conf[index]
                .cpu()
                .numpy()
            )
        else:
            confidences = [1.0] * len(points)

        from skeleton import KEYPOINT_NAMES

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