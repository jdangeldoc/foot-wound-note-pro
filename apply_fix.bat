@echo off
cd /d "%~dp0"
echo === Applying dependency pin (openai + httpx) ===
for /r %%D in (__pycache__) do if exist "%%D" rmdir /s /q "%%D"
py -m pip uninstall -y httpx
py -m pip install -U -r requirements.txt
echo.
echo Done. Launch the app using launch_app_fixed.bat
pause
