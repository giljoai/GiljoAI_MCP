@echo off
setlocal

cd /d %~dp0

if not exist .venv (
  echo Creating venv...
  py -3 -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

uvicorn dev_tools.simulator.simulator_app:app --host 0.0.0.0 --port 7390

