# MOCAP — Genesis + Blender 4.4

Aplicación Windows para detectar movimiento desde imagen, vídeo o cámara, filtrar jitter, generar keyframes y transferirlos a un Genesis real en Blender 4.4.

## Rama y estado

Rama de trabajo: `feature/01-entrada-y-pose`.

Esta entrega consolida en un único commit la base funcional del pipeline:
- imagen, vídeo y cámara con OpenCV;
- MediaPipe Pose;
- calibración con comprobación de estabilidad;
- suavizado;
- comparación contra el último keyframe aceptado;
- eliminación de micro-movimientos;
- KeyframeStore serializable;
- GUI PySide6;
- inspección del armature real;
- exportación de keyframes a una copia del `.blend`;
- liberación determinista de cámara/detector.

El código externo no importa `bpy`: Blender usa su propio Python mediante un proceso separado.

## Entorno

La máquina objetivo usa Windows 11, Ryzen 7 7435HS, 16 GB RAM y RTX 2050 4 GB. Para mantener el consumo bajo, MediaPipe usa `model_complexity=0`.

Se requiere Python 3.10.x 64 bits.

```powershell
cd D:\Mios\mocap_live_blender
git checkout feature/01-entrada-y-pose
git pull
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python scripts\smoke_test.py
python -m pytest -q
```

## 1. Probar imagen

```powershell
python scripts\pose_test.py --image "D:\ruta\persona.jpg"
python scripts\process_test.py --image "D:\ruta\persona.jpg"
```

La segunda prueba crea `outputs/image_keyframe.json`. Una imagen siempre queda en frame 1.

## 2. Probar vídeo

```powershell
python scripts\pose_test.py --video "D:\ruta\movimiento.mp4" --max-frames 120
```

Para comprobar además calibración, filtro y keyframes:

```powershell
python -c "import sys;sys.path.insert(0,'src');from mocap.app import MocapPipeline;r=MocapPipeline().process_video(r'D:\ruta\movimiento.mp4',300);print('frames=',r.processed_frames,'detectados=',r.detected_frames,'keyframes=',r.keyframes.frames())"
```

## 3. Probar cámara

```powershell
python scripts\live_test.py
```

- `C`: calibrar.
- Mantén T-pose estable hasta completar.
- `R`: grabar.
- Mover brazos/cuerpo: solo cambios significativos generan keyframes.
- `X`: reset.
- `ESC`: salir.

## 4. Probar el Genesis real

Primero inspecciona tu archivo real. No copies el `.blend` al repositorio.

```powershell
python scripts\blender_inspect.py --blend "D:\my blender\bases\Baseic_flutter.blend"
```

Debe aparecer `"ok": true` y encontrarse:
`IK1_regular` con `Bone`, `HAND_IK.L`, `HAND_IK.R`, `HAND_POLE.L`, `HAND_POLE.R`, `FOOT_IK.L`, `FOOT_IK.R`, `FOOT_POLE.L`, `FOOT_POLE.R`.

Si falta un control, **no fuerces la exportación**: el worker aborta para no dañar el rig.

## 5. Exportar una prueba a Blender

Después de tener keyframes, desde Python:

```powershell
python -c "import sys;sys.path.insert(0,'src');from mocap.app import MocapPipeline;from pathlib import Path;p=MocapPipeline();r=p.process_video(r'D:\ruta\movimiento.mp4',300);print(p.save_to_blender(r'D:\my blender\bases\Baseic_flutter.blend',r'D:\my blender\bases\MOCAP_TEST.blend',r.keyframes).message)"
```

Abre `MOCAP_TEST.blend` manualmente en Blender 4.4 y revisa:
1. que `IK1_regular` exista;
2. que los controles tengan keyframes;
3. que la línea de tiempo empiece en frame 1;
4. que el personaje se mueva sin modificar el archivo original.

El worker usa desplazamientos relativos y conservadores sobre los controles IK. Esto es deliberado: el rig no se recrea ni se destruyen constraints.

## 6. Ejecutar la GUI

```powershell
python scripts\run_app.py
```

Botones:
- **Cargar .blend**: selecciona el Genesis.
- **Imagen**: detecta y crea frame 1.
- **Vídeo**: procesa los primeros 300 frames.
- **Cámara**: muestra el esqueleto.
- **Calibrar**: inicia la captura estable.
- **Grabar**: habilita keyframes.
- **Reset**: limpia el estado.
- **Guardar**: genera una copia animada del `.blend`.

## 7. Orden recomendado de validación

No pruebes todo de golpe. Haz exactamente:

```
A. smoke_test.py
B. pytest
C. pose_test.py con una imagen
D. process_test.py con esa imagen
E. pose_test.py con un vídeo corto
F. live_test.py con cámara
G. blender_inspect.py con Baseic_flutter.blend
H. exportación a MOCAP_TEST.blend
I. GUI
```

Si A–H pasan, ya tenemos validada la tubería de datos hasta Blender. La calidad del retargeting se debe ajustar con el comportamiento de tu Genesis real; los nombres de controles están validados de forma estricta para evitar escribir sobre un rig diferente.

## Archivos que nunca se suben

`.blend`, `.blend1`, `.blend2`, `.venv`, `.pyc`, modelos descargados, grabaciones y `outputs/`.

## Arquitectura

```
Imagen / Vídeo / Cámara
        ↓
      OpenCV
        ↓
  MediaPipe Pose
        ↓
Calibración estable
        ↓
Suavizado
        ↓
Comparación contra último keyframe aceptado
        ↓
    KeyframeStore
        ↓
BlenderBridge
        ↓
Blender 4.4 / IK1_regular
        ↓
Copia .blend animada
```

La entrada y el procesamiento se mantienen fuera de Blender para no iniciar Blender por cada frame. Blender solo se invoca para inspección/exportación en esta etapa.
