@echo off
REM GiljoAI MCP Launcher for Windows
REM Simplified launcher that uses Python launcher script

setlocal enabledelayedexpansion

echo ========================================================
echo    GiljoAI MCP Service Launcher
echo ========================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if config exists
if not exist "config.yaml" (
    if not exist ".env" (
        echo ERROR: No configuration found.
        echo Please run the installer first:
        echo   python installer\cli\install.py
        pause
        exit /b 1
    )
)

REM Launch Python launcher
echo Starting GiljoAI MCP services...
echo.

python start_giljo.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start services
    echo Check the logs in: logs\launcher\
    pause
    exit /b 1
)

exit /b 0