import cv2
import numpy as np


CONNECTIONS = (
    ("left_ankle", "left_knee"),
    ("left_knee", "left_hip"),
    ("left_hip", "right_hip"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("left_hip", "left_shoulder"),
    ("right_hip", "right_shoulder"),
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
)


def _point(keypoints, name, threshold=0.25):
    point = keypoints.get(name)
    if not point or float(point.get("confidence", 0.0)) < threshold:
        return None
    return float(point["x"]), float(point["y"])


def render(keypoints, width=640, height=720):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (5, 8, 11)

    if not keypoints:
        cv2.putText(
            image,
            "ESPERANDO POSE...",
            (width // 2 - 125, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (150, 165, 180),
            2,
            cv2.LINE_AA,
        )
        return image

    visible = [
        _point(keypoints, name)
        for name in (
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
        )
    ]
    visible = [point for point in visible if point is not None]

    if len(visible) < 4:
        return image

    xs = [point[0] for point in visible]
    ys = [point[1] for point in visible]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min(
        (width * 0.72) / span_x,
        (height * 0.78) / span_y,
    )

    center_x = (min_x + max_x) * 0.5
    center_y = (min_y + max_y) * 0.5

    def convert(point):
        return (
            int((point[0] - center_x) * scale + width * 0.5),
            int((point[1] - center_y) * scale + height * 0.52),
        )

    points = {
        name: convert(point)
        for name in keypoints
        if (point := _point(keypoints, name)) is not None
    }

    hip_l = points.get("left_hip")
    hip_r = points.get("right_hip")
    shoulder_l = points.get("left_shoulder")
    shoulder_r = points.get("right_shoulder")

    if all((hip_l, hip_r, shoulder_l, shoulder_r)):
        torso = np.array(
            [shoulder_l, shoulder_r, hip_r, hip_l],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(
            image,
            torso,
            (45, 65, 82),
        )
        cv2.polylines(
            image,
            [torso],
            True,
            (100, 145, 180),
            2,
            cv2.LINE_AA,
        )

    for a, b in CONNECTIONS:
        pa = points.get(a)
        pb = points.get(b)
        if pa is None or pb is None:
            continue

        cv2.line(
            image,
            pa,
            pb,
            (90, 190, 235),
            14,
            cv2.LINE_AA,
        )
        cv2.line(
            image,
            pa,
            pb,
            (185, 220, 240),
            6,
            cv2.LINE_AA,
        )

    if shoulder_l and shoulder_r:
        neck = (
            int((shoulder_l[0] + shoulder_r[0]) * 0.5),
            int((shoulder_l[1] + shoulder_r[1]) * 0.5 - 10),
        )

        cv2.line(
            image,
            neck,
            (neck[0], neck[1] - 22),
            (185, 220, 240),
            8,
            cv2.LINE_AA,
        )
        cv2.circle(
            image,
            (neck[0], neck[1] - 48),
            28,
            (185, 220, 240),
            -1,
            cv2.LINE_AA,
        )

    for name, point in points.items():
        radius = 7 if (
            "wrist" in name
            or "ankle" in name
        ) else 8

        cv2.circle(
            image,
            point,
            radius,
            (235, 245, 250),
            -1,
            cv2.LINE_AA,
        )

    cv2.putText(
        image,
        "LIVE  •  PYTHON / OPENCV",
        (18, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (145, 210, 240),
        2,
        cv2.LINE_AA,
    )

    return image
