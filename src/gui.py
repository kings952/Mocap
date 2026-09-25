import cv2
import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox

from skeleton import SKELETON_CONNECTIONS


class MocapGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Mocap")
        self.resize(1800, 900)
        self.setMinimumSize(1200, 700)
        self.last_camera = None
        self.last_keypoints = None
        self._build_ui()

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(8)

        self.camera_label = self._panel()
        self.skeleton_label = self._panel()
        self.live_label = self._panel()

        main.addWidget(self._group("1. CAMARA / CALIBRACION", self.camera_label), 4)
        main.addWidget(self._group("2. YOLO / ESQUELETO", self.skeleton_label), 3)
        main.addWidget(self._group("3. LIVE BLENDER", self.live_label), 2)

        side = QVBoxLayout()
        self.state_label = QLabel("IDLE")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("font-size:18px;font-weight:bold;")

        self.live_status = QLabel("Blender: esperando...")
        self.live_status.setWordWrap(True)

        buttons = QHBoxLayout()
        self.calibrate_button = QPushButton("C - CALIBRAR")
        self.reset_button = QPushButton("R - REINICIAR")
        self.quit_button = QPushButton("Q - SALIR")
        buttons.addWidget(self.calibrate_button)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.quit_button)

        side.addWidget(self.state_label)
        side.addWidget(self.live_status)
        side.addLayout(buttons)

        metrics = QGridLayout()
        group = QGroupBox("METRICAS")
        group.setLayout(metrics)
        self.labels = {}
        names = ["Camera FPS","YOLO FPS","Recording FPS","Recorded Frames","Visibility","Body Scale","Body Center","Left Elbow","Right Elbow","Left Knee","Right Knee"]

        for row, name in enumerate(names):
            title = QLabel(name)
            value = QLabel("-")
            value.setStyleSheet("font-weight:bold;")
            metrics.addWidget(title, row, 0)
            metrics.addWidget(value, row, 1)
            self.labels[name] = value

        side.addWidget(group)
        main.addLayout(side, 2)

        self.calibrate_button.clicked.connect(self._calibrate)
        self.reset_button.clicked.connect(self._reset)
        self.quit_button.clicked.connect(self.close)

    def _group(self, title, widget):
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.addWidget(widget)
        return group

    def _panel(self):
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(250, 250)
        label.setStyleSheet("background:#111;color:white;")
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
        self.state_label.setText(str(state))

    def update_metrics(self, metrics):
        metrics = metrics or {}
        self.labels["Camera FPS"].setText(f"{metrics.get('camera_fps', 0):.1f}")
        self.labels["YOLO FPS"].setText(f"{metrics.get('yolo_fps', 0):.1f}")
        self.labels["Recording FPS"].setText("10.0")
        self.labels["Recorded Frames"].setText(str(metrics.get("recorded_frames", 0)))
        self.labels["Visibility"].setText(f"{metrics.get('visibility', 0) * 100:.1f}%")
        self.labels["Body Scale"].setText(f"{metrics.get('body_scale', 0):.1f}")

        center = metrics.get("body_center")
        self.labels["Body Center"].setText(f"{center[0]:.1f}, {center[1]:.1f}" if center else "-")

        for key, label in [
            ("left_elbow_angle", "Left Elbow"),
            ("right_elbow_angle", "Right Elbow"),
            ("left_knee_angle", "Left Knee"),
            ("right_knee_angle", "Right Knee"),
        ]:
            value = metrics.get(key)
            self.labels[label].setText(f"{value:.1f}°" if value is not None else "-")

        if metrics.get("live_connected"):
            self.live_status.setText(
                "Blender LIVE: CONECTADO\n"
                "Modelo actualizado en tiempo real.\n"
                "Piernas: solo deteccion real."
            )
        else:
            self.live_status.setText(
                "Blender LIVE: DESCONECTADO\n"
                + str(metrics.get("live_error", "Iniciando Blender..."))
            )

        self._draw_live_panel(metrics)

    def _draw_live_panel(self, metrics):
        image = np.zeros((600, 500, 3), dtype=np.uint8)
        cv2.putText(image, "BLENDER LIVE", (35, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "Ventana 3: Blender", (35, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "Socket: " + ("OK" if metrics.get("live_connected") else "WAIT"), (35, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "Mueve torso y brazos", (35, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, "Las piernas no se inventan", (35, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        self._show_image(self.live_label, image)

    def _show_image(self, label, frame):
        if frame is None:
            label.clear()
            return
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = image.shape
        qimage = QImage(image.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage).scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(pixmap)

    def _draw_skeleton(self, keypoints):
        image = np.zeros((800, 700, 3), dtype=np.uint8)

        if keypoints:
            visible = [p for p in keypoints.values() if p.get("confidence", 0.0) >= 0.25]
            if visible:
                xs = [p["x"] for p in visible]
                ys = [p["y"] for p in visible]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                scale = min(620 / max(max_x - min_x, 1), 720 / max(max_y - min_y, 1))
                cx = (min_x + max_x) / 2
                cy = (min_y + max_y) / 2

                def convert(point):
                    return int((point["x"] - cx) * scale + 350), int((point["y"] - cy) * scale + 400)

                for a, b in SKELETON_CONNECTIONS:
                    pa, pb = keypoints.get(a), keypoints.get(b)
                    if not pa or not pb:
                        continue
                    if pa.get("confidence", 0) < 0.25 or pb.get("confidence", 0) < 0.25:
                        continue
                    cv2.line(image, convert(pa), convert(pb), (0, 220, 255), 4)

                for point in visible:
                    cv2.circle(image, convert(point), 7, (255, 255, 255), -1)

        self._show_image(self.skeleton_label, image)

    def _calibrate(self):
        if hasattr(self, "on_calibrate"):
            self.on_calibrate()

    def _reset(self):
        if hasattr(self, "on_reset"):
            self.on_reset()
