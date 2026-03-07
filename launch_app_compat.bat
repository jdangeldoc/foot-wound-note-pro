@echo off
setlocal enabledelayedexpansion
title OrthoCoder Pro - Compatibility Launcher

REM 1) Always run from this folder
cd /d "%~dp0"

REM 2) Find a working Python (try 3.12, 3.11, fallback py -3, then python)
set "TARGET_PY="
for %%V in (3.12 3.11) do (
  py -%%V -c "import sys; print(sys.version)" >nul 2>&1 && set "TARGET_PY=py -%%V"
  if defined TARGET_PY goto :found
)
where py >nul 2>&1 && set "TARGET_PY=py -3"
if not defined TARGET_PY (
  where python >nul 2>&1 && set "TARGET_PY=python"
)
if not defined TARGET_PY (
  echo [ERROR] Python 3.11+ not found. Install from https://www.python.org/downloads/ and re-run.
  pause
  exit /b 1
)
:found
echo Using Python launcher: %TARGET_PY%

REM 3) Create venv if missing
if not exist ".venv" (
  echo Creating virtual environment...
  %TARGET_PY% -m venv .venv || (echo [ERROR] Failed to create venv & pause & exit /b 1)
)

REM 4) Upgrade pip and install requirements
echo Installing/Updating dependencies (this may take a minute)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\pip.exe" install -r requirements.txt || (echo [ERROR] pip install failed & pause & exit /b 1)

REM 5) Launch the app
echo Launching OrthoCoder Pro on Streamlit...
".venv\Scripts\python.exe" -m streamlit run app.py
echo.
echo If a browser didn't open automatically, copy the local URL shown above and paste it into your browser.
echo (Example: http://localhost:8501)
pause
