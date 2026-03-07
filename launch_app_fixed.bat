@echo off
cd /d "%~dp0"
echo === Launch Orthocoder Pro (pinned interpreter) ===
if "%OPENAI_API_KEY%"=="" (
  echo [WARN] OPENAI_API_KEY not set. Set it with:  setx OPENAI_API_KEY "sk-..."
)
REM Use the same interpreter as 'py' to avoid mismatched PATH streamlit
py -m streamlit run app.py
pause
