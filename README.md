# MOCAP — Genesis + Blender 4.4

Aplicación de captura de movimiento para detectar poses desde imagen, vídeo o cámara y transferirlas por etapas al rig Genesis de Blender 4.4.

## Estado

Este repositorio se reconstruye por etapas verificables. `main` conserva la base estable; el desarrollo activo se realiza en ramas `feature/*`.

## Entorno

- Windows 10/11 64 bits.
- Python 3.10.x 64 bits.
- Blender 4.4.x instalado por separado.
- Webcam para las pruebas posteriores de captura en vivo.

La combinación de dependencias está fijada para Python 3.10 porque la máquina de desarrollo dispone de Python 3.10 y 3.14, y NumPy 1.26.4 no proporciona wheel para Python 3.13/3.14.

## Validar el entorno

Desde `D:\\Mios\\mocap_live_blender`:

```powershell
py -3.10 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python scripts\\smoke_test.py
python -m pytest -q
```

## Etapa actual — entrada y pose

Esta rama implementa la primera capa funcional:

- **RF-002:** detección de persona y keypoints.
- **RF-003:** pose desde una imagen.
- **RF-004:** procesamiento de vídeo frame a frame.
- Lectura de imagen con OpenCV sin cargar recursos innecesarios.
- Lectura de vídeo mediante iterador, sin cargar el vídeo completo en RAM.
- Detección mediante MediaPipe Pose.
- Modelo `model_complexity=0` como configuración inicial de bajo consumo.
- Salida propia `PoseFrame/PoseLandmark`, desacoplada de MediaPipe.
- Liberación explícita del detector mediante context manager.

### Probar una imagen

Usa una imagen de una persona:

```powershell
python scripts\\pose_test.py --image "D:\\ruta\\persona.jpg"
```

La prueba procesa la imagen como frame **1**, aunque todavía no genera keyframes. Esto deja preparada la regla RF-008 para la siguiente etapa.

### Probar un vídeo

```powershell
python scripts\\pose_test.py --video "D:\\ruta\\movimiento.mp4" --max-frames 120
```

El vídeo se procesa frame a frame y se libera `VideoCapture` al terminar.

## Siguiente etapa

La siguiente rama/commit funcional será la **calibración**:

1. Definir el estado `CALIBRATING`.
2. Estabilizar la pose inicial.
3. No generar keyframes durante calibración.
4. Guardar una referencia corporal.
5. Preparar la comparación de movimiento para el filtro posterior.

Después vendrán jitter/umbral, retargeting al rig `IK1_regular`, integración con Blender, live camera y GUI.

## Git

- `main`: base estable.
- `feature/*`: desarrollo de cada etapa.
- Cada etapa debe terminar con pruebas pasando y un commit identificable.
- No se suben `.blend`, `.pyc`, `.venv`, modelos ni archivos generados.
