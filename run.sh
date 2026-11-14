#!/usr/bin/env bash
# VetRed – crea el entorno, instala dependencias, carga el seed (si la base está vacía) y levanta la app.
# Uso: ./run.sh            (normal)
#      ./run.sh --reset    (regenera la base de datos de prueba)
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidato in python3.12 python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then PY="$candidato"; break; fi
  done
fi
if [ ! -d .venv ]; then
  echo ">> Creando entorno virtual con $PY"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo ">> Instalando dependencias"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo ">> Cargando datos de prueba"
python -m app.seed "$@"
echo ">> VetRed en http://localhost:8000  (Ctrl+C para detener)"
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
