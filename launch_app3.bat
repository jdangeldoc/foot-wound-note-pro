@echo off
REM OrthoCoder Pro - Local Launcher (Windows)
REM Creates a venv in .venv, installs deps, and runs the Streamlit app.
setlocal enabledelayedexpansion

REM 1) Set working directory to this script's folder
cd /d "%~dp0"

REM 2) Prefer Python 3.11+
where py >nul 2>&1
if %errorlevel% neq 0 (
  echo Python launcher (py.exe) not found. Please install Python 3.11+ from python.org and re-run.
  pause
  exit /b 1
)

REM 3) Create virtual environment if missing
if not exist ".venv" (
  echo Creating virtual environment...
  py -3.11 -m venv .venv || (echo Failed to create venv & pause & exit /b 1)
)

REM 4) Upgrade pip and install requirements
echo Installing/Updating dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\pip.exe" install -r requirements.txt || (echo pip install failed & pause & exit /b 1)

REM 5) Run Streamlit app
echo Launching OrthoCoder Pro...
".venv\Scripts\python.exe" -m streamlit run app.py
