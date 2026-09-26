import bpy


ARMATURES = [
    "RootNode",
    "IK1_regular",
]


def print_header(title):
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def inspect_armature(name):
    armature = bpy.data.objects.get(name)

    if armature is None:
        print(f"\nNO EXISTE ARMATURE: {name}")
        return

    print_header(f"ARMATURE: {name}")

    print(f"Object type: {armature.type}")
    print(f"Bone count: {len(armature.data.bones)}")

    print("\nBONES:")

    for bone in armature.data.bones:
        print(
            f"  {bone.name}"
            f" | parent={bone.parent.name if bone.parent else 'NONE'}"
            f" | head={tuple(round(v, 4) for v in bone.head_local)}"
            f" | tail={tuple(round(v, 4) for v in bone.tail_local)}"
        )


def inspect_constraints():

    root = bpy.data.objects.get("RootNode")

    if root is None:
        print("\nNO EXISTE RootNode")
        return

    print_header("ROOTNODE IK CONSTRAINTS")

    for pose_bone in root.pose.bones:

        ik_constraints = [
            c
            for c in pose_bone.constraints
            if c.type == "IK"
        ]

        if not ik_constraints:
            continue

        print()
        print(f"BONE: {pose_bone.name}")

        for c in ik_constraints:

            print(f"  Constraint : {c.name}")
            print(f"  Type       : {c.type}")
            print(f"  Influence  : {c.influence}")
            print(
                f"  Target     : "
                f"{c.target.name if c.target else 'NONE'}"
            )
            print(f"  Subtarget  : {c.subtarget}")
            print(f"  Chain      : {c.chain_count}")
            print(f"  Use Tail   : {getattr(c, 'use_tail', 'N/A')}")
            print(
                f"  Target Pos : "
                f"{getattr(c, 'target_space', 'N/A')}"
            )
            print(
                f"  Owner Pos  : "
                f"{getattr(c, 'owner_space', 'N/A')}"
            )


def find_foot_names():

    armature = bpy.data.objects.get("IK1_regular")

    if armature is None:
        return

    print_header("POSSIBLE FOOT IK / POLE NAMES")

    for bone in armature.data.bones:

        name = bone.name.upper()

        if (
            "FOOT" in name
            or "ANKLE" in name
            or "LEG" in name
            or "POLE" in name
            or "IK" in name
        ):
            print(
                f"  {bone.name}"
                f" | head={tuple(round(v, 4) for v in bone.head_local)}"
                f" | tail={tuple(round(v, 4) for v in bone.tail_local)}"
            )


def inspect_control_constraints():

    armature = bpy.data.objects.get("IK1_regular")

    if armature is None:
        return

    print_header("IK1_REGULAR CONTROL CONSTRAINTS")

    for pose_bone in armature.pose.bones:

        if not pose_bone.constraints:
            continue

        print()
        print(f"CONTROL: {pose_bone.name}")

        for c in pose_bone.constraints:

            print(f"  Constraint : {c.name}")
            print(f"  Type       : {c.type}")
            print(f"  Influence  : {c.influence}")

            if hasattr(c, "target"):
                print(
                    f"  Target     : "
                    f"{c.target.name if c.target else 'NONE'}"
                )

            if hasattr(c, "subtarget"):
                print(f"  Subtarget  : {c.subtarget}")


def main():

    print_header("FINAL RIG INSPECTION")

    print(
        f"Blender version: "
        f"{bpy.app.version_string}"
    )

    inspect_armature("IK1_regular")

    inspect_armature("RootNode")

    find_foot_names()

    inspect_constraints()

    inspect_control_constraints()

    print_header("END")

    print(
        "\nNo se modifico ni se guardo el .blend."
    )


main()