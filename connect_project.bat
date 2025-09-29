@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM GiljoAI MCP - Project Connection Script
REM Run this in your development project folder to connect
REM to the GiljoAI MCP orchestration server
REM ============================================================

echo ============================================================
echo   GiljoAI MCP Project Connector
echo ============================================================
echo.
echo This script will configure your project to use GiljoAI MCP
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check if the connect script exists
if not exist "%SCRIPT_DIR%\connect_project.py" (
    echo [ERROR] connect_project.py not found!
    echo Please ensure the GiljoAI MCP package is properly installed.
    pause
    exit /b 1
)

REM Run the Python connection script
python "%SCRIPT_DIR%\connect_project.py"

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo Project connection configured successfully!
    echo ============================================================
) else (
    echo.
    echo [ERROR] Connection setup failed!
    pause
    exit /b 1
)

pause