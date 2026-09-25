from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "models" / "yolo11n-pose.pt"

CONFIG_DIR = PROJECT_ROOT / "config"
CALIBRATION_DIR = PROJECT_ROOT / "calibration"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"

ARMATURE_MAPPING = CONFIG_DIR / "armature_mapping.json"
RIG_REFERENCE = CONFIG_DIR / "rig_reference.json"

BLENDER_EXE = Path(
    r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
)

SOURCE_BLEND = Path(
    r"D:\my blender\bases\Baseic_flutter.blend"
)

BLENDER_GENERATOR = PROJECT_ROOT / "blender" / "generate_animation.py"
BLENDER_LIVE_SCRIPT = PROJECT_ROOT / "blender" / "live_preview.py"

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
YOLO_IMAGE_SIZE = 640

RECORDING_FPS = 10.0
SAMPLE_INTERVAL = 1.0 / RECORDING_FPS

SMOOTHING_ALPHA = 0.30
CONFIDENCE_THRESHOLD = 0.35

CALIBRATION_FRAMES = 20
CALIBRATION_MIN_CONFIDENCE = 0.45

KEYFRAME_TOLERANCE = 0.4
ALWAYS_KEEP_FIRST = True
ALWAYS_KEEP_LAST = True

PREVIEW_FILE = RECORDINGS_DIR / "preview.glb"
PREVIEW_FPS = 10.0

OUTPUT_EXTENSION = ".blend"

LIVE_HOST = "127.0.0.1"
LIVE_PORT = 8765
LIVE_SCALE = 1.0


def ensure_directories():
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
