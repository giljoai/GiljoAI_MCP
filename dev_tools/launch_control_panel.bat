@echo off
REM ============================================================
REM Launch Control Panel from Isolated Dev Tools Environment
REM ============================================================

cd /d "%~dp0"

REM Check if dev tools venv exists
if not exist "venv_devtools\Scripts\python.exe" (
    echo.
    echo Dev tools environment not found!
    echo.
    echo Please run setup first:
    echo   dev_tools\setup_devtools_venv.bat
    echo.
    pause
    exit /b 1
)

REM Launch control panel from isolated venv
echo Starting GiljoAI MCP Developer Control Panel...
echo Using isolated environment: dev_tools\venv_devtools\
echo.

venv_devtools\Scripts\python.exe control_panel.py

if %errorlevel% neq 0 (
    echo.
    echo Control panel exited with error code: %errorlevel%
    pause
)
