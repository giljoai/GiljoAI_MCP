# GiljoAI MCP Developer Control Panel

A comprehensive GUI tool for managing the GiljoAI MCP development environment.

## Quick Start (Recommended - Isolated Environment)

The control panel uses its own **isolated virtual environment** to avoid conflicts with the main application venv.

### First Time Setup

```bash
# From project root (or cd to dev_tools/)
dev_tools\setup_devtools_venv.bat
```

This creates `dev_tools/venv_devtools/` with all required dependencies (psutil, psycopg2-binary, pyyaml).

### Launch Control Panel

**Option 1: Use the Launcher (Easiest)**
```bash
# From anywhere in project
dev_tools\launch_control_panel.bat
```

**Option 2: Manual Launch**
```bash
cd dev_tools
venv_devtools\Scripts\activate
python control_panel.py
```

### Why Separate Virtual Environment?

The control panel needs to delete the main `venv/` folder during reset operations. Running from the main venv would lock those files. The isolated `dev_tools/venv_devtools/` environment allows:

- ✅ **Full venv deletion** without file locks
- ✅ **Independent dependencies** (won't break if main venv is corrupted)
- ✅ **No interference** with main application
- ✅ **Can run even if** main venv is broken or missing

---

## Features

### Service Management
- **Start/Stop/Restart** backend API server
- **Start/Stop/Restart** frontend dev server
- **Start All** - Launch both services simultaneously
- **Stop All** - Gracefully shut down all services
- **Real-time status indicators** - Green (running), Red (stopped)

### Database Management
- **Check Connection** - Verify PostgreSQL is accessible on localhost:5432
- **Check Database** - Verify `giljo_mcp` database exists
- **Delete Database** - Remove `giljo_mcp` database with confirmation
- **Visual status indicators** for connection and database state

### Development Reset
- **Reset to Fresh State** - Simulate fresh download by removing:
  - `venv/` - Python virtual environment
  - `config.yaml` - System configuration
  - `.env` - Environment variables
  - `install_config.yaml` - Installer configuration
- **Confirmation dialog** showing exactly what will be deleted
- **Error handling** for permission issues

### Cache Management
- **Clear Python Cache** - Remove all `__pycache__/`, `*.pyc`, `*.pyo` files
- **Clear Frontend Cache** - Remove `frontend/node_modules/.vite/`, `frontend/dist/`
- **Clear All Caches** - Both Python and frontend in one click

### Frontend Tools
- **Hard Reload Frontend** - Aggressive reload process:
  1. Stop frontend dev server
  2. Clear Vite cache
  3. Restart dev server
  4. Open browser with cache-busting URL parameter

## Installation

### 1. Install Dependencies

```bash
# From project root
pip install -r dev_tools/requirements.txt
```

Dependencies:
- `psutil` - Process management and system utilities
- `psycopg2-binary` - PostgreSQL database driver
- `pyyaml` - YAML configuration parsing

### 2. Run Control Panel

```bash
# From project root
python dev_tools/control_panel.py
```

### Windows: Run as Administrator

For full functionality, right-click and select "Run as Administrator":

```bash
# PowerShell as Administrator
cd F:\GiljoAI_MCP
python dev_tools/control_panel.py
```

### Linux/macOS: Run with sudo

```bash
sudo python3 dev_tools/control_panel.py
```

## Usage

### Starting Services

1. **Backend Only**: Click "Start" next to "Backend API"
2. **Frontend Only**: Click "Start" next to "Frontend Dev"
3. **Both**: Click "Start All Services"

Services will show green indicator when running.

### Stopping Services

1. **Individual Service**: Click "Stop" next to the service
2. **All Services**: Click "Stop All Services"
3. **Restart**: Click "Restart" to stop and start a service

### Database Operations

#### Check Connection
1. Click "Check Connection"
2. Green indicator = Connected
3. Red indicator = Connection failed

#### Check Database
1. Click "Check Database"
2. Green indicator = Database exists
3. Red indicator = Database not found

#### Delete Database
1. Click "Delete Database"
2. **Confirmation dialog** shows what will be deleted
3. Click "Yes" to confirm
4. All data in `giljo_mcp` database will be permanently removed

**Warning**: Database deletion is permanent and cannot be undone!

### Development Reset

To simulate a fresh download:

1. Click "Reset to Fresh State"
2. **Confirmation dialog** shows files/directories to be deleted:
   - `venv/` - Virtual environment
   - `config.yaml` - Configuration
   - `.env` - Environment variables
   - `install_config.yaml` - Installer config
3. Click "Yes" to confirm
4. Files are removed
5. Run installer again to set up fresh

**Use Case**: Testing the installation process or fixing corrupted configs

### Cache Clearing

#### Python Cache
- Removes all `__pycache__/` directories
- Removes all `*.pyc` compiled Python files
- Removes all `*.pyo` optimized Python files

**When to Use**: After significant code changes or refactoring

#### Frontend Cache
- Removes `frontend/node_modules/.vite/` cache
- Removes `frontend/dist/` build directory

**When to Use**: Frontend not reflecting changes, build issues

#### All Caches
- Clears both Python and frontend caches in sequence

**When to Use**: General cache issues, preparing for clean build

### Hard Reload Frontend

For stubborn frontend caching issues:

1. Click "Hard Reload Frontend"
2. Process:
   - Stops frontend dev server (if running)
   - Removes Vite cache completely
   - Restarts dev server
   - Opens browser with cache-busting parameter (`?_=timestamp`)
3. Browser opens with fresh frontend

**When to Use**:
- Frontend changes not visible despite normal reload
- Vite HMR (Hot Module Replacement) not working
- UI rendering issues

## Cross-Platform Support

The control panel works on:
- **Windows** - Full support, run as Administrator recommended
- **Linux** - Full support, run with sudo recommended
- **macOS** - Full support, run with sudo recommended

All file operations use `pathlib.Path()` for cross-platform compatibility.

## Troubleshooting

### "Admin Privileges Required" Warning

**Windows**: Right-click → "Run as Administrator"
**Linux/macOS**: `sudo python3 dev_tools/control_panel.py`

Some features (stopping services, deleting files) may require elevated privileges.

### Missing Dependencies Warning

If you see warnings about missing dependencies:

```bash
pip install psutil psycopg2-binary pyyaml
```

Features requiring missing dependencies will be disabled.

### Database Connection Failed

**Check PostgreSQL is running**:
```bash
# Windows
Get-Service -Name postgresql*

# Linux
sudo systemctl status postgresql
```

**Verify credentials** in `.env` or `config.yaml`:
- Password: set via `dev_tools/devtools.local.ini` or `PG_SUPERUSER_PASSWORD` in `.env`
- Default user: `postgres`
- Default host: `localhost`
- Default port: `5432`

### Service Won't Start

**Check ports are available**:
```bash
# Windows
netstat -ano | findstr :7272
netstat -ano | findstr :7274

# Linux
netstat -tulpn | grep 7272
netstat -tulpn | grep 7274
```

**Check files exist**:
- Backend: `api/run_api.py` must exist
- Frontend: `frontend/` directory must exist

### Permission Errors During Reset

If reset fails with permission errors:
1. **Close all applications** using project files
2. **Stop all services** first
3. **Run as administrator/sudo**
4. **Manually delete** stubborn files/folders if needed

## Architecture

### Service Management
- Uses `subprocess.Popen()` to spawn service processes
- Tracks PIDs for start/stop/restart operations
- Graceful shutdown with `terminate()` then `kill()` if needed
- Status checking with `poll()` to detect if process is running

### Database Operations
- Uses `psycopg2` for PostgreSQL connections
- Connects to `postgres` database to check/manage `giljo_mcp`
- Terminates active connections before dropping database
- 5-second connection timeout for responsiveness

### Cache Management
- Recursive glob patterns (`rglob()`) to find all cache files
- `shutil.rmtree()` for directory removal
- `Path.unlink()` for file deletion
- Counts removed items for user feedback

### Admin Detection
- **Windows**: `ctypes.windll.shell32.IsUserAnAdmin()`
- **Linux/macOS**: `os.geteuid() == 0` (checks for root)

## Security Considerations

### Database Credentials
- Credentials are stored in `dev_tools/devtools.local.ini` (gitignored, per-developer)
- Legacy fallback: `PG_SUPERUSER_PASSWORD` in `.env`
- The control panel prompts on first use and saves to the local config
- **Never commit credentials** — both `.env` and `devtools.local.ini` are gitignored

### Service Binding
- Backend binds to `127.0.0.1` in localhost mode (config.yaml)
- Frontend dev server binds to `localhost` by default
- **Server mode**: Requires API key authentication

### Admin Privileges
- Required for some file operations
- Required for reliable process management
- Warning shown if not running as admin

## Development

### Adding New Features

1. **Add tests first** in `tests/dev_tools/test_control_panel.py`
2. **Implement feature** in `control_panel.py`
3. **Update README** with usage instructions
4. **Test cross-platform** on Windows, Linux, macOS

### Testing

```bash
# Run all tests
pytest tests/dev_tools/test_control_panel.py

# Run specific test class
pytest tests/dev_tools/test_control_panel.py::TestServiceManagement

# Run with coverage
pytest tests/dev_tools/test_control_panel.py --cov=dev_tools
```

### Code Quality

```bash
# Linting
ruff dev_tools/

# Formatting
black dev_tools/

# Type checking
mypy dev_tools/
```

## Known Limitations

1. **Process tracking**: Processes started outside control panel are not tracked
2. **npm requirement**: Frontend features require npm installed
3. **PostgreSQL requirement**: Database features require PostgreSQL 18
4. **Privilege escalation**: Cannot self-elevate, must be run as admin initially

## Future Enhancements

Potential features for future versions:
- Log viewing panel
- Configuration editor
- Database backup/restore
- Service health monitoring
- Performance metrics
- Multiple environment profiles
- Dark mode UI theme

## Support

For issues or questions:
1. Check troubleshooting section above
2. Verify dependencies are installed
3. Check logs in `logs/giljo_mcp.log`
4. Ensure running with admin privileges

## License

Part of the GiljoAI MCP project. See main project LICENSE file.
