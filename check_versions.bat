@echo off
cd /d "%~dp0"
echo === Interpreter & Package Versions ===
py -V
where streamlit
py -m pip show openai
py -m pip show httpx
py -m pip show streamlit
python -c "import httpx, sys; print('python exe:', sys.executable); print('httpx:', httpx.__version__)"
pause
