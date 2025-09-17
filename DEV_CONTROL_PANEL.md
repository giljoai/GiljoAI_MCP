# GiljoAI MCP Development Control Panel

## Overview
A Flask-based web dashboard for managing all GiljoAI MCP services during development. Provides service control, cache management, and real-time log viewing.

## Quick Start
```bash
# Easy startup
./launch_dev.bat

# Manual startup
python dev_control_panel.py
```

## Access
- **Control Panel**: http://localhost:5500
- **Auto-refresh**: Every 5 seconds
- **No-refresh mode**: Add `?no_refresh=1` to URL

## Services Managed
| Service | Port | Description |
|---------|------|-------------|
| MCP Server | 6001 | FastMCP protocol server |
| REST API | 6002 | FastAPI backend |
| WebSocket | 6003 | Real-time communication |
| Frontend | 6000 | Vue.js dashboard |
| PostgreSQL | 5432 | Database (external) |

## Features

### Service Control
- ✅ Start/Stop/Restart individual services
- ✅ Bulk operations (Start All, Stop All, Restart All)
- ✅ Visual status indicators (🟢🟡🔴)
- ✅ Real-time status monitoring

### Cache Management
- ✅ Clear Python bytecode cache (`__pycache__`, `.pyc`, `.pyo`)
- ✅ Clear pytest cache (`.pytest_cache`)
- ✅ Clear mypy cache (`.mypy_cache`)
- ✅ Clear ruff cache (`.ruff_cache`)
- ✅ "Clear & Restart All" combo action

### Log Viewing
- ✅ Real-time log tailing (last 50 lines)
- ✅ Per-service log files in `logs/` directory
- ✅ Terminal-style viewer with syntax highlighting

## Critical Problem Solved
**60% Success Rate Issue**: The unification_specialist2 discovered that architectural fixes were complete but bytecode caching was masking improvements. The cache clearing functionality resolves this by:

1. Removing all Python bytecode cache
2. Clearing testing framework caches
3. Enabling clean service restarts
4. Allowing proper verification of integration fixes

## API Endpoints
- `POST /api/start/<service>` - Start service
- `POST /api/stop/<service>` - Stop service
- `POST /api/restart/<service>` - Restart service
- `POST /api/start_all` - Start all services
- `POST /api/stop_all` - Stop all services
- `POST /api/restart_all` - Restart all services
- `POST /api/clear_cache` - Clear Python cache
- `POST /api/clear_and_restart` - Clear cache + restart all
- `GET /api/logs/<service>` - Get service logs

## File Structure
```
dev_control_panel.py     # Main Flask application
launch_dev.bat          # Easy startup script
control_panel_requirements.txt  # Dependencies
logs/                   # Service log files
├── mcp_server.log
├── api_server.log
├── websocket_server.log
└── frontend.log
```

## Status Indicators
- 🟢 **Running**: Service is active and managed by control panel
- 🟡 **External**: Port is in use by external process
- 🔴 **Stopped**: Service is not running

## Windows Environment
- Uses `subprocess.CREATE_NEW_CONSOLE` for Windows service isolation
- Handles Windows process termination properly
- Compatible with Windows paths and commands

## Development Notes
- Port 5500 chosen to avoid conflicts with AKE-MCP (ports 5000-5002)
- Auto-refresh can be disabled for debugging
- Logs persist across service restarts
- Cache clearing is recursive across entire project
- Process cleanup handles both managed and external processes

## Dependencies
- Flask 2.3+
- psutil 5.9+
- Python 3.8+

## Usage in CI/CD
The control panel enables proper testing by allowing agents to:
1. Clear stale cache that masks code changes
2. Restart services to pick up new code
3. Monitor service health during integration tests
4. View real-time logs for debugging

This tool is essential for Phase 4 testing and validation workflows.