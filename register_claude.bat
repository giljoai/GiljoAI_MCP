@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM GiljoAI MCP - Claude Registration Script
REM Registers the MCP stdio adapter with Claude Code
REM The adapter bridges Claude's stdio to the HTTP server
REM ============================================================

echo ============================================================
echo   GiljoAI MCP - Claude Registration (HTTP Bridge)
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

echo ============================================================
echo IMPORTANT: Architecture Update
echo ============================================================
echo.
echo GiljoAI MCP now uses a unified HTTP server architecture:
echo   - The main server runs on port 8000 (HTTP/REST/WebSocket)
echo   - Claude connects via a stdio adapter
echo   - This enables multi-user support and persistence
echo.
echo Make sure the server is running before using with Claude:
echo   Run: start_giljo.bat
echo.

echo Registering GiljoAI MCP adapter with Claude...
echo.

REM Register the MCP adapter (not the server directly)
REM The adapter translates stdio to HTTP calls to localhost:7272
claude mcp add giljo-mcp "%SCRIPT_DIR%\venv\Scripts\python.exe -m giljo_mcp.mcp_adapter" --scope user

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo SUCCESS! GiljoAI MCP adapter has been registered!
    echo ============================================================
    echo.
    echo How it works:
    echo   1. Start the server: run start_giljo.bat
    echo   2. The server runs persistently on port 8000
    echo   3. Claude connects through the stdio adapter
    echo   4. Multiple users can connect simultaneously
    echo.
    echo Next steps:
    echo   1. Start the server (if not running): start_giljo.bat
    echo   2. Close Claude if it's running
    echo   3. Restart Claude
    echo   4. The MCP tools will be available in Claude
    echo.
    echo Benefits of the new architecture:
    echo   - Multiple concurrent connections supported
    echo   - Server persists between Claude sessions
    echo   - Can be accessed over network (if configured)
    echo   - Supports team collaboration
    echo.
    echo You can verify the registration by running:
    echo   claude mcp list
    echo.
) else (
    echo.
    echo [ERROR] Registration failed!
    echo.
    echo You can try registering manually:
    echo   claude mcp add giljo-mcp "%SCRIPT_DIR%\venv\Scripts\python.exe -m giljo_mcp.mcp_adapter" --scope user
    echo.
    echo Make sure:
    echo   1. The virtual environment exists
    echo   2. The mcp_adapter.py file is in src\giljo_mcp\
    echo   3. Claude CLI is properly installed
    echo.
    pause
    exit /b 1
)

pause