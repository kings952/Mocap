import os

import cv2
import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QFrame,
)

from config import LIVE_PREVIEW_IMAGE
from skeleton import SKELETON_CONNECTIONS


class MocapGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MOCAP  •  Live Capture")
        self.resize(1760, 960)
        self.setMinimumSize(1280, 780)

        self.last_camera = None
        self.last_keypoints = None
        self.last_live_preview = None

        self._build_ui()
        self._start_preview_timer()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                background: #090d12;
                color: #e8edf2;
                font-family: Segoe UI;
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #26313b;
                border-radius: 12px;
                margin-top: 12px;
                padding: 10px;
                background: #10161d;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 7px;
                color: #91d8ff;
            }
            QLabel#title {
                font-size: 22pt;
                font-weight: 800;
                color: #f5f7fa;
            }
            QLabel#subtitle {
                color: #8793a0;
                font-size: 10pt;
            }
            QLabel#state {
                font-size: 17pt;
                font-weight: 800;
                padding: 10px 16px;
                border-radius: 10px;
                background: #17212b;
            }
            QLabel#status {
                padding: 10px;
                border-radius: 9px;
                background: #111a22;
                color: #c2ced8;
            }
            QLabel#metricValue {
                font-weight: 700;
                color: #f5f7fa;
            }
            QLabel#liveHint {
                color: #91d8ff;
                font-weight: 700;
                padding: 3px 4px;
            }
            QPushButton {
                min-height: 40px;
                padding: 0 15px;
                border: 1px solid #31404d;
                border-radius: 9px;
                background: #17212b;
                color: #f5f7fa;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #20303d;
            }
            QPushButton:pressed {
                background: #10171e;
            }
            QFrame#preview {
                background: #05080b;
                border: 1px solid #26313b;
                border-radius: 8px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel("MOCAP  •  LIVE")
        title.setObjectName("title")

        subtitle = QLabel(
            "YOLO Pose + tracking  →  calibración normalizada  →  IK Blender"
        )
        subtitle.setObjectName("subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.state_label = QLabel("INICIANDO")
        self.state_label.setObjectName("state")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setMinimumWidth(220)

        header.addLayout(title_box, 1)
        header.addWidget(self.state_label)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(10)

        self.camera_label = self._panel()
        self.skeleton_label = self._panel()
        self.live_label = self._panel()

        content.addWidget(
            self._group("01  CÁMARA / CALIBRACIÓN", self.camera_label),
            4,
        )
        content.addWidget(
            self._group("02  YOLO / ESQUELETO", self.skeleton_label),
            2,
        )

        live_group = self._group("03  MODELO BLENDER • LIVE", self.live_label)
        live_group.setMinimumWidth(440)
        content.addWidget(live_group, 4)

        root.addLayout(content, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        status_box = QVBoxLayout()
        status_title = QLabel("CONEXIÓN LIVE")
        status_title.setStyleSheet("font-weight:800;color:#91d8ff;")

        self.live_status = QLabel("Preparando Blender...")
        self.live_status.setObjectName("status")
        self.live_status.setWordWrap(True)

        self.live_hint = QLabel(
            "El panel 03 es el modelo real del .blend temporal, no un esqueleto 2D."
        )
        self.live_hint.setObjectName("liveHint")
        self.live_hint.setWordWrap(True)

        status_box.addWidget(status_title)
        status_box.addWidget(self.live_status)
        status_box.addWidget(self.live_hint)

        controls = QHBoxLayout()
        self.calibrate_button = QPushButton("C  •  CALIBRAR")
        self.reset_button = QPushButton("R  •  REINICIAR")
        self.quit_button = QPushButton("Q  •  SALIR")

        controls.addWidget(self.calibrate_button)
        controls.addWidget(self.reset_button)
        controls.addWidget(self.quit_button)
        status_box.addLayout(controls)

        metrics_group = QGroupBox("MÉTRICAS")
        metrics = QGridLayout(metrics_group)
        metrics.setHorizontalSpacing(18)
        metrics.setVerticalSpacing(4)

        names = [
            "Model",
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

        self.labels = {}

        for row, name in enumerate(names):
            title = QLabel(name)
            value = QLabel("-")
            value.setObjectName("metricValue")
            metrics.addWidget(title, row, 0)
            metrics.addWidget(value, row, 1)
            self.labels[name] = value

        bottom.addLayout(status_box, 2)
        bottom.addWidget(metrics_group, 2)

        root.addLayout(bottom)

        self.calibrate_button.clicked.connect(self._calibrate)
        self.reset_button.clicked.connect(self._reset)
        self.quit_button.clicked.connect(self.close)

    def _start_preview_timer(self):
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._refresh_live_preview)
        self.preview_timer.start(50)

    def _group(self, title, widget):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(7, 7, 7, 7)
        layout.setSpacing(5)
        layout.addWidget(widget)
        return group

    def _panel(self):
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(300, 300)
        label.setFrameStyle(QFrame.Shape.NoFrame)
        label.setStyleSheet(
            "background:#05080b;border:1px solid #202a33;border-radius:8px;"
        )
        return label

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_C:
            self._calibrate()
        elif event.key() == Qt.Key.Key_R:
            self._reset()
        elif event.key() == Qt.Key.Key_Q:
            self.close()
        else:
            super().keyPressEvent(event)

    def set_camera(self, frame, keypoints=None):
        self.last_camera = frame
        self.last_keypoints = keypoints
        self._show_image(self.camera_label, frame)
        self._draw_skeleton(keypoints)

    def set_state(self, state):
        text = str(state)
        self.state_label.setText(text)

        if "ERROR" in text or "DESCONECT" in text:
            self.state_label.setStyleSheet(
                "font-size:17pt;font-weight:800;padding:10px;border-radius:10px;"
                "background:#3a171b;color:#ff9da5;"
            )
        elif "CALIBR" in text:
            self.state_label.setStyleSheet(
                "font-size:17pt;font-weight:800;padding:10px;border-radius:10px;"
                "background:#302718;color:#ffd58a;"
            )
        else:
            self.state_label.setStyleSheet(
                "font-size:17pt;font-weight:800;padding:10px;border-radius:10px;"
                "background:#143025;color:#8ff0b8;"
            )

    def update_metrics(self, metrics):
        metrics = metrics or {}

        self.labels["Model"].setText(str(metrics.get("model_name", "-")))
        self.labels["Camera FPS"].setText(
            f"{metrics.get('camera_fps', 0):.1f}"
        )
        self.labels["YOLO FPS"].setText(
            f"{metrics.get('yolo_fps', 0):.1f}"
        )
        self.labels["Recording FPS"].setText("10.0")
        self.labels["Recorded Frames"].setText(
            str(metrics.get("recorded_frames", 0))
        )
        self.labels["Visibility"].setText(
            f"{metrics.get('visibility', 0) * 100:.1f}%"
        )
        self.labels["Body Scale"].setText(
            f"{metrics.get('body_scale', 0):.1f}px"
        )

        center = metrics.get("body_center")
        self.labels["Body Center"].setText(
            f"{center[0]:.1f}, {center[1]:.1f}"
            if center else "-"
        )

        for key, label in [
            ("left_elbow_angle", "Left Elbow"),
            ("right_elbow_angle", "Right Elbow"),
            ("left_knee_angle", "Left Knee"),
            ("right_knee_angle", "Right Knee"),
        ]:
            value = metrics.get(key)
            self.labels[label].setText(
                f"{value:.1f}°" if value is not None else "-"
            )

        if metrics.get("live_connected"):
            self.live_status.setText(
                "● BLENDER CONECTADO\n"
                "LIVE activo sobre una copia temporal del .blend.\n"
                "Bone permanece estático; hip mueve Genesis."
            )
        else:
            self.live_status.setText(
                "○ BLENDER DESCONECTADO\n"
                + str(
                    metrics.get(
                        "live_error",
                        "Iniciando Blender...",
                    )
                )
            )

    def _refresh_live_preview(self):
        path = str(LIVE_PREVIEW_IMAGE)

        if not os.path.exists(path):
            return

        try:
            image = cv2.imread(path, cv2.IMREAD_COLOR)

            if image is None:
                return

            self.last_live_preview = image
            self._show_image(self.live_label, image)

        except Exception:
            if self.last_live_preview is not None:
                self._show_image(
                    self.live_label,
                    self.last_live_preview,
                )

    def _show_image(self, label, frame):
        if frame is None:
            return

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = image.shape

        qimage = QImage(
            image.data,
            w,
            h,
            ch * w,
            QImage.Format.Format_RGB888,
        ).copy()

        pixmap = QPixmap.fromImage(qimage).scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        label.setPixmap(pixmap)

    def _draw_skeleton(self, keypoints):
        image = np.zeros((720, 640, 3), dtype=np.uint8)

        if keypoints:
            visible = [
                p for p in keypoints.values()
                if p.get("confidence", 0.0) >= 0.25
            ]

            if visible:
                xs = [p["x"] for p in visible]
                ys = [p["y"] for p in visible]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)

                scale = min(
                    560 / max(max_x - min_x, 1),
                    620 / max(max_y - min_y, 1),
                )
                cx = (min_x + max_x) / 2
                cy = (min_y + max_y) / 2

                def convert(point):
                    return (
                        int((point["x"] - cx) * scale + 320),
                        int((point["y"] - cy) * scale + 360),
                    )

                for a, b in SKELETON_CONNECTIONS:
                    pa = keypoints.get(a)
                    pb = keypoints.get(b)

                    if not pa or not pb:
                        continue
                    if pa.get("confidence", 0) < 0.25:
                        continue
                    if pb.get("confidence", 0) < 0.25:
                        continue

                    cv2.line(
                        image,
                        convert(pa),
                        convert(pb),
                        (80, 190, 255),
                        4,
                        cv2.LINE_AA,
                    )

                for point in visible:
                    cv2.circle(
                        image,
                        convert(point),
                        7,
                        (240, 245, 250),
                        -1,
                        cv2.LINE_AA,
                    )

        self._show_image(self.skeleton_label, image)

    def _calibrate(self):
        if hasattr(self, "on_calibrate"):
            self.on_calibrate()

    def _reset(self):
        if hasattr(self, "on_reset"):
            self.on_reset()
