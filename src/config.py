from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = PROJECT_ROOT / "config"
CALIBRATION_DIR = PROJECT_ROOT / "calibration"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"

# Modelo pequeño para priorizar latencia en LIVE.
# YOLO26n-pose tiene una latencia publicada muy inferior a YOLO26s-pose.
MODEL_NAME = "yolo26n-pose.pt"
MODEL_PATH = PROJECT_ROOT / "models" / MODEL_NAME
FALLBACK_MODEL_PATH = PROJECT_ROOT / "models" / "yolo11n-pose.pt"

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

LIVE_TEMP_BLEND = RECORDINGS_DIR / "_live_preview.blend"
# JPEG reduce mucho el coste de escritura/lectura frente a PNG.
LIVE_PREVIEW_IMAGE = RECORDINGS_DIR / "_live_preview.jpg"

CAMERA_INDEX = 0
# Resolucion suficiente para una captura corporal y menor latencia USB.
CAMERA_WIDTH = 960
CAMERA_HEIGHT = 540

# Entrada de inferencia mas pequeña para el modo live.
YOLO_IMAGE_SIZE = 512

# La captura sigue siendo continua; 10 FPS solo limita el guardado.
RECORDING_FPS = 10.0
SAMPLE_INTERVAL = 1.0 / RECORDING_FPS

# Menos suavizado = menos retraso entre tu movimiento y el modelo.
SMOOTHING_ALPHA = 0.55
SMOOTHING_MAX_JUMP_RATIO = 0.35
SMOOTHING_HOLD_FRAMES = 2

CONFIDENCE_THRESHOLD = 0.35
POSE_DETECTION_CONFIDENCE = 0.25
POSE_IOU = 0.50
POSE_TRACKER = "bytetrack.yaml"

CALIBRATION_FRAMES = 20
CALIBRATION_MIN_CONFIDENCE = 0.45

# Un keyframe grabado solo se crea cuando la pose cambia mas de 0.5
# unidades normalizadas respecto al ancho de hombros.
KEYFRAME_TOLERANCE = 0.5
ALWAYS_KEEP_FIRST = True
ALWAYS_KEEP_LAST = True

PREVIEW_FILE = RECORDINGS_DIR / "preview.glb"
PREVIEW_FPS = 10.0
OUTPUT_EXTENSION = ".blend"

LIVE_HOST = "127.0.0.1"
LIVE_PORT = 8765
LIVE_SCALE = 1.0

# El detector puede trabajar a la velocidad disponible, pero el pipeline
# LIVE se entrega a Blender a una frecuencia estable para evitar sobrecarga.
LIVE_FPS = 12.0
LIVE_INTERVAL = 1.0 / LIVE_FPS

# Renderizar el modelo no necesita la misma frecuencia que la captura.
LIVE_RENDER_FPS = 15.0


def ensure_directories():
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "models").mkdir(parents=True, exist_ok=True)
