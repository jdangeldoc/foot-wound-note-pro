@echo off
SET SCRIPT_DIR=%~dp0
PUSHD "%SCRIPT_DIR%"
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
POPD
