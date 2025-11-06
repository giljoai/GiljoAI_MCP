@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\.." >nul 2>&1
set "REPO_ROOT=%CD%"

rem Determine Python command (prefer py -3 on Windows, fallback to python)
set "PYTHON_CMD="
where py >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>&1 && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [DevPanel] Python interpreter not found on PATH.
    echo Install Python 3 and retry.
    exit /b 1
)

echo [DevPanel] Generating inventories (Phase 1001)...
call %PYTHON_CMD% dev_tools\devpanel\scripts\devpanel_index.py --out temp\devpanel\index
if errorlevel 1 (
    echo [DevPanel] Inventory generation failed. Aborting.
    exit /b 1
)

echo [DevPanel] Launching backend on http://127.0.0.1:8283 ...
start "DevPanel Backend" cmd /k call %PYTHON_CMD% dev_tools\devpanel\run_backend.py

set "FRONTEND_HTML=%REPO_ROOT%\dev_tools\devpanel\frontend\index.html"
if exist "%FRONTEND_HTML%" (
    echo [DevPanel] Opening frontend: %FRONTEND_HTML%
    start "" "%FRONTEND_HTML%"
) else (
    echo [DevPanel] Frontend HTML not found at %FRONTEND_HTML%
)

echo [DevPanel] Ready. Close this window when finished.
popd >nul 2>&1
endlocal
