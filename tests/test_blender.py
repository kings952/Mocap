from pathlib import Path
from mocap.blender import BlenderBridge, BlenderConfig
from mocap.keyframes import KeyframeStore
from mocap.pose import PoseFrame, PoseLandmark

def test_missing_blend_is_reported(tmp_path):
    bridge=BlenderBridge(BlenderConfig(executable=tmp_path/"blender.exe"))
    result=bridge.inspect(tmp_path/"missing.blend")
    assert not result.ok and "No existe" in result.message

def test_export_refuses_to_overwrite_original(tmp_path):
    blend=tmp_path/"source.blend"; blend.write_bytes(b"blend")
    store=KeyframeStore()
    result=BlenderBridge(BlenderConfig(executable=tmp_path/"blender.exe")).apply(blend,store,blend)
    assert not result.ok and "distinto" in result.message

def test_export_requires_keyframes(tmp_path):
    blend=tmp_path/"source.blend"; blend.write_bytes(b"blend")
    result=BlenderBridge(BlenderConfig(executable=tmp_path/"blender.exe")).apply(
        blend,KeyframeStore(),tmp_path/"output.blend")
    assert not result.ok and "No hay keyframes" in result.message
