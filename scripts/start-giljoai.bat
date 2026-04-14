@echo off
title GiljoAI MCP Server
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m api.run_api
pause
