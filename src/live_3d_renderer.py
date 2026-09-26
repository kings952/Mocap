import math
import cv2
import numpy as np

from retarget import build_live_targets, load_rig_reference


BONES = (
    ("head", "neck"),
    ("neck", "left_shoulder"),
    ("neck", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_hand"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_hand"),
    ("neck", "pelvis"),
    ("pelvis", "left_hip"),
    ("pelvis", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_foot"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_foot"),
)


class Live3DRenderer:
    """CPU-only 3D rig preview. Blender is not required for the live loop."""

    def __init__(self, width=720, height=720):
        self.width = int(width)
        self.height = int(height)
        self.yaw = math.radians(8.0)
        self.pitch = math.radians(-5.0)
        self.distance = 250.0
        self._depth = {}
        self.reference = load_rig_reference()

    def render(self, keypoints, calibration):
        image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        image[:] = (7, 10, 14)

        if not keypoints or not calibration:
            self._text(image, "CALIBRA PARA INICIAR TRACKING", 0.72)
            return image

        try:
            targets = build_live_targets(
                keypoints,
                calibration,
                self.reference,
            )
            joints = self._make_joints(
                keypoints,
                calibration,
                targets,
            )
            projected = self._project(joints)
            self._draw_grid(image)
            self._draw_bones(image, projected)
            self._draw_joints(image, projected)
            self._draw_overlay(image, targets)
            return image
        except Exception as exc:
            self._text(
                image,
                f"LIVE 3D ERROR: {str(exc)[:42]}",
                0.55,
            )
            return image

    def _make_joints(self, keypoints, calibration, targets):
        rig_width = self._rig_width()
        half = rig_width * 0.5
        scale = rig_width / max(
            float(calibration.get("body_scale", 1.0)),
            1.0,
        )
        center = calibration.get("center", [0.0, 0.0])
        points = calibration.get("keypoints", {})

        def norm(name):
            p = keypoints.get(name)
            if not p or name not in points:
                return None
            return (
                (float(p["x"]) - float(center[0])) * scale,
                (float(p["y"]) - float(center[1])) * scale,
            )

        def depth(name, a, b):
            ca, cb = points.get(a), points.get(b)
            pa, pb = keypoints.get(a), keypoints.get(b)
            if not ca or not cb or not pa or not pb:
                return 0.0

            ref_len = math.hypot(
                float(ca["x"]) - float(cb["x"]),
                float(ca["y"]) - float(cb["y"]),
            )
            cur_len = math.hypot(
                float(pa["x"]) - float(pb["x"]),
                float(pa["y"]) - float(pb["y"]),
            )
            target = max(
                -rig_width * 0.75,
                min(
                    rig_width * 0.75,
                    (ref_len - cur_len) * scale,
                ),
            )
            previous = self._depth.get(name, target)
            value = previous * 0.72 + target * 0.28
            self._depth[name] = value
            return value

        def target_pos(name, fallback):
            item = targets.get(name)
            if not item:
                return fallback
            return np.asarray(
                item["position"],
                dtype=np.float32,
            )

        joints = {
            "head": np.array(
                [0.0, 0.0, rig_width * 1.55],
                dtype=np.float32,
            ),
            "neck": np.array(
                [0.0, 0.0, rig_width * 1.32],
                dtype=np.float32,
            ),
            "left_shoulder": np.array(
                [half, 0.0, rig_width * 1.25],
                dtype=np.float32,
            ),
            "right_shoulder": np.array(
                [-half, 0.0, rig_width * 1.25],
                dtype=np.float32,
            ),
            "pelvis": np.array(
                [0.0, 0.0, rig_width * 0.65],
                dtype=np.float32,
            ),
            "left_hip": np.array(
                [rig_width * 0.20, 0.0, rig_width * 0.65],
                dtype=np.float32,
            ),
            "right_hip": np.array(
                [-rig_width * 0.20, 0.0, rig_width * 0.65],
                dtype=np.float32,
            ),
        }

        body = targets.get("hip")
        if body:
            joints["pelvis"] += np.asarray(
                body["position"],
                dtype=np.float32,
            )

        for side in ("left", "right"):
            shoulder = f"{side}_shoulder"
            elbow = f"{side}_elbow"
            hand = f"{side}_hand"
            hip = f"{side}_hip"
            knee = f"{side}_knee"
            foot = f"{side}_foot"

            shoulder_ref = joints[shoulder].copy()
            p = norm(elbow)

            if p:
                x, z = p
                expected_x = half if side == "left" else -half
                joints[elbow] = np.array(
                    [
                        expected_x + x * 0.72,
                        depth(elbow, shoulder, elbow),
                        rig_width * 0.92 + z * 0.72,
                    ],
                    dtype=np.float32,
                )
            else:
                joints[elbow] = shoulder_ref + np.array(
                    [0.0, 0.0, -rig_width * 0.25],
                    dtype=np.float32,
                )

            fallback_hand = joints[elbow] + np.array(
                [
                    (half if side == "left" else -half) * 0.8,
                    0.0,
                    -rig_width * 0.18,
                ],
                dtype=np.float32,
            )
            joints[hand] = target_pos(
                hand,
                fallback_hand,
            )

            p = norm(knee)
            if p:
                x, z = p
                expected_x = (
                    rig_width * 0.20
                    if side == "left"
                    else -rig_width * 0.20
                )
                joints[knee] = np.array(
                    [
                        expected_x + x * 0.30,
                        depth(knee, hip, knee),
                        rig_width * 0.32 + z * 0.55,
                    ],
                    dtype=np.float32,
                )
            else:
                joints[knee] = joints[hip] + np.array(
                    [0.0, 0.0, -rig_width * 0.30],
                    dtype=np.float32,
                )

            fallback_foot = joints[knee] + np.array(
                [0.0, 0.0, -rig_width * 0.58],
                dtype=np.float32,
            )
            joints[foot] = target_pos(
                foot,
                fallback_foot,
            )

        return joints

    def _project(self, joints):
        cy = math.cos(self.yaw)
        sy = math.sin(self.yaw)
        cp = math.cos(self.pitch)
        sp = math.sin(self.pitch)
        projected = {}
        scale = min(self.width, self.height) * 0.58

        for name, point in joints.items():
            x, y, z = map(float, point)
            xr = x * cy - y * sy
            yr = x * sy + y * cy
            zr = z * cp - yr * sp
            camera_depth = (
                self.distance
                + z * sp
                + yr * cp
            )
            camera_depth = max(camera_depth, 10.0)
            factor = scale / camera_depth

            projected[name] = (
                int(self.width * 0.5 + xr * factor),
                int(self.height * 0.58 - zr * factor),
                camera_depth,
            )

        return projected

    def _draw_grid(self, image):
        origin = self._project(
            {
                "o": np.array(
                    [0.0, 0.0, 0.0],
                    dtype=np.float32,
                )
            }
        )["o"]

        for value in range(-5, 6):
            p1 = self._project(
                {
                    "a": np.array(
                        [value * 20.0, -100.0, 0.0],
                        dtype=np.float32,
                    ),
                    "b": np.array(
                        [value * 20.0, 100.0, 0.0],
                        dtype=np.float32,
                    ),
                }
            )
            p2 = self._project(
                {
                    "a": np.array(
                        [-100.0, value * 20.0, 0.0],
                        dtype=np.float32,
                    ),
                    "b": np.array(
                        [100.0, value * 20.0, 0.0],
                        dtype=np.float32,
                    ),
                }
            )
            cv2.line(
                image,
                p1["a"][:2],
                p1["b"][:2],
                (24, 31, 39),
                1,
                cv2.LINE_AA,
            )
            cv2.line(
                image,
                p2["a"][:2],
                p2["b"][:2],
                (24, 31, 39),
                1,
                cv2.LINE_AA,
            )

        cv2.circle(
            image,
            origin[:2],
            4,
            (90, 145, 185),
            -1,
            cv2.LINE_AA,
        )

    def _draw_bones(self, image, projected):
        for a, b in BONES:
            if a not in projected or b not in projected:
                continue

            pa = projected[a]
            pb = projected[b]
            thickness = max(
                4,
                int(
                    9
                    - min(pa[2], pb[2]) / 80
                ),
            )

            cv2.line(
                image,
                pa[:2],
                pb[:2],
                (82, 174, 220),
                thickness,
                cv2.LINE_AA,
            )
            cv2.line(
                image,
                pa[:2],
                pb[:2],
                (190, 222, 238),
                max(2, thickness // 3),
                cv2.LINE_AA,
            )

    def _draw_joints(self, image, projected):
        for _, (x, y, depth) in projected.items():
            radius = max(
                5,
                int(12 - depth / 70),
            )
            cv2.circle(
                image,
                (x, y),
                radius,
                (232, 242, 248),
                -1,
                cv2.LINE_AA,
            )

    def _draw_overlay(self, image, targets):
        self._text(
            image,
            "LIVE 3D TRACKER  •  CPU  •  BLENDER OFF",
            0.52,
            y=28,
        )
        cv2.putText(
            image,
            f"IK TARGETS: {len(targets)}",
            (18, 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (130, 190, 225),
            1,
            cv2.LINE_AA,
        )

    def _text(self, image, text, scale, y=None):
        if y is None:
            y = self.height // 2

        size = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            2,
        )[0]

        cv2.putText(
            image,
            text,
            (
                (self.width - size[0]) // 2,
                y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (160, 200, 225),
            2,
            cv2.LINE_AA,
        )

    def _rig_width(self):
        controls = self.reference.get(
            "controls",
            {},
        )
        left = controls.get(
            "left_hand",
            {},
        ).get(
            "position",
            [25.0, 0.0, 50.0],
        )
        right = controls.get(
            "right_hand",
            {},
        ).get(
            "position",
            [-25.0, 0.0, 50.0],
        )
        return max(
            abs(
                float(left[0])
                - float(right[0])
            ),
            40.0,
        )

    def set_view(
        self,
        yaw_degrees=None,
        pitch_degrees=None,
    ):
        if yaw_degrees is not None:
            self.yaw = math.radians(
                float(yaw_degrees)
            )
        if pitch_degrees is not None:
            self.pitch = math.radians(
                float(pitch_degrees)
            )
