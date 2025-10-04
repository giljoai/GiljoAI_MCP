@echo off
setlocal EnableDelayedExpansion

echo ======================================
echo GiljoAI MCP DEBUG LAUNCHER
echo ======================================
echo.

:: Show current directory
echo [DEBUG] Current directory: %CD%
echo.

:: Check Python version
echo [DEBUG] Checking Python installation...
python --version 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo.

:: Check if venv exists
echo [DEBUG] Checking virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found
) else (
    echo [MISSING] Virtual environment not found - will create
)
echo.

:: Create or activate venv
if not exist "venv\Scripts\activate.bat" (
    echo [ACTION] Creating virtual environment...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
)

echo [ACTION] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

:: Check giljo-mcp installation
echo [DEBUG] Checking giljo-mcp package installation...
pip show giljo-mcp 2>&1
if !errorlevel! neq 0 (
    echo [MISSING] giljo-mcp not installed
    echo [ACTION] Installing giljo-mcp in development mode...
    pip install -e . --no-deps
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install giljo-mcp
        pause
        exit /b 1
    )
    echo [ACTION] Installing requirements...
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install requirements
        pause
        exit /b 1
    )
) else (
    echo [OK] giljo-mcp is installed
)
echo.

:: Check if modules can be imported
echo [DEBUG] Testing Python imports...
python -c "import giljo_mcp; print('[OK] giljo_mcp module found at:', giljo_mcp.__file__)" 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Cannot import giljo_mcp module
    echo [DEBUG] Python path:
    python -c "import sys; print('\n'.join(sys.path))"
    echo.
    echo [DEBUG] Installed packages:
    pip list | findstr giljo
    pause
    exit /b 1
)
echo.

:: Check frontend
echo [DEBUG] Checking frontend...
if exist "frontend\package.json" (
    echo [OK] Frontend package.json found
    cd frontend
    if exist "node_modules" (
        echo [OK] node_modules exists
    ) else (
        echo [MISSING] node_modules not found
        echo [ACTION] Installing frontend dependencies...
        call npm install
        if !errorlevel! neq 0 (
            echo [ERROR] npm install failed - is Node.js installed?
            cd ..
            pause
            exit /b 1
        )
    )
    cd ..
) else (
    echo [WARNING] No frontend found
)
echo.

:: Start services with full output
echo ======================================
echo STARTING SERVICES WITH VERBOSE OUTPUT
echo ======================================
echo.

echo [START] MCP Server on port 6001...
start "GiljoMCP Server - DEBUG" cmd /k "call venv\Scripts\activate && echo [DEBUG] Starting MCP server... && python -m giljo_mcp.server"

timeout /t 3 /nobreak >nul

echo [START] API Server on port 6002...
start "GiljoMCP API - DEBUG" cmd /k "call venv\Scripts\activate && echo [DEBUG] Starting API server... && python -m giljo_mcp.api_server"

timeout /t 3 /nobreak >nul

if exist "frontend\package.json" (
    echo [START] Frontend on port 6000...
    cd frontend
    start "GiljoMCP Frontend - DEBUG" cmd /k "echo [DEBUG] Starting frontend dev server... && npm run dev"
    cd ..
)

echo.
echo ======================================
echo DEBUG LAUNCHER COMPLETE
echo ======================================
echo.
echo Services should be running in separate windows.
echo Check each window for errors.
echo.
echo Dashboard: http://localhost:7274
echo API: http://localhost:7272
echo MCP Server: stdio (via API)
echo.
pause