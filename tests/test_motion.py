from mocap.keyframes import KeyframeStore, image_keyframe
from mocap.motion import CaptureState, MotionConfig, MotionProcessor, smooth_pose
from mocap.pose import PoseFrame, PoseLandmark


def pose(frame: int, offset: float = 0.0) -> PoseFrame:
    data = [
        ("NOSE", 0.5, 0.1), ("LEFT_SHOULDER", 0.4, 0.3),
        ("RIGHT_SHOULDER", 0.6, 0.3), ("LEFT_ELBOW", 0.35, 0.45),
        ("RIGHT_ELBOW", 0.65, 0.45), ("LEFT_WRIST", 0.3, 0.6),
        ("RIGHT_WRIST", 0.7, 0.6), ("LEFT_HIP", 0.43, 0.55),
        ("RIGHT_HIP", 0.57, 0.55),
    ]
    points = tuple(
        PoseLandmark(i, name, x + offset, y, 0.0, 1.0, 1.0)
        for i, (name, x, y) in enumerate(data)
    )
    return PoseFrame(frame, 640, 480, points)


def test_calibration_does_not_generate_keyframes():
    processor = MotionProcessor(MotionConfig(calibration_samples=3))
    processor.start_calibration()
    for frame in range(3):
        assert not processor.evaluate(pose(frame), frame).accepted
        processor.add_calibration_sample(pose(frame))
    assert processor.state is CaptureState.READY
    assert processor.calibrated


def test_first_recorded_pose_is_accepted_after_calibration():
    processor = MotionProcessor(MotionConfig(calibration_samples=2))
    processor.start_calibration()
    processor.add_calibration_sample(pose(0))
    processor.add_calibration_sample(pose(1))
    processor.begin_recording()
    decision = processor.evaluate(pose(10), 10)
    assert decision.accepted
    assert decision.reason == "primer_keyframe"


def test_small_movement_is_filtered():
    processor = MotionProcessor(MotionConfig(calibration_samples=2, movement_threshold=0.2))
    processor.start_calibration()
    processor.add_calibration_sample(pose(0))
    processor.add_calibration_sample(pose(1))
    processor.begin_recording()
    processor.evaluate(pose(1), 1)
    decision = processor.evaluate(pose(2, 0.01), 2)
    assert not decision.accepted
    assert decision.reason == "movimiento_pequeno"


def test_image_keyframe_is_frame_one():
    assert image_keyframe(pose(0)).frame == 1


def test_keyframe_store_keeps_order():
    store = KeyframeStore()
    store.add(pose(0), frame=1)
    store.add(pose(2), frame=10)
    assert store.frames() == (1, 10)


def test_smoothing_reduces_jump():
    first, second = pose(0), pose(1, 0.2)
    smoothed = smooth_pose(first, second, alpha=0.5)
    assert smoothed.by_name("NOSE").x < second.by_name("NOSE").x
