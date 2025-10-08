@echo off
REM ============================================================
REM Setup Separate Virtual Environment for Developer Tools
REM ============================================================
REM This creates dev_tools/venv_devtools/ (isolated from main venv/)
REM Allows dev tools to run independently and delete main venv

echo.
echo ============================================================
echo     GiljoAI MCP - Dev Tools Environment Setup
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "control_panel.py" (
    echo ERROR: Please run this script from dev_tools/ directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Creating isolated virtual environment for dev tools...
echo Location: dev_tools/venv_devtools/
echo.

REM Create virtual environment in dev_tools/venv_devtools
python -m venv venv_devtools

if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
call venv_devtools\Scripts\activate.bat

echo.
echo Installing dev tools dependencies...
pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Dev Tools Environment Setup Complete!
echo ============================================================
echo.
echo Virtual Environment: dev_tools\venv_devtools\
echo Dependencies Installed: psutil, psycopg2-binary, pyyaml
echo.
echo To run the control panel:
echo   1. cd dev_tools
echo   2. venv_devtools\Scripts\activate
echo   3. python control_panel.py
echo.
echo OR use the launcher:
echo   dev_tools\launch_control_panel.bat
echo ============================================================
echo.

pause
