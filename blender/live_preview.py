import bpy
import json
import socket
import sys
import threading
import time
from mathutils import Vector


HOST = "127.0.0.1"
PORT = 8765
ARMATURE_NAME = "IK1_regular"

CONTROL_NAMES = {
    "left_hand": "HAND_IK.L",
    "right_hand": "HAND_IK.R",
    "left_hand_pole": "HAND_POLE.L",
    "right_hand_pole": "HAND_POLE.R",
    "left_foot": "FOOT_IK.L",
    "right_foot": "FOOT_IK.R",
    "left_foot_pole": "FOOT_POLE.L",
    "right_foot_pole": "FOOT_POLE.R",
}

_queue = []
_lock = threading.Lock()
_running = True


def parse_args():
    global HOST, PORT
    if "--" not in sys.argv:
        return

    args = sys.argv[sys.argv.index("--") + 1:]
    for i, value in enumerate(args):
        if value == "--host" and i + 1 < len(args):
            HOST = args[i + 1]
        elif value == "--port" and i + 1 < len(args):
            PORT = int(args[i + 1])


def enqueue(packet):
    with _lock:
        _queue.clear()
        _queue.append(packet)


def receiver():
    global _running

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    server.settimeout(0.5)

    print(f"[LIVE] Socket escuchando en {HOST}:{PORT}")
    buffer = b""

    while _running:
        try:
            conn, address = server.accept()
            conn.settimeout(0.5)
            print(f"[LIVE] Cliente conectado: {address}")

            while _running:
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    continue

                if not chunk:
                    break

                buffer += chunk

                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)
                    if not raw:
                        continue
                    try:
                        enqueue(json.loads(raw.decode("utf-8")))
                    except Exception as exc:
                        print(f"[LIVE] JSON invalido: {exc}")

            try:
                conn.close()
            except Exception:
                pass

        except socket.timeout:
            continue
        except Exception as exc:
            print(f"[LIVE] Socket: {exc}")
            time.sleep(0.2)

    try:
        server.close()
    except Exception:
        pass


def apply_target(armature, pose_bone, target_world):
    target_world = Vector(target_world)

    target_armature = armature.matrix_world.inverted() @ target_world
    current_world = armature.matrix_world @ pose_bone.matrix
    current_armature = armature.matrix_world.inverted() @ current_world.translation
    delta = target_armature - current_armature

    pose_bone.location += delta


def apply_packet(armature, packet):
    for logical_name, position in packet.get("targets", {}).items():
        bone_name = CONTROL_NAMES.get(logical_name)
        if not bone_name:
            continue

        bone = armature.pose.bones.get(bone_name)
        if bone is None:
            continue

        apply_target(armature, bone, position)

    bpy.context.view_layer.update()


def tick():
    if not _running:
        return None

    packet = None
    with _lock:
        if _queue:
            packet = _queue.pop()

    if packet is not None:
        armature = bpy.data.objects.get(ARMATURE_NAME)
        if armature is not None:
            try:
                apply_packet(armature, packet)
            except Exception as exc:
                print(f"[LIVE] Error aplicando pose: {exc}")

    return 0.0


def setup_view():
    # Blender 4.4 NO acepta "FRONT" en view_perspective.
    # Los enums validos aqui son PERSP, ORTHO y CAMERA.
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue

            region_3d = area.spaces.active.region_3d
            if region_3d is None:
                continue

            region_3d.view_perspective = "ORTHO"
            region_3d.view_location = Vector((0.0, 0.0, 40.0))
            region_3d.view_distance = 110.0


def main():
    parse_args()

    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None:
        raise RuntimeError(
            f"No existe el armature '{ARMATURE_NAME}'."
        )

    setup_view()

    thread = threading.Thread(target=receiver, daemon=True)
    thread.start()

    print("[LIVE] Modelo listo.")
    print("[LIVE] Piernas: solo se actualizan con deteccion real.")

    bpy.app.timers.register(tick, first_interval=0.0, persistent=True)


main()
