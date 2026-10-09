# MOCAP — Genesis + Blender 4.4

Aplicación de captura de movimiento para detectar poses desde imagen, vídeo o cámara y transferirlas por etapas al rig Genesis de Blender 4.4.

## Estado

Este repositorio se está reconstruyendo desde una base limpia. El primer objetivo es tener un entorno reproducible y verificable antes de implementar detección, calibración, filtrado, retargeting, Blender y GUI.

## Entorno de desarrollo

- Windows 10/11 de 64 bits.
- **Python 3.10.x de 64 bits**.
- Blender 4.4.x instalado por separado.
- Git.
- Webcam para las pruebas de captura en vivo.

### Por qué Python 3.10

La máquina de desarrollo dispone actualmente de Python 3.10 y 3.14, pero no de Python 3.12.

La dependencia fijada **NumPy 1.26.4** no tiene wheel para Python 3.13/3.14. Por eso **no se debe crear este entorno con Python 3.14** ni cambiar NumPy a 2.x como solución rápida: MediaPipe y el resto del stack deben validarse juntos.

Para esta base se usa Python 3.10, que permite instalar NumPy 1.26.4 mediante wheel y mantiene la combinación fijada con MediaPipe 0.10.21.

Comprueba tus intérpretes:

```powershell
py -0p
```

Debe aparecer Python 3.10.

## Crear el entorno desde cero

Desde:

```text
D:\Mios\mocap_live_blender
```

Ejecuta:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

La versión debe mostrar:

```text
Python 3.10.x
```

Si PowerShell bloquea la activación, usa directamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Validar la base

```powershell
python scripts\smoke_test.py
python -m pytest -q
```

El smoke test verifica Python, NumPy, SciPy, OpenCV, MediaPipe y PySide6. No abre la webcam ni necesita Blender.

## Estructura

```text
src/mocap/             Código de la aplicación
scripts/               Diagnósticos ejecutables
tests/                 Pruebas automatizadas
requirements.txt       Dependencias de ejecución
requirements-dev.txt   Dependencias de desarrollo
pyproject.toml         Configuración del paquete y pytest
```

## Etapas de implementación

1. Entorno reproducible y diagnóstico.
2. Entrada de imagen y vídeo.
3. Detección de pose.
4. Calibración sin generar keyframes.
5. Filtro de jitter y umbral de movimiento.
6. Mapeo de keypoints al rig `IK1_regular`.
7. Comunicación con Blender 4.4 y guardado de una copia del archivo.
8. Cámara en vivo, previsualización y GUI.
9. Pruebas de integración y control de recursos.

La integración con Blender permanecerá separada del Python de la aplicación; Blender no se instala mediante pip. Los archivos `.blend`, entornos virtuales, modelos descargados y salidas generadas no deben subirse al repositorio.

## Regla de trabajo con Git

El estado inicial funcional se mantiene como una base recuperable. Las siguientes etapas se harán en commits pequeños y verificables; si una etapa rompe algo, se podrá volver al último estado estable.
