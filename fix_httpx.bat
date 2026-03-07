@echo off
echo === OrthoCoder Pro: OpenAI/httpx compatibility fix ===
echo.
echo 1) Uninstalling incompatible httpx...
py -m pip uninstall -y httpx
echo.

echo 2) Installing compatible httpx==0.26.0 ...
py -m pip install httpx==0.26.0
echo.

echo 3) Making sure openai==1.43.1 is present...
py -m pip install openai==1.43.1
echo.

echo 4) Showing versions:
py - <<PYCODE
import httpx, pkgutil, importlib
import importlib.metadata as md
print("httpx version:", httpx.__version__)
try:
    print("openai version:", md.version("openai"))
except Exception as e:
    print("openai version: <unknown>", e)
PYCODE

echo.
echo Done. Press any key to exit.
pause
