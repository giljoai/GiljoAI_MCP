# GiljoAI MCP - Quick Start Guide

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 18 (or 14-18)
- 500MB free disk space
- Available ports: 8000, 8001, 3000

### Step 1: Install Dependencies

```bash
cd C:\Projects\GiljoAI_MCP
pip install -r installer/requirements.txt
```

### Step 2: Run the Installer

#### Interactive Mode (Recommended)
```bash
python installer/cli/install.py
```

#### Batch Mode
```bash
python installer/cli/install.py --mode localhost --batch --pg-password your_password
```

#### Using Config File
```bash
# Generate template
python installer/cli/install.py --generate-config

# Edit install_config.yaml with your settings

# Run installation
python installer/cli/install.py --config install_config.yaml
```

### Step 3: Start the Services

#### Windows
```cmd
.\launchers\start_giljo.bat
```

#### Linux/macOS
```bash
./launchers/start_giljo.sh
```

#### Python (Universal)
```bash
python launchers/start_giljo.py
```

### Step 4: Access the Dashboard

Open your browser to:
```
http://localhost:3000
```

API Documentation available at:
```
http://localhost:8000/docs
```

---

## Command Reference

### Installation Options

```bash
# Show version
python installer/cli/install.py --version

# Show help
python installer/cli/install.py --help

# Localhost mode (default)
python installer/cli/install.py --mode localhost

# Server mode (network accessible)
python installer/cli/install.py --mode server

# Batch mode (non-interactive)
python installer/cli/install.py --batch --pg-password secret

# Custom ports
python installer/cli/install.py --api-port 9000 --ws-port 9001 --dashboard-port 4000
```

### Launcher Options

```bash
# Start all services
python launchers/start_giljo.py

# View service logs
tail -f logs/*.log  # Unix
type logs\*.log     # Windows
```

---

## Troubleshooting

### PostgreSQL Not Found

If PostgreSQL is not installed:

**Windows:**
1. Download from https://www.postgresql.org/download/windows/
2. Run installer as Administrator
3. Remember the postgres password
4. Return and run the installer again

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql-18
```

**macOS:**
```bash
brew install postgresql@18
brew services start postgresql@18
```

### Port Already in Use

Check which process is using the port:

**Windows:**
```cmd
netstat -ano | findstr :8000
```

**Linux/macOS:**
```bash
lsof -i :8000
```

Stop the conflicting service or choose different ports during installation.

### Database Creation Failed

If you see "Database setup required" message:

1. A script has been generated in `installer/scripts/`
2. Run the script with elevated privileges:

**Windows:**
```powershell
# Open PowerShell as Administrator
cd C:\Projects\GiljoAI_MCP
.\installer\scripts\create_db.ps1
```

**Linux/macOS:**
```bash
cd /path/to/GiljoAI_MCP
bash installer/scripts/create_db.sh
```

3. Return to the installer and press Enter

### Services Won't Start

1. Check the logs: `logs/*.log`
2. Verify configuration: `.env` and `config.yaml` exist
3. Test database connection:
   ```bash
   psql -h localhost -U giljo_user -d giljo_mcp
   # Password is in installer/credentials/db_credentials_*.txt
   ```

---

## File Locations

### Configuration Files
- `.env` - Environment variables (database, ports, secrets)
- `config.yaml` - Application configuration
- `api_keys.yaml` - API keys (server mode only)

### Credentials
- `installer/credentials/db_credentials_*.txt` - Database passwords

### Logs
- `install_logs/` - Installation logs
- `logs/` - Service logs
- `logs/launcher_*.log` - Launcher logs

### Scripts
- `installer/scripts/create_db.ps1` - Windows database setup
- `installer/scripts/create_db.sh` - Unix database setup

---

## Modes

### Localhost Mode
- **Binding:** 127.0.0.1 (local only)
- **Authentication:** None
- **Use Case:** Local development

### Server Mode
- **Binding:** 0.0.0.0 (network accessible)
- **Authentication:** API keys
- **SSL:** Optional
- **Use Case:** Team deployment

---

## Next Steps

1. **Register AI Tools** (Optional)
   ```bash
   python register_ai_tools.py
   ```

2. **Read Documentation**
   - Integration guide: `docs/AI_TOOL_INTEGRATION.md`
   - API reference: `http://localhost:8000/docs`

3. **Connect Projects**
   ```bash
   # In your project directory
   C:\Projects\GiljoAI_MCP\connect_project.bat
   ```

---

## Uninstallation

To completely remove GiljoAI MCP:

1. Stop all services (Ctrl+C in launcher)
2. Drop the database:
   ```sql
   DROP DATABASE IF EXISTS giljo_mcp;
   DROP ROLE IF EXISTS giljo_user;
   DROP ROLE IF EXISTS giljo_owner;
   ```
3. Remove the installation directory

---

## Getting Help

- **Installation Issues:** Check `install_logs/install_*.log`
- **Runtime Issues:** Check `logs/*.log`
- **Documentation:** See `docs/` directory
- **Support:** Create an issue on GitHub

---

## Quick Commands Cheat Sheet

```bash
# Install
pip install -r installer/requirements.txt
python installer/cli/install.py

# Start
python launchers/start_giljo.py

# Check status
curl http://localhost:8000/health

# View logs
tail -f logs/api_server_stdout.log

# Stop
Ctrl+C (in launcher terminal)
```
