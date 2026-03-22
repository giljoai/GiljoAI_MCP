@echo off
REM ============================================================
REM Launch Control Panel using isolated devtools environment
REM Prefers venv_devtools (can delete main venv during resets)
REM Falls back to project venv, then system Python
REM ============================================================

cd /d "%~dp0.."

REM Prefer isolated devtools venv (recommended)
if exist "dev_tools\venv_devtools\Scripts\python.exe" (
    echo Starting GiljoAI MCP Developer Control Panel...
    echo Using isolated dev_tools venv
    echo.
    "dev_tools\venv_devtools\Scripts\python.exe" "dev_tools\control_panel.py" %*
    goto :done
)

REM Fallback to project venv
if exist "venv\Scripts\python.exe" (
    echo Starting GiljoAI MCP Developer Control Panel...
    echo Using project venv Python
    echo.
    "venv\Scripts\python.exe" "dev_tools\control_panel.py" %*
    goto :done
)

if exist ".venv\Scripts\python.exe" (
    echo Starting GiljoAI MCP Developer Control Panel...
    echo Using project .venv Python
    echo.
    ".venv\Scripts\python.exe" "dev_tools\control_panel.py" %*
    goto :done
)

REM Fallback to system Python
echo Warning: No venv found. Run: python dev_tools\setup_control_panel.py
echo Falling back to system Python (some features may be unavailable).
echo.
python "dev_tools\control_panel.py" %*

:done
if %errorlevel% neq 0 (
    echo.
    echo Control panel exited with error code: %errorlevel%
    pause
)
