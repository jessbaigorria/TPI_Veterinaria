@echo off
REM VetRed - crea el entorno, instala dependencias, carga el seed y levanta la app.
REM Uso: run.bat            (normal)
REM      run.bat --reset    (regenera la base de datos de prueba)
cd /d "%~dp0"
if not exist .venv (
    echo ^>^> Creando entorno virtual
    py -3.12 -m venv .venv 2>nul || python -m venv .venv
)
if not exist .venv\Scripts\python.exe (
    echo No se pudo crear el entorno virtual. Instala Python 3.12 desde python.org
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
echo ^>^> Instalando dependencias
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo ^>^> Cargando datos de prueba
python -m app.seed %*
echo ^>^> VetRed en http://localhost:8000  (Ctrl+C para detener)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
