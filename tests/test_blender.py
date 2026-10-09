from pathlib import Path
from mocap.blender import BlenderBridge, BlenderConfig

def test_missing_blend_is_reported(tmp_path):
    bridge=BlenderBridge(BlenderConfig(executable=tmp_path/"blender.exe"))
    result=bridge.inspect(tmp_path/"missing.blend")
    assert not result.ok and "No existe" in result.message
