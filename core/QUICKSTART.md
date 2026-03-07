# OrthoCoder Pro — Quickstart (Local)

## Run on Windows (recommended)
1. Ensure Python **3.11+** is installed (from python.org).
2. Place all project files in a single folder (no nested folders).
3. Double‑click **`launch_app.bat`**.
   - The script will create `.venv`, install `requirements.txt`, and start the Streamlit app.

If you prefer a terminal:
```
cd path\to\orthocoder-pro
py -3.11 -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

## Render Deploy (from this folder)
- The included `render.yaml` is configured to run:
  ```
  streamlit run app.py --server.port $PORT --server.address 0.0.0.0
  ```
- Create a new **Web Service** on Render, connect your repo, and Render will build from `requirements.txt` automatically.
