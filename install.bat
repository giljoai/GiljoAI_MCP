@echo off
REM ============================================================
REM GiljoAI MCP Minimal Installation Script for Windows
REM Version 3.0 - Minimal Setup (Configuration via Web Wizard)
REM ============================================================

echo.
echo ============================================================
echo     GiljoAI MCP Minimal Installer v3.0
echo     Simplified Setup - Configuration via Web Wizard
echo ============================================================
echo.
echo Press any key to begin installation...
pause >nul
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from https://www.python.org
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "installer\cli\minimal_installer.py" (
    echo ERROR: Installation files not found!
    echo Please run this script from the GiljoAI MCP root directory
    pause
    exit /b 1
)

REM Launch the minimal installer
echo Starting GiljoAI MCP Minimal Installer...
echo.
echo This installer will:
echo   1. Detect Python and PostgreSQL
echo   2. Create virtual environment
echo   3. Install Python dependencies
echo   4. Install frontend dependencies (npm)
echo   5. Create minimal configuration
echo   6. Start backend service
echo   7. Start frontend service
echo   8. Open browser to setup wizard
echo.
echo All configuration is handled via the web wizard.
echo.
python installer\cli\minimal_installer.py

REM Check if installation was successful
if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo Minimal installation completed!
    echo.
    echo Next step: Complete setup wizard in your browser
    echo URL: http://localhost:7274/setup
    echo ============================================================
) else (
    echo.
    echo Installation encountered an error.
    echo Please check the error messages above.
    echo.
    echo Common issues:
    echo - Python 3.11+ not installed
    echo - PostgreSQL 18 not installed or not running
    echo - Missing installation files
)

pause