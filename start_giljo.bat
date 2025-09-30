@echo off
setlocal EnableDelayedExpansion

echo Starting GiljoAI MCP Orchestrator Server...
echo ==========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please run install.bat to install Python
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

:: Check frontend dependencies (optional for development)
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
        echo Claude detected but GiljoAI MCP not registered.
        echo Would you like to register it now? (Y/N^)
        choice /C YN /T 5 /D N /M "Register with Claude"
        if !errorlevel! equ 1 (
            echo Registering with Claude...
            call register_claude.bat
        )
    )
)

echo.
echo Starting unified orchestration server...
echo ----------------------------------------

:: Try to read port from config if exists
set SERVER_PORT=7272
if exist config.yaml (
    for /f "tokens=2 delims=:" %%a in ('findstr /c:"port:" config.yaml 2^>nul') do (
        set SERVER_PORT=%%a
        :: Remove leading/trailing spaces
        for /f "tokens=* delims= " %%b in ("!SERVER_PORT!") do set SERVER_PORT=%%b
    )
)

:: Start the API server (which now includes all MCP functionality)
echo Starting API server on port !SERVER_PORT!...
echo This server handles:
echo   - REST API endpoints
echo   - MCP tool execution
echo   - WebSocket connections
echo   - Multi-user orchestration
echo.

:: Set environment variable for the port
set GILJO_PORT=!SERVER_PORT!

:: Start in a new window for visibility
start "GiljoAI Orchestrator" cmd /k "call venv\Scripts\activate && set GILJO_PORT=!SERVER_PORT! && cd api && python run_api.py"

:: Wait for API to be ready
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

:: Check if server is running
curl -s http://localhost:!SERVER_PORT!/health >nul 2>&1
if !errorlevel! neq 0 (
    echo Warning: Server may not have started properly
    echo Please check the server window for errors
) else (
    echo Server is running and healthy!
)

:: Optional: Start frontend for development
if exist "frontend\package.json" (
    echo.
    echo Would you like to start the frontend development server? (Y/N^)
    choice /C YN /T 5 /D N /M "Start frontend"
    if !errorlevel! equ 1 (
        echo Starting frontend on port 6000...
        cd frontend
        start "GiljoAI Frontend" cmd /k "npm run dev"
        cd ..

        :: Open browser to dashboard
        timeout /t 3 /nobreak >nul
        echo Opening dashboard in browser...
        start http://localhost:6000
    )
)

echo.
echo ==========================================
echo GiljoAI MCP Orchestrator is running!
echo ==========================================
echo.
echo Server URL: http://localhost:!SERVER_PORT!
echo.
echo Available endpoints:
echo   - API Documentation: http://localhost:!SERVER_PORT!/docs
echo   - Health Check: http://localhost:!SERVER_PORT!/health
echo   - MCP Tools: http://localhost:!SERVER_PORT!/mcp/tools
echo   - WebSocket: ws://localhost:!SERVER_PORT!/ws
echo.
if exist "frontend\package.json" (
    echo   - Frontend Dashboard: http://localhost:6000 (if started)
    echo.
)
echo This server supports:
echo   - Multiple concurrent connections
echo   - Network access (LAN/WAN if configured)
echo   - Persistent operation
echo   - Multi-project orchestration
echo.
echo To connect Claude, use the MCP adapter (register_claude.bat)
echo To stop the server, close the server window or use stop_giljo.bat
echo.

pause