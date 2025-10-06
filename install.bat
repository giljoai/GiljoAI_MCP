@echo off
REM ============================================================
REM GiljoAI MCP Installation Script for Windows
REM Version 2.0 - CLI-Only Installer
REM ============================================================

echo.
echo ============================================================
echo     GiljoAI MCP Installation System v2.0
echo     Professional CLI Installer
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "installer\cli\install.py" (
    echo ERROR: Installation files not found!
    echo Please run this script from the GiljoAI MCP root directory
    pause
    exit /b 1
)

REM Check for PostgreSQL
echo Checking PostgreSQL installation...
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: PostgreSQL command-line tools not found in PATH
    echo The installer will check for PostgreSQL during setup
    echo.
)

REM Launch the installer
echo Starting GiljoAI MCP Installer...
echo.
echo This will guide you through the installation process.
echo You can choose between localhost (development) or server (production) mode.
echo.
python installer\cli\install.py

REM Check if installation was successful
if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo Installation completed successfully!
    echo.
    echo To start GiljoAI MCP, run:
    echo   launchers\start_giljo.bat
    echo.
    echo Or use the Python launcher:
    echo   python launchers\start_giljo.py
    echo ============================================================
) else (
    echo.
    echo Installation encountered an error.
    echo Please check the error messages above.
    echo.
    echo Common issues:
    echo - PostgreSQL not installed or not running
    echo - Incorrect PostgreSQL password
    echo - Port 7272 already in use
    echo - Missing Python dependencies
)

pause