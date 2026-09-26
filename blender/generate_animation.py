import sys
import json
import argparse
import unicodedata

import bpy


# ============================================================
# ARGUMENTOS
# ============================================================

def arguments():

    if "--" not in sys.argv:
        return argparse.Namespace(
            poses=None,
            output=None,
        )

    args = sys.argv[
        sys.argv.index("--") + 1:
    ]

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--poses",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    return parser.parse_args(args)


# ============================================================
# NOMBRES DE HUESOS
# ============================================================

def normalize_bone_name(name):

    name = unicodedata.normalize(
        "NFKC",
        name,
    )

    name = name.replace(
        "\u00A0",
        " ",
    )

    name = " ".join(
        name.split()
    )

    return name.casefold()


def find_pose_bone(
    armature,
    requested_name,
):

    exact = armature.pose.bones.get(
        requested_name
    )

    if exact is not None:
        return exact

    wanted = normalize_bone_name(
        requested_name
    )

    for bone in armature.pose.bones:

        if (
            normalize_bone_name(
                bone.name
            )
            == wanted
        ):
            return bone

    return None


# ============================================================
# REDUCCIÓN
# ============================================================

def point_difference(a, b):

    max_difference = 0.0

    for name in a:

        if name not in b:
            continue

        pa = a[name]
        pb = b[name]

        if (
            pa["confidence"] < 0.35
            or pb["confidence"] < 0.35
        ):
            continue

        dx = pb["x"] - pa["x"]
        dy = pb["y"] - pa["y"]

        value = (
            (dx * dx + dy * dy)
            ** 0.5
        )

        max_difference = max(
            max_difference,
            value,
        )

    return max_difference


def reduce_frames(
    frames,
    tolerance=0.4,
):

    if not frames:
        return []

    if len(frames) <= 2:
        return frames

    result = [
        frames[0]
    ]

    last_saved = frames[0]

    for current in frames[1:-1]:

        a = last_saved.get(
            "keypoints",
            {},
        )

        b = current.get(
            "keypoints",
            {},
        )

        scale = (
            last_saved
            .get("metrics", {})
            .get("body_scale", 100.0)
        )

        scale = max(
            float(scale),
            1.0,
        )

        difference = (
            point_difference(
                a,
                b,
            )
            / scale
        )

        if difference >= tolerance:

            result.append(current)

            last_saved = current

    if result[-1] is not frames[-1]:

        result.append(
            frames[-1]
        )

    return result


# ============================================================
# APLICAR
# ============================================================

def apply_animation(
    armature,
    frames,
):

    driver = bpy.data.objects.get(
        "IK1_regular"
    )

    if driver is None:
        raise RuntimeError(
            "No se encontró IK1_regular."
        )

    driver.animation_data_create()

    action = bpy.data.actions.new(
        "Live_Mocap_Action"
    )

    action.use_fake_user = True

    driver.animation_data.action = action

    scene = bpy.context.scene

    scene.render.fps = 10
    scene.render.fps_base = 1.0

    scene.frame_start = 0

    scene.frame_end = max(
        frame["frame_id"]
        for frame in frames
    )

    # --------------------------------------------------------
    # Resolver controles
    # --------------------------------------------------------

    controls = {

        "left_hand":
            "HAND_IK.L",

        "right_hand":
            "HAND_IK.R",

        "left_hand_pole":
            "HAND_POLE.L",

        "right_hand_pole":
            "HAND_POLE.R",

        "left_foot":
            "FOOT_IK.L",

        "right_foot":
            "FOOT_IK.R",

        "left_foot_pole":
            "FOOT_POLE.L",

        "right_foot_pole":
            "FOOT_POLE.R",
    }

    resolved = {}

    for logical, name in controls.items():

        bone = find_pose_bone(
            driver,
            name,
        )

        if bone is None:

            print(
                f"[WARNING] "
                f"No encontrado: {name}"
            )

            continue

        resolved[logical] = bone

        print(
            f"[OK] {logical} -> "
            f"{bone.name!r}"
        )

    # --------------------------------------------------------
    # Actualmente la captura conserva
    # todos los keypoints.
    #
    # La conversión completa del cuerpo
    # se hará progresivamente.
    # --------------------------------------------------------

    print(
        f"[BLENDER] Aplicando "
        f"{len(frames)} frames."
    )

    for packet in frames:

        frame_id = int(
            packet["frame_id"]
        )

        scene.frame_set(
            frame_id
        )

        # Actualmente dejamos preparada
        # la estructura de animación.
        #
        # Los IK se incorporarán aquí cuando
        # hagamos el retarget 3D completo.

        for bone in resolved.values():

            bone.keyframe_insert(
                data_path="location",
                frame=frame_id,
                group="Live Mocap",
            )

    # --------------------------------------------------------
    # Interpolación LINEAR
    # --------------------------------------------------------

    for fcurve in action.fcurves:

        for keyframe in fcurve.keyframe_points:

            keyframe.interpolation = (
                "LINEAR"
            )

    print(
        f"[BLENDER] Action creada: "
        f"{action.name}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    args = arguments()

    if not args.poses:
        raise RuntimeError(
            "Falta --poses"
        )

    if not args.output:
        raise RuntimeError(
            "Falta --output"
        )

    print(
        "[BLENDER] "
        "Generando animación..."
    )

    with open(
        args.poses,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    original_frames = data["frames"]

    print(
        f"[BLENDER] Capturados: "
        f"{len(original_frames)}"
    )

    frames = reduce_frames(
        original_frames,
        tolerance=0.4,
    )

    print(
        f"[BLENDER] Keyframes reducidos: "
        f"{len(frames)}"
    )

    armature = bpy.data.objects.get(
        "RootNode"
    )

    if armature is None:
        raise RuntimeError(
            "No se encontró RootNode."
        )

    apply_animation(
        armature,
        frames,
    )

    bpy.context.scene.frame_set(0)

    bpy.ops.wm.save_as_mainfile(
        filepath=args.output
    )

    print(
        f"[BLENDER] Guardado: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()