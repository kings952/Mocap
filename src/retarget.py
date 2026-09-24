import math
import numpy as np

from skeleton import (
    xy,
    valid,
    distance,
    angle,
)


def body_center(
    keypoints,
    threshold=0.35,
):

    if not valid(
        keypoints,
        "left_hip",
        threshold,
    ):
        return None

    if not valid(
        keypoints,
        "right_hip",
        threshold,
    ):
        return None

    left = xy(
        keypoints,
        "left_hip",
    )

    right = xy(
        keypoints,
        "right_hip",
    )

    return [
        (left[0] + right[0]) / 2.0,
        (left[1] + right[1]) / 2.0,
    ]


def body_scale(
    keypoints,
    threshold=0.35,
):

    if not valid(
        keypoints,
        "left_shoulder",
        threshold,
    ):
        return 1.0

    if not valid(
        keypoints,
        "right_shoulder",
        threshold,
    ):
        return 1.0

    left = xy(
        keypoints,
        "left_shoulder",
    )

    right = xy(
        keypoints,
        "right_shoulder",
    )

    return max(
        distance(left, right),
        1.0,
    )


def calculate_metrics(keypoints):

    center = body_center(keypoints)

    scale = body_scale(keypoints)

    visibility = 0

    total = len(keypoints)

    for point in keypoints.values():

        if point["confidence"] >= 0.35:
            visibility += 1

    visibility_ratio = (
        visibility / total
        if total
        else 0.0
    )

    left_elbow = angle(
        xy(keypoints, "left_shoulder"),
        xy(keypoints, "left_elbow"),
        xy(keypoints, "left_wrist"),
    )

    right_elbow = angle(
        xy(keypoints, "right_shoulder"),
        xy(keypoints, "right_elbow"),
        xy(keypoints, "right_wrist"),
    )

    left_knee = angle(
        xy(keypoints, "left_hip"),
        xy(keypoints, "left_knee"),
        xy(keypoints, "left_ankle"),
    )

    right_knee = angle(
        xy(keypoints, "right_hip"),
        xy(keypoints, "right_knee"),
        xy(keypoints, "right_ankle"),
    )

    return {
        "body_center": center,

        "body_scale": float(scale),

        "visibility": float(
            visibility_ratio
        ),

        "left_elbow_angle": left_elbow,

        "right_elbow_angle": right_elbow,

        "left_knee_angle": left_knee,

        "right_knee_angle": right_knee,
    }


def build_packet(
    keypoints,
    frame_id,
    timestamp,
):

    metrics = calculate_metrics(
        keypoints
    )

    return {
        "type": "mocap_pose",

        "frame_id": int(frame_id),

        "time": float(timestamp),

        "keypoints": keypoints,

        "metrics": metrics,
    }