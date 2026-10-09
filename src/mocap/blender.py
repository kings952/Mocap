"""Integración con Blender 4.4 mediante un proceso separado.

La aplicación Python no importa bpy. Blender se ejecuta como proceso propio,
lo que mantiene aislado su Python y permite usar el mismo entorno externo
para OpenCV/MediaPipe/PySide6.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
import sys
from .keyframes import KeyframeStore

@dataclass(frozen=True)
class BlenderConfig:
    executable: Path = Path(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe")
    worker_script: Path = Path("scripts/blender_worker.py")
    armature: str = "IK1_regular"

@dataclass(frozen=True)
class BlenderResult:
    ok: bool
    message: str
    output_path: Path | None = None
    details: dict | None = None

class BlenderBridge:
    def __init__(self, config: BlenderConfig | None = None) -> None:
        self.config = config or BlenderConfig()

    def inspect(self, blend_path: str | Path) -> BlenderResult:
        blend = Path(blend_path)
        if not blend.is_file():
            return BlenderResult(False, f"No existe el .blend: {blend}")
        if not self.config.executable.is_file():
            return BlenderResult(False, f"No se encontró Blender: {self.config.executable}")
        command = [str(self.config.executable), "-b", str(blend), "--python", str(self.config.worker_script),
                   "--", "inspect", "--armature", self.config.armature]
        return self._run(command)

    def apply(self, blend_path: str | Path, store: KeyframeStore, output_path: str | Path) -> BlenderResult:
        blend, output = Path(blend_path), Path(output_path)
        if not blend.is_file():
            return BlenderResult(False, f"No existe el .blend: {blend}")
        if not self.config.executable.is_file():
            return BlenderResult(False, f"No se encontró Blender: {self.config.executable}")
        data_path = output.with_suffix(".mocap.json")
        store.save_json(data_path)
        command = [str(self.config.executable), "-b", str(blend), "--python", str(self.config.worker_script),
                   "--", "apply", "--armature", self.config.armature,
                   "--data", str(data_path), "--output", str(output)]
        result = self._run(command)
        if result.ok:
            try:
                data_path.unlink()
            except OSError:
                pass
        return BlenderResult(result.ok, result.message, output if result.ok else None, result.details)

    def _run(self, command: list[str]) -> BlenderResult:
        try:
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", check=False)
        except OSError as exc:
            return BlenderResult(False, f"No se pudo ejecutar Blender: {exc}")
        output = (completed.stdout + "\n" + completed.stderr).strip()
        details = {"returncode": completed.returncode, "output": output[-12000:]}
        if completed.returncode != 0:
            return BlenderResult(False, "Blender terminó con error.", details=details)
        try:
            payload = json.loads(completed.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            payload = {}
        return BlenderResult(True, payload.get("message", "Blender terminó correctamente."), details=details)
