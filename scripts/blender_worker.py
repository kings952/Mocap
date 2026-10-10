"""Worker Blender 4.4: aplica poses y verifica que la animación quedó guardada."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

ALIASES = {
    "Bone": ("Bone",),
    "HAND_IK.L": ("HAND_IK.L",), "HAND_IK.R": ("HAND_IK.R",),
    "HAND_POLE.L": ("HAND_POLE.L",), "HAND_POLE.R": ("HAND_POLE.R",),
    "FOOT_IK.L": ("FOOT_IK.L",), "FOOT_IK.R": ("FOOT_IK.R", "FOOT_IK.R "),
    "FOOT_POLE.L": ("FOOT_POLE.L",), "FOOT_POLE.R": ("FOOT_POLE.R",),
}
TARGETS = {
    "HAND_IK.L": ("LEFT_WRIST", "LEFT_SHOULDER"),
    "HAND_IK.R": ("RIGHT_WRIST", "RIGHT_SHOULDER"),
    "FOOT_IK.L": ("LEFT_ANKLE", "LEFT_HIP"),
    "FOOT_IK.R": ("RIGHT_ANKLE", "RIGHT_HIP"),
    "HAND_POLE.L": ("LEFT_ELBOW", "LEFT_SHOULDER"),
    "HAND_POLE.R": ("RIGHT_ELBOW", "RIGHT_SHOULDER"),
    "FOOT_POLE.L": ("LEFT_KNEE", "LEFT_HIP"),
    "FOOT_POLE.R": ("RIGHT_KNEE", "RIGHT_HIP"),
}
GAIN = 2.5

def parse():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("inspect", "apply"):
        s = sub.add_parser(name); s.add_argument("--armature", default="IK1_regular")
        if name == "apply":
            s.add_argument("--data", required=True); s.add_argument("--output", required=True)
    return p.parse_args(argv)

def armature(name):
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "ARMATURE":
        raise RuntimeError(f"No se encontró el armature '{name}'.")
    return obj

def resolve_controls(obj):
    names = {b.name for b in obj.pose.bones}; resolved = {}; missing = []
    for logical, options in ALIASES.items():
        actual = next((n for n in options if n in names), None)
        if actual is None: missing.append(logical)
        else: resolved[logical] = actual
    return {"armature": obj.name, "controls_found": list(resolved),
            "controls_resolved": resolved, "controls_missing": missing,
            "bone_count": len(obj.pose.bones), "ok": not missing}

def load_data(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not data.get("keyframes"):
        raise RuntimeError("El JSON no contiene keyframes.")
    return data

def point_map(item):
    return {p["name"]: p for p in item["pose"]["landmarks"]}

def relative_point(points, baseline, point, anchor):
    p, a, bp, ba = points.get(point), points.get(anchor), baseline.get(point), baseline.get(anchor)
    if not all((p, a, bp, ba)):
        return Vector((0.0, 0.0, 0.0))
    # Movimiento relativo a la primera pose; la calibración no desplaza el rig.
    dx = (p["x"]-a["x"]) - (bp["x"]-ba["x"])
    dy = (p["y"]-a["y"]) - (bp["y"]-ba["y"])
    dz = (p["z"]-a["z"]) - (bp["z"]-ba["z"])
    return Vector((dx, -dz, -dy)) * GAIN

def action_stats(obj):
    action = obj.animation_data.action if obj.animation_data else None
    if action is None:
        return {"action": None, "fcurves": 0, "key_points": 0}
    curves = []
    # Legacy actions expose action.fcurves. Blender 4.4 can also use layered
    # actions, whose curves live inside each keyframe strip's channel bags.
    try:
        curves.extend(list(action.fcurves))
    except (AttributeError, RuntimeError, TypeError):
        pass
    if not curves:
        for layer in getattr(action, "layers", []):
            for strip in getattr(layer, "strips", []):
                for bag in getattr(strip, "channelbags", []):
                    curves.extend(list(getattr(bag, "fcurves", [])))
    keys = sum(len(fc.keyframe_points) for fc in curves)
    return {"action": action.name, "fcurves": len(curves), "key_points": keys}

def apply_keyframes(obj, data):
    info = resolve_controls(obj)
    if not info["ok"]:
        raise RuntimeError("Faltan controles del rig: " + ", ".join(info["controls_missing"]))
    items = sorted(data["keyframes"], key=lambda x: int(x["frame"]))
    baseline = point_map(items[0])
    controls = {logical: obj.pose.bones[actual] for logical, actual in info["controls_resolved"].items()}
    rest = {name: (bone.location.copy(), bone.rotation_euler.copy())
            for name, bone in controls.items()}
    scene = bpy.context.scene
    # Evita que la exportación parezca exitosa si no se generó ninguna curva.
    for item in items:
        frame = max(1, int(item["frame"]))
        scene.frame_set(frame)
        points = point_map(item)
        for logical, pair in TARGETS.items():
            if logical not in controls:
                continue
            point, anchor = pair
            bone = controls[logical]
            base_location, base_rotation = rest[logical]
            delta = relative_point(points, baseline, point, anchor)
            bone.location = base_location + delta
            bone.rotation_euler = base_rotation
            bone.keyframe_insert(data_path="location", frame=frame, group="MOCAP | " + logical,
                                 options={"INSERTKEY_VISUAL"})
            bone.keyframe_insert(data_path="rotation_euler", frame=frame, group="MOCAP | " + logical,
                                 options={"INSERTKEY_VISUAL"})
        root = controls["Bone"]
        root.keyframe_insert(data_path="location", frame=frame, group="MOCAP | Root")
    scene.frame_start = 1
    scene.frame_end = max(1, max(int(x["frame"]) for x in items))
    scene.frame_set(1)
    stats = action_stats(obj)
    if not stats["action"] or stats["fcurves"] == 0 or stats["key_points"] == 0:
        raise RuntimeError("Blender no creó curvas de animación; se cancela el guardado.")
    return info, stats, len(items)

def main():
    args = parse()
    try:
        obj = armature(args.armature)
        info = resolve_controls(obj)
        if args.command == "inspect":
            print(json.dumps({"ok": info["ok"], "message": "Inspección completada", "rig": info}, ensure_ascii=False))
            return 0
        data = load_data(args.data)
        info, stats, count = apply_keyframes(obj, data)
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        # Comprueba que el archivo se escribió y la acción sigue presente en memoria.
        if not output.is_file() or output.stat().st_size < 1024:
            raise RuntimeError("Blender no generó un archivo .blend válido.")
        print(json.dumps({"ok": True, "message": f"Guardado {output}: {count} poses, {stats['key_points']} puntos de keyframe.",
                          "output": str(output), "poses": count, "animation": stats, "rig": info}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "message": str(exc)}, ensure_ascii=False))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
