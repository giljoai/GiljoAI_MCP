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
    taskkill /F /PID %%a 2>nul
    if errorlevel 1 (
        echo Failed to kill process %%a
    ) else (
        echo Backend server stopped (PID: %%a^)
    )
)

REM Also try to kill any python.exe running run_api.py as fallback
taskkill /F /IM python.exe /FI "COMMANDLINE eq *run_api.py*" 2>nul

echo.
echo ===============================================
echo    Backend stopped
echo ===============================================
echo.
pause
