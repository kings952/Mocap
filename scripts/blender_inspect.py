"""Inspecciona el Genesis .blend usando la instalación local de Blender."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--blend",type=Path,required=True)
    p.add_argument("--blender",type=Path,default=Path(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"))
    a=p.parse_args()
    if not a.blend.is_file(): print(f"ERROR: no existe {a.blend}"); return 2
    if not a.blender.is_file(): print(f"ERROR: no existe {a.blender}"); return 2
    cmd=[str(a.blender),"-b",str(a.blend),"--python",str(ROOT/"scripts/blender_worker.py"),"--","inspect","--armature","IK1_regular"]
    r=subprocess.run(cmd,text=True,capture_output=True,encoding="utf-8",errors="replace")
    print((r.stdout+"\n"+r.stderr).strip())
    return r.returncode
if __name__=="__main__": raise SystemExit(main())
