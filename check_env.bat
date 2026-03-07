@echo off
cd /d "%~dp0"
echo === Interpreter & packages ===
py -V
py - << PY
import sys, httpx, openai
print("python:", sys.executable)
print("httpx:", getattr(httpx,'__version__','?'))
print("openai:", getattr(openai,'__version__','?'))
PY
pause
