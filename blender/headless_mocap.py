import bpy
import json
import os
import socket
import sys
import traceback


HOST = "127.0.0.1"
PORT = 8765


running = True
recording = False
current_frame = 0


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

    if len(args) < 2:
        raise RuntimeError(
            "Se esperaba output_file y reference_file."
        )

    return args[0], args[1]


# ============================================================
# BONE RESOLUTION
# ============================================================

def normalize_bone_name(name):

    if name is None:
        return ""

    value = str(name).strip().lower()

    for char in [
        " ",
        "_",
        ".",
        "-",
        ":",
        "/",
        "\\"
    ]:

        value = value.replace(
            char,
            ""
        )

    return value


def resolve_bone(
    armature,
    requested_name
):

    bone = armature.pose.bones.get(
        requested_name
    )

    if bone is not None:
        return bone

    normalized = (
        normalize_bone_name(
            requested_name
        )
    )

    candidates = []

    for bone in armature.pose.bones:

        if (
            normalize_bone_name(
                bone.name
            )
            == normalized
        ):

            candidates.append(
                bone
            )

    if len(candidates) == 1:

        print(
            f"[BONE] "
            f"'{requested_name}' -> "
            f"'{candidates[0].name}'"
        )

        return candidates[0]

    if len(candidates) > 1:

        print(
            f"[BONE] Varias coincidencias "
            f"para '{requested_name}'"
        )

        for candidate in candidates:

            print(
                f"    -> {candidate.name}"
            )

        return candidates[0]

    print(
        f"[BONE] NO ENCONTRADO: "
        f"'{requested_name}'"
    )

    print(
        "[BONE] Posibles huesos relacionados:"
    )

    for bone in armature.pose.bones:

        name = bone.name.lower()

        if (
            "foot" in name or
            "ik" in name
        ):

            print(
                f"    -> '{bone.name}'"
            )

    return None


# ============================================================
# RIG
# ============================================================

def get_driver_armature():

    armature = bpy.data.objects.get(
        "IK1_regular"
    )

    if armature is None:

        raise RuntimeError(
            "No se encontró "
            "IK1_regular"
        )

    return armature


def generate_rig_reference(
    armature,
    reference_path
):

    requested_controls = {

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
            "FOOT_POLE.R"
    }

    controls = {}

    for logical_name, requested_name in (
        requested_controls.items()
    ):

        bone = resolve_bone(
            armature,
            requested_name
        )

        if bone is None:

            print(
                f"WARNING: "
                f"no existe control "
                f"{requested_name}"
            )

            continue

        position = (
            armature.matrix_world @
            bone.head
        )

        controls[logical_name] = {

            "requested_name":
                requested_name,

            "bone":
                bone.name,

            "position": [
                float(position.x),
                float(position.y),
                float(position.z)
            ]
        }

    root = resolve_bone(
        armature,
        "Bone"
    )

    root_position = [0.0, 0.0, 0.0]

    if root is not None:

        position = (
            armature.matrix_world @
            root.head
        )

        root_position = [
            float(position.x),
            float(position.y),
            float(position.z)
        ]

    data = {

        "version": 1,

        "driver_armature":
            armature.name,

        "root_bone":
            root.name
            if root
            else "Bone",

        "controls":
            controls,

        "root_position":
            root_position
    }

    os.makedirs(
        os.path.dirname(
            reference_path
        ),
        exist_ok=True
    )

    with open(
        reference_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )

    print()
    print(
        "=" * 60
    )
    print(
        "REFERENCIA DEL RIG GENERADA"
    )
    print(
        "=" * 60
    )

    print(
        json.dumps(
            data,
            indent=4
        )
    )


# ============================================================
# COPY
# ============================================================

def create_output_copy(
    output_path
):

    print()
    print(
        "Archivo actual:"
    )

    print(
        bpy.data.filepath
    )

    print(
        "Archivo de salida:"
    )

    print(
        output_path
    )

    bpy.ops.wm.save_as_mainfile(
        filepath=output_path
    )


# ============================================================
# ANIMATION
# ============================================================

def create_action(armature):

    animation = armature.animation_data

    if animation is None:

        animation = (
            armature.animation_data_create()
        )

    action = bpy.data.actions.new(
        "MOCAP_ACTION"
    )

    animation.action = action

    return action


def set_bone_position(
    armature,
    bone,
    position
):

    from mathutils import Vector

    world_position = Vector(
        position
    )

    armature_position = (
        armature.matrix_world.inverted()
        @ world_position
    )

    matrix = bone.matrix.copy()

    matrix.translation = (
        armature_position
    )

    bone.matrix = matrix


def insert_keyframes(
    armature,
    controls,
    root_bone
):

    for bone in controls.values():

        bone.keyframe_insert(
            data_path="location",
            frame=current_frame
        )

        bone.keyframe_insert(
            data_path="rotation_euler",
            frame=current_frame
        )

    if root_bone:

        root_bone.keyframe_insert(
            data_path="location",
            frame=current_frame
        )

        root_bone.keyframe_insert(
            data_path="rotation_euler",
            frame=current_frame
        )


# ============================================================
# POSE
# ============================================================

def apply_pose(
    armature,
    data
):

    controls = {}

    for logical_name, info in (
        data["controls"].items()
    ):

        bone = resolve_bone(
            armature,
            info["bone"]
        )

        if bone:

            controls[
                logical_name
            ] = bone

    for logical_name, target in (
        data.get("targets", {}).items()
    ):

        bone = controls.get(
            logical_name
        )

        if bone is None:
            continue

        set_bone_position(
            armature,
            bone,
            target
        )

    root = resolve_bone(
        armature,
        data.get(
            "root_bone",
            "Bone"
        )
    )

    if root and "root" in data:

        set_bone_position(
            armature,
            root,
            data["root"]
        )

    bpy.context.view_layer.update()

    return controls, root


# ============================================================
# SAVE
# ============================================================

def save_file(
    output_path
):

    bpy.context.scene.frame_set(
        current_frame
    )

    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(
        filepath=output_path
    )

    print(
        f"Guardado: {output_path}"
    )


# ============================================================
# PACKET PROCESSING
# ============================================================

def process_packet(
    packet,
    armature,
    output_path
):

    global running
    global recording
    global current_frame

    packet_type = packet.get(
        "type"
    )

    if packet_type == "record_start":

        current_frame = 0

        create_action(
            armature
        )

        recording = True

        print(
            "Recording START"
        )

        return

    if packet_type == "record_stop":

        recording = False

        save_file(
            output_path
        )

        print(
            "Recording STOP"
        )

        return

    if packet_type == "mocap_pose":

        if not recording:
            return

        controls, root = apply_pose(
            armature,
            packet
        )

        insert_keyframes(
            armature,
            controls,
            root
        )

        current_frame += 1

        return

    if packet_type == "shutdown":

        recording = False

        save_file(
            output_path
        )

        running = False

        print(
            "Shutdown recibido."
        )


# ============================================================
# MAIN BLENDER
# ============================================================

def main():

    global running

    output_path, reference_path = (
        get_arguments()
    )

    source_path = (
        bpy.data.filepath
    )

    print()
    print(
        "=" * 60
    )

    print(
        "MOCAP BLENDER HEADLESS"
    )

    print(
        "=" * 60
    )

    print(
        f"Fuente: {source_path}"
    )

    create_output_copy(
        output_path
    )

    armature = (
        get_driver_armature()
    )

    generate_rig_reference(
        armature,
        reference_path
    )

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.bind(
        (HOST, PORT)
    )

    sock.settimeout(0.5)

    print()
    print(
        f"Blender Mocap Server: "
        f"{HOST}:{PORT}"
    )

    print(
        "Blender LISTO."
    )

    try:

        while running:

            try:

                data, address = (
                    sock.recvfrom(65535)
                )

            except socket.timeout:

                continue

            try:

                packet = json.loads(
                    data.decode("utf-8")
                )

                process_packet(
                    packet,
                    armature,
                    output_path
                )

            except Exception as exc:

                print(
                    "Error procesando packet:"
                )

                print(exc)

                traceback.print_exc()

    finally:

        sock.close()

        print(
            "Blender quit."
        )


if __name__ == "__main__":

    try:
        main()

    except Exception:

        traceback.print_exc()

        raise