@echo off
REM ============================================================
REM Launch Control Panel using System Python
REM ============================================================

cd /d "%~dp0"

REM Check if Python is available in system PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python is not installed or not in system PATH
    echo Please install Python or add it to your PATH
    echo.
    pause
    exit /b 1
)

REM Launch control panel using system Python
echo Starting GiljoAI MCP Developer Control Panel...
echo Using system Python from PATH
echo.

python "%~dp0control_panel.py"

if %errorlevel% neq 0 (
    echo.
    echo Control panel exited with error code: %errorlevel%
    pause
)
