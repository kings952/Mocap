# MOCAP — Genesis + Blender 4.4

Aplicación de pruebas para detectar pose desde imagen, vídeo o cámara y exportar una copia animada de un rig Genesis.

## Rama de trabajo
`feature/02-blender-gui-testing`, creada desde `be2758992a1994557e559b1584f3dcd36cc007d2`. Los cambios de esta etapa se agrupan en un solo commit.

## Instalar y ejecutar (Windows / Python 3.10)
```powershell
cd D:\Mios\mocap_live_blender
git fetch origin
git checkout feature/02-blender-gui-testing
git reset --hard origin/feature/02-blender-gui-testing
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python scripts\smoke_test.py
python -m pytest -q
python scripts\run_app.py
```

## Flujo recomendado de prueba
1. **Cargar modelo .blend**: elige `D:\my blender\bases\Baseic_flutter.blend`.
2. **Imagen**: comprueba que aparece el esqueleto detectado y se crea un keyframe en frame 1.
3. **Vídeo**: usa un clip corto (máximo 300 frames); mira la lista de keyframes y confirma que los frames aumentan.
4. **Cámara**: pulsa Iniciar cámara, colócate en T-pose y pulsa Calibrar T-pose; espera a que el progreso termine, luego empieza a grabar y mueve brazos/cuerpo.
5. **Guardar animación**: guarda como otro archivo, por ejemplo `Baseic_flutter_MOCAP.blend`. No sobrescribe el original. La exportación informa de curvas y puntos de keyframe y falla si no se crea acción.
6. **Abrir visor Blender**: abre el archivo animado en Blender para inspeccionar el personaje y reproducir la línea de tiempo.

## Corrección de la exportación
- Los desplazamientos del rig se calculan respecto de la primera pose capturada; la primera pose es la referencia neutra y no mueve el personaje por sí sola.
- Se insertan keyframes en canales de transformación de los controles IK/pole, usando keying visual cuando está disponible.
- Se comprueba que exista una acción con curvas y puntos de keyframe y que el archivo de salida se haya escrito.
- La ruta de salida debe ser distinta de la original.

## GUI
Incluye selección del Genesis, entrada por imagen/vídeo/cámara, calibración, grabación, reset, lista de keyframes, visor del esqueleto, guardado verificado y botón para abrir el modelo en Blender.

**Nota:** el visor 3D se abre como ventana de Blender separada; no está incrustado dentro de PySide6 ni sincronizado en vivo todavía. El retargeting es una primera aproximación basada en landmarks y necesita validarse con el rig Genesis real. No se puede confirmar la calidad visual sin ejecutar la prueba con tu archivo `.blend`.

## Diagnóstico
Si la exportación falla, el cuadro de error incluye el registro de Blender. En PowerShell se puede probar una imagen con:
```powershell
python scripts\process_test.py --image "D:\ruta\persona.jpg"
```
No subas archivos `.blend`, grabaciones ni modelos al repositorio.
