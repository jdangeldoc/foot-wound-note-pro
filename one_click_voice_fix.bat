@echo off
setlocal enableextensions enabledelayedexpansion
title OrthoCoder Pro - One-Click Voice Fix

echo =====================================================
echo   OrthoCoder Pro - One-Click Voice Fix (OpenAI 1.x)
echo   This script updates packages, patches voice_io.py,
echo   sets your OPENAI_API_KEY for this session if needed,
echo   and launches Streamlit.
echo =====================================================
echo.

REM Verify we are in the project root (should have app.py)
if not exist "app.py" (
    echo [ERROR] app.py not found. 
    echo Right-click your project folder (the one with app.py) and choose "Open in Terminal",
    echo then run this script again from that directory.
    pause
    exit /b 1
)

REM Ensure wound_voice directory exists
if not exist "wound_voice" mkdir "wound_voice"

REM Backup existing voice_io.py if present
if exist "wound_voice\voice_io.py" (
    for /f "tokens=1-3 delims=/.- " %%a in ("%date%") do set d=%%c-%%a-%%b
    set tm=%time: =0%
    set tm=%tm::=%
    set ts=%d%_%tm%
    copy /y "wound_voice\voice_io.py" "wound_voice\voice_io.backup.%ts%.py" >nul
    echo Backed up existing voice_io.py to voice_io.backup.%ts%.py
)

REM Write new voice_io.py using PowerShell
echo Patching wound_voice\voice_io.py ...
powershell -NoProfile -Command "$c = Get-Content -Raw -LiteralPath '%~dp0voice_io.py'; Set-Content -LiteralPath 'wound_voice\\voice_io.py' -Value $c -Encoding UTF8"
if errorlevel 1 (
    echo [ERROR] Failed to write wound_voice\voice_io.py
    pause
    exit /b 1
)

REM Decide pip command
where py >nul 2>&1
if %errorlevel%==0 (
    set PYCMD=py -m pip
) else (
    set PYCMD=pip
)

echo.
echo Updating Python packages ...
%PYCMD% uninstall -y openai
%PYCMD% cache purge
%PYCMD% install --upgrade "openai>=1.40.0" "httpx>=0.27" "streamlit>=1.36"
if errorlevel 1 (
    echo [ERROR] Package installation failed.
    pause
    exit /b 1
)

REM Update requirements.txt pins (idempotent)
if exist "requirements.txt" (
    powershell -NoProfile -Command ^
      "$p = Get-Content requirements.txt; "^
      "$p = $p | Where-Object {$_ -notmatch '^openai\s*==|^openai\s*>=|^openai\s*$'}; "^
      "$p = $p | Where-Object {$_ -notmatch '^httpx'}; "^
      "$p = $p | Where-Object {$_ -notmatch '^streamlit'}; "^
      "$p | Set-Content requirements.txt; "^
      "Add-Content requirements.txt 'openai>=1.40.0'; "^
      "Add-Content requirements.txt 'httpx>=0.27'; "^
      "Add-Content requirements.txt 'streamlit>=1.36'"
)

REM Ensure API key for this session
if "%OPENAI_API_KEY%"=="" (
    echo.
    echo Paste your OPENAI_API_KEY then press ENTER:
    set /p OPENAI_API_KEY=
    if "%OPENAI_API_KEY%"=="" (
        echo [ERROR] No key entered. Cannot continue.
        pause
        exit /b 1
    )
)

echo.
echo Launching Streamlit...
start "" cmd /c "streamlit run app.py"
echo Done. A Streamlit window should open shortly.
echo.
pause
