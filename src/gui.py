import cv2
import numpy as np

from PySide6.QtCore import (
    Qt,
    QTimer,
)

from PySide6.QtGui import (
    QImage,
    QPixmap,
)

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
)

from skeleton import (
    SKELETON_CONNECTIONS,
)


class MocapGUI(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Live Mocap Diagnostic"
        )

        self.resize(
            1500,
            850,
        )

        self.last_camera = None
        self.last_keypoints = None

        self._build_ui()

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self):

        main = QHBoxLayout(self)

        # ----------------------------------------------------
        # IZQUIERDA
        # ----------------------------------------------------

        left_box = QVBoxLayout()

        self.camera_label = QLabel(
            "CAMERA"
        )

        self.camera_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.camera_label.setMinimumSize(
            700,
            500,
        )

        self.camera_label.setStyleSheet(
            "background:#111;"
            "color:white;"
        )

        left_box.addWidget(
            self.camera_label
        )

        self.state_label = QLabel(
            "IDLE"
        )

        self.state_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.state_label.setStyleSheet(
            "font-size:20px;"
            "font-weight:bold;"
        )

        left_box.addWidget(
            self.state_label
        )

        buttons = QHBoxLayout()

        self.calibrate_button = QPushButton(
            "C - CALIBRAR"
        )

        self.record_button = QPushButton(
            "R - REINICIAR"
        )

        self.quit_button = QPushButton(
            "Q - SALIR"
        )

        buttons.addWidget(
            self.calibrate_button
        )

        buttons.addWidget(
            self.record_button
        )

        buttons.addWidget(
            self.quit_button
        )

        left_box.addLayout(
            buttons
        )

        main.addLayout(
            left_box,
            2,
        )

        # ----------------------------------------------------
        # DERECHA
        # ----------------------------------------------------

        right_box = QVBoxLayout()

        skeleton_group = QGroupBox(
            "YOLO SKELETON"
        )

        skeleton_layout = QVBoxLayout(
            skeleton_group
        )

        self.skeleton_label = QLabel()

        self.skeleton_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.skeleton_label.setMinimumSize(
            500,
            500,
        )

        self.skeleton_label.setStyleSheet(
            "background:#080808;"
        )

        skeleton_layout.addWidget(
            self.skeleton_label
        )

        right_box.addWidget(
            skeleton_group
        )

        # ----------------------------------------------------
        # MÉTRICAS
        # ----------------------------------------------------

        metrics = QGridLayout()

        self.labels = {}

        names = [
            "Camera FPS",
            "YOLO FPS",
            "Recording FPS",
            "Recorded Frames",
            "Visibility",
            "Body Scale",
            "Body Center",
            "Left Elbow",
            "Right Elbow",
            "Left Knee",
            "Right Knee",
        ]

        for row, name in enumerate(names):

            title = QLabel(
                name
            )

            value = QLabel(
                "-"
            )

            value.setStyleSheet(
                "font-weight:bold;"
            )

            metrics.addWidget(
                title,
                row,
                0,
            )

            metrics.addWidget(
                value,
                row,
                1,
            )

            self.labels[name] = value

        right_box.addLayout(
            metrics
        )

        main.addLayout(
            right_box,
            1,
        )

        # ----------------------------------------------------
        # TIMER
        # ----------------------------------------------------

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self._refresh
        )

        self.timer.start(15)

        # ----------------------------------------------------
        # BOTONES
        # ----------------------------------------------------

        self.calibrate_button.clicked.connect(
            self._calibrate
        )

        self.record_button.clicked.connect(
            self._reset
        )

        self.quit_button.clicked.connect(
            self.close
        )

    # ========================================================
    # KEYBOARD
    # ========================================================

    def keyPressEvent(self, event):

        key = event.key()

        if key == Qt.Key.Key_C:

            self._calibrate()

        elif key == Qt.Key.Key_R:

            self._reset()

        elif key == Qt.Key.Key_Q:

            self.close()

        else:

            super().keyPressEvent(event)

    # ========================================================
    # API
    # ========================================================

    def set_camera(
        self,
        frame,
        keypoints=None,
    ):

        self.last_camera = frame
        self.last_keypoints = keypoints

        self._show_camera(
            frame,
            keypoints,
        )

    def set_state(
        self,
        state,
    ):

        self.state_label.setText(
            str(state)
        )

    def update_metrics(
        self,
        metrics,
    ):

        if metrics is None:
            metrics = {}

        self.labels[
            "Camera FPS"
        ].setText(
            f"{metrics.get('camera_fps', 0):.1f}"
        )

        self.labels[
            "YOLO FPS"
        ].setText(
            f"{metrics.get('yolo_fps', 0):.1f}"
        )

        self.labels[
            "Recording FPS"
        ].setText(
            "10.0"
        )

        self.labels[
            "Recorded Frames"
        ].setText(
            str(
                metrics.get(
                    "recorded_frames",
                    0,
                )
            )
        )

        self.labels[
            "Visibility"
        ].setText(
            f"{metrics.get('visibility', 0) * 100:.1f}%"
        )

        self.labels[
            "Body Scale"
        ].setText(
            f"{metrics.get('body_scale', 0):.1f}"
        )

        center = metrics.get(
            "body_center"
        )

        if center is not None and len(center) >= 2:

            self.labels[
                "Body Center"
            ].setText(
                f"{center[0]:.1f}, "
                f"{center[1]:.1f}"
            )

        else:

            self.labels[
                "Body Center"
            ].setText(
                "-"
            )

        for key, label in [
            (
                "left_elbow_angle",
                "Left Elbow",
            ),
            (
                "right_elbow_angle",
                "Right Elbow",
            ),
            (
                "left_knee_angle",
                "Left Knee",
            ),
            (
                "right_knee_angle",
                "Right Knee",
            ),
        ]:

            value = metrics.get(
                key
            )

            if value is not None:

                self.labels[
                    label
                ].setText(
                    f"{value:.1f}°"
                )

            else:

                self.labels[
                    label
                ].setText(
                    "-"
                )

    # ========================================================
    # CAMERA
    # ========================================================

    def _show_camera(
        self,
        frame,
        keypoints,
    ):

        if frame is None:

            self.camera_label.clear()

            self.camera_label.setText(
                "CAMERA"
            )

            self._draw_skeleton(
                keypoints
            )

            return

        try:

            image = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

        except cv2.error:

            return

        h, w, ch = image.shape

        qimage = QImage(
            image.data,
            w,
            h,
            ch * w,
            QImage.Format.Format_RGB888,
        )

        qimage = qimage.copy()

        pixmap = QPixmap.fromImage(
            qimage
        )

        pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.camera_label.setPixmap(
            pixmap
        )

        self._draw_skeleton(
            keypoints
        )

    # ========================================================
    # SKELETON
    # ========================================================

    def _draw_skeleton(
        self,
        keypoints,
    ):

        width = 800
        height = 800

        image = np.ones(
            (
                height,
                width,
                3,
            ),
            dtype=np.uint8,
        ) * 255

        if keypoints:

            xs = [
                p["x"]
                for p in keypoints.values()
                if p.get(
                    "confidence",
                    0
                ) >= 0.25
            ]

            ys = [
                p["y"]
                for p in keypoints.values()
                if p.get(
                    "confidence",
                    0
                ) >= 0.25
            ]

            if xs and ys:

                min_x = min(xs)
                max_x = max(xs)

                min_y = min(ys)
                max_y = max(ys)

                body_width = max(
                    max_x - min_x,
                    1,
                )

                body_height = max(
                    max_y - min_y,
                    1,
                )

                scale = min(
                    650 / body_width,
                    650 / body_height,
                )

                center_x = (
                    min_x + max_x
                ) / 2

                center_y = (
                    min_y + max_y
                ) / 2

                def convert(point):

                    x = (
                        (
                            point["x"]
                            - center_x
                        )
                        * scale
                        + width / 2
                    )

                    y = (
                        (
                            point["y"]
                            - center_y
                        )
                        * scale
                        + height / 2
                    )

                    return (
                        int(x),
                        int(y),
                    )

                for a, b in SKELETON_CONNECTIONS:

                    pa = keypoints.get(a)
                    pb = keypoints.get(b)

                    if not pa or not pb:
                        continue

                    if (
                        pa.get(
                            "confidence",
                            0
                        ) < 0.25
                        or pb.get(
                            "confidence",
                            0
                        ) < 0.25
                    ):
                        continue

                    cv2.line(
                        image,
                        convert(pa),
                        convert(pb),
                        (0, 0, 0),
                        4,
                    )

                for point in keypoints.values():

                    if point.get(
                        "confidence",
                        0
                    ) < 0.25:

                        continue

                    cv2.circle(
                        image,
                        convert(point),
                        8,
                        (0, 0, 255),
                        -1,
                    )

        image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB,
        )

        h, w, ch = image.shape

        qimage = QImage(
            image.data,
            w,
            h,
            ch * w,
            QImage.Format.Format_RGB888,
        )

        qimage = qimage.copy()

        pixmap = QPixmap.fromImage(
            qimage
        )

        pixmap = pixmap.scaled(
            self.skeleton_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.skeleton_label.setPixmap(
            pixmap
        )

    # ========================================================
    # EVENTS
    # ========================================================

    def _calibrate(self):

        if hasattr(
            self,
            "on_calibrate",
        ):

            self.on_calibrate()

    def _reset(self):

        if hasattr(
            self,
            "on_reset",
        ):

            self.on_reset()

    def _refresh(self):

        pass