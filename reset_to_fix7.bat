@echo off
REM OrthoCoder Pro - Reset to latest archive
REM Usage: Place this BAT in the same folder as your ZIP (e.g., Downloads), then double-click.

setlocal ENABLEDELAYEDEXPANSION

echo.
echo ===== OrthoCoder Pro - Reset to Latest Archive =====
echo.

REM 1) Locate a ZIP
set "ZIP="
for /f "delims=" %%F in ('dir /b /od /a-d orthocoder-pro_*.zip orthocoder-pro_fix*.zip orthocoder-pro_archive_*.zip 2^>NUL') do set "ZIP=%%F"
if "%ZIP%"=="" (
  echo Could not find an OrthoCoder Pro ZIP in this folder.
  echo Please put the archive here, or drag/drop it onto this BAT.
  echo Ex: orthocoder-pro_fix7_YYYYMMDD_HHMMSS.zip  or  orthocoder-pro_archive_*.zip
  pause
  exit /b 1
)
echo Found ZIP: %ZIP%

REM 2) Set default targets (edit if needed)
set "TARGET1=C:\Users\jdang\OneDrive – Jefferygroup\DocProjectVault\orthocoder-pro"
set "TARGET2=C:\Users\jdang\OneDrive – Jefferygroup\DocProjectVault"
set "TARGET3=C:\Users\jdang\OneDrive-Jefferygroup\Orthocoder-Pro"

REM 3) Confirm
echo.
echo Will extract to:
echo   [1] %TARGET1%
echo   [2] %TARGET3%  (cloud mirror)
echo.
choice /c YN /n /m "Proceed with extraction? (Y/N): "
if errorlevel 2 (
  echo Cancelled.
  exit /b 0
)

REM 4) Ensure folders exist
for %%D in ("%TARGET1%","%TARGET3%") do (
  if not exist "%%~D" (
    echo Creating %%~D
    mkdir "%%~D" >NUL 2>&1
  )
)

REM 5) Use PowerShell Expand-Archive (built-in on Win10+)
echo Extracting... this may take a moment.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try {Expand-Archive -Path '%ZIP%' -DestinationPath '%TARGET1%' -Force; ^
        Expand-Archive -Path '%ZIP%' -DestinationPath '%TARGET3%' -Force; ^
        Write-Host 'Done.'} catch {Write-Error $_; exit 1}"

if errorlevel 1 (
  echo Extraction failed.
  pause
  exit /b 1
)

echo.
echo Reset complete!
echo Launching Streamlit from %TARGET1% ...
echo.
pushd "%TARGET1%"
if exist launch_app.bat (
  call launch_app.bat
) else (
  echo Could not find launch_app.bat in %TARGET1%
)
popd

echo.
echo All set.
pause
