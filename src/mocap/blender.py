"""Integración con Blender en un proceso separado, con verificación de salida."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, subprocess
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
        blend = Path(blend_path).resolve()
        if not blend.is_file(): return BlenderResult(False, f"No existe el .blend: {blend}")
        if not self.config.executable.is_file(): return BlenderResult(False, f"No se encontró Blender: {self.config.executable}")
        return self._run([str(self.config.executable), "-b", str(blend), "--python", str(self.config.worker_script.resolve()),
                          "--", "inspect", "--armature", self.config.armature])

    def apply(self, blend_path: str | Path, store: KeyframeStore, output_path: str | Path) -> BlenderResult:
        blend, output = Path(blend_path).resolve(), Path(output_path).resolve()
        if not blend.is_file(): return BlenderResult(False, f"No existe el .blend original: {blend}")
        if blend == output: return BlenderResult(False, "El archivo de salida debe ser distinto del original.")
        if len(store) == 0: return BlenderResult(False, "No hay keyframes para exportar.")
        if not self.config.executable.is_file(): return BlenderResult(False, f"No se encontró Blender: {self.config.executable}")
        worker = self.config.worker_script.resolve()
        if not worker.is_file(): return BlenderResult(False, f"No se encontró el worker: {worker}")
        output.parent.mkdir(parents=True, exist_ok=True)
        data_path = output.with_suffix(".mocap.json")
        store.save_json(data_path)
        command = [str(self.config.executable), "-b", str(blend), "--python", str(worker), "--", "apply",
                   "--armature", self.config.armature, "--data", str(data_path), "--output", str(output)]
        result = self._run(command)
        try: data_path.unlink(missing_ok=True)
        except OSError: pass
        if result.ok and (not output.is_file() or output.stat().st_size < 1024):
            return BlenderResult(False, "Blender reportó éxito pero no se encontró un .blend válido.", details=result.details)
        return BlenderResult(result.ok, result.message, output if result.ok else None, result.details)

    def _run(self, command: list[str]) -> BlenderResult:
        try:
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", check=False, timeout=180)
        except subprocess.TimeoutExpired:
            return BlenderResult(False, "Blender excedió el tiempo máximo de 180 segundos.")
        except OSError as exc:
            return BlenderResult(False, f"No se pudo ejecutar Blender: {exc}")
        output = (completed.stdout + "\n" + completed.stderr).strip()
        details = {"returncode": completed.returncode, "output": output[-12000:]}
        lines = [line for line in completed.stdout.splitlines() if line.strip().startswith("{")]
        payload = {}
        if lines:
            try: payload = json.loads(lines[-1])
            except ValueError: pass
        if completed.returncode != 0 or payload.get("ok") is False:
            return BlenderResult(False, payload.get("message", "Blender terminó con error."), details=details)
        if payload.get("ok") is not True:
            return BlenderResult(False, "Blender terminó sin confirmar el resultado. Revisa el registro.", details=details)
        details["payload"] = payload
        return BlenderResult(True, payload.get("message", "Blender terminó correctamente."), details=details)
