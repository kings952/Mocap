# MOCAP

Sistema de captura de movimiento para trabajar con Blender 4.4.

Esta rama `main` parte de una base limpia. La implementacion se construira por etapas:

1. Preparacion del entorno Python.
2. Prueba de captura de imagen.
3. Deteccion de pose.
4. Calibracion.
5. Filtrado de movimiento.
6. Retargeting hacia el rig de Blender.
7. Integracion con Blender.
8. GUI y modos de trabajo.

## Requisitos

- Windows 10/11
- Python 3.11.x
- Blender 4.4.x
- Git
- Webcam para las pruebas de captura

> Blender no se instala mediante `requirements.txt`. Su Python interno se tratara por separado cuando integremos el addon.

## Crear el entorno virtual

En PowerShell, desde la raiz del repositorio:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Prueba inicial

```powershell
python scripts\smoke_test.py
```

La prueba debe terminar indicando que NumPy, SciPy, OpenCV, MediaPipe y PySide6 pueden importarse correctamente.

## Estructura inicial

```text
Mocap/
|-- src/
|   |-- mocap/
|       |-- __init__.py
|       |-- config.py
|-- scripts/
|   |-- smoke_test.py
|-- tests/
|   |-- test_base.py
|-- requirements.txt
|-- requirements-dev.txt
|-- README.md
|-- .gitignore
```

## Regla de trabajo

Cada etapa debe quedar funcional antes de pasar a la siguiente. No se incorporaran dependencias o componentes de Blender hasta que la prueba independiente correspondiente funcione.
