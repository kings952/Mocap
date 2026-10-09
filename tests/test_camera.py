import numpy as np

from mocap.camera import draw_pose
from mocap.pose import PoseFrame, PoseLandmark


def test_draw_pose_returns_same_size():
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    points = (
        PoseLandmark(0, "NOSE", 0.5, 0.2, 0.0, 1.0, 1.0),
        PoseLandmark(1, "LEFT_SHOULDER", 0.4, 0.4, 0.0, 1.0, 1.0),
        PoseLandmark(2, "RIGHT_SHOULDER", 0.6, 0.4, 0.0, 1.0, 1.0),
    )
    pose = PoseFrame(1, 120, 100, points)
    result = draw_pose(frame, pose)
    assert result.shape == frame.shape
    assert not np.array_equal(result, frame)
