import bpy
import json
import os
import socket
import sys
import threading
import time

from mathutils import Matrix, Vector


HOST = "127.0.0.1"
PORT = 8765
PREVIEW_PATH = ""
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
_initial_visual_translation = {}


def parse_args():
    global HOST, PORT, PREVIEW_PATH

    if "--" not in sys.argv:
        return

    args = sys.argv[sys.argv.index("--") + 1:]
    for i, value in enumerate(args):
        if value == "--host" and i + 1 < len(args):
            HOST = args[i + 1]
        elif value == "--port" and i + 1 < len(args):
            PORT = int(args[i + 1])
        elif value == "--preview" and i + 1 < len(args):
            PREVIEW_PATH = os.path.abspath(args[i + 1])


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

    print(f"[LIVE] Socket escuchando en {HOST}:{PORT}", flush=True)

    while _running:
        try:
            conn, address = server.accept()
            conn.settimeout(0.5)
            print(f"[LIVE] Cliente conectado: {address}", flush=True)
            buffer = b""

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
                        print(f"[LIVE] JSON invalido: {exc}", flush=True)

            try:
                conn.close()
            except Exception:
                pass

        except socket.timeout:
            continue
        except Exception as exc:
            print(f"[LIVE] Socket: {exc}", flush=True)
            time.sleep(0.2)

    try:
        server.close()
    except Exception:
        pass


def get_pose_matrix_in_other_space(mat, pose_bone):
    """
    Convierte una matriz en espacio del armature al espacio local del
    pose bone, respetando el hueso de reposo y su padre.
    """
    rest = pose_bone.bone.matrix_local.copy()
    rest_inv = rest.inverted()

    if pose_bone.parent:
        par_mat = pose_bone.parent.matrix.copy()
        par_inv = par_mat.inverted()
        par_rest = pose_bone.parent.bone.matrix_local.copy()
    else:
        par_mat = Matrix()
        par_inv = Matrix()
        par_rest = Matrix()

    return rest_inv @ (par_rest @ (par_inv @ mat))


def set_pose_translation(pose_bone, mat):
    if pose_bone.bone.use_local_location:
        pose_bone.location = mat.to_translation()
        return

    loc = mat.to_translation()
    rest = pose_bone.bone.matrix_local.copy()
    par_rest = (
        pose_bone.bone.parent.matrix_local.copy()
        if pose_bone.bone.parent
        else Matrix()
    )

    q = (par_rest.inverted() @ rest).to_quaternion()
    pose_bone.location = q @ loc


def apply_target(pose_bone, target):
    if not isinstance(target, dict):
        return

    position = target.get("position")
    reference = target.get("reference")
    if not position or not reference:
        return

    # El retarget ya produjo coordenadas del armature. Solo aplicamos
    # el desplazamiento respecto a la referencia, sin acumularlo.
    delta = Vector(position) - Vector(reference)

    base_matrix = pose_bone.matrix.copy()
    base_matrix.translation = (
        _initial_visual_translation.get(pose_bone.name, base_matrix.translation)
        + delta
    )

    local_matrix = get_pose_matrix_in_other_space(base_matrix, pose_bone)
    set_pose_translation(pose_bone, local_matrix)


def capture_initial_pose(armature):
    _initial_visual_translation.clear()
    bpy.context.view_layer.update()

    for logical_name, bone_name in CONTROL_NAMES.items():
        bone = armature.pose.bones.get(bone_name)
        if bone is not None:
            _initial_visual_translation[bone.name] = bone.matrix.translation.copy()

    print(
        f"[LIVE] Pose inicial capturada: "
        f"{len(_initial_visual_translation)} controles",
        flush=True,
    )


def apply_packet(armature, packet):
    targets = packet.get("targets", {})
    applied = 0

    for logical_name, target in targets.items():
        bone_name = CONTROL_NAMES.get(logical_name)
        if not bone_name:
            continue

        bone = armature.pose.bones.get(bone_name)
        if bone is None:
            continue

        apply_target(bone, target)
        applied += 1

    bpy.context.view_layer.update()
    return applied


def calculate_bounds(armature):
    points = []

    for bone in armature.pose.bones:
        points.append(armature.matrix_world @ bone.head)
        points.append(armature.matrix_world @ bone.tail)

    if not points:
        return Vector((0.0, 0.0, 50.0)), 100.0

    min_v = Vector((
        min(p.x for p in points),
        min(p.y for p in points),
        min(p.z for p in points),
    ))
    max_v = Vector((
        max(p.x for p in points),
        max(p.y for p in points),
        max(p.z for p in points),
    ))

    center = (min_v + max_v) * 0.5
    height = max(max_v.z - min_v.z, 10.0)
    return center, height


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_preview_camera(armature):
    global PREVIEW_PATH

    scene = bpy.context.scene
    center, height = calculate_bounds(armature)

    camera = bpy.data.objects.get("MOCAP_LIVE_CAMERA")
    if camera is None:
        camera_data = bpy.data.cameras.new("MOCAP_LIVE_CAMERA_DATA")
        camera = bpy.data.objects.new("MOCAP_LIVE_CAMERA", camera_data)
        scene.collection.objects.link(camera)

    camera.data.type = "ORTHO"
    camera.data.ortho_scale = height * 1.20
    camera.location = center + Vector((0.0, -height * 2.0, 0.0))
    look_at(camera, center)
    scene.camera = camera

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True

    scene.render.resolution_x = 420
    scene.render.resolution_y = 620
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.filepath = PREVIEW_PATH

    try:
        scene.display.render_aa = "FXAA"
    except Exception:
        pass

    print(
        f"[LIVE] Preview listo: {PREVIEW_PATH}",
        flush=True,
    )


def render_preview():
    if not PREVIEW_PATH:
        return

    scene = bpy.context.scene
    scene.render.filepath = PREVIEW_PATH

    try:
        bpy.ops.render.render(write_still=True)
    except Exception as exc:
        print(f"[LIVE] Error render preview: {exc}", flush=True)


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
                applied = apply_packet(armature, packet)
                print(
                    f"[LIVE] frame={packet.get('frame_id')} "
                    f"targets={len(packet.get('targets', {}))} "
                    f"applied={applied}",
                    flush=True,
                )
                render_preview()
            except Exception as exc:
                print(f"[LIVE] Error aplicando pose: {exc}", flush=True)

    # No bloquear el viewport: Blender vuelve a llamar al timer.
    return 0.03


def setup_view():
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
    capture_initial_pose(armature)
    setup_preview_camera(armature)

    # Imagen inicial aunque todavía no llegue un frame.
    render_preview()

    thread = threading.Thread(target=receiver, daemon=True)
    thread.start()

    print("[LIVE] Modelo listo y preview activo.", flush=True)
    print("[LIVE] Piernas: solo se actualizan con deteccion real.", flush=True)

    bpy.app.timers.register(tick, first_interval=0.03, persistent=True)


main()
