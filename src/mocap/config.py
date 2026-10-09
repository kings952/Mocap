"""Basic project configuration.

Blender integration will be added later. Keeping configuration independent
from Blender lets us test the motion-capture pipeline in a normal Python
virtual environment first.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    camera_index: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: int = 30


DEFAULT_CONFIG = AppConfig()
