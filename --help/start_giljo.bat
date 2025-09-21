@echo off
setlocal

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
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Start the MCP server in the background
echo Starting MCP server on port 6001...
start /b python -m giljo_mcp.server

:: Wait a moment for server to start
timeout /t 2 /nobreak >nul

:: Start the API server
echo Starting API server on port 6002...
start /b python -m giljo_mcp.api_server

:: Wait for API to be ready
timeout /t 2 /nobreak >nul

:: Start the frontend development server
if exist "frontend\package.json" (
    echo Starting frontend on port 6000...
    cd frontend
    start /b npm run dev
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
echo API: http://localhost:6002
echo MCP Server: localhost:6001
echo.
echo Press Ctrl+C to stop all services
echo.

:: Keep the script running
:loop
timeout /t 60 /nobreak >nul
goto loop
