import json
import math

from skeleton import xy, valid, distance, angle
from config import RIG_REFERENCE


_RIG_REFERENCE_CACHE = None


def body_center(keypoints, threshold=0.35):
    if not valid(keypoints, "left_hip", threshold) or not valid(
        keypoints, "right_hip", threshold
    ):
        return None

    left = xy(keypoints, "left_hip")
    right = xy(keypoints, "right_hip")

    return [
        (left[0] + right[0]) / 2.0,
        (left[1] + right[1]) / 2.0,
    ]


def shoulder_center(keypoints, threshold=0.35):
    if not valid(keypoints, "left_shoulder", threshold) or not valid(
        keypoints, "right_shoulder", threshold
    ):
        return None

    left = xy(keypoints, "left_shoulder")
    right = xy(keypoints, "right_shoulder")

    return [
        (left[0] + right[0]) / 2.0,
        (left[1] + right[1]) / 2.0,
    ]


def shoulder_width(keypoints, threshold=0.35):
    if not valid(keypoints, "left_shoulder", threshold) or not valid(
        keypoints, "right_shoulder", threshold
    ):
        return None

    return max(
        distance(
            xy(keypoints, "left_shoulder"),
            xy(keypoints, "right_shoulder"),
        ),
        1.0,
    )


def body_scale(keypoints, threshold=0.35):
    return shoulder_width(keypoints, threshold) or 1.0


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
    global _RIG_REFERENCE_CACHE

    if _RIG_REFERENCE_CACHE is None:
        with open(RIG_REFERENCE, "r", encoding="utf-8") as file:
            _RIG_REFERENCE_CACHE = json.load(file)

    return _RIG_REFERENCE_CACHE


def _rig_position(reference, name):
    controls = reference.get("controls", {})
    data = controls.get(name, {})
    return list(data.get("position", [0.0, 0.0, 0.0]))


def _confidence(keypoints, name):
    point = keypoints.get(name)
    if not point:
        return 0.0
    return float(point.get("confidence", 0.0))


def _normalized_delta(point_name, keypoints, calibration, current_width):
    current = keypoints.get(point_name)
    origin = calibration.get("keypoints", {}).get(point_name)

    if not current or not origin:
        return None

    if _confidence(keypoints, point_name) < 0.35:
        return None

    current_center = shoulder_center(keypoints, 0.35)
    reference_center = calibration.get("center")

    if current_center is None or not reference_center:
        return None

    reference_width = max(float(calibration.get("body_scale", 1.0)), 1.0)
    current_width = max(float(current_width), 1.0)

    current_relative = [
        (float(current["x"]) - current_center[0]) / current_width,
        (float(current["y"]) - current_center[1]) / current_width,
    ]
    reference_relative = [
        (float(origin["x"]) - float(reference_center[0])) / reference_width,
        (float(origin["y"]) - float(reference_center[1])) / reference_width,
    ]

    # Normalize first, then clamp. This is what makes the live independent
    # from camera distance and from the absolute pixel scale.
    dx = max(-1.25, min(1.25, current_relative[0] - reference_relative[0]))
    dy = max(-1.25, min(1.25, current_relative[1] - reference_relative[1]))

    return [dx, dy]


def _make_target(base, delta_xy, rig_width, gain=1.0):
    if delta_xy is None:
        return None

    dx = float(delta_xy[0]) * rig_width * gain
    dz = -float(delta_xy[1]) * rig_width * gain

    return {
        "position": [
            float(base[0] + dx),
            float(base[1]),
            float(base[2] + dz),
        ],
        "reference": [float(v) for v in base],
        "gain": float(gain),
    }


def build_live_targets(keypoints, calibration, reference=None):
    """
    Retarget 2D -> IK usando coordenadas relativas al torso.

    El error anterior era convertir directamente pixeles a unidades Blender.
    Ahora:
      1. se elimina la escala de la camara con el ancho de hombros;
      2. se compara contra la pose calibrada;
      3. se limita el desplazamiento;
      4. Blender aplica una segunda proteccion basada en el tamaño real del .blend.

    El bone "Bone" nunca aparece como target.
    """
    if not calibration:
        return {}

    reference = reference or load_rig_reference()

    current_width = shoulder_width(keypoints, 0.35)
    if current_width is None:
        return {}

    reference_width = float(calibration.get("body_scale", 0.0))
    if reference_width < 20.0 or reference_width > 1000.0:
        return {}

    rig_left_hand = _rig_position(reference, "left_hand")
    rig_right_hand = _rig_position(reference, "right_hand")
    rig_left_pole = _rig_position(reference, "left_hand_pole")
    rig_right_pole = _rig_position(reference, "right_hand_pole")

    # The hand controls represent the rig's shoulder span closely enough for
    # a stable normalized scale. The actual Blender model size is enforced
    # again by live_preview.py, so even unusual .blend scales stay safe.
    rig_width = max(
        abs(float(rig_left_hand[0]) - float(rig_right_hand[0])),
        0.0001,
    )

    targets = {}

    # Body translation uses the shoulder center. It is intentionally damped:
    # moving the person in front of the camera moves Genesis, but never the
    # static Bone controller.
    current_center = shoulder_center(keypoints, 0.45)
    reference_center = calibration.get("center")

    if current_center is not None and reference_center:
        translation_x = (
            (current_center[0] - float(reference_center[0]))
            / max(reference_width, 1.0)
        )
        translation_y = (
            (current_center[1] - float(reference_center[1]))
            / max(reference_width, 1.0)
        )

        translation_x = max(-1.0, min(1.0, translation_x))
        translation_y = max(-1.0, min(1.0, translation_y))

        body_gain = 0.65
        targets["hip"] = {
            "position": [
                float(translation_x * rig_width * body_gain),
                0.0,
                float(-translation_y * rig_width * body_gain),
            ],
            "reference": [0.0, 0.0, 0.0],
            "gain": 1.0,
        }

    left_hand = _make_target(
        rig_left_hand,
        _normalized_delta("left_wrist", keypoints, calibration, current_width),
        rig_width,
        gain=0.90,
    )
    right_hand = _make_target(
        rig_right_hand,
        _normalized_delta("right_wrist", keypoints, calibration, current_width),
        rig_width,
        gain=0.90,
    )

    if left_hand is not None:
        targets["left_hand"] = left_hand
    if right_hand is not None:
        targets["right_hand"] = right_hand

    # Poles are deliberately damped. Large pole jumps are a common cause of
    # IK flipping when a 2D detector jitters by only a few pixels.
    left_pole = _make_target(
        rig_left_pole,
        _normalized_delta("left_elbow", keypoints, calibration, current_width),
        rig_width,
        gain=0.25,
    )
    right_pole = _make_target(
        rig_right_pole,
        _normalized_delta("right_elbow", keypoints, calibration, current_width),
        rig_width,
        gain=0.25,
    )

    if left_pole is not None:
        targets["left_hand_pole"] = left_pole
    if right_pole is not None:
        targets["right_hand_pole"] = right_pole

    # Legs remain confidence-gated and normalized. They are also damped more
    # than the hands because a 2D ankle cannot encode real depth.
    for side in ("left", "right"):
        ankle_name = f"{side}_ankle"
        knee_name = f"{side}_knee"
        foot_name = f"{side}_foot"
        pole_name = f"{side}_foot_pole"

        if _confidence(keypoints, ankle_name) >= 0.55:
            foot_base = _rig_position(reference, foot_name)
            foot_target = _make_target(
                foot_base,
                _normalized_delta(
                    ankle_name, keypoints, calibration, current_width
                ),
                rig_width,
                gain=0.55,
            )
            if foot_target is not None:
                targets[foot_name] = foot_target

        if _confidence(keypoints, knee_name) >= 0.55:
            pole_base = _rig_position(reference, pole_name)
            pole_target = _make_target(
                pole_base,
                _normalized_delta(
                    knee_name, keypoints, calibration, current_width
                ),
                rig_width,
                gain=0.20,
            )
            if pole_target is not None:
                targets[pole_name] = pole_target

    return targets
