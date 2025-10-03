@echo off
REM Stop GiljoAI MCP Frontend Dashboard

echo ===============================================
echo    Stopping GiljoAI MCP Frontend...
echo ===============================================
echo.

REM Kill Node.js processes running the frontend
echo Stopping frontend dashboard...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *npm*" 2>nul
if errorlevel 1 (
    echo No frontend server found running.
) else (
    echo Frontend dashboard stopped.
)

echo.
echo Done.
timeout /t 2 >nul
