@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\..\.." >nul 2>&1
set "REPO_ROOT=%CD%"

rem Determine Python command (prefer py -3 on Windows, fallback to python)
set "PYTHON_BOOT="
where py >nul 2>&1 && set "PYTHON_BOOT=py -3"
if not defined PYTHON_BOOT (
    where python >nul 2>&1 && set "PYTHON_BOOT=python"
)
if not defined PYTHON_BOOT (
    echo [DevPanel] Python interpreter not found on PATH.
    echo Install Python 3 and retry.
    exit /b 1
)

set "VENV_DIR=%REPO_ROOT%\dev_tools\devpanel\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "SETUP_SENTINEL=%VENV_DIR%\devpanel_setup_done.txt"

if not exist "%VENV_PY%" (
    echo [DevPanel] Creating isolated virtual environment...
    call %PYTHON_BOOT% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [DevPanel] Failed to create virtual environment.
        exit /b 1
    )
)

if not exist "%SETUP_SENTINEL%" (
    echo [DevPanel] Installing project dependencies into isolated venv...
call "%VENV_PY%" -m pip install --upgrade pip
call "%VENV_PY%" -m pip install -e .[dev]
    call "%VENV_PY%" -m pip install -r requirements.txt
    if exist dev-requirements.txt call "%VENV_PY%" -m pip install -r dev-requirements.txt
    if errorlevel 1 (
        echo [DevPanel] Dependency installation failed.
        exit /b 1
    )
    echo setup>"%SETUP_SENTINEL%"
)

echo [DevPanel] Ensuring runtime utilities are present (watchdog, rich, aiohttp, tiktoken, aiofiles, packaging)...
call "%VENV_PY%" -m pip install watchdog rich aiohttp tiktoken aiofiles packaging >nul 2>&1

echo [DevPanel] Generating inventories (Phase 1001)...
call "%VENV_PY%" dev_tools\devpanel\scripts\devpanel_index.py --out temp\devpanel\index
if errorlevel 1 (
    echo [DevPanel] Inventory generation failed. Aborting.
    exit /b 1
)

echo [DevPanel] Launching backend on http://127.0.0.1:8283 ...
set "ENABLE_DEVPANEL=true"
start "DevPanel Backend" cmd /k call "%VENV_PY%" dev_tools\devpanel\run_backend.py

echo [DevPanel] Launching frontend server on http://127.0.0.1:5173 ...
start "DevPanel Frontend" cmd /k call "%VENV_PY%" dev_tools\devpanel\scripts\start_frontend_server.py

timeout 2 >nul
start "" "http://127.0.0.1:5173/index.html"

echo [DevPanel] Ready. Close this window when finished.
popd >nul 2>&1
endlocal
