@echo off
REM ============================================================
REM GiljoAI MCP - Release Simulation & Test Deployment
REM ============================================================
REM
REM PURPOSE:
REM   Simulates downloading and extracting a GitHub release
REM   Copies ONLY files that would be in a release archive
REM
REM USAGE:
REM   giltest.bat           - Run interactive deployment
REM   giltest.bat --quick   - Quick sync (files changed in last 2 min)
REM   giltest.bat -q        - Quick sync (short option)
REM
REM WHAT IT DOES:
REM   1. Reads .gitattributes export-ignore rules
REM   2. Copies ~400 files (release) vs ~1,600 (development)
REM   3. Excludes: tests, dev docs, logs, caches, IDE configs
REM   4. Target: C:\install_test\Giljo_MCP
REM
REM ============================================================

python "%~dp0giltest.py" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Deployment script failed with error code %ERRORLEVEL%
    pause
)