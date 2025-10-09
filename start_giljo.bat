@echo off
REM GiljoAI MCP Windows Launcher
REM Updated to use unified startup.py

echo ===============================================
echo    GiljoAI MCP Launcher
echo ===============================================
echo.

REM Set working directory to script location
cd /d "%~dp0"

REM Check if venv exists
if exist "venv\Scripts\python.exe" (
    echo Using virtual environment Python
    venv\Scripts\python.exe startup.py %*
) else (
    REM Fallback to system Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Python not found and venv not found
        echo Please install Python 3.10+ from python.org
        pause
        exit /b 1
    )
    echo Warning: Using system Python (venv not found)
    python startup.py %*
)

if errorlevel 1 (
    echo.
    echo Launch failed. Check the error messages above.
    pause
)
