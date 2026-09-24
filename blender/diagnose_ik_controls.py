import bpy
import sys
from mathutils import Vector


# ============================================================
# CONFIGURACION
# ============================================================

ARMATURE_NAME = "IK1_regular"

CONTROL_NAMES = [
    "HAND_IK.L",
    "HAND_IK.R",
    "HAND_POLE.L",
    "HAND_POLE.R",
    "FOOT_IK.L",
    "FOOT_IK.R",
    "FOOT_POLE.L",
    "FOOT_POLE.R",
]


# ============================================================
# UTILIDADES
# ============================================================

def fmt_vector(v):

    return (
        f"({v.x:.6f}, "
        f"{v.y:.6f}, "
        f"{v.z:.6f})"
    )


def world_head(armature, pose_bone):

    return (
        armature.matrix_world
        @ pose_bone.head
    )


def world_tail(armature, pose_bone):

    return (
        armature.matrix_world
        @ pose_bone.tail
    )


def world_origin(armature, pose_bone):

    return (
        armature.matrix_world
        @ pose_bone.matrix.translation
    )


def print_matrix(label, matrix):

    print(label)

    for row in matrix:

        print(
            "    "
            + " ".join(
                f"{value: .6f}"
                for value in row
            )
        )


# ============================================================
# BUSCAR ARMATURE
# ============================================================

def find_armature():

    armature = bpy.data.objects.get(
        ARMATURE_NAME
    )

    if armature is None:

        raise RuntimeError(
            f"No existe el armature "
            f"'{ARMATURE_NAME}'"
        )

    if armature.type != "ARMATURE":

        raise RuntimeError(
            f"{ARMATURE_NAME} no es ARMATURE."
        )

    return armature


# ============================================================
# INFORMACION DEL CONTROL
# ============================================================

def inspect_control(
    armature,
    pose_bone
):

    print()
    print("=" * 70)

    print(
        f"CONTROL: {pose_bone.name}"
    )

    print("=" * 70)

    bone = pose_bone.bone

    print(
        f"Parent: "
        f"{bone.parent.name if bone.parent else 'NONE'}"
    )

    print(
        f"Head local: "
        f"{fmt_vector(bone.head_local)}"
    )

    print(
        f"Tail local: "
        f"{fmt_vector(bone.tail_local)}"
    )

    print(
        f"Pose location: "
        f"{fmt_vector(pose_bone.location)}"
    )

    print(
        f"Pose rotation: "
        f"{pose_bone.rotation_quaternion}"
    )

    print(
        f"Pose scale: "
        f"{fmt_vector(pose_bone.scale)}"
    )

    print()

    print(
        "WORLD HEAD:"
    )

    print(
        fmt_vector(
            world_head(
                armature,
                pose_bone
            )
        )
    )

    print(
        "WORLD TAIL:"
    )

    print(
        fmt_vector(
            world_tail(
                armature,
                pose_bone
            )
        )
    )

    print(
        "WORLD ORIGIN:"
    )

    print(
        fmt_vector(
            world_origin(
                armature,
                pose_bone
            )
        )
    )

    print()

    print_matrix(
        "POSE MATRIX:",
        pose_bone.matrix
    )

    print()

    print_matrix(
        "MATRIX BASIS:",
        pose_bone.matrix_basis
    )

    # --------------------------------------------------------
    # CONSTRAINTS
    # --------------------------------------------------------

    print()
    print("CONSTRAINTS:")

    if not pose_bone.constraints:

        print("    NONE")

    for constraint in pose_bone.constraints:

        print(
            f"    Name      : {constraint.name}"
        )

        print(
            f"    Type      : {constraint.type}"
        )

        print(
            f"    Influence : {constraint.influence:.6f}"
        )

        print(
            f"    Enabled   : "
            f"{constraint.enabled}"
        )

        print(
            f"    Muted     : "
            f"{constraint.mute}"
        )

        if hasattr(
            constraint,
            "target"
        ):

            target = constraint.target

            print(
                f"    Target    : "
                f"{target.name if target else 'NONE'}"
            )

        if hasattr(
            constraint,
            "subtarget"
        ):

            print(
                f"    Subtarget : "
                f"{constraint.subtarget}"
            )

        if hasattr(
            constraint,
            "owner_space"
        ):

            print(
                f"    Owner     : "
                f"{constraint.owner_space}"
            )

        if hasattr(
            constraint,
            "target_space"
        ):

            print(
                f"    Target    : "
                f"{constraint.target_space}"
            )

        if hasattr(
            constraint,
            "inverse_matrix"
        ):

            print_matrix(
                "    INVERSE MATRIX:",
                constraint.inverse_matrix
            )

        print()

    # --------------------------------------------------------
    # DRIVERS
    # --------------------------------------------------------

    print("DRIVERS:")

    driver_found = False

    for fcurve in armature.animation_data.drivers \
            if armature.animation_data else []:

        if pose_bone.name in fcurve.data_path:

            driver_found = True

            print(
                f"    {fcurve.data_path}"
            )

    if not driver_found:

        print("    NONE")


# ============================================================
# EVALUACION
# ============================================================

def evaluated_position(
    armature,
    pose_bone
):

    depsgraph = bpy.context.evaluated_depsgraph_get()

    evaluated_armature = (
        armature.evaluated_get(
            depsgraph
        )
    )

    evaluated_pose = (
        evaluated_armature.pose.bones[
            pose_bone.name
        ]
    )

    return (
        evaluated_armature.matrix_world
        @ evaluated_pose.head
    )


# ============================================================
# PRUEBA 1
# LOCATION
# ============================================================

def test_location(
    armature,
    pose_bone
):

    print()
    print("-" * 70)

    print(
        f"TEST LOCATION: "
        f"{pose_bone.name}"
    )

    print("-" * 70)

    original_location = (
        pose_bone.location.copy()
    )

    before = evaluated_position(
        armature,
        pose_bone
    )

    print(
        "Antes:"
        f" {fmt_vector(before)}"
    )

    # Mover +10 en X
    pose_bone.location.x += 10.0

    bpy.context.view_layer.update()

    after = evaluated_position(
        armature,
        pose_bone
    )

    print(
        "Después:"
        f" {fmt_vector(after)}"
    )

    print(
        "Delta:"
        f" {fmt_vector(after - before)}"
    )

    # Restaurar
    pose_bone.location = (
        original_location
    )

    bpy.context.view_layer.update()


# ============================================================
# PRUEBA 2
# MATRIX BASIS
# ============================================================

def test_matrix_basis(
    armature,
    pose_bone
):

    print()
    print("-" * 70)

    print(
        f"TEST MATRIX BASIS: "
        f"{pose_bone.name}"
    )

    print("-" * 70)

    original = (
        pose_bone.matrix_basis.copy()
    )

    before = evaluated_position(
        armature,
        pose_bone
    )

    print(
        "Antes:"
        f" {fmt_vector(before)}"
    )

    matrix = (
        pose_bone.matrix_basis.copy()
    )

    matrix.translation.x += 10.0

    pose_bone.matrix_basis = matrix

    bpy.context.view_layer.update()

    after = evaluated_position(
        armature,
        pose_bone
    )

    print(
        "Después:"
        f" {fmt_vector(after)}"
    )

    print(
        "Delta:"
        f" {fmt_vector(after - before)}"
    )

    # Restaurar
    pose_bone.matrix_basis = original

    bpy.context.view_layer.update()


# ============================================================
# PRUEBA 3
# MATRIX
# ============================================================

def test_matrix(
    armature,
    pose_bone
):

    print()
    print("-" * 70)

    print(
        f"TEST MATRIX WORLD: "
        f"{pose_bone.name}"
    )

    print("-" * 70)

    original = (
        pose_bone.matrix.copy()
    )

    before = evaluated_position(
        armature,
        pose_bone
    )

    print(
        "Antes:"
        f" {fmt_vector(before)}"
    )

    matrix = (
        pose_bone.matrix.copy()
    )

    matrix.translation.x += 10.0

    pose_bone.matrix = matrix

    bpy.context.view_layer.update()

    after = evaluated_position(
        armature,
        pose_bone
    )

    print(
        "Después:"
        f" {fmt_vector(after)}"
    )

    print(
        "Delta:"
        f" {fmt_vector(after - before)}"
    )

    # Restaurar
    pose_bone.matrix = original

    bpy.context.view_layer.update()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("DIAGNOSTICO IK1_REGULAR")
    print("=" * 80)

    armature = find_armature()

    print()
    print(
        f"Armature: {armature.name}"
    )

    print(
        f"World Matrix:"
    )

    print_matrix(
        "",
        armature.matrix_world
    )

    # --------------------------------------------------------
    # INFORMACION
    # --------------------------------------------------------

    for name in CONTROL_NAMES:

        pose_bone = (
            armature.pose.bones.get(
                name
            )
        )

        if pose_bone is None:

            print()
            print(
                f"NO ENCONTRADO: {name}"
            )

            continue

        inspect_control(
            armature,
            pose_bone
        )

    # --------------------------------------------------------
    # PRUEBAS
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("PRUEBAS DE TRANSFORMACION")
    print("=" * 80)

    test_names = [
        "HAND_IK.L",
        "HAND_IK.R",
        "HAND_POLE.L",
        "HAND_POLE.R",
    ]

    for name in test_names:

        pose_bone = (
            armature.pose.bones.get(
                name
            )
        )

        if pose_bone is None:

            continue

        test_location(
            armature,
            pose_bone
        )

        test_matrix_basis(
            armature,
            pose_bone
        )

        test_matrix(
            armature,
            pose_bone
        )

    print()
    print("=" * 80)
    print("DIAGNOSTICO TERMINADO")
    print("=" * 80)
    print()
    print(
        "No se modifico ni se guardo el .blend."
    )


main()