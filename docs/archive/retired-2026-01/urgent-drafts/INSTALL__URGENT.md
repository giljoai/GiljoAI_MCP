# GiljoAI MCP Coding Orchestrator - Installation Guide

**Version**: 2.0.0
**Last Updated**: October 5, 2025
**Installation Type**: Two-Phase (CLI + Web Wizard)

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation Flow](#installation-flow)
- [Phase 1: CLI Installer](#phase-1-cli-installer)
- [Phase 2: Setup Wizard](#phase-2-setup-wizard)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Advanced Options](#advanced-options)

## Overview

GiljoAI MCP uses a **two-phase installation process**:

1. **Phase 1 - CLI Installer**: Handles core system setup (PostgreSQL, dependencies, services)
2. **Phase 2 - Setup Wizard**: Handles configuration and integration (deployment mode, AI tools, firewall)

This approach provides:
- Automated infrastructure setup (CLI)
- Interactive configuration with validation (Web Wizard)
- Better user experience with real-time feedback
- Cross-platform compatibility

## Prerequisites

### Required Software

- **Python 3.11 or higher** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 18** - Required database version
  - **Recommended**: Pre-install PostgreSQL 18
  - **Auto-Install**: CLI installer can install if not detected
- **Terminal Access**:
  - Windows: PowerShell, Command Prompt, or Git Bash
  - Linux/macOS: Terminal

### Optional Software

- **Node.js 18+** - For frontend development (not required for usage)
- **Git** - For cloning repository (or download ZIP)

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| RAM | 4 GB | 8 GB+ |
| Disk Space | 2 GB | 5 GB+ |
| CPU | 2 cores | 4+ cores |
| Network | Optional | Required for LAN/WAN |

## Installation Flow

```
┌─────────────────────────────────────┐
│ Step 1: Download/Clone Repository   │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Step 2: Run CLI Installer           │
│ python install.py or install.bat    │
│                                     │
│ - Detects OS and requirements       │
│ - Installs PostgreSQL 18            │
│ - Creates virtual environment       │
│ - Installs Python dependencies      │
│ - Configures database               │
│ - Creates system services           │
│ - Starts backend and frontend       │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Step 3: Setup Wizard Opens          │
│ http://localhost:7274/setup         │
│                                     │
│ - Test database connection          │
│ - Select deployment mode            │
│ - Create admin account (LAN/WAN)    │
│ - Configure AI tool integration     │
│ - Setup firewall (LAN/WAN)          │
│ - Verify system health              │
└───────────────┬─────────────────────┘
                ↓
┌─────────────────────────────────────┐
│ Step 4: Ready to Use!               │
│ Dashboard at http://localhost:7274  │
└─────────────────────────────────────┘
```

## Phase 1: CLI Installer

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/giljoai/GiljoAI_MCP.git
cd GiljoAI_MCP

# 2. Run installer
python install.py
```

### What the CLI Installer Does

The CLI installer automates all system-level setup tasks:

1. **System Detection**
   - Identifies operating system (Windows/Linux/macOS)
   - Checks Python version (requires 3.11+)
   - Detects existing PostgreSQL installation

2. **PostgreSQL 18 Installation** (if needed)
   - Downloads and installs PostgreSQL 18
   - Configures default database settings
   - Creates `giljo_mcp` database
   - Sets up postgres user credentials

3. **Python Environment Setup**
   - Creates isolated virtual environment
   - Installs all Python dependencies from `requirements.txt`
   - Installs GiljoAI package in editable mode

4. **Database Table Creation**
   - **Uses DatabaseManager.create_tables_async()** (same as api/app.py:186)
   - Creates all tables via Base.metadata.create_all()
   - **NOT using Alembic migrations**
   - Creates setup state for first-admin creation during wizard
   - Creates setup_state record

5. **Service Configuration**
   - Creates `.env` file from template
   - Generates `config.yaml` with defaults
   - Configures database connection
   - Sets default ports (API: 7272, Dashboard: 7274)

6. **Service Startup**
   - Starts backend API server
   - Starts frontend dashboard server
   - Verifies services are running
   - Opens dashboard in browser

### Installation Time

- **Typical Duration**: 3-7 minutes
- **Factors**: Internet speed (downloading PostgreSQL), system performance

### Installation Log

All installer activities are logged to:
- `install_logs/install.log` - Detailed installation log
- Console output - Real-time progress updates

---

## Phase 2: Setup Wizard

### Automatic Launch

After CLI installer completes:
1. Dashboard opens automatically in your default browser
2. URL: `http://localhost:7274`
3. If setup incomplete, wizard appears automatically
4. If wizard doesn't appear, navigate to: `http://localhost:7274/setup`

### What the Setup Wizard Does

The Setup Wizard handles configuration tasks requiring user interaction:

1. **Database Connection Verification**
   - Tests PostgreSQL connection
   - Validates credentials
   - Checks database schema

2. **Deployment Mode Selection**
   - **Localhost**: Single-user, this PC only
   - **LAN**: Multi-user, local network
   - **WAN**: Multi-user, internet-accessible

3. **Admin Account Creation** (LAN/WAN only)
   - Username and password setup
   - Initial administrator account
   - Optional email configuration

4. **AI Tool Integration**
   - Detects installed AI coding tools (Claude Code, Cline, Cursor)
   - Generates tool-specific MCP configurations
   - Writes configurations to tool config files
   - Tests MCP connections

5. **Firewall Configuration** (LAN/WAN only)
   - Provides platform-specific firewall commands
   - Tests network connectivity
   - Verifies ports are accessible

6. **Final Verification**
   - Checks all services healthy
   - Validates complete configuration
   - Saves final settings

### Setup Wizard Time

- **Localhost Mode**: 3-5 minutes
- **LAN Mode**: 8-12 minutes
- **WAN Mode**: 15-20 minutes

### Detailed Wizard Guide

For complete Setup Wizard instructions, see:
**[Setup Wizard Guide](../guides/SETUP_WIZARD_GUIDE.md)**

---

## Verification

### Post-Installation Checks

After both phases complete, verify your installation:

**1. Check Services Running**:

Windows:
```powershell
# Check if processes are running
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

Linux/macOS:
```bash
# Check backend
ps aux | grep "uvicorn"

# Check frontend
ps aux | grep "node"
```

**2. Test API Health**:

```bash
curl http://localhost:7272/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "2.0.0"
}
```

**3. Access Dashboard**:

Open browser to: `http://localhost:7274`

Should see GiljoAI Dashboard with:
- Navigation sidebar
- Welcome message or projects list
- No error messages

**4. Check Database Connection**:

```bash
# Using psql
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM projects;"
```

Should connect without errors.

**5. Verify MCP Integration** (if configured):

Open your AI coding tool (Claude Code, etc.) and try:
```
Use the giljo-mcp tool to list available projects
```

Should return project list without errors.

---

## Troubleshooting

### CLI Installer Issues

**Issue**: PostgreSQL installation fails

**Solutions**:
1. Pre-install PostgreSQL 18 manually from [postgresql.org](https://www.postgresql.org/download/)
2. Check installer logs: `install_logs/install.log`
3. Ensure admin/sudo privileges
4. See [PostgreSQL Troubleshooting Guide](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt)

**Issue**: "Module not found" errors after installation

**Solutions**:
1. Verify virtual environment created: `ls venv/` (should exist)
2. Check `pyproject.toml` exists in project root
3. Manually install package: `venv/Scripts/pip install -e .` (Windows) or `venv/bin/pip install -e .` (Linux/macOS)

**Issue**: Installer hangs during dependency installation

**Solutions**:
1. Check internet connection
2. Try again with better network
3. Manually install dependencies: `pip install -r requirements.txt`

### Setup Wizard Issues

**Issue**: Wizard doesn't appear

**Solutions**:
1. Manually navigate to: `http://localhost:7274/setup`
2. Check if `config.yaml` already exists (setup may be complete)
3. Delete `config.yaml` to trigger wizard again

**Issue**: Database connection test fails

**Solutions**:
- See [PostgreSQL Troubleshooting Guide](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt)
- Verify PostgreSQL service running
- Check credentials in `.env` file

**Issue**: AI tool not detected

**Solutions**:
1. Verify tool is actually installed
2. Use "Manual Setup" option in wizard
3. Configure tool manually (see Setup Wizard Guide)

**Issue**: Firewall test fails (LAN mode)

**Solutions**:
- See [Firewall Setup Guide](../deployment/FIREWALL_SETUP.md)
- Verify firewall rules created
- Check third-party firewall software
- Temporarily disable firewall to test

### General Issues

**Issue**: Port already in use (7272 or 7274)

**Solutions**:
1. Find process using port:
   - Windows: `netstat -ano | findstr :7272`
   - Linux/macOS: `lsof -i :7272`
2. Stop conflicting process or change ports in `config.yaml`

**Issue**: Permission denied errors

**Solutions**:
- Run installer as administrator (Windows) or with sudo (Linux)
- Check file permissions in installation directory
- Ensure write access to installation folder

### Getting Help

**Documentation**:
- [Setup Wizard Guide](../guides/SETUP_WIZARD_GUIDE.md) - Detailed wizard instructions
- [PostgreSQL Troubleshooting](../troubleshooting/POSTGRES_TROUBLESHOOTING.txt) - Database issues
- [Firewall Setup Guide](../deployment/FIREWALL_SETUP.md) - Network configuration
- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md) - System internals

**Support**:
- GitHub Issues: https://github.com/giljoai/GiljoAI_MCP/issues
- Installation Logs: `install_logs/install.log`
- Backend Logs: `logs/backend.log`

---

## Advanced Options

### Manual Installation (No Installer)

For developers or advanced users who want full control:

**1. Install Prerequisites**:
```bash
# PostgreSQL 18
# Download from https://www.postgresql.org/download/

# Python 3.11+
# Download from https://www.python.org/downloads/
```

**2. Setup Python Environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -e .
```

**3. Configure Database**:
```bash
# Create database
createdb -U postgres giljo_mcp

# Initialize schema
python -c "from src.giljo_mcp.database import init_db; init_db()"
```

**4. Configure Application**:
```bash
cp .env.example .env
cp config.yaml.example config.yaml

# Edit .env with database credentials
# Edit config.yaml with deployment settings
```

**5. Start Services**:
```bash
# Terminal 1: Backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 7272

# Terminal 2: Frontend (if developing)
cd frontend
npm install
npm run dev
```

### Custom PostgreSQL Configuration

If using existing PostgreSQL instance:

**1. Update `.env`**:
```env
DATABASE_HOST=your_host
DATABASE_PORT=your_port
DATABASE_NAME=giljo_mcp
DATABASE_USER=your_user
DATABASE_PASSWORD=your_password
```

**2. Update `config.yaml`**:
```yaml
database:
  host: your_host
  port: your_port
  database: giljo_mcp
  user: your_user
```

**3. Initialize Database**:
```bash
python -c "from src.giljo_mcp.database import init_db; init_db()"
```

### Custom Port Configuration

To use different ports:

**1. Edit `config.yaml`**:
```yaml
server:
  ports:
    api: 8080      # Change from 7272
    frontend: 8081  # Change from 7274
```

**2. Update firewall rules** (if LAN/WAN mode):
```bash
# Update firewall to allow new ports
# See Firewall Setup Guide
```

**3. Restart services** for changes to take effect.

### Silent/Unattended Installation

For automated deployments (future feature):

```bash
# Not yet implemented
python install.py --silent --config=deploy_config.yaml
```

---

## Next Steps

After successful installation:

1. **Complete Setup Wizard** - Finish configuration in web interface
2. **Create First Project** - Start using GiljoAI for your development work
3. **Configure AI Tools** - Integrate with Claude Code, Cline, or Cursor
4. **Explore Documentation**:
   - [Quick Start Guide](QUICK_START.md) - Getting started tutorial
   - [User Guide](../guides/USER_GUIDE.md) - Complete feature guide
   - [MCP Tools Manual](MCP_TOOLS_MANUAL.md) - Available MCP tools

5. **Join Community**:
   - GitHub Discussions: Share experiences and ask questions
   - Issue Tracker: Report bugs or request features

---

**Last Updated**: October 5, 2025
**Version**: 2.0.0
**Maintained By**: Documentation Manager Agent