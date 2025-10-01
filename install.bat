@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM GiljoAI MCP Installation Launcher for Windows
REM ============================================================
REM This is the PRIMARY entry point for installing GiljoAI MCP
REM
REM What this script does:
REM   1. Check for Python 3.10+ (ONLY dependency required)
REM   2. Install Python if missing (interactive)
REM   3. Launch bootstrap.py for full installation wizard
REM
REM You can also run these directly if Python is installed:
REM   - python bootstrap.py    (full installer, auto-detects GUI/CLI)
REM   - python setup_gui.py    (direct GUI installer)
REM   - python setup_cli.py    (direct CLI installer)
REM ============================================================

title GiljoAI MCP Quick Start

echo ============================================================
echo   GiljoAI MCP Orchestrator - Intelligent Quick Start
echo ============================================================
echo.

REM Check if we're running with admin privileges (needed for some installs)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [^^!] Note: Not running as Administrator
    echo     Some installation options may require admin rights
    echo.
)

REM ============================================================
REM STEP 1: Check for Python
REM ============================================================
echo [1/4] Checking for Python installation...

REM Try python command first
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Found Python !PYTHON_VERSION!
    
    REM Check if it's 3.10 or higher
    for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
        if %%a geq 3 (
            if %%a gtr 3 (
                goto :python_ok
            ) else if %%b geq 10 (
                goto :python_ok
            )
        )
    )
    echo [^^!] Python version too old. Need 3.10+, found !PYTHON_VERSION!
    goto :install_python
)

REM Try python3 command
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Found Python !PYTHON_VERSION!
    set PYTHON_CMD=python3
    goto :check_version
)

REM Try py launcher
py --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Found Python !PYTHON_VERSION! via py launcher
    set PYTHON_CMD=py
    goto :check_version
)

REM No Python found
echo [X] Python not found on this system
goto :install_python

:check_version
REM Verify Python version is 3.10+
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    if %%a geq 3 (
        if %%a gtr 3 (
            goto :python_ok
        ) else if %%b geq 10 (
            goto :python_ok
        )
    )
)
echo [^^!] Python version too old. Need 3.10+, found !PYTHON_VERSION!

REM ============================================================
REM STEP 2: Install Python if needed
REM ============================================================
:install_python
echo.
echo Python 3.10+ is required but not found or too old.
echo.
echo Installation options:
echo   1. Automatically download and install Python 3.12 (recommended)
echo   2. Use winget to install Python
echo   3. Open Python download page in browser
echo   4. Exit and install manually
echo.
choice /C 1234 /N /M "Select option [1-4]: "

if %errorlevel% equ 1 goto :auto_install
if %errorlevel% equ 2 goto :winget_install
if %errorlevel% equ 3 goto :browser_install
if %errorlevel% equ 4 goto :exit_manual

:auto_install
echo.
echo [2/4] Downloading Python installer...

REM Determine architecture
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    set PYTHON_INSTALLER=python_installer_amd64.exe
) else (
    set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0.exe
    set PYTHON_INSTALLER=python_installer.exe
)

REM Download using PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\%PYTHON_INSTALLER%'}" >nul 2>&1

if exist "%TEMP%\%PYTHON_INSTALLER%" (
    echo [OK] Download complete
    echo.
    echo [3/4] Installing Python...
    echo      Please follow the installer prompts
    echo      IMPORTANT: Check "Add Python to PATH"^^!
    echo.

    REM Run installer with recommended options
    "%TEMP%\%PYTHON_INSTALLER%" /passive PrependPath=1 Include_test=0 Include_pip=1 Include_launcher=1

    if %errorlevel% equ 0 (
        echo [OK] Python installed successfully
        echo.
        echo Please close and reopen this window for PATH changes to take effect
        pause
        exit /b 0
    ) else (
        echo [X] Installation failed. Please install manually.
        start https://www.python.org/downloads/
        pause
        exit /b 1
    )
) else (
    echo [X] Download failed
    goto :browser_install
)

:winget_install
echo.
echo [2/4] Installing Python via winget...

REM Check if winget is available
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] winget not found. Trying another method...
    goto :browser_install
)

winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements

if %errorlevel% equ 0 (
    echo [OK] Python installed successfully
    echo.
    echo Please close and reopen this window for PATH changes to take effect
    pause
    exit /b 0
) else (
    echo [X] winget installation failed
    goto :browser_install
)

:browser_install
echo.
echo [2/4] Opening Python download page...
echo.
echo Please:
echo   1. Download Python 3.12 or later
echo   2. Run the installer
echo   3. CHECK "Add Python to PATH" during installation
echo   4. After installation, run this script again
echo.
start https://www.python.org/downloads/
pause
exit /b 0

:exit_manual
echo.
echo Please install Python 3.10 or newer from:
echo https://www.python.org/downloads/
echo.
echo Recommended: Python 3.11 or Python 3.12 (stable and well-tested)
echo.
echo IMPORTANT: Check "Add Python to PATH" during installation!
pause
exit /b 1

REM ============================================================
REM STEP 3: Python is OK, proceed with bootstrap
REM ============================================================
:python_ok
echo.
echo [2/3] Checking Python installation...

REM Set Python command if not set
if not defined PYTHON_CMD set PYTHON_CMD=python

REM Check for pip (essential for Python packages)
%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [^^!] pip not found, installing...
    %PYTHON_CMD% -m ensurepip --default-pip
    if %errorlevel% neq 0 (
        echo [X] Failed to install pip
        echo     Please reinstall Python with pip included
        pause
        exit /b 1
    )
)
echo [OK] Python and pip are ready

REM ============================================================
REM STEP 4: Launch bootstrap.py
REM ============================================================
echo.
echo [3/3] Checking for bootstrap.py...

if not exist "bootstrap.py" (
    echo [X] bootstrap.py not found in current directory
    echo     Please make sure you're in the GiljoAI MCP directory
    pause
    exit /b 1
)

echo [OK] bootstrap.py found
echo.
echo Launching GiljoAI MCP installer...
echo.
echo ============================================================
echo.
echo Starting GiljoAI MCP installer...
echo.

REM Launch bootstrap with Python
%PYTHON_CMD% bootstrap.py

if %errorlevel% neq 0 (
    echo.
    echo [X] Installation encountered an error
    echo     Please check the error messages above
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo   Installation completed successfully^^!
echo ============================================================
echo.
echo To start GiljoAI MCP, use the launcher created on your desktop
echo or run: python -m src.giljo_mcp.mcp_server
echo.
pause