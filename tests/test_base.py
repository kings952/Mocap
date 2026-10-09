from mocap.config import DEFAULT_CONFIG


def test_default_camera_config():
    assert DEFAULT_CONFIG.camera_index == 0
    assert DEFAULT_CONFIG.camera_width == 1280
    assert DEFAULT_CONFIG.camera_height == 720
    assert DEFAULT_CONFIG.camera_fps == 30
