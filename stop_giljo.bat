@echo off
REM GiljoAI MCP Service Stopper (Windows)

echo ===============================================
echo    GiljoAI MCP - Stopping Services
echo ===============================================
echo.

REM Set working directory to script location
cd /d "%~dp0"

echo Stopping all GiljoAI MCP services...
echo.

REM Kill Python processes running GiljoAI
taskkill /F /FI "WINDOWTITLE eq GiljoAI*" 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *start_giljo*" 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *giljo_mcp*" 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "COMMANDLINE eq *uvicorn*" 2>nul

REM Also try graceful shutdown via Python
python -c "import psutil; [p.terminate() for p in psutil.process_iter() if 'giljo' in ' '.join(p.cmdline()).lower()]" 2>nul

echo.
echo ===============================================
echo    All GiljoAI MCP services stopped
echo ===============================================
echo.
pause
