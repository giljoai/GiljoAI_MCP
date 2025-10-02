@echo off
REM GiljoAI MCP - Windows Firewall Configuration (netsh)
REM Generated: 2025-10-02T05:22:24.782300
REM Run as Administrator

echo ==========================================================
echo   GiljoAI MCP - Windows Firewall Configuration
echo ==========================================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click the script and select "Run as administrator"
    pause
    exit /b 1
)

echo Configuring firewall rules for GiljoAI MCP services...
echo.

REM API Server
netsh advfirewall firewall delete rule name="GiljoAI MCP API" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP API" ^
    dir=in action=allow ^
    protocol=TCP localport=8000 ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP API (port 8000)

REM WebSocket Server
netsh advfirewall firewall delete rule name="GiljoAI MCP WebSocket" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP WebSocket" ^
    dir=in action=allow ^
    protocol=TCP localport=8001 ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP WebSocket (port 8001)

REM Dashboard
netsh advfirewall firewall delete rule name="GiljoAI MCP Dashboard" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP Dashboard" ^
    dir=in action=allow ^
    protocol=TCP localport=3000 ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP Dashboard (port 3000)

REM PostgreSQL
netsh advfirewall firewall delete rule name="GiljoAI MCP PostgreSQL" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="GiljoAI MCP PostgreSQL" ^
    dir=in action=allow ^
    protocol=TCP localport=5432 ^
    profile=domain,private
echo   [OK] Created rule: GiljoAI MCP PostgreSQL (port 5432)

echo.
echo Firewall configuration completed successfully!
echo.
echo SECURITY REMINDER:
echo   - Review rules in Windows Defender Firewall
echo   - Consider limiting access to specific IP ranges
echo   - Enable SSL/TLS for production use
echo.
pause
