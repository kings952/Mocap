# MOCAP — Genesis + Blender 4.4

Aplicación de captura de movimiento para detectar poses desde imagen, vídeo o cámara y, por etapas, transferirlas al rig Genesis de Blender 4.4.

## Base de desarrollo

Esta base prioriza que el entorno sea reproducible antes de implementar la detección, la calibración, el filtrado, el retargeting y la interfaz. No se considera terminada ninguna etapa hasta que sus pruebas pasen.

### Requisitos

- Windows 10/11 de 64 bits.
- **Python 3.12.x de 64 bits** para la aplicación.
- Blender 4.4.x instalado por separado.
- Git.
- Webcam para probar la captura en vivo.

**Importante sobre NumPy:** el error de instalación aparece normalmente al ejecutar pip con Python 3.13 o 3.14. NumPy 1.26.4 ofrece wheels para Python 3.9–3.12, pero no para 3.13/3.14. Esta base conserva NumPy 1.26.4 porque la combinación fijada con MediaPipe 0.10.21 está preparada para Python 3.12. No cambies la dependencia a NumPy 2.x sin validar primero la compatibilidad de MediaPipe y el resto del stack.

Comprueba qué versiones de Python están instaladas:

```powershell
py -0p
```

Si no aparece Python 3.12 de 64 bits, instálalo antes de continuar.

## Preparar el entorno en PowerShell

Ejecuta desde la carpeta raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

La versión mostrada por `python --version` debe comenzar con `Python 3.12.`. Si PowerShell bloquea la activación, puedes usar directamente `.\.venv\Scripts\python.exe` en los comandos siguientes sin activar el entorno.

## Validar instalación y pruebas

```powershell
python scripts\smoke_test.py
python -m pytest -q
```

La prueba de entorno comprueba versiones e importaciones; no abre la webcam ni necesita Blender. La suite inicial valida la configuración base. Son pruebas de infraestructura, no una afirmación de que el sistema MOCAP completo ya esté implementado.

## Estructura

```text
src/mocap/          Código de la aplicación
scripts/            Diagnósticos ejecutables
tests/              Pruebas automatizadas
requirements.txt    Dependencias de ejecución
requirements-dev.txt Dependencias de desarrollo y pruebas
pyproject.toml      Configuración del paquete y pytest
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

La integración con Blender se mantendrá separada del Python de la aplicación; no se instalará Blender mediante pip. Los archivos `.blend`, entornos virtuales, modelos descargados y salidas generadas no deben subirse al repositorio.
