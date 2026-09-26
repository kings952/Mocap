import cv2

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
)


class Camera:

    def __init__(self):
        self.cap = cv2.VideoCapture(
            CAMERA_INDEX,
            cv2.CAP_DSHOW,
        )

        # Evita que OpenCV acumule frames viejos mientras YOLO procesa.
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # MJPG reduce el ancho de banda USB en muchas webcams.
        try:
            self.cap.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*"MJPG"),
            )
        except Exception:
            pass

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            CAMERA_WIDTH,
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            CAMERA_HEIGHT,
        )

        if not self.cap.isOpened():
            raise RuntimeError(
                "No se pudo abrir la cámara."
            )

    def read(self):
        ok, frame = self.cap.read()

        if not ok:
            return None

        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
