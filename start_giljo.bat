@echo off
setlocal EnableDelayedExpansion

echo Starting GiljoAI MCP Orchestrator...
echo =====================================

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please run quickstart.bat to install Python
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing giljo-mcp package in development mode...
    pip install -e . --no-deps
    echo Installing requirements...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
    :: Check if giljo-mcp is installed
    pip show giljo-mcp >nul 2>&1
    if !errorlevel! neq 0 (
        echo Installing giljo-mcp package in development mode...
        pip install -e . --no-deps
    )
)

:: Check frontend dependencies
if exist "frontend\package.json" (
    cd frontend
    if not exist "node_modules" (
        echo Installing frontend dependencies...
        call npm install
    )
    cd ..
)

:: Check Claude registration (optional)
where claude >nul 2>&1
if !errorlevel! equ 0 (
    :: Claude CLI exists, check if giljo-mcp is registered
    claude mcp list 2>nul | findstr /i "giljo-mcp" >nul
    if !errorlevel! neq 0 (
        echo.
        echo Claude detected but GiljoAI MCP not registered.
        echo Would you like to register it now? (Y/N^)
        choice /C YN /T 5 /D N /M "Register with Claude"
        if !errorlevel! equ 1 (
            echo Registering with Claude...
            call register_claude.bat
        )
    )
)

:: Start the MCP server in a new window for visibility
echo Starting MCP server on port 6001...
start "GiljoMCP Server" cmd /k "call venv\Scripts\activate && python -m giljo_mcp.server"

:: Wait a moment for server to start
timeout /t 3 /nobreak >nul

:: Start the API server in a new window for visibility
echo Starting API server on port 8000...
start "GiljoMCP API" cmd /k "call venv\Scripts\activate && cd api && python run_api.py"

:: Wait for API to be ready
timeout /t 3 /nobreak >nul

:: Start the frontend development server in a new window
if exist "frontend\package.json" (
    echo Starting frontend on port 6000...
    cd frontend
    start "GiljoMCP Frontend" cmd /k "npm run dev"
    cd ..
)

:: Open browser to dashboard
timeout /t 3 /nobreak >nul
echo Opening dashboard in browser...
start http://localhost:6000

echo.
echo GiljoAI MCP Orchestrator is running!
echo =====================================
echo Dashboard: http://localhost:6000
echo API: http://localhost:8000
echo MCP Server: localhost:6001
echo.
echo Press Ctrl+C to stop all services
echo.

:: Keep the script running
:loop
timeout /t 60 /nobreak >nul
goto loop
