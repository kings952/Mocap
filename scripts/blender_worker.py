"""Worker ejecutado por Blender 4.4.

Uso:
  blender -b archivo.blend --python scripts/blender_worker.py -- inspect --armature IK1_regular
  blender -b archivo.blend --python scripts/blender_worker.py -- apply --armature IK1_regular --data poses.json --output salida.blend
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ALIASES={
 "Bone":("Bone",),
 "HAND_IK.L":("HAND_IK.L",),
 "HAND_IK.R":("HAND_IK.R",),
 "HAND_POLE.L":("HAND_POLE.L",),
 "HAND_POLE.R":("HAND_POLE.R",),
 "FOOT_IK.L":("FOOT_IK.L",),
 "FOOT_IK.R":("FOOT_IK.R","FOOT_IK.R "),
 "FOOT_POLE.L":("FOOT_POLE.L",),
 "FOOT_POLE.R":("FOOT_POLE.R",),
}

def parse():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    for name in ("inspect","apply"):
        s=sub.add_parser(name); s.add_argument("--armature",default="IK1_regular")
        if name=="apply":
            s.add_argument("--data",required=True); s.add_argument("--output",required=True)
    return p.parse_args(argv)

def armature(name):
    obj=bpy.data.objects.get(name)
    if obj is None or obj.type!="ARMATURE":
        raise RuntimeError(f"No se encontró armature '{name}'.")
    return obj

def resolve_controls(obj):
    names={b.name for b in obj.pose.bones}
    resolved={}
    missing=[]
    for logical,options in ALIASES.items():
        actual=next((n for n in options if n in names),None)
        if actual is None: missing.append(logical)
        else: resolved[logical]=actual
    return resolved,missing

def inspect_rig(obj):
    resolved,missing=resolve_controls(obj)
    return {"armature":obj.name,"controls_found":list(resolved),
            "controls_resolved":resolved,"controls_missing":missing,
            "bone_count":len(obj.pose.bones),"ok":not missing}

def load_data(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def landmarks(item):
    return {p["name"]:p for p in item["pose"]["landmarks"]}

def delta_point(points,name,anchor):
    p,a=points.get(name),points.get(anchor)
    if not p or not a:return Vector((0,0,0))
    return Vector((p["x"]-a["x"],-(p["z"]-a["z"]),-(p["y"]-a["y"])))

def apply_keyframes(obj,data):
    info=inspect_rig(obj)
    if not info["ok"]:
        raise RuntimeError("Rig incompleto: faltan "+", ".join(info["controls_missing"]))
    controls={logical:obj.pose.bones[actual] for logical,actual in info["controls_resolved"].items()}
    anchors={n:controls[n].matrix.copy() for n in controls}
    scene=bpy.context.scene
    targets={
      "HAND_IK.L":("LEFT_WRIST","LEFT_SHOULDER"),
      "HAND_IK.R":("RIGHT_WRIST","RIGHT_SHOULDER"),
      "FOOT_IK.L":("LEFT_ANKLE","LEFT_HIP"),
      "FOOT_IK.R":("RIGHT_ANKLE","RIGHT_HIP"),
      "HAND_POLE.L":("LEFT_ELBOW","LEFT_SHOULDER"),
      "HAND_POLE.R":("RIGHT_ELBOW","RIGHT_SHOULDER"),
      "FOOT_POLE.L":("LEFT_KNEE","LEFT_HIP"),
      "FOOT_POLE.R":("RIGHT_KNEE","RIGHT_HIP"),
    }
    for item in data["keyframes"]:
        scene.frame_set(max(1,int(item["frame"])))
        pts=landmarks(item)
        for logical,(point,anchor) in targets.items():
            if logical not in controls:continue
            matrix=anchors[logical].copy()
            matrix.translation += delta_point(pts,point,anchor)*1.25
            controls[logical].matrix=matrix
            controls[logical].keyframe_insert(data_path="location",frame=scene.frame_current)
            controls[logical].keyframe_insert(data_path="rotation_euler",frame=scene.frame_current)
        controls["Bone"].keyframe_insert(data_path="location",frame=scene.frame_current)
        controls["Bone"].keyframe_insert(data_path="rotation_euler",frame=scene.frame_current)
    scene.frame_start=1
    if data["keyframes"]:scene.frame_end=max(1,max(int(x["frame"]) for x in data["keyframes"]))
    return info

def main():
    args=parse()
    try:
        obj=armature(args.armature); info=inspect_rig(obj)
        if args.command=="inspect":
            print(json.dumps({"ok":info["ok"],"message":"Inspección completada","rig":info},ensure_ascii=False)); return 0
        data=load_data(args.data); apply_keyframes(obj,data)
        output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        print(json.dumps({"ok":True,"message":f"Archivo guardado: {output}","rig":info},ensure_ascii=False)); return 0
    except Exception as exc:
        print(json.dumps({"ok":False,"message":str(exc)},ensure_ascii=False)); return 1

if __name__=="__main__":raise SystemExit(main())
