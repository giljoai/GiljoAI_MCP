@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM GiljoAI MCP - Claude Registration Script
REM Registers the MCP server with Claude Code
REM ============================================================

echo ============================================================
echo   GiljoAI MCP - Claude Registration
echo ============================================================
echo.

REM Check if Claude CLI is available
where claude >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Claude CLI not found!
    echo.
    echo Please install Claude Code first:
    echo   https://claude.ai/download
    echo.
    echo After installing Claude, run this script again.
    pause
    exit /b 1
)

echo [OK] Claude CLI found
echo.

REM Get the script directory
set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Check if venv exists
if not exist "%SCRIPT_DIR%\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run the installation first.
    pause
    exit /b 1
)

echo Registering GiljoAI MCP with Claude...
echo.

REM Register the MCP server with Claude
REM Using the full path to the Python executable in venv
claude mcp add giljo-mcp "%SCRIPT_DIR%\venv\Scripts\python.exe -m giljo_mcp" --scope user

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo SUCCESS! GiljoAI MCP has been registered with Claude!
    echo ============================================================
    echo.
    echo Next steps:
    echo   1. Close Claude if it's running
    echo   2. Restart Claude
    echo   3. The MCP server will be available automatically
    echo.
    echo You can verify the registration by running:
    echo   claude mcp list
    echo.
) else (
    echo.
    echo [ERROR] Registration failed!
    echo.
    echo You can try registering manually:
    echo   claude mcp add giljo-mcp "%SCRIPT_DIR%\venv\Scripts\python.exe -m giljo_mcp" --scope user
    echo.
    pause
    exit /b 1
)

pause