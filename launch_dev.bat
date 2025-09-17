@echo off
REM GiljoAI MCP Development Launcher
REM Starts the development control panel and opens the dashboard in browser

echo.
echo ========================================
echo  GiljoAI MCP Development Environment
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask not found. Installing required packages...
    pip install flask psutil
    if errorlevel 1 (
        echo ERROR: Failed to install Flask
        pause
        exit /b 1
    )
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

echo Starting Development Control Panel...
echo.
echo Dashboard will be available at: http://localhost:5500
echo.
echo Services available for management:
echo - MCP Server (Port 6001)
echo - REST API + WebSocket Server (Port 6002)
echo - Frontend/Dashboard (Port 6000)
echo - PostgreSQL Database (Port 5432)
echo.
echo Features:
echo - Start/Stop/Restart all services
echo - Clear Python cache (fixes 60%% success rate issue)
echo - Real-time log viewing
echo - Service status monitoring
echo.

REM Start the control panel
echo Starting control panel server...
python dev_control_panel.py

REM If we get here, the server stopped
echo.
echo Control panel stopped.
pause