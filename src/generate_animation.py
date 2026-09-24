import bpy
import sys
import json
from pathlib import Path
from mathutils import Vector


# ============================================================
# ARGUMENTOS
# ============================================================

def get_arguments():

    args = sys.argv

    if "--" not in args:

        raise RuntimeError(
            "No se recibieron argumentos."
        )

    args = args[
        args.index("--") + 1:
    ]

    if len(args) < 3:

        raise RuntimeError(
            "Uso:\n"
            "blender --background archivo.blend "
            "--python generate_animation.py "
            "-- poses.json salida.blend referencia.json"
        )

    poses_file = Path(args[0])
    output_file = Path(args[1])
    reference_file = Path(args[2])

    return (
        poses_file,
        output_file,
        reference_file,
    )


# ============================================================
# CARGAR JSON
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# RESOLVER NOMBRE
# ============================================================

def normalize_name(name):

    return (
        str(name)
        .strip()
        .lower()
        .replace("_", "")
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
    )


def resolve_pose_bone(
    armature,
    name
):

    if name in armature.pose.bones:

        return armature.pose.bones[name]

    wanted = normalize_name(name)

    for bone in armature.pose.bones:

        if normalize_name(
            bone.name
        ) == wanted:

            return bone

    return None


# ============================================================
# ENCONTRAR ARMATURE
# ============================================================

def find_armature():

    armature = bpy.data.objects.get(
        "IK1_regular"
    )

    if armature is not None:

        return armature

    for obj in bpy.data.objects:

        if obj.type == "ARMATURE":

            return obj

    raise RuntimeError(
        "No se encontró ningún armature."
    )


# ============================================================
# CREAR ACTION
# ============================================================

def create_action(
    armature
):

    if armature.animation_data is None:

        armature.animation_data_create()

    action = bpy.data.actions.get(
        "MOCAP_ACTION"
    )

    if action is not None:

        bpy.data.actions.remove(
            action
        )

    action = bpy.data.actions.new(
        "MOCAP_ACTION"
    )

    armature.animation_data.action = action

    return action


# ============================================================
# APLICAR TARGET
# ============================================================

def apply_target(
    armature,
    pose_bone,
    world_position
):

    target_world = Vector(
        world_position
    )

    inv_world = (
        armature.matrix_world.inverted()
    )

    target_armature = (
        inv_world
        @ target_world
    )

    # --------------------------------------------------------
    # Usamos matrix_basis.
    #
    # No utilizamos operadores bpy.ops.
    # --------------------------------------------------------

    current_world = (
        armature.matrix_world
        @ pose_bone.matrix
        @ Vector((0, 0, 0))
    )

    delta = (
        target_armature
        - (
            armature.matrix_world.inverted()
            @ current_world
        )
    )

    pose_bone.location += delta


# ============================================================
# PROCESAR FRAME
# ============================================================

def process_frame(
    armature,
    frame_data,
    mapping
):

    targets = frame_data.get(
        "targets",
        {}
    )

    for logical_name, position in targets.items():

        bone_name = mapping.get(
            logical_name
        )

        if not bone_name:

            continue

        pose_bone = resolve_pose_bone(
            armature,
            bone_name
        )

        if pose_bone is None:

            continue

        apply_target(
            armature,
            pose_bone,
            position
        )

        pose_bone.keyframe_insert(
            data_path="location"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("========================================")
    print("MOCAP BLENDER GENERATOR")
    print("========================================")

    (
        poses_file,
        output_file,
        reference_file,
    ) = get_arguments()

    print(
        f"Poses: {poses_file}"
    )

    print(
        f"Output: {output_file}"
    )

    # --------------------------------------------------------
    # Cargar datos
    # --------------------------------------------------------

    poses_data = load_json(
        poses_file
    )

    mapping_data = load_json(
        reference_file
    )

    # --------------------------------------------------------
    # Armature
    # --------------------------------------------------------

    armature = find_armature()

    print(
        f"Armature: {armature.name}"
    )

    # --------------------------------------------------------
    # Mapping
    # --------------------------------------------------------

    controls = (
        mapping_data
        .get("controls", {})
    )

    mapping = {}

    for logical_name, data in controls.items():

        if isinstance(data, dict):

            mapping[
                logical_name
            ] = data.get(
                "bone_name"
                or data.get("name")
            )

        else:

            mapping[
                logical_name
            ] = data

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------

    action = create_action(
        armature
    )

    print(
        f"Action: {action.name}"
    )

    # --------------------------------------------------------
    # Frames
    # --------------------------------------------------------

    frames = poses_data.get(
        "frames",
        []
    )

    fps = poses_data.get(
        "fps",
        30
    )

    scene = bpy.context.scene

    scene.render.fps = fps

    print(
        f"Frames: {len(frames)}"
    )

    for index, frame_data in enumerate(
        frames
    ):

        frame_number = (
            index + 1
        )

        scene.frame_set(
            frame_number
        )

        process_frame(
            armature,
            frame_data,
            mapping
        )

        if index % 30 == 0:

            print(
                f"Frame "
                f"{index + 1}/"
                f"{len(frames)}"
            )

    # --------------------------------------------------------
    # Timeline
    # --------------------------------------------------------

    scene.frame_start = 1

    scene.frame_end = max(
        len(frames),
        1
    )

    # --------------------------------------------------------
    # Guardar
    # --------------------------------------------------------

    print()
    print("Guardando .blend...")

    bpy.ops.wm.save_as_mainfile(
        filepath=str(
            output_file
        )
    )

    print()
    print("========================================")
    print("ANIMACION GENERADA")
    print("========================================")

    print(
        output_file
    )

def normalize_bone_name(name):
    return " ".join(name.strip().split()).casefold()


def find_pose_bone(armature, requested_name):
    wanted = normalize_bone_name(requested_name)

    # 1. Coincidencia exacta
    bone = armature.pose.bones.get(requested_name)

    if bone is not None:
        return bone

    # 2. Coincidencia normalizada
    for candidate in armature.pose.bones:
        if normalize_bone_name(candidate.name) == wanted:
            return candidate

    return None



if __name__ == "__main__":

    main()