@echo off
echo ============================================================
echo   Redis Uninstaller for GiljoAI MCP
echo ============================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This script needs to run as Administrator to remove Redis.
    echo Please right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo Stopping Redis service if running...
sc stop Redis 2>nul
timeout /t 2 >nul

echo Removing Redis service if exists...
sc delete Redis 2>nul

echo Killing any remaining Redis processes...
taskkill /F /IM redis-server.exe 2>nul
timeout /t 2 >nul

echo Removing Redis directory...
if exist "C:\Redis" (
    echo Found Redis at C:\Redis - removing...
    rmdir /S /Q "C:\Redis"
    echo Redis directory removed.
) else (
    echo Redis directory not found.
)

echo.
echo ============================================================
echo   Redis has been uninstalled successfully!
echo ============================================================
echo.
pause