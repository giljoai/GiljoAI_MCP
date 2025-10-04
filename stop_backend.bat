@echo off
REM Stop GiljoAI MCP Backend Server

echo ===============================================
echo    Stopping GiljoAI MCP Backend...
echo ===============================================
echo.

REM Kill port 7272 (Backend API)
echo Stopping backend API server on port 7272...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7272" ^| findstr "LISTENING"') do (
    echo   Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   Failed to kill PID %%a
    ) else (
        echo   Backend stopped (PID: %%a^)
    )
)

REM Fallback: Kill any python.exe running run_api.py
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*run_api.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo.
echo Done.
timeout /t 2 >nul
