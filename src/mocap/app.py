"""Orquestador de captura y exportación."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .blender import BlenderBridge, BlenderResult
from .inputs import iter_video, load_image
from .keyframes import KeyframeStore, image_keyframe
from .motion import CaptureState, MotionConfig, MotionProcessor
from .pose import PoseDetector

@dataclass(frozen=True)
class ProcessResult:
    keyframes: KeyframeStore
    detected_frames: int
    processed_frames: int

class MocapPipeline:
    def __init__(self,motion:MotionConfig|None=None,blender:BlenderBridge|None=None):
        self.motion=MotionProcessor(motion); self.blender=blender or BlenderBridge()
    def process_image(self,path:str|Path)->ProcessResult:
        with PoseDetector(static_image_mode=True,model_complexity=0) as d:
            pose=d.detect(load_image(path),frame_index=1)
        store=KeyframeStore()
        if pose.detected: store.add(image_keyframe(pose).pose,frame=1,score=1,reason="imagen")
        return ProcessResult(store,int(pose.detected),1)
    def process_video(self,path:str|Path,max_frames:int=300)->ProcessResult:
        store=KeyframeStore(); processed=detected=0
        self.motion.reset(); self.motion.start_calibration()
        with PoseDetector(model_complexity=0) as d:
            for packet in iter_video(path):
                pose=d.detect(packet.image_bgr,frame_index=max(1,packet.index)); processed+=1
                detected+=int(pose.detected)
                if self.motion.state is CaptureState.CALIBRATING:
                    self.motion.add_calibration_sample(pose)
                    if self.motion.calibrated: self.motion.begin_recording()
                elif self.motion.state is CaptureState.RECORDING:
                    decision=self.motion.evaluate(pose,packet.index)
                    if decision.accepted and decision.pose:
                        store.add(decision.pose,frame=max(1,packet.index),
                                  score=decision.score,reason=decision.reason)
                if processed>=max_frames: break
        return ProcessResult(store,detected,processed)
    def save_to_blender(self,blend:str|Path,output:str|Path,store:KeyframeStore)->BlenderResult:
        return self.blender.apply(blend,store,output)
