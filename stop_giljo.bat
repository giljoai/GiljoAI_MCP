@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM GiljoAI MCP - Stop Server Script
REM Gracefully shuts down the MCP orchestration server
REM ============================================================

echo ============================================================
echo   GiljoAI MCP Server Shutdown
echo ============================================================
echo.
echo Stopping GiljoAI MCP Server components...

REM Kill Python processes running our services
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *giljo_mcp*" 2>nul

REM Kill processes by port (using port 8000 for the unified server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /F /PID %%a 2>nul
    if !errorlevel! equ 0 echo   [OK] Stopped process on port 8000
)

REM Also check legacy ports if configured differently
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6000') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6001') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6002') do taskkill /F /PID %%a 2>nul

REM Kill any frontend dev server
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *frontend*" 2>nul

echo.
echo ============================================================
echo   Server shutdown complete!
echo ============================================================
echo.
pause
