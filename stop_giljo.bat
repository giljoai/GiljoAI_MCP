@echo off
REM GiljoAI MCP Service Stopper (Windows)
REM Stops all GiljoAI services on ports 7272, 7273, and 7274

echo ===============================================
echo    GiljoAI MCP - Stopping All Services
echo ===============================================
echo.

REM Set working directory to script location
cd /d "%~dp0"

REM Kill port 7272 (Backend API)
echo [1/3] Stopping Backend API on port 7272...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7272" ^| findstr "LISTENING"') do (
    echo   Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   Failed to kill PID %%a
    ) else (
        echo   Stopped (PID: %%a^)
    )
)

REM Kill port 7273 (WebSocket)
echo [2/3] Stopping WebSocket on port 7273...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7273" ^| findstr "LISTENING"') do (
    echo   Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   Failed to kill PID %%a
    ) else (
        echo   Stopped (PID: %%a^)
    )
)

REM Kill port 7274 (Frontend)
echo [3/3] Stopping Frontend on port 7274...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7274" ^| findstr "LISTENING"') do (
    echo   Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   Failed to kill PID %%a
    ) else (
        echo   Stopped (PID: %%a^)
    )
)

REM Fallback: Kill any python.exe running run_api.py
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*run_api.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

REM Fallback: Kill only frontend node processes (not Claude Code!)
REM This is already handled by the port-based killing above, so we skip the blanket node kill

echo.
echo ===============================================
echo    All services stopped
echo ===============================================
echo.
pause
