"""GUI ligera para Windows: imagen, vídeo, cámara y exportación Blender."""
from __future__ import annotations
from pathlib import Path
import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication,QFileDialog,QHBoxLayout,QLabel,QMainWindow,QPushButton,QVBoxLayout,QWidget,QMessageBox
from .blender import BlenderBridge
from .camera import CameraCapture,CameraConfig,draw_pose
from .keyframes import KeyframeStore,image_keyframe
from .motion import CaptureState,MotionProcessor
from .pose import PoseDetector

class MocapWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("MOCAP — Genesis + Blender 4.4"); self.resize(1100,800)
        self.blend:Path|None=None; self.store=KeyframeStore(); self.processor=MotionProcessor()
        self.detector=PoseDetector(model_complexity=0); self.camera:CameraCapture|None=None; self.frame=0
        self.timer=QTimer(self); self.timer.timeout.connect(self._camera_tick)
        self.image=QLabel("Carga una imagen, vídeo o inicia cámara"); self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status=QLabel("Estado: IDLE")
        buttons=QHBoxLayout()
        for text,slot in [("Cargar .blend",self.load_blend),("Imagen",self.load_image),("Vídeo",self.load_video),
                          ("Cámara",self.start_camera),("Calibrar",self.calibrate),("Grabar",self.record),
                          ("Reset",self.reset),("Guardar",self.save)]:
            b=QPushButton(text); b.clicked.connect(slot); buttons.addWidget(b)
        root=QVBoxLayout(); root.addLayout(buttons); root.addWidget(self.image,1); root.addWidget(self.status)
        w=QWidget(); w.setLayout(root); self.setCentralWidget(w)
    def load_blend(self):
        p,_=QFileDialog.getOpenFileName(self,"Seleccionar Genesis .blend","","Blender (*.blend)")
        if p: self.blend=Path(p); self.status.setText(f"Blend: {self.blend}")
    def load_image(self):
        p,_=QFileDialog.getOpenFileName(self,"Seleccionar imagen","","Imagen (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not p:return
        frame=cv2.imread(p); pose=self.detector.detect(frame,frame_index=1)
        self.store.clear()
        if pose.detected:self.store._items.append(image_keyframe(pose))
        self._show(draw_pose(frame,pose)); self.status.setText(f"Imagen: {len(pose.landmarks)} landmarks | keyframe=1")
    def load_video(self):
        p,_=QFileDialog.getOpenFileName(self,"Seleccionar vídeo","","Vídeo (*.mp4 *.avi *.mov *.mkv)")
        if not p:return
        self.store.clear(); self.processor.reset(); self.processor.start_calibration()
        cap=cv2.VideoCapture(p); count=0
        while count<300:
            ok,frame=cap.read()
            if not ok:break
            pose=self.detector.detect(frame,frame_index=max(1,count))
            if self.processor.state is CaptureState.CALIBRATING:
                self.processor.add_calibration_sample(pose)
                if self.processor.calibrated:self.processor.begin_recording()
            elif self.processor.state is CaptureState.RECORDING:
                d=self.processor.evaluate(pose,count)
                if d.accepted and d.pose:self.store.add(d.pose,frame=max(1,count),score=d.score,reason=d.reason)
            count+=1
        cap.release(); self.status.setText(f"Vídeo procesado: {count} frames | keyframes={len(self.store)}")
    def start_camera(self):
        if self.camera:return
        try:self.camera=CameraCapture(CameraConfig())
        except Exception as e:QMessageBox.critical(self,"Cámara",str(e));return
        try:self.camera.open()
        except Exception as e:self.camera=None;QMessageBox.critical(self,"Cámara",str(e));return
        self.frame=0; self.timer.start(33); self.status.setText("Cámara: IDLE")
    def _camera_tick(self):
        if not self.camera:return
        packet=self.camera.read(self.frame)
        if packet is None:return
        pose=self.detector.detect(packet.image_bgr,frame_index=self.frame)
        if self.processor.state is CaptureState.CALIBRATING:
            self.processor.add_calibration_sample(pose); state=f"CALIBRANDO {self.processor.calibration_progress*100:.0f}%"
        elif self.processor.state is CaptureState.RECORDING:
            d=self.processor.evaluate(pose,self.frame)
            if d.accepted and d.pose:self.store.add(d.pose,frame=max(1,self.frame),score=d.score,reason=d.reason)
            state=f"GRABANDO | KF={len(self.store)} | score={d.score:.3f}"
        else:state=self.processor.state.value.upper()
        self._show(draw_pose(packet.image_bgr,pose)); self.status.setText(state); self.frame+=1
    def calibrate(self):
        self.processor.start_calibration(); self.store.clear(); self.status.setText("CALIBRANDO: mantén T-pose estable")
    def record(self):
        try:self.processor.begin_recording(); self.status.setText("GRABANDO")
        except RuntimeError as e:QMessageBox.warning(self,"Calibración",str(e))
    def reset(self):
        self.processor.reset(); self.store.clear(); self.status.setText("Estado: IDLE")
    def save(self):
        if not self.blend:QMessageBox.warning(self,"Guardar","Primero carga el .blend");return
        if not self.store:QMessageBox.warning(self,"Guardar","No hay keyframes");return
        p,_=QFileDialog.getSaveFileName(self,"Guardar .blend animado","","Blender (*.blend)")
        if not p:return
        result=BlenderBridge().apply(self.blend,self.store,p)
        if result.ok:QMessageBox.information(self,"MOCAP",result.message)
        else:QMessageBox.critical(self,"Blender",result.message+"\n"+str((result.details or {}).get("output","")))
    def _show(self,frame):
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB); h,w,_=rgb.shape
        q=QImage(rgb.data,w,h,3*w,QImage.Format.Format_RGB888).copy()
        self.image.setPixmap(QPixmap.fromImage(q).scaled(self.image.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
    def closeEvent(self,event):
        self.timer.stop()
        if self.camera:self.camera.close()
        self.detector.close(); event.accept()

def main():
    app=QApplication([]); win=MocapWindow(); win.show(); return app.exec()
