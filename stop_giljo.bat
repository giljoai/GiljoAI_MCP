@echo off
REM GiljoAI MCP Service Stopper (Windows)
REM Stops backend only (start_giljo.bat now starts backend only)

echo ===============================================
echo    GiljoAI MCP - Stopping Backend
echo ===============================================
echo.

REM Set working directory to script location
cd /d "%~dp0"

echo Stopping backend API server on port 7272...
echo.

REM Find and kill process using port 7272
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7272" ^| findstr "LISTENING"') do (
    echo Killing process %%a on port 7272...
    powershell -Command "Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue"
    if errorlevel 1 (
        echo Failed to kill process %%a
    ) else (
        echo Backend server stopped (PID: %%a^)
    )
)

REM Also try to kill any python.exe running run_api.py as fallback
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*run_api.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue"

echo.
echo ===============================================
echo    Backend stopped
echo ===============================================
echo.
pause
