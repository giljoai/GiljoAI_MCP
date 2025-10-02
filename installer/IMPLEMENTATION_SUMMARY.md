# CLI Installer Implementation Summary
## Quick Reference Guide

---

## KEY FILES MODIFIED

### 1. installer/core/installer.py
**Absolute Path**: `C:\Projects\GiljoAI_MCP\installer\core\installer.py`

**New Methods Added**:

```python
# Lines 433-482
def create_venv(self) -> Dict[str, Any]:
    """Create virtual environment in installation directory"""
    # Creates venv at {install_dir}/venv
    # Upgrades pip automatically
    # Cross-platform path handling

# Lines 484-534
def install_dependencies(self) -> Dict[str, Any]:
    """Install Python dependencies in the virtual environment"""
    # Uses venv pip instead of system pip
    # Copies requirements.txt to install directory
    # Proper venv isolation

# Lines 536-577
def register_with_claude(self) -> Dict[str, Any]:
    """Register MCP server with Claude Code"""
    # Imports UniversalMCPInstaller
    # Uses venv Python path
    # Non-blocking (warns on failure)
```

**Updated Method**:
```python
# Lines 57-167
def install(self) -> Dict[str, Any]:
    """Main installation workflow"""
    # Step 1: Create Virtual Environment (NEW)
    # Step 2: Setup Database
    # Step 3: Generate Configuration Files
    # Step 4: Install Dependencies (UPDATED to use venv)
    # Step 5: Create Launchers
    # Step 6: Mode-Specific Setup
    # Step 7: Register with Claude Code (NEW)
    # Step 8: Post-Installation Validation
```

---

### 2. launchers/start_giljo.py
**Absolute Path**: `C:\Projects\GiljoAI_MCP\launchers\start_giljo.py`

**New Function Added**:

```python
# Lines 183-231
def start_services(settings: dict = None):
    """
    Start services after installation (called from installer)

    Args:
        settings: Optional settings dict from installer with config overrides
    """
    # Creates GiljoLauncher instance
    # Overrides config with installation settings
    # Starts all services
    # Handles graceful shutdown
```

**Usage**:
```python
# From installer/cli/install.py:545
from launchers.start_giljo import start_services
start_services(settings)
```

---

### 3. installer/cli/install.py
**Absolute Path**: `C:\Projects\GiljoAI_MCP\installer\cli\install.py`

**Updated Functions**:

```python
# Lines 192-206
def display_header(mode: str):
    """Display installation header"""
    # Added Claude Code exclusivity notice:
    click.echo("IMPORTANT NOTICE:")
    click.echo("  Currently supports Claude Code only")
    click.echo("  Support for Codex and Gemini coming in 2026")

# Lines 496-546
def display_success(settings: Dict[str, Any], result: Dict[str, Any]):
    """Display successful installation message"""
    # Added MCP registration status
    # Added Claude Code exclusivity notice
    # Updated port displays (7272, 6000)
    # Fixed start_services import
```

---

## KEY CODE SNIPPETS

### Creating Virtual Environment

```python
import venv
from pathlib import Path

venv_path = Path(install_dir) / 'venv'
venv.create(venv_path, with_pip=True, clear=False,
           symlinks=(platform.system() != "Windows"))

# Verify creation
if platform.system() == "Windows":
    venv_python = venv_path / 'Scripts' / 'python.exe'
else:
    venv_python = venv_path / 'bin' / 'python'
```

### Installing Dependencies in venv

```python
import subprocess
import shutil

# Get venv pip
if platform.system() == "Windows":
    venv_pip = venv_path / 'Scripts' / 'pip.exe'
else:
    venv_pip = venv_path / 'bin' / 'pip'

# Copy requirements.txt
shutil.copy(source_req, dest_req)

# Install with venv pip
cmd = [str(venv_pip), "install", "-r", str(dest_req)]
subprocess.run(cmd, capture_output=True, text=True)
```

### Registering with Claude Code

```python
from installer.universal_mcp_installer import UniversalMCPInstaller

mcp_installer = UniversalMCPInstaller()
registration_result = mcp_installer.register_all(
    server_name='giljo-mcp',
    command=str(venv_python),
    args=['-m', 'src.mcp_adapter'],
    env=None
)

if registration_result.get('claude', False):
    # Success!
    pass
```

---

## CONFIGURATION VERIFICATION

The `installer/core/config.py` already generates all required variables.

**Port Configuration** (Correct):
```bash
GILJO_API_PORT=7272
GILJO_PORT=7272
GILJO_FRONTEND_PORT=6000
VITE_FRONTEND_PORT=6000
```

**Database Configuration** (Complete):
```bash
# PostgreSQL specific
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=giljo_mcp
POSTGRES_USER=giljo_user
POSTGRES_PASSWORD={generated}

# Generic aliases
DB_HOST=localhost
DB_PORT=5432
DB_NAME=giljo_mcp
DB_USER=giljo_user
DB_PASSWORD={generated}

# Full URL
DATABASE_URL=postgresql://giljo_user:{password}@localhost:5432/giljo_mcp
```

**Frontend Configuration** (Complete):
```bash
VITE_API_URL=http://localhost:7272
VITE_WS_URL=ws://localhost:7272
VITE_APP_MODE=local
VITE_API_PORT=7272
```

---

## INSTALLATION COMMANDS

### Interactive Mode
```bash
python installer/cli/install.py
```

### Batch Mode (Localhost)
```bash
python installer/cli/install.py \
  --mode localhost \
  --batch \
  --pg-password your_postgres_password
```

### Batch Mode (Server)
```bash
python installer/cli/install.py \
  --mode server \
  --batch \
  --pg-password your_postgres_password \
  --api-port 7272 \
  --dashboard-port 6000 \
  --bind 0.0.0.0 \
  --admin-username admin \
  --admin-password secure_password
```

### Config File Mode
```bash
# Generate template
python installer/cli/install.py --generate-config

# Edit install_config.yaml
# Then run:
python installer/cli/install.py --config install_config.yaml
```

---

## TESTING CHECKLIST

### Pre-Flight
- [ ] Python 3.8+ installed
- [ ] PostgreSQL 16+ installed and running
- [ ] Ports 7272 and 6000 available

### Installation
- [ ] Virtual environment created at `{install_dir}/venv`
- [ ] Dependencies installed in venv
- [ ] Database `giljo_mcp` created
- [ ] Users `giljo_owner` and `giljo_user` created
- [ ] `.env` file generated with correct variables
- [ ] `config.yaml` generated
- [ ] Launcher scripts created
- [ ] MCP registered with Claude Code

### Post-Installation
- [ ] Can activate venv: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- [ ] Can start services: `launchers/start_giljo.bat` or `launchers/start_giljo.sh`
- [ ] API accessible at http://localhost:7272
- [ ] Dashboard accessible at http://localhost:6000
- [ ] Claude Code can connect to MCP server

---

## TROUBLESHOOTING

### Virtual Environment Not Created
```bash
# Check Python has venv module
python -m venv --help

# On some systems, need to install:
# Debian/Ubuntu: apt-get install python3-venv
# CentOS/RHEL: yum install python3-venv
```

### Dependencies Install Fails
```bash
# Check venv pip exists
Windows: venv\Scripts\pip.exe --version
Unix: venv/bin/pip --version

# Manually upgrade pip if needed
Windows: venv\Scripts\python.exe -m pip install --upgrade pip
Unix: venv/bin/python -m pip install --upgrade pip
```

### MCP Registration Fails
```bash
# Check Claude Code is installed
# Installation continues anyway with warning

# Can manually register later:
python -m installer.universal_mcp_installer
```

---

## FILE STRUCTURE AFTER INSTALLATION

```
{install_dir}/
├── venv/                  # Virtual environment (NEW)
│   ├── Scripts/          # Windows
│   ├── bin/              # Unix
│   ├── Lib/              # Python packages
│   └── pyvenv.cfg        # Venv config
├── .env                   # Environment variables
├── config.yaml            # Installation config
├── requirements.txt       # Copied from source
├── launchers/             # Start scripts
│   ├── start_giljo.py
│   ├── start_giljo.bat   # Windows
│   └── start_giljo.sh    # Unix
├── logs/                  # Log directory
├── data/                  # Data directory
├── uploads/               # Upload directory
└── temp/                  # Temp directory
```

---

## ENVIRONMENT VARIABLES REFERENCE

### Critical Variables (Application Expects)
```bash
# Ports
GILJO_API_PORT=7272
GILJO_FRONTEND_PORT=6000

# Database
DATABASE_URL=postgresql://giljo_user:{password}@localhost:5432/giljo_mcp
DB_HOST=localhost
DB_NAME=giljo_mcp
DB_USER=giljo_user
DB_PASSWORD={generated}

# Frontend
VITE_API_URL=http://localhost:7272
VITE_WS_URL=ws://localhost:7272
VITE_APP_MODE=local

# Server
GILJO_MCP_MODE=LOCAL
GILJO_API_HOST=127.0.0.1

# Features
ENABLE_VISION_CHUNKING=true
ENABLE_MULTI_TENANT=true
ENABLE_WEBSOCKET=true

# Agent Limits
MAX_AGENTS_PER_PROJECT=20
AGENT_CONTEXT_LIMIT=150000
```

---

## IMPORTANT NOTES

1. **Virtual Environment is Critical**
   - All dependencies must be in venv
   - Launcher uses venv Python
   - MCP registration uses venv path

2. **Port Configuration**
   - API: 7272 (not 8000 or 8080)
   - Frontend: 6000 (not 3000)
   - WebSocket: Same as API (unified in v2.0)

3. **Claude Code Only**
   - Codex and Gemini support disabled
   - Will be re-enabled in 2026
   - See CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md

4. **Database Schema**
   - Relies on Alembic migrations
   - Verify alembic.ini exists
   - Check migrations in alembic/ directory

---

*Quick Reference - Implementation Developer*
*Last Updated: 2025-10-02*
