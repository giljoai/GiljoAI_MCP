@echo off
REM GiljoAI MCP - Update Dependencies
REM Run this after git pull to update Python dependencies

echo ===============================================
echo    GiljoAI MCP - Dependency Updater
echo ===============================================
echo.

REM Set working directory to script location
cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo Error: Virtual environment not found
    echo Please run the installer first: python installer/cli/install.py
    pause
    exit /b 1
)

echo Using virtual environment: %~dp0venv
echo.
echo Updating Python dependencies from requirements.txt...
echo.

REM Activate venv and upgrade pip first
venv\Scripts\python.exe -m pip install --upgrade pip

REM Install/update all requirements
venv\Scripts\python.exe -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to update dependencies
    echo.
    echo Please check:
    echo   1. requirements.txt exists and is valid
    echo   2. You have internet connection
    echo   3. No conflicting packages
    echo.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo    Dependencies Updated Successfully!
echo ===============================================
echo.
echo You can now start GiljoAI MCP services:
echo   - start_giljo.bat (all services)
echo   - start_backend.bat (backend only)
echo   - start_frontend.bat (frontend only)
echo.
pause
