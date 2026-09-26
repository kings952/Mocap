import json
import socket
import subprocess
import threading
import time
from pathlib import Path

import cv2

from config import (
    BLENDER_EXE,
    BLENDER_LIVE_SCRIPT,
    LIVE_FPS,
    LIVE_HOST,
    LIVE_PORT,
    LIVE_PREVIEW_IMAGE,
    SOURCE_BLEND,
)
from retarget import build_live_targets


class LivePreviewClient:
    """Cliente no bloqueante que transmite el ultimo estado al .blend real."""

    def __init__(self):
        self.connected=False
        self.last_error=""
        self.last_send=0.0
        self.sent_frames=0
        self.dropped_frames=0
        self.last_target_count=0
        self.preview=None
        self.interval=1.0/max(float(LIVE_FPS),1.0)
        self._process=None
        self._socket=None
        self._socket_lock=threading.Lock()
        self._preview_thread=None
        self._preview_running=False
        self._last_preview_mtime=0
        self._last_connect_attempt=0.0

    def start(self):
        self.stop()
        self.last_error=""
        self.last_send=0.0
        self.preview=None
        self._last_preview_mtime=0
        self._last_connect_attempt=0.0

        if not BLENDER_EXE.exists():
            self.last_error=f"Blender no encontrado: {BLENDER_EXE}"
            print(f"[LIVE] {self.last_error}",flush=True)
            return False
        if not SOURCE_BLEND.exists():
            self.last_error=f".blend no encontrado: {SOURCE_BLEND}"
            print(f"[LIVE] {self.last_error}",flush=True)
            return False

        LIVE_PREVIEW_IMAGE.parent.mkdir(parents=True,exist_ok=True)
        command=[
            str(BLENDER_EXE),"-b",str(SOURCE_BLEND),
            "--python",str(BLENDER_LIVE_SCRIPT),"--",
            "--host",LIVE_HOST,"--port",str(LIVE_PORT),
            "--preview",str(LIVE_PREVIEW_IMAGE),
        ]
        try:
            self._process=subprocess.Popen(
                command,
                cwd=str(SOURCE_BLEND.parent),
                stdin=subprocess.DEVNULL,
                stdout=None,
                stderr=None,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),
            )
        except Exception as exc:
            self.last_error=f"No se pudo iniciar Blender LIVE: {exc}"
            print(f"[LIVE] {self.last_error}",flush=True)
            return False

        self._preview_running=True
        self._preview_thread=threading.Thread(
            target=self._preview_loop,
            name="live-preview-reader",
            daemon=True,
        )
        self._preview_thread.start()
        print("[LIVE] Blender iniciado con el .blend real.",flush=True)
        return True

    def send(self,keypoints,calibration,frame_id,timestamp):
        now=time.perf_counter()
        if self.last_send>0.0 and now-self.last_send<self.interval:
            self.dropped_frames+=1
            return False
        if self._process is not None and self._process.poll() is not None:
            self.connected=False
            self.last_error=f"Blender LIVE terminó con código {self._process.returncode}"
            return False

        try:
            targets=build_live_targets(keypoints,calibration)
            self.last_target_count=len(targets)
            packet={
                "type":"live_targets",
                "frame_id":int(frame_id),
                "time":float(timestamp),
                "targets":targets,
            }
            if not self._send_packet(packet):
                self.dropped_frames+=1
                return False
            self.last_send=now
            self.sent_frames+=1
            return True
        except Exception as exc:
            self.last_error=f"Error LIVE: {exc}"
            self._close_socket()
            return False

    def stop(self):
        self.connected=False
        self._preview_running=False
        with self._socket_lock:
            sock=self._socket
            self._socket=None
        if sock is not None:
            try: sock.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            try: sock.close()
            except OSError: pass
        if self._preview_thread is not None:
            self._preview_thread.join(timeout=0.5)
            self._preview_thread=None
        if self._process is not None:
            if self._process.poll() is None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=1.5)
                except Exception:
                    try: self._process.kill()
                    except Exception: pass
            self._process=None
        self.preview=None

    def _send_packet(self,packet):
        payload=(json.dumps(packet,separators=(",",":"))+"\n").encode("utf-8")
        with self._socket_lock:
            if self._socket is None:
                self._try_connect_locked()
            if self._socket is None:
                return False
            try:
                self._socket.sendall(payload)
                self.connected=True
                self.last_error=""
                return True
            except (OSError,ConnectionError):
                self.connected=False
                try: self._socket.close()
                except OSError: pass
                self._socket=None
                return False

    def _try_connect_locked(self):
        now=time.perf_counter()
        if now-self._last_connect_attempt<0.15:
            return
        self._last_connect_attempt=now
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.settimeout(0.03)
        try:
            sock.connect((LIVE_HOST,LIVE_PORT))
            sock.settimeout(0.10)
            self._socket=sock
            self.connected=True
        except OSError:
            try: sock.close()
            except OSError: pass

    def _close_socket(self):
        with self._socket_lock:
            if self._socket is not None:
                try: self._socket.close()
                except OSError: pass
                self._socket=None
            self.connected=False

    def _preview_loop(self):
        path=Path(LIVE_PREVIEW_IMAGE)
        while self._preview_running:
            try:
                if path.exists():
                    mtime=path.stat().st_mtime_ns
                    if mtime!=self._last_preview_mtime:
                        image=cv2.imread(str(path),cv2.IMREAD_COLOR)
                        if image is not None:
                            self.preview=image
                            self._last_preview_mtime=mtime
            except Exception as exc:
                self.last_error=f"Error leyendo preview LIVE: {exc}"
            time.sleep(0.035)
