"""Arranque de la aplicación gráfica."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from mocap.gui import main
raise SystemExit(main())
