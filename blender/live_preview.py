import bpy
import json
import os
import socket
import sys
import threading
import time

from mathutils import Matrix, Vector

from pathlib import Path


HOST = "127.0.0.1"
PORT = 8765
PREVIEW_PATH = ""
ARMATURE_NAME = "IK1_regular"

CONTROL_NAMES = {
    "hip": ("hip",),
    "left_hand": ("HAND_IK.L",),
    "right_hand": ("HAND_IK.R",),
    "left_hand_pole": ("HAND_POLE.L",),
    "right_hand_pole": ("HAND_POLE.R",),
    "left_foot": ("FOOT_IK.L",),
    "right_foot": ("FOOT_IK.R",),
    "left_foot_pole": ("FOOT_POLE.L",),
    "right_foot_pole": ("FOOT_POLE.R",),
}

STATIC_BONE_NAMES = ("Bone",)

_queue = []
_lock = threading.Lock()
_running = True

_initial_visual_translation = {}
_static_matrix_basis = {}

_preview_camera = None
_preview_center = None
_preview_scale = None

# Bounds del modelo se calculan una vez. Antes se calculaban por cada target
# de cada paquete, lo cual hacia que el LIVE gastara mucho tiempo en Blender.
_model_center = None
_model_size = None

_last_render_time = 0.0
_RENDER_INTERVAL = 1.0 / 18.0

# Estadisticas ligeras: no escribimos una linea de consola por cada paquete.
_processed_packets = 0
_last_stats_time = 0.0


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
    # Solo importa el ultimo paquete. Nunca dejamos que Blender procese
    # poses viejas si el detector va mas rapido que el render.
    with _lock:
        _queue.clear()
        _queue.append(packet)


def receiver():
    global _running

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )
    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )
    server.bind((HOST, PORT))
    server.listen(1)
    server.settimeout(0.5)

    print(
        f"[LIVE] Socket escuchando en {HOST}:{PORT}",
        flush=True,
    )

    while _running:
        try:
            conn, address = server.accept()
            conn.settimeout(0.25)

            print(
                f"[LIVE] Cliente conectado: {address}",
                flush=True,
            )

            buffer = b""

            while _running:
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    continue

                if not chunk:
                    break

                buffer += chunk

                # Nunca permitimos que una conexion rota o un paquete
                # incompleto haga crecer el buffer indefinidamente.
                if len(buffer) > 2 * 1024 * 1024:
                    print(
                        "[LIVE] Buffer de socket excedido; reiniciando conexion.",
                        flush=True,
                    )
                    buffer = b""
                    break

                while b"\n" in buffer:
                    raw, buffer = buffer.split(b"\n", 1)

                    if not raw:
                        continue

                    try:
                        enqueue(
                            json.loads(
                                raw.decode("utf-8")
                            )
                        )
                    except Exception as exc:
                        print(
                            f"[LIVE] JSON invalido: {exc}",
                            flush=True,
                        )

            try:
                conn.close()
            except Exception:
                pass

        except socket.timeout:
            continue
        except Exception as exc:
            print(
                f"[LIVE] Socket: {exc}",
                flush=True,
            )
            time.sleep(0.1)

    try:
        server.close()
    except Exception:
        pass


def normalize_name(name):
    return str(name).strip().casefold()


def resolve_pose_bone(armature, logical_name):
    candidates = CONTROL_NAMES.get(logical_name, ())

    if not candidates:
        return None

    for candidate in candidates:
        bone = armature.pose.bones.get(candidate)

        if bone is not None:
            return bone

    wanted = {
        normalize_name(candidate)
        for candidate in candidates
    }

    for bone in armature.pose.bones:
        if normalize_name(bone.name) in wanted:
            return bone

    return None


def resolve_static_bone(armature, name):
    exact = armature.pose.bones.get(name)

    if exact is not None:
        return exact

    wanted = normalize_name(name)

    for bone in armature.pose.bones:
        if normalize_name(bone.name) == wanted:
            return bone

    return None


def get_pose_matrix_in_other_space(mat, pose_bone):
    rest = pose_bone.bone.matrix_local.copy()
    rest_inv = rest.inverted()

    if pose_bone.parent:
        par_mat = pose_bone.parent.matrix.copy()
        par_inv = par_mat.inverted()
        par_rest = (
            pose_bone.parent.bone.matrix_local.copy()
        )
    else:
        par_mat = Matrix()
        par_inv = Matrix()
        par_rest = Matrix()

    return (
        rest_inv
        @ (par_rest @ (par_inv @ mat))
    )


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

    q = (
        par_rest.inverted() @ rest
    ).to_quaternion()

    pose_bone.location = q @ loc


def geometry_bounds(armature):
    points = []

    armature_children = set()
    stack = [armature]

    while stack:
        parent = stack.pop()

        for child in parent.children:
            if child in armature_children:
                continue

            armature_children.add(child)
            stack.append(child)

    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue

        related = (
            obj in armature_children
            or obj.parent == armature
        )

        if not related:
            for modifier in obj.modifiers:
                if (
                    modifier.type == "ARMATURE"
                    and modifier.object == armature
                ):
                    related = True
                    break

        if not related:
            continue

        for corner in obj.bound_box:
            points.append(
                obj.matrix_world @ Vector(corner)
            )

    if not points:
        for bone in armature.pose.bones:
            points.append(
                armature.matrix_world @ bone.head
            )
            points.append(
                armature.matrix_world @ bone.tail
            )

    if not points:
        return (
            Vector((0.0, 0.0, 50.0)),
            Vector((40.0, 40.0, 100.0)),
        )

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

    return (
        (min_v + max_v) * 0.5,
        max_v - min_v,
    )


def clamp_delta_to_model(delta, model_size, ratio):
    dimensions = [
        abs(float(model_size.x)),
        abs(float(model_size.y)),
        abs(float(model_size.z)),
    ]

    reference_size = max(dimensions)

    if reference_size <= 0.000001:
        return Vector((0.0, 0.0, 0.0))

    limit = reference_size * ratio

    if delta.length <= limit:
        return delta

    return delta.normalized() * limit


def apply_target(armature, pose_bone, target):
    if not isinstance(target, dict):
        return False

    position = target.get("position")
    reference = target.get("reference")

    if not position or not reference:
        return False

    delta = (
        Vector(position)
        - Vector(reference)
    )

    logical_gain = float(
        target.get("gain", 1.0)
    )
    logical_gain = max(
        0.0,
        min(1.0, logical_gain),
    )
    delta *= logical_gain

    # Bounds cacheados: no hacemos geometria_bounds() por cada hueso.
    if _model_size is not None:
        name = normalize_name(pose_bone.name)

        if name == "hip":
            ratio = 0.25
        elif "pole" in name:
            ratio = 0.12
        elif (
            "foot_ik" in name
            or "hand_ik" in name
        ):
            ratio = 0.35
        else:
            ratio = 0.25

        delta = clamp_delta_to_model(
            delta,
            _model_size,
            ratio,
        )

    initial = _initial_visual_translation.get(
        pose_bone.name,
        pose_bone.matrix.translation.copy(),
    )

    base_matrix = pose_bone.matrix.copy()
    base_matrix.translation = (
        initial + delta
    )

    local_matrix = get_pose_matrix_in_other_space(
        base_matrix,
        pose_bone,
    )

    set_pose_translation(
        pose_bone,
        local_matrix,
    )

    return True


def capture_initial_pose(armature):
    global _model_center, _model_size

    _initial_visual_translation.clear()
    _static_matrix_basis.clear()

    bpy.context.view_layer.update()

    for logical_name in CONTROL_NAMES:
        bone = resolve_pose_bone(
            armature,
            logical_name,
        )

        if bone is not None:
            _initial_visual_translation[
                bone.name
            ] = bone.matrix.translation.copy()

    for static_name in STATIC_BONE_NAMES:
        bone = resolve_static_bone(
            armature,
            static_name,
        )

        if bone is not None:
            _static_matrix_basis[
                bone.name
            ] = bone.matrix_basis.copy()

    _model_center, _model_size = geometry_bounds(
        armature
    )

    print(
        f"[LIVE] Pose inicial: "
        f"{len(_initial_visual_translation)} controles; "
        f"estaticos={len(_static_matrix_basis)}",
        flush=True,
    )

    print(
        f"[LIVE] Escala modelo: "
        f"{tuple(round(v, 4) for v in _model_size)}",
        flush=True,
    )


def restore_static_bones(armature):
    for name, matrix_basis in _static_matrix_basis.items():
        bone = resolve_static_bone(
            armature,
            name,
        )

        if bone is not None:
            bone.matrix_basis = (
                matrix_basis.copy()
            )


def apply_packet(armature, packet):
    targets = packet.get("targets", {})
    applied = 0

    for logical_name, target in targets.items():
        if normalize_name(logical_name) == "bone":
            continue

        bone = resolve_pose_bone(
            armature,
            logical_name,
        )

        if bone is None:
            continue

        if apply_target(
            armature,
            bone,
            target,
        ):
            applied += 1

    bpy.context.view_layer.update()
    restore_static_bones(armature)
    bpy.context.view_layer.update()

    return applied


def look_at(obj, target):
    direction = (
        Vector(target) - obj.location
    )

    if direction.length > 0.0001:
        obj.rotation_euler = (
            direction.to_track_quat(
                "-Z",
                "Y",
            ).to_euler()
        )


def update_preview_camera(armature, force=False):
    global _preview_camera
    global _preview_center
    global _preview_scale

    scene = bpy.context.scene

    # El tamaño se calculo al arrancar y no en cada frame.
    if _model_center is None or _model_size is None:
        center, size = geometry_bounds(
            armature
        )
    else:
        center = _model_center
        size = _model_size

    width = max(
        float(size.x),
        0.0001,
    )
    height = max(
        float(size.z),
        0.0001,
    )
    depth = max(
        float(size.y),
        0.0001,
    )

    aspect = (
        scene.render.resolution_x
        / max(
            scene.render.resolution_y,
            1,
        )
    )

    required_vertical = max(
        height,
        width / max(aspect, 0.1),
    )

    required_vertical *= 1.18

    if (
        _preview_center is None
        or force
    ):
        _preview_center = center.copy()
    else:
        _preview_center = _preview_center.lerp(
            center,
            0.10,
        )

    if (
        _preview_scale is None
        or force
    ):
        _preview_scale = required_vertical
    else:
        # Camera casi fija: evita que el modelo haga zoom atrasado.
        _preview_scale = (
            _preview_scale * 0.95
            + required_vertical * 0.05
        )

    camera = _preview_camera

    if camera is None:
        camera_data = bpy.data.cameras.new(
            "MOCAP_LIVE_CAMERA_DATA"
        )

        camera = bpy.data.objects.new(
            "MOCAP_LIVE_CAMERA",
            camera_data,
        )

        scene.collection.objects.link(
            camera
        )
        _preview_camera = camera

    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(
        _preview_scale,
        0.0001,
    )

    distance = max(
        width,
        height,
        depth,
        0.1,
    ) * 3.0

    camera.location = (
        _preview_center
        + Vector((0.0, -distance, 0.0))
    )

    camera.data.clip_start = max(
        distance * 0.001,
        0.00001,
    )

    camera.data.clip_end = max(
        distance * 8.0,
        1.0,
    )

    look_at(
        camera,
        _preview_center,
    )

    scene.camera = camera


def setup_preview_scene(armature):
    scene = bpy.context.scene

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False

    # Preview pequeño y rapido. El .blend original no se modifica.
    scene.render.resolution_x = 420
    scene.render.resolution_y = 570
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.quality = 70
    scene.render.film_transparent = False
    scene.render.filepath = PREVIEW_PATH

    try:
        scene.display.render_aa = "FXAA"
    except Exception:
        pass

    update_preview_camera(
        armature,
        force=True,
    )

    print(
        f"[LIVE] Preview rapido: {PREVIEW_PATH}",
        flush=True,
    )


def render_preview(armature, force_camera=False):
    global _last_render_time

    if not PREVIEW_PATH:
        return

    now = time.perf_counter()

    if (
        not force_camera
        and now - _last_render_time
        < _RENDER_INTERVAL
    ):
        return

    update_preview_camera(
        armature,
        force=force_camera,
    )

    scene = bpy.context.scene
    output_path = Path(PREVIEW_PATH)
    temp_path = output_path.with_name(
        output_path.stem + "_tmp" + output_path.suffix
    )

    scene.render.filepath = str(temp_path)

    try:
        bpy.ops.render.render(
            write_still=True,
        )

        # Publicacion atomica: la GUI solo ve imagenes completas.
        if temp_path.exists():
            os.replace(
                str(temp_path),
                str(output_path),
            )

        _last_render_time = time.perf_counter()
    except Exception as exc:
        print(
            f"[LIVE] Error render preview: {exc}",
            flush=True,
        )


def setup_view():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue

            region_3d = (
                area.spaces.active.region_3d
            )

            if region_3d is None:
                continue

            region_3d.view_perspective = "ORTHO"
            region_3d.view_location = Vector(
                (0.0, 0.0, 40.0)
            )
            region_3d.view_distance = 110.0


def tick():
    global _processed_packets
    global _last_stats_time

    if not _running:
        return None

    packet = None

    with _lock:
        if _queue:
            packet = _queue.pop()

    if packet is not None:
        armature = bpy.data.objects.get(
            ARMATURE_NAME
        )

        if armature is not None:
            try:
                applied = apply_packet(
                    armature,
                    packet,
                )

                render_preview(
                    armature
                )

                _processed_packets += 1

                now = time.perf_counter()
                if now - _last_stats_time >= 2.0:
                    print(
                        f"[LIVE] procesados={_processed_packets} "
                        f"ultimo_frame={packet.get('frame_id')} "
                        f"targets={len(packet.get('targets', {}))}",
                        flush=True,
                    )
                    _last_stats_time = now

            except Exception as exc:
                print(
                    f"[LIVE] Error aplicando pose: {exc}",
                    flush=True,
                )

    # Poll frecuente, pero sin una tormenta de callbacks. El render tiene su propio limite.
    return 0.01


def main():
    parse_args()

    armature = bpy.data.objects.get(
        ARMATURE_NAME
    )

    if armature is None:
        raise RuntimeError(
            f"No existe el armature "
            f"'{ARMATURE_NAME}'."
        )

    setup_view()
    capture_initial_pose(
        armature
    )

    setup_preview_scene(
        armature
    )

    render_preview(
        armature,
        force_camera=True,
    )

    thread = threading.Thread(
        target=receiver,
        daemon=True,
    )
    thread.start()

    print(
        "[LIVE] Modelo listo.",
        flush=True,
    )
    print(
        "[LIVE] Pipeline low-latency: "
        "solo se procesa el ultimo paquete.",
        flush=True,
    )
    print(
        "[LIVE] hip mueve Genesis; "
        "Bone permanece estatico.",
        flush=True,
    )
    print(
        "[LIVE] Nombres IK toleran "
        "espacios al final.",
        flush=True,
    )

    bpy.app.timers.register(
        tick,
        first_interval=0.005,
        persistent=True,
    )


main()
