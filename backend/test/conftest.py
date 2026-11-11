import sys
from pathlib import Path

# Permite importar titular.py, mascota.py, etc. desde la carpeta de arriba
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dominio"))