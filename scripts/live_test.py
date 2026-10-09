"""Prueba de cámara, pose, calibración y filtro.

C = calibrar, R = grabar, X = reset, ESC = salir.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from mocap.camera import CameraCapture,CameraConfig,draw_pose
from mocap.keyframes import KeyframeStore
from mocap.motion import MotionConfig,MotionProcessor
from mocap.pose import PoseDetector

def main():
    p=argparse.ArgumentParser(); p.add_argument("--camera",type=int,default=0)
    p.add_argument("--width",type=int,default=1280); p.add_argument("--height",type=int,default=720)
    a=p.parse_args(); processor=MotionProcessor(MotionConfig()); keyframes=KeyframeStore()
    detector=PoseDetector(model_complexity=0)
    try:
        with CameraCapture(CameraConfig(a.camera,a.width,a.height,30)) as camera:
            index=0
            while True:
                packet=camera.read(index)
                if packet is None: break
                pose=detector.detect(packet.image_bgr,frame_index=index); view=draw_pose(packet.image_bgr,pose)
                if processor.state.value=="calibrating":
                    processor.add_calibration_sample(pose); status=f"CALIBRANDO {processor.calibration_progress*100:.0f}%"
                elif processor.state.value=="recording":
                    d=processor.evaluate(pose,index)
                    if d.accepted and d.pose:
                        keyframes.add(d.pose,frame=max(1,index),score=d.score,reason=d.reason)
                    status=f"GRABANDO KF={len(keyframes)} score={d.score:.3f}"
                elif processor.state.value=="ready": status="LISTO - pulsa R para grabar"
                else: status="IDLE - pulsa C para calibrar"
                cv2.putText(view,status,(20,35),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2)
                cv2.imshow("MOCAP - prueba",view); key=cv2.waitKey(1)&0xFF
                if key==27: break
                if key in (ord("c"),ord("C")): processor.start_calibration()
                elif key in (ord("r"),ord("R")):
                    try: processor.begin_recording()
                    except RuntimeError: pass
                elif key in (ord("x"),ord("X")): processor.reset(); keyframes.clear()
                index+=1
    finally:
        detector.close(); cv2.destroyAllWindows()
    print(f"Keyframes aceptados: {len(keyframes)}"); print(f"Frames: {keyframes.frames()}")
    return 0
if __name__=="__main__": raise SystemExit(main())
