import json
import math

from skeleton import xy, valid, distance, angle
from config import RIG_REFERENCE


def body_center(keypoints, threshold=0.35):
    if not valid(keypoints, "left_hip", threshold) or not valid(keypoints, "right_hip", threshold):
        return None
    left = xy(keypoints, "left_hip")
    right = xy(keypoints, "right_hip")
    return [(left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0]


def body_scale(keypoints, threshold=0.35):
    if not valid(keypoints, "left_shoulder", threshold) or not valid(keypoints, "right_shoulder", threshold):
        return 1.0
    return max(
        distance(xy(keypoints, "left_shoulder"), xy(keypoints, "right_shoulder")),
        1.0,
    )


def calculate_metrics(keypoints):
    center = body_center(keypoints)
    scale = body_scale(keypoints)

    visibility = sum(
        1 for point in keypoints.values()
        if point.get("confidence", 0.0) >= 0.35
    )
    total = len(keypoints)

    def safe_angle(a, b, c):
        if not all(valid(keypoints, n, 0.35) for n in (a, b, c)):
            return None
        return angle(xy(keypoints, a), xy(keypoints, b), xy(keypoints, c))

    return {
        "body_center": center,
        "body_scale": float(scale),
        "visibility": visibility / total if total else 0.0,
        "left_elbow_angle": safe_angle("left_shoulder", "left_elbow", "left_wrist"),
        "right_elbow_angle": safe_angle("right_shoulder", "right_elbow", "right_wrist"),
        "left_knee_angle": safe_angle("left_hip", "left_knee", "left_ankle"),
        "right_knee_angle": safe_angle("right_hip", "right_knee", "right_ankle"),
    }


def build_packet(keypoints, frame_id, timestamp):
    return {
        "type": "mocap_pose",
        "frame_id": int(frame_id),
        "time": float(timestamp),
        "keypoints": keypoints,
        "metrics": calculate_metrics(keypoints),
    }


def load_rig_reference():
    with open(RIG_REFERENCE, "r", encoding="utf-8") as file:
        return json.load(file)


def _rig_position(reference, name):
    controls = reference.get("controls", {})
    data = controls.get(name, {})
    return list(data.get("position", [0.0, 0.0, 0.0]))


def build_live_targets(keypoints, calibration, reference=None):
    """
    Convierte el desplazamiento 2D desde la calibracion a desplazamientos
    3D del rig.

    Cada target lleva:
      - position: posicion absoluta de referencia + desplazamiento
      - reference: posicion de reposo del control

    Blender usa ambos valores para aplicar SOLO el desplazamiento.
    Esto evita acumulacion/deriva frame a frame.
    """
    if not calibration:
        return {}

    reference = reference or load_rig_reference()
    calib = calibration.get("keypoints", {})
    base_scale = float(calibration.get("body_scale", 1.0))

    if base_scale <= 1.0:
        return {}

    rig_ls = _rig_position(reference, "left_hand")
    rig_rs = _rig_position(reference, "right_hand")
    rig_le = _rig_position(reference, "left_hand_pole")
    rig_re = _rig_position(reference, "right_hand_pole")

    rig_shoulder_width = max(abs(rig_ls[0] - rig_rs[0]), 1.0)
    scale = rig_shoulder_width / base_scale

    def project(point_name, base):
        current = keypoints.get(point_name)
        origin = calib.get(point_name)

        if not current or not origin:
            return None

        confidence = float(current.get("confidence", 0.0))
        if confidence < 0.35:
            return None

        dx = (float(current["x"]) - float(origin["x"])) * scale
        dy = (float(current["y"]) - float(origin["y"])) * scale

        position = [
            float(base[0] + dx),
            float(base[1]),
            float(base[2] - dy),
        ]

        return {
            "position": position,
            "reference": [float(v) for v in base],
        }

    targets = {}

    left_hand = project("left_wrist", rig_ls)
    right_hand = project("right_wrist", rig_rs)
    left_pole = project("left_elbow", rig_le)
    right_pole = project("right_elbow", rig_re)

    if left_hand is not None:
        targets["left_hand"] = left_hand
    if right_hand is not None:
        targets["right_hand"] = right_hand
    if left_pole is not None:
        targets["left_hand_pole"] = left_pole
    if right_pole is not None:
        targets["right_hand_pole"] = right_pole

    # Las piernas no se inventan. Solo se mandan cuando YOLO las ve realmente.
    for side in ("left", "right"):
        ankle_name = f"{side}_ankle"
        knee_name = f"{side}_knee"
        foot_name = f"{side}_foot"
        pole_name = f"{side}_foot_pole"

        ankle = keypoints.get(ankle_name)
        knee = keypoints.get(knee_name)

        if ankle and float(ankle.get("confidence", 0.0)) >= 0.50:
            base = _rig_position(reference, foot_name)
            target = project(ankle_name, base)
            if target is not None:
                targets[foot_name] = target

        if knee and float(knee.get("confidence", 0.0)) >= 0.50:
            base = _rig_position(reference, pole_name)
            target = project(knee_name, base)
            if target is not None:
                targets[pole_name] = target

    return targets
