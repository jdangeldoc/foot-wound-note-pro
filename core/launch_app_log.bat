@echo off
setlocal enabledelayedexpansion
title OrthoCoder Pro - Launcher with Logging

cd /d "%~dp0"

REM Timestamp-safe values
for /f "tokens=1-4 delims=/.- " %%a in ("%date%") do set DATESTAMP=%%a%%b%%c%%d
for /f "tokens=1-3 delims=:. " %%a in ("%time%") do set TIMESTAMP=%%a%%b%%c

set "LOGDIR=logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\launch_%DATESTAMP%_%TIMESTAMP%.txt"

echo Writing logs to "%LOG%"
echo ===== OrthoCoder Pro Launch Log ===== >"%LOG%"
echo Date: %date%  Time: %time% >>"%LOG%"
echo Working Dir: %cd% >>"%LOG%"
echo. >>"%LOG%"

set "TARGET_PY="
for %%V in (3.12 3.11) do (
  py -%%V -c "import sys; print(sys.version)" >>"%LOG%" 2>&1 && set "TARGET_PY=py -%%V"
  if defined TARGET_PY goto :found
)
where py >>"%LOG%" 2>&1 && set "TARGET_PY=py -3"
if not defined TARGET_PY (
  where python >>"%LOG%" 2>&1 && set "TARGET_PY=python"
)
if not defined TARGET_PY (
  echo [ERROR] Python 3.11+ not found. >>"%LOG%"
  echo [ERROR] Python 3.11+ not found. See "%LOG%".
  pause
  exit /b 1
)
:found
echo Using Python launcher: %TARGET_PY% >>"%LOG%"

if not exist ".venv" (
  echo Creating virtual environment... >>"%LOG%"
  %TARGET_PY% -m venv .venv >>"%LOG%" 2>&1 || (echo [ERROR] Failed to create venv. See "%LOG%". & pause & exit /b 1)
)

echo Upgrading pip and installing requirements... >>"%LOG%"
".venv\Scripts\python.exe" -m pip install --upgrade pip >>"%LOG%" 2>&1
".venv\Scripts\pip.exe" install -r requirements.txt >>"%LOG%" 2>&1 || (echo [ERROR] pip install failed. See "%LOG%". & pause & exit /b 1)

echo Starting Streamlit... >>"%LOG%"
".venv\Scripts\python.exe" -m streamlit run app.py >>"%LOG%" 2>&1

echo.
echo Done. If the app didn't open, open "%LOG%" and scroll to the bottom for errors.
pause
