@echo off
REM GiljoAI MCP Frontend Launcher
REM Starts only the frontend dashboard with colored output

REM Set working directory to script location
cd /d "%~dp0"

REM Change to frontend directory
cd frontend

REM Check if Node.js is installed
where node >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js not found
    echo Please install Node.js from nodejs.org
    pause
    exit /b 1
)

REM Check if npm dependencies are installed
if not exist "node_modules\" (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Run the colored frontend launcher
node run_frontend.js

if errorlevel 1 (
    echo.
    echo Frontend launch failed. Check the error messages above.
    pause
)
