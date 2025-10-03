@echo off
REM GiljoAI MCP Frontend Launcher
REM Starts only the frontend dashboard

echo ===============================================
echo    GiljoAI MCP - Frontend Dashboard
echo ===============================================
echo.

REM Set working directory to script location
cd /d "%~dp0"

REM Check if venv exists
if exist "venv\Scripts\python.exe" (
    echo Using virtual environment Python
    venv\Scripts\python.exe start_giljo.py --frontend-only %*
) else (
    REM Fallback to system Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Python not found and venv not found
        echo Please install Python 3.8+ from python.org
        pause
        exit /b 1
    )
    echo Warning: Using system Python (venv not found)
    python start_giljo.py --frontend-only %*
)

if errorlevel 1 (
    echo.
    echo Frontend launch failed. Check the error messages above.
    pause
)
