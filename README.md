# MOCAP — Genesis + Blender 4.4

Aplicación de captura de movimiento para detectar poses desde imagen, vídeo o cámara y transferirlas por etapas al rig Genesis de Blender 4.4.

## Estado de esta rama

La rama \`feature/01-entrada-y-pose\` consolida las primeras capas funcionales del documento de requerimientos. El pipeline puede probarse sin depender todavía de Blender en cada frame.

### Implementado

- RF-002: detección de persona y keypoints.
- RF-003: pose desde una imagen.
- RF-004: vídeo frame a frame.
- RF-005: captura de cámara en vivo.
- RF-006: calibración inicial mediante muestras de una pose estable.
- RF-007: la calibración no produce keyframes.
- RF-008: una imagen se representa en el frame 1.
- RF-009: vídeo/live comparan el movimiento y aceptan solo cambios significativos.
- RF-010: filtro contra micro-movimientos mediante umbral y suavizado.
- Liberación determinista de cámara y detector.
- Visualización del esqueleto detectado.
- Modelo de keyframes independiente de Blender.

## Entorno

- Windows 10/11 64 bits.
- Python 3.10.x 64 bits.
- Blender 4.4.x instalado por separado.
- Webcam para la prueba live.

La combinación de dependencias está fijada para Python 3.10 porque la máquina de desarrollo dispone de Python 3.10 y 3.14, y NumPy 1.26.4 no proporciona wheel para Python 3.13/3.14.

\`\`\`powershell
py -3.10 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python scripts\\smoke_test.py
python -m pytest -q
\`\`\`

## Pruebas

### Imagen

\`\`\`powershell
python scripts\\pose_test.py --image "D:\\ruta\\persona.jpg"
\`\`\`

Una imagen queda asociada al frame 1 en el modelo de keyframes. Esta etapa todavía no escribe un \`.blend\`.

### Vídeo

\`\`\`powershell
python scripts\\pose_test.py --video "D:\\ruta\\movimiento.mp4" --max-frames 120
\`\`\`

El vídeo se lee mediante un iterador y no se carga completo en memoria.

### Cámara + calibración + filtro

\`\`\`powershell
python scripts\\live_test.py
\`\`\`

Controles:

- C: comenzar calibración.
- Mantener una pose estable hasta llegar al 100%.
- R: comenzar grabación.
- Moverse: solo los cambios que superen el umbral generan keyframes.
- X: reiniciar.
- ESC: salir.

## Arquitectura

\`\`\`
Imagen / Vídeo / Cámara
          |
          v
     OpenCV input
          |
          v
    MediaPipe Pose
          |
          v
 PoseFrame/PoseLandmark
          |
          +--> Calibración
          |
          +--> Suavizado + filtro
          |
          v
     KeyframeStore
          |
          v
   Adaptador Genesis
          |
          v
       Blender 4.4
\`\`\`

El adaptador Genesis/Blender se mantiene separado deliberadamente: antes de escribir transformaciones sobre \`IK1_regular\` hay que validar el mapeo exacto de los controles del \`.blend\` real.

## Próxima integración

La siguiente capa será el adaptador Blender:

1. Cargar una copia del \`.blend\`.
2. Encontrar el armature \`IK1_regular\`.
3. Validar \`Bone\`, \`HAND_IK.L/R\`, \`HAND_POLE.L/R\`, \`FOOT_IK.L/R\` y \`FOOT_POLE.L/R\`.
4. Aplicar una pose de prueba.
5. Guardar keyframes en Blender.
6. Conectar el retargeting de pose humana a esos controles.

No se suben \`.blend\`, \`.pyc\`, \`.venv\`, modelos ni archivos generados.
