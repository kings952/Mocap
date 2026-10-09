import cv2
import numpy as np

from mocap.inputs import load_image
from mocap.pose import PoseDetector


def test_pose_detector_accepts_bgr_frame():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    with PoseDetector(static_image_mode=True, model_complexity=0) as detector:
        result = detector.detect(frame, frame_index=1)

    assert result.frame_index == 1
    assert result.width == 320
    assert result.height == 240
    assert result.landmarks == ()


def test_load_image_reads_bgr(tmp_path):
    path = tmp_path / "test.png"
    expected = np.zeros((10, 20, 3), dtype=np.uint8)
    expected[:, :, 0] = 255
    assert cv2.imwrite(str(path), expected)

    loaded = load_image(path)

    assert loaded.shape == (10, 20, 3)
    assert int(loaded[0, 0, 0]) == 255
