@echo off
REM Start Serena MCP server isolated to this project only

REM Kill any existing Serena processes
taskkill /F /IM serena-mcp-server.exe 2>nul

REM Start Serena with this project only
"C:\Program Files\Python311\Scripts\serena-mcp-server.exe" --project "F:\GiljoAI_MCP" --enable-web-dashboard false --enable-gui-log-window false