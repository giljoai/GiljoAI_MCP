@echo off
setlocal EnableDelayedExpansion

REM Enable ANSI color codes in Windows 10+
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM GiljoAI Color Palette
set "ESC="
set "YELLOW=%ESC%[38;2;255;195;0m"
set "GREEN=%ESC%[38;2;103;189;109m"
set "PINK=%ESC%[38;2;198;41;140m"
set "GRAY=%ESC%[38;2;225;225;225m"
set "RESET=%ESC%[0m"

REM ============================================================
REM GiljoAI MCP - Direct CLI Installer Launcher
REM ============================================================
REM This script launches the CLI installer directly
REM Use this if you already have Python installed and want CLI mode
REM
REM For full installation with Python check, use: quickstart.bat
REM ============================================================

title GiljoAI MCP CLI Installer

echo %YELLOW%============================================================%RESET%
echo %YELLOW%  GiljoAI MCP - CLI Installer%RESET%
echo %YELLOW%============================================================%RESET%
echo.

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %PINK%[X] Python not found!%RESET%
    echo.
    echo Please install Python 3.10+ first, or use quickstart.bat
    echo for automatic Python installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %GREEN%[OK] Found Python !PYTHON_VERSION!%RESET%
echo.

REM Check if setup_interactive.py exists
if not exist "setup_interactive.py" (
    echo %PINK%[X] setup_interactive.py not found in current directory%RESET%
    echo %GRAY%    Make sure you're in the GiljoAI MCP directory%RESET%
    echo.
    pause
    exit /b 1
)

echo %GRAY%Checking for test dependencies...%RESET%

REM Check if psycopg2 is installed (optional for PostgreSQL testing)
python -c "import psycopg2" >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%[!] PostgreSQL test dependencies not installed%RESET%
    echo.
    echo For PostgreSQL connection testing during setup, we recommend
    echo installing psycopg2-binary now (takes ~5 seconds).
    echo.
    choice /C YN /N /M "Install test dependencies now? [Y/n]: "
    if !errorlevel! equ 1 (
        echo.
        echo %GRAY%Installing psycopg2-binary...%RESET%
        python -m pip install psycopg2-binary
        if !errorlevel! equ 0 (
            echo %GREEN%[OK] Test dependencies installed%RESET%
        ) else (
            echo %YELLOW%[!] Installation failed - continuing anyway%RESET%
        )
    ) else (
        echo %GRAY%Skipped - you can test connections after full installation%RESET%
    )
    echo.
)

echo %GRAY%Launching CLI installer...%RESET%
echo.
echo %YELLOW%============================================================%RESET%
echo.

REM Launch CLI installer
python setup_interactive.py

if %errorlevel% neq 0 (
    echo.
    echo %PINK%[X] CLI installer encountered an error%RESET%
    echo %GRAY%    Please check the error messages above%RESET%
    pause
    exit /b %errorlevel%
)

echo.
echo %GREEN%============================================================%RESET%
echo %GREEN%  Setup completed!%RESET%
echo %GREEN%============================================================%RESET%
echo.
pause
