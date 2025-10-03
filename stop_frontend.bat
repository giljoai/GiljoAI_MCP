@echo off
REM Stop GiljoAI MCP Frontend Dashboard

echo ===============================================
echo    Stopping GiljoAI MCP Frontend...
echo ===============================================
echo.

REM Find and kill process using port 7274
echo Stopping frontend dashboard on port 7274...

REM Get PID of process using port 7274
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7274" ^| findstr "LISTENING"') do (
    echo Killing process %%a on port 7274...
    powershell -Command "Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue"
    if errorlevel 1 (
        echo Failed to kill process %%a
    ) else (
        echo Frontend dashboard stopped (PID: %%a^)
    )
)

REM Also try to kill any node.exe running npm as fallback
powershell -Command "Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue"

echo.
echo Done.
timeout /t 2 >nul
