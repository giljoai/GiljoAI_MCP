@echo off
REM ============================================================
REM Launch Control Panel using isolated devtools environment
REM Auto-creates venv_devtools if missing (self-bootstrapping)
REM Validates venv integrity via pyvenv.cfg before use
REM ============================================================

cd /d "%~dp0.."

REM ── Check isolated devtools venv (preferred) ────────────────
if exist "dev_tools\venv_devtools\pyvenv.cfg" (
    if exist "dev_tools\venv_devtools\Scripts\python.exe" (
        echo Starting GiljoAI MCP Developer Control Panel...
        echo Using isolated dev_tools venv
        echo.
        "dev_tools\venv_devtools\Scripts\python.exe" "dev_tools\control_panel.py" %*
        goto :done
    )
)

REM ── venv_devtools missing or corrupted -- auto-bootstrap ────
echo.
echo  Developer Control Panel - Auto Setup
echo  =====================================
echo  Isolated venv_devtools not found. Creating it now...
echo.

REM Find a working system Python
set "SYS_PYTHON="

REM Try py launcher first (most reliable on Windows)
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "SYS_PYTHON=py -3"
    goto :found_python
)

REM Try python on PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "SYS_PYTHON=python"
    goto :found_python
)

REM Try python3 on PATH
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set "SYS_PYTHON=python3"
    goto :found_python
)

echo  [FAIL] No system Python found. Install Python 3.10+ from python.org
echo         then re-run this launcher.
pause
exit /b 1

:found_python
echo  [OK] Found system Python: %SYS_PYTHON%

REM Clean up corrupted venv_devtools if it exists without pyvenv.cfg
if exist "dev_tools\venv_devtools" (
    echo  [..] Removing corrupted venv_devtools...
    rmdir /s /q "dev_tools\venv_devtools" >nul 2>&1
)

REM Create the venv
echo  [..] Creating dev_tools\venv_devtools...
%SYS_PYTHON% -m venv "dev_tools\venv_devtools"
if %errorlevel% neq 0 (
    echo  [FAIL] Failed to create virtual environment.
    echo         Try: %SYS_PYTHON% -m venv dev_tools\venv_devtools
    pause
    exit /b 1
)
echo  [OK] Virtual environment created

REM Install dependencies
echo  [..] Installing dependencies (psutil, psycopg2-binary, pyyaml)...
"dev_tools\venv_devtools\Scripts\pip.exe" install --upgrade pip -q >nul 2>&1
if exist "dev_tools\requirements.txt" (
    "dev_tools\venv_devtools\Scripts\pip.exe" install -r "dev_tools\requirements.txt" -q
) else (
    "dev_tools\venv_devtools\Scripts\pip.exe" install psutil psycopg2-binary pyyaml -q
)
if %errorlevel% neq 0 (
    echo  [FAIL] Failed to install dependencies.
    pause
    exit /b 1
)
echo  [OK] Dependencies installed
echo.
echo  Setup complete. Launching control panel...
echo.

"dev_tools\venv_devtools\Scripts\python.exe" "dev_tools\control_panel.py" %*
goto :done

:done
if %errorlevel% neq 0 (
    echo.
    echo Control panel exited with error code: %errorlevel%
    pause
)
