@echo off
REM GiljoAI MCP - Quick Test Deployment Script
REM This batch file launches the Python deployment script

python "%~dp0giltest.py" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Deployment script failed with error code %ERRORLEVEL%
    pause
)