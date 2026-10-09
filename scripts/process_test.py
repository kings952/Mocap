"""Prueba completa de imagen: detectar pose y producir un keyframe en frame 1."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from mocap.inputs import load_image
from mocap.keyframes import KeyframeStore, image_keyframe
from mocap.pose import PoseDetector

def main():
    p=argparse.ArgumentParser(); p.add_argument("--image",type=Path,required=True)
    p.add_argument("--json",type=Path,default=Path("outputs/image_keyframe.json")); a=p.parse_args()
    with PoseDetector(static_image_mode=True,model_complexity=0) as d:
        pose=d.detect(load_image(a.image),frame_index=1)
    if not pose.detected: print("ERROR: no se detectó una persona."); return 2
    store=KeyframeStore(); store._items.append(image_keyframe(pose)); store.save_json(a.json)
    print(f"OK: pose detectada con {len(pose.landmarks)} landmarks. Keyframe: frame 1. JSON: {a.json}")
    return 0
if __name__=="__main__": raise SystemExit(main())
