@echo off
REM ============================================================
REM Launch Control Panel using project virtual environment
REM ============================================================

cd /d "%~dp0.."

REM Try project venv first (has psycopg2 and other deps)
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
echo Warning: No project venv found. Using system Python (some features may be unavailable).
echo.
python "dev_tools\control_panel.py" %*

:done
if %errorlevel% neq 0 (
    echo.
    echo Control panel exited with error code: %errorlevel%
    pause
)
