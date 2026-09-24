import math


KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


SKELETON_CONNECTIONS = [
    ("nose", "left_eye"),
    ("nose", "right_eye"),
    ("left_eye", "left_ear"),
    ("right_eye", "right_ear"),

    ("left_shoulder", "right_shoulder"),

    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),

    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),

    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),

    ("left_hip", "right_hip"),

    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),

    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]


def xy(keypoints, name):
    point = keypoints.get(name)

    if point is None:
        return None

    return point["x"], point["y"]


def confidence(keypoints, name):
    point = keypoints.get(name)

    if point is None:
        return 0.0

    return float(point.get("confidence", 0.0))


def valid(
    keypoints,
    name,
    threshold=0.35,
):
    return confidence(keypoints, name) >= threshold


def distance(a, b):
    if a is None or b is None:
        return 0.0

    dx = a[0] - b[0]
    dy = a[1] - b[1]

    return math.sqrt(dx * dx + dy * dy)


def angle(a, b, c):
    """
    Ángulo ABC.
    """

    if a is None or b is None or c is None:
        return None

    ax = a[0] - b[0]
    ay = a[1] - b[1]

    cx = c[0] - b[0]
    cy = c[1] - b[1]

    dot = ax * cx + ay * cy

    len_a = math.sqrt(ax * ax + ay * ay)
    len_c = math.sqrt(cx * cx + cy * cy)

    if len_a <= 0.00001 or len_c <= 0.00001:
        return None

    value = dot / (len_a * len_c)

    value = max(-1.0, min(1.0, value))

    return math.degrees(math.acos(value))