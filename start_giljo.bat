@echo off
REM GiljoAI MCP Windows Launcher

echo ===============================================
echo    GiljoAI MCP Launcher
echo ===============================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Set working directory to script location
cd /d "%~dp0"

REM Launch with Python from root
python start_giljo.py %*

if errorlevel 1 (
    echo.
    echo Launch failed. Check the error messages above.
    pause
)
