@echo off
REM Stop GiljoAI MCP Backend Server

echo ===============================================
echo    Stopping GiljoAI MCP Backend...
echo ===============================================
echo.

REM Kill Python processes running the API
echo Stopping backend API server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *run_api.py*" 2>nul
if errorlevel 1 (
    echo No backend server found running.
) else (
    echo Backend server stopped.
)

echo.
echo Done.
timeout /t 2 >nul
