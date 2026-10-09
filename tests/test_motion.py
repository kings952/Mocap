from mocap.keyframes import KeyframeStore, image_keyframe
from mocap.motion import CaptureState, MotionConfig, MotionProcessor, smooth_pose
from mocap.pose import PoseFrame, PoseLandmark

def pose(frame:int,offset:float=0.0)->PoseFrame:
    data=[("NOSE",.5,.1),("LEFT_SHOULDER",.4,.3),("RIGHT_SHOULDER",.6,.3),
          ("LEFT_ELBOW",.35,.45),("RIGHT_ELBOW",.65,.45),("LEFT_WRIST",.3,.6),
          ("RIGHT_WRIST",.7,.6),("LEFT_HIP",.43,.55),("RIGHT_HIP",.57,.55)]
    return PoseFrame(frame,640,480,tuple(PoseLandmark(i,n,x+offset,y,0,1,1) for i,(n,x,y) in enumerate(data)))

def test_calibration_does_not_generate_keyframes():
    p=MotionProcessor(MotionConfig(calibration_samples=3)); p.start_calibration()
    for i in range(3): assert not p.evaluate(pose(i),i).accepted; p.add_calibration_sample(pose(i))
    assert p.state is CaptureState.READY and p.calibrated

def test_first_recorded_pose_is_accepted_after_calibration():
    p=MotionProcessor(MotionConfig(calibration_samples=2)); p.start_calibration()
    p.add_calibration_sample(pose(0)); p.add_calibration_sample(pose(1)); p.begin_recording()
    d=p.evaluate(pose(10),10); assert d.accepted and d.reason=="primer_keyframe"

def test_small_movement_is_filtered_against_last_keyframe():
    p=MotionProcessor(MotionConfig(calibration_samples=2,movement_threshold=.2)); p.start_calibration()
    p.add_calibration_sample(pose(0)); p.add_calibration_sample(pose(1)); p.begin_recording()
    p.evaluate(pose(1),1); d=p.evaluate(pose(2,.01),2); assert not d.accepted
    d=p.evaluate(pose(3,.01),3); assert not d.accepted

def test_image_keyframe_is_frame_one(): assert image_keyframe(pose(0)).frame==1

def test_keyframe_store_keeps_order():
    s=KeyframeStore(); s.add(pose(0),frame=1); s.add(pose(2),frame=10); assert s.frames()==(1,10)

def test_smoothing_reduces_jump():
    first,second=pose(0),pose(1,.2); smoothed=smooth_pose(first,second,.5)
    assert smoothed.by_name("NOSE").x < second.by_name("NOSE").x
