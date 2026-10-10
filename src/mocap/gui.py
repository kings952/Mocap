"""GUI de pruebas MOCAP: entradas, reconocimiento, calibración, captura y exportación."""
from __future__ import annotations
from pathlib import Path
import subprocess
import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QVBoxLayout, QWidget, QMessageBox, QGroupBox, QGridLayout, QProgressBar,
    QSplitter, QListWidget, QFrame
)
from .blender import BlenderBridge, BlenderConfig
from .camera import CameraCapture, CameraConfig, draw_pose
from .keyframes import KeyframeStore
from .motion import CaptureState, MotionProcessor
from .pose import PoseDetector

class MocapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOCAP Studio | Genesis + Blender 4.4")
        self.resize(1280, 820); self.setMinimumSize(980, 650)
        self.blend: Path | None = None; self.output_blend: Path | None = None
        self.store = KeyframeStore(); self.processor = MotionProcessor()
        self.detector = PoseDetector(model_complexity=0)
        self.camera: CameraCapture | None = None; self.frame = 0; self.last_frame = None
        self.bridge = BlenderBridge()
        self.timer = QTimer(self); self.timer.timeout.connect(self._camera_tick)
        self._build_ui()

    def _build_ui(self):
        root = QWidget(); main = QVBoxLayout(root); main.setContentsMargins(16,16,16,16); main.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("MOCAP STUDIO"); title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        subtitle = QLabel("Captura de movimiento · Genesis · Blender 4.4")
        header.addWidget(title); header.addStretch(); header.addWidget(subtitle); main.addLayout(header)
        files = QGroupBox("PROYECTO"); grid = QGridLayout(files)
        self.blend_label = QLabel("Genesis: no seleccionado"); self.blend_label.setWordWrap(True)
        self.output_label = QLabel("Salida animada: todavía no guardada"); self.output_label.setWordWrap(True)
        load_blend = self._button("Cargar modelo .blend", self.load_blend)
        grid.addWidget(load_blend,0,0); grid.addWidget(self.blend_label,0,1)
        grid.addWidget(self.output_label,1,1)
        main.addWidget(files)
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget(); left_layout = QVBoxLayout(left)
        actions = QGroupBox("ENTRADA Y CONTROL"); actions_grid = QGridLayout(actions)
        buttons = [
            ("Imagen", self.load_image), ("Vídeo", self.load_video),
            ("Iniciar cámara", self.start_camera), ("Detener cámara", self.stop_camera),
            ("Calibrar T-pose", self.calibrate), ("Empezar / detener grabación", self.toggle_record),
            ("Reset", self.reset), ("Guardar animación", self.save),
            ("Abrir visor Blender", self.open_blender),
        ]
        for i,(label,slot) in enumerate(buttons):
            actions_grid.addWidget(self._button(label,slot),i//2,i%2)
        left_layout.addWidget(actions)
        state_box = QGroupBox("ESTADO DE CAPTURA"); state_layout = QVBoxLayout(state_box)
        self.state_label = QLabel("IDLE · Esperando entrada"); self.state_label.setWordWrap(True)
        self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0)
        self.metrics = QLabel("Frames: 0 | Poses detectadas: 0 | Keyframes: 0")
        state_layout.addWidget(self.state_label); state_layout.addWidget(self.progress); state_layout.addWidget(self.metrics)
        left_layout.addWidget(state_box)
        kf_box = QGroupBox("KEYFRAMES A EXPORTAR"); kf_layout = QVBoxLayout(kf_box)
        self.kf_list = QListWidget(); kf_layout.addWidget(self.kf_list)
        left_layout.addWidget(kf_box,1)
        split.addWidget(left)
        right = QWidget(); right_layout = QVBoxLayout(right)
        viewer_box = QGroupBox("VISOR DE RECONOCIMIENTO · ESQUELETO"); viewer_layout = QVBoxLayout(viewer_box)
        self.viewer = QLabel("Carga una imagen/vídeo o inicia la cámara.\nAquí aparecerá la pose detectada.")
        self.viewer.setAlignment(Qt.AlignmentFlag.AlignCenter); self.viewer.setMinimumSize(420,420)
        self.viewer.setFrameShape(QFrame.Shape.StyledPanel); self.viewer.setWordWrap(True)
        viewer_layout.addWidget(self.viewer,1); right_layout.addWidget(viewer_box,1)
        model_box = QGroupBox("VISOR DEL MODELO GENESIS"); model_layout = QVBoxLayout(model_box)
        self.model_status = QLabel("La vista 3D se abre en Blender mediante «Abrir visor Blender».")
        self.model_status.setWordWrap(True); model_layout.addWidget(self.model_status)
        right_layout.addWidget(model_box)
        split.addWidget(right); split.setSizes([420,800]); main.addWidget(split,1)
        self.statusBar().showMessage("Listo · carga el .blend y elige una entrada")
        self.setCentralWidget(root)

    def _button(self,text,slot):
        b=QPushButton(text); b.setMinimumHeight(36); b.clicked.connect(slot); return b

    def load_blend(self):
        path,_=QFileDialog.getOpenFileName(self,"Seleccionar Genesis .blend","","Blender (*.blend)")
        if path:
            self.blend=Path(path).resolve(); self.blend_label.setText(f"Genesis: {self.blend}")
            self.model_status.setText("Modelo cargado como origen. Guarda una copia animada y abre esa copia para inspeccionar el movimiento.")
            self._status("Archivo Genesis seleccionado.")

    def load_image(self):
        path,_=QFileDialog.getOpenFileName(self,"Seleccionar imagen","","Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not path:return
        frame=cv2.imread(path)
        if frame is None: self._error("No se pudo leer la imagen."); return
        pose=self.detector.detect(frame,frame_index=1); self.store.clear(); self.processor.reset()
        if pose.detected:self.store.add(pose,frame=1,score=1.0,reason="imagen")
        self.last_frame=draw_pose(frame,pose); self._show(self.last_frame)
        self._refresh_metrics(1,int(pose.detected))
        self._status(f"Imagen: {len(pose.landmarks)} landmarks. La pose se guarda en frame 1.")
        if not pose.detected: self._warning("No se detectó una persona. Prueba una imagen con cuerpo completo y buena iluminación.")
        self._refresh_keyframes()

    def load_video(self):
        path,_=QFileDialog.getOpenFileName(self,"Seleccionar vídeo","","Vídeos (*.mp4 *.avi *.mov *.mkv)")
        if not path:return
        cap=cv2.VideoCapture(path)
        if not cap.isOpened(): self._error("No se pudo abrir el vídeo."); return
        self.store.clear(); self.processor.reset(); self.processor.start_calibration()
        count=detected=0; preview=None
        try:
            while count<300:
                ok,frame=cap.read()
                if not ok:break
                pose=self.detector.detect(frame,frame_index=max(1,count+1))
                detected+=int(pose.detected); preview=draw_pose(frame,pose)
                if self.processor.state is CaptureState.CALIBRATING:
                    self.processor.add_calibration_sample(pose)
                    if self.processor.calibrated:self.processor.begin_recording()
                elif self.processor.state is CaptureState.RECORDING:
                    decision=self.processor.evaluate(pose,count+1)
                    if decision.accepted and decision.pose:
                        self.store.add(decision.pose,frame=max(1,count+1),score=decision.score,reason=decision.reason)
                count+=1
        finally: cap.release()
        if preview is not None:self.last_frame=preview; self._show(preview)
        self._refresh_metrics(count,detected); self._refresh_keyframes()
        self._status(f"Vídeo terminado: {count} frames, {detected} detecciones, {len(self.store)} keyframes.")
        if not self.store:self._warning("No se generaron keyframes. Usa un vídeo estable al inicio y con movimiento claro después de la calibración.")

    def start_camera(self):
        if self.camera:return
        try:
            self.camera=CameraCapture(CameraConfig()); self.camera.open()
        except Exception as exc:
            self.camera=None; self._error(f"No se pudo iniciar la cámara: {exc}"); return
        self.frame=0; self.timer.start(33); self._status("Cámara activa · pulsa «Calibrar T-pose» cuando estés en posición estable.")

    def _camera_tick(self):
        if not self.camera:return
        packet=self.camera.read(self.frame+1)
        if packet is None:return
        pose=self.detector.detect(packet.image_bgr,frame_index=self.frame+1)
        if self.processor.state is CaptureState.CALIBRATING:
            self.processor.add_calibration_sample(pose)
            state=f"CALIBRANDO · {self.processor.calibration_progress*100:.0f}%"
        elif self.processor.state is CaptureState.RECORDING:
            decision=self.processor.evaluate(pose,self.frame+1)
            if decision.accepted and decision.pose:
                self.store.add(decision.pose,frame=max(1,self.frame+1),score=decision.score,reason=decision.reason)
                self._refresh_keyframes()
            state=f"GRABANDO · score {decision.score:.3f}"
        else: state=self.processor.state.value.upper()
        self.last_frame=draw_pose(packet.image_bgr,pose); self._show(self.last_frame)
        self._refresh_metrics(self.frame+1,int(pose.detected)); self.state_label.setText(state)
        self.progress.setValue(int(self.processor.calibration_progress*100)); self.frame+=1

    def stop_camera(self):
        self.timer.stop()
        if self.camera:
            self.camera.close(); self.camera=None
        self._status("Cámara detenida.")

    def calibrate(self):
        self.processor.start_calibration(); self.store.clear(); self._refresh_keyframes()
        self.progress.setValue(0); self._status("CALIBRANDO · mantén una T-pose estable y visible.")

    def toggle_record(self):
        if self.processor.state is CaptureState.RECORDING:
            self.processor.state=CaptureState.READY; self._status("Grabación pausada.")
            return
        try:self.processor.begin_recording(); self._status("GRABANDO · mueve el cuerpo con cambios claros.")
        except RuntimeError as exc:self._warning(str(exc)+" Pulsa «Calibrar T-pose» primero.")

    def reset(self):
        self.processor.reset(); self.store.clear(); self.progress.setValue(0)
        self._refresh_keyframes(); self._refresh_metrics(0,0); self._status("Reset completado · IDLE.")

    def save(self):
        if not self.blend:self._warning("Primero carga el archivo Genesis .blend."); return
        if not self.store:self._warning("No hay keyframes. Procesa una imagen o graba movimiento antes de guardar."); return
        suggested=self.blend.with_name(self.blend.stem+"_MOCAP.blend")
        path,_=QFileDialog.getSaveFileName(self,"Guardar copia animada",str(suggested),"Blender (*.blend)")
        if not path:return
        output=Path(path).resolve()
        if output.suffix.lower()!=".blend":output=output.with_suffix(".blend")
        self._status("Exportando a Blender y verificando curvas de animación…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:result=self.bridge.apply(self.blend,self.store,output)
        finally:QApplication.restoreOverrideCursor()
        if result.ok:
            self.output_blend=output; self.output_label.setText(f"Salida animada: {output}")
            payload=(result.details or {}).get("payload",{}); anim=payload.get("animation",{})
            self.model_status.setText(f"Exportación verificada: {anim.get('fcurves','?')} curvas, {anim.get('key_points','?')} puntos. Abre el archivo para comprobar el movimiento.")
            self._status(result.message); QMessageBox.information(self,"Exportación completada",result.message)
        else:
            details=(result.details or {}).get("output","")
            self._error(result.message+(f"\n\nRegistro de Blender:\n{details[-2500:]}" if details else ""))

    def open_blender(self):
        target=self.output_blend or self.blend
        if not target or not target.is_file():self._warning("Carga primero un .blend o guarda una salida animada."); return
        exe=BlenderConfig().executable
        if not exe.is_file():self._error(f"No se encontró Blender: {exe}"); return
        try:subprocess.Popen([str(exe),str(target)],cwd=str(target.parent))
        except OSError as exc:self._error(f"No se pudo abrir Blender: {exc}")

    def _show(self,frame):
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB); h,w,_=rgb.shape
        q=QImage(rgb.data,w,h,3*w,QImage.Format.Format_RGB888).copy()
        self.viewer.setPixmap(QPixmap.fromImage(q).scaled(self.viewer.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def _refresh_keyframes(self):
        self.kf_list.clear()
        for item in self.store.items:
            self.kf_list.addItem(f"Frame {item.frame:04d} · score {item.score:.3f} · {item.reason}")
        self.metrics.setText(f"Keyframes almacenados: {len(self.store)}")

    def _refresh_metrics(self,frames,detected):
        self.metrics.setText(f"Frames procesados: {frames} | Detecciones: {detected} | Keyframes: {len(self.store)}")

    def _status(self,message):
        self.state_label.setText(message); self.statusBar().showMessage(message)

    def _warning(self,message):QMessageBox.warning(self,"MOCAP",message)
    def _error(self,message):QMessageBox.critical(self,"MOCAP",message)

    def closeEvent(self,event):
        self.stop_camera()
        self.detector.close()
        event.accept()

def main():
    app=QApplication([]); window=MocapWindow(); window.show(); return app.exec()
