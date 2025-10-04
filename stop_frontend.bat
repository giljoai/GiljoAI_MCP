@echo off
REM Stop GiljoAI MCP Frontend Dashboard

echo ===============================================
echo    Stopping GiljoAI MCP Frontend...
echo ===============================================
echo.

REM Kill port 7274 (Frontend)
echo Stopping frontend dashboard on port 7274...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7274" ^| findstr "LISTENING"') do (
    echo   Killing process %%a...
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo   Failed to kill PID %%a
    ) else (
        echo   Frontend stopped (PID: %%a^)
    )
)

REM Fallback: Kill only frontend node processes (not Claude Code!)
REM This is already handled by the port-based killing above, so we skip the blanket node kill

echo.
echo Done.
timeout /t 2 >nul
