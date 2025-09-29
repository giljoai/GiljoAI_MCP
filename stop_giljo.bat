@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM GiljoAI MCP - Stop Server Script
REM Gracefully shuts down the unified orchestration server
REM ============================================================

echo ============================================================
echo   GiljoAI MCP Server Shutdown
echo ============================================================
echo.
echo Stopping GiljoAI MCP Orchestration Server...

REM Try to read port from config if exists
set SERVER_PORT=7272
if exist config.yaml (
    for /f "tokens=2 delims=:" %%a in ('findstr /c:"port:" config.yaml 2^>nul') do (
        set SERVER_PORT=%%a
        REM Remove leading/trailing spaces
        for /f "tokens=* delims= " %%b in ("!SERVER_PORT!") do set SERVER_PORT=%%b
    )
)

REM Kill the main API server
echo Stopping API server on port !SERVER_PORT!...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :!SERVER_PORT!') do (
    taskkill /F /PID %%a 2>nul
    if !errorlevel! equ 0 (
        echo   [OK] Stopped orchestration server (PID: %%a)
    )
)

REM Also check legacy port 8000 if different
if NOT "!SERVER_PORT!"=="8000" (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
        taskkill /F /PID %%a 2>nul
        if !errorlevel! equ 0 (
            echo   [OK] Stopped legacy server on port 8000 (PID: %%a)
        )
    )
)

REM Kill Python processes with our window titles
taskkill /F /FI "WINDOWTITLE eq GiljoAI Orchestrator" 2>nul
if !errorlevel! equ 0 echo   [OK] Stopped orchestrator window

REM Kill any frontend dev server (optional)
if exist "frontend\package.json" (
    echo Checking for frontend dev server...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6000') do (
        taskkill /F /PID %%a 2>nul
        if !errorlevel! equ 0 echo   [OK] Stopped frontend dev server
    )
    taskkill /F /FI "WINDOWTITLE eq GiljoAI Frontend" 2>nul
)

REM Clean up any orphaned Python processes from our venv
echo Cleaning up any remaining processes...
wmic process where "CommandLine like '%%giljo%%' and name='python.exe'" delete 2>nul

REM Remove lock file if it exists
set "LOCK_FILE=%USERPROFILE%\.giljo_mcp\locks\giljo_mcp.lock"
if exist "%LOCK_FILE%" (
    del "%LOCK_FILE%" 2>nul
    if !errorlevel! equ 0 echo   [OK] Removed lock file
)

echo.
echo ============================================================
echo   Server shutdown complete!
echo ============================================================
echo.
echo The GiljoAI MCP Orchestration Server has been stopped.
echo To restart, run: start_giljo.bat
echo.

pause