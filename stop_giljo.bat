@echo off
echo Stopping GiljoAI MCP Orchestrator...

:: Kill Python processes running our services
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *giljo_mcp*" 2>nul
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *frontend*" 2>nul

:: Kill processes by port if still running
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6000') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6001') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6002') do taskkill /F /PID %%a 2>nul

echo All services stopped.
pause
