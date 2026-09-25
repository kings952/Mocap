import json
import socket
import shutil
import subprocess
import time

from config import (
    BLENDER_EXE,
    BLENDER_LIVE_SCRIPT,
    SOURCE_BLEND,
    LIVE_HOST,
    LIVE_PORT,
    LIVE_TEMP_BLEND,
)
from retarget import build_live_targets


class LivePreviewClient:
    def __init__(self):
        self.process = None
        self.sock = None
        self.connected = False
        self.last_error = ""
        self.last_send = 0.0

    def start(self):
        self.stop()

        if not BLENDER_EXE.exists():
            self.last_error = f"Blender no encontrado: {BLENDER_EXE}"
            return False
        if not SOURCE_BLEND.exists():
            self.last_error = f".blend no encontrado: {SOURCE_BLEND}"
            return False
        if not BLENDER_LIVE_SCRIPT.exists():
            self.last_error = f"Script live no encontrado: {BLENDER_LIVE_SCRIPT}"
            return False

        try:
            LIVE_TEMP_BLEND.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_BLEND, LIVE_TEMP_BLEND)
        except OSError as exc:
            self.last_error = f"No se pudo crear el .blend temporal: {exc}"
            return False

        command = [
            str(BLENDER_EXE),
            str(LIVE_TEMP_BLEND),
            "--python",
            str(BLENDER_LIVE_SCRIPT),
            "--",
            "--host",
            LIVE_HOST,
            "--port",
            str(LIVE_PORT),
        ]

        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(BLENDER_EXE.parent),
            )
        except Exception as exc:
            self.last_error = str(exc)
            return False

        deadline = time.time() + 12.0
        while time.time() < deadline:
            try:
                self.sock = socket.create_connection(
                    (LIVE_HOST, LIVE_PORT),
                    timeout=0.5,
                )
                self.sock.settimeout(0.0)
                self.connected = True
                self.last_error = ""
                return True
            except OSError:
                time.sleep(0.15)

        self.last_error = "Blender abrio, pero no se pudo conectar al live socket."
        return False

    def send(self, keypoints, calibration, frame_id, timestamp):
        if not self.connected:
            return

        targets = build_live_targets(keypoints, calibration)
        packet = {
            "type": "live_pose",
            "frame_id": int(frame_id),
            "time": float(timestamp),
            "targets": targets,
        }

        try:
            data = (json.dumps(packet, separators=(",", ":")) + "\n").encode("utf-8")
            self.sock.sendall(data)
            self.last_send = time.perf_counter()
        except OSError as exc:
            self.connected = False
            self.last_error = str(exc)
            self._close_socket()

    def stop(self):
        self.connected = False
        self._close_socket()

        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self.process = None

    def _close_socket(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
