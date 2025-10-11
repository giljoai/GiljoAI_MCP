# GiljoAI MCP Installation Guide

**Version**: 3.0+
**Updated**: October 9, 2025

## Quick Start (All Platforms)

```bash
# Clone repository
git clone https://github.com/patrik-giljoai/GiljoAI-MCP.git
cd GiljoAI_MCP

# Single command installation and startup
python startup.py
```

That's it! The startup script will:
1. Check dependencies (Python, PostgreSQL, pip, npm)
2. Verify database connectivity
3. Detect if this is your first run
4. Launch setup wizard (first run) or dashboard (subsequent runs)
5. Start API and Frontend servers
6. Open browser automatically

---

## Prerequisites

### Required
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 18** - [Download](https://www.postgresql.org/download/)
- **pip** (usually included with Python)

### Optional
- **Node.js 18+** - [Download](https://nodejs.org/) (for frontend dashboard)
- **Git** - For cloning the repository

---

## Installation Methods

### Method 1: Direct Python (Recommended)

```bash
python startup.py
```

**First Run**:
- Opens setup wizard in browser
- Create admin account
- Configure MCP tools (optional)
- Enable Serena integration (optional)
- Database health check

**Subsequent Runs**:
- Starts API and Frontend servers
- Opens dashboard in browser

### Method 2: Platform-Specific Launchers

**Windows**:
```bash
start_giljo.bat
```

**Linux/macOS**:
```bash
./start_giljo.sh
```

These scripts automatically use your virtual environment if present, or fall back to system Python.

### Method 3: Legacy CLI Installer

```bash
python installer/cli/install.py
```

This still works for backward compatibility, but `startup.py` is now the recommended method.

---

## Command-Line Options

```bash
python startup.py --help          # Show all options
python startup.py --check-only    # Check dependencies only (no startup)
python startup.py --verbose       # Verbose output for debugging
```

---

## Troubleshooting

### PostgreSQL Not Found

**Error**: `PostgreSQL not found in system PATH`

**Solution**:
1. Install PostgreSQL 18 from https://www.postgresql.org/download/
2. Add to PATH (Windows):
   - Add `C:\Program Files\PostgreSQL\18\bin` to system PATH
   - Restart terminal

**Alternative**: The script checks common PostgreSQL installation paths automatically.

### Database Connection Failed

**Error**: `Database connection failed`

**Solutions**:
1. Verify PostgreSQL is running:
   ```bash
   # Windows
   services.msc  # Check "postgresql-x64-18" service

   # Linux
   sudo systemctl status postgresql
   ```

2. Check credentials in `.env` file:
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/giljo_mcp
   ```

3. Verify database exists:
   ```bash
   psql -U postgres -l
   ```

### Port Already in Use

**Error**: `Port 7272 is occupied`

**Solution**: The script automatically finds alternative ports. Or manually specify:
```yaml
# config.yaml
services:
  api:
    port: 7273  # Use different port
```

### Python Version Too Old

**Error**: `Python X.X detected, but 3.10+ is required`

**Solution**: Install Python 3.10 or newer from https://www.python.org/downloads/

---

## What Gets Installed

### Core Dependencies (22 packages)

Automatically installed from `requirements.txt`:
- FastAPI + Uvicorn (API framework)
- SQLAlchemy + Alembic (database)
- PostgreSQL drivers (psycopg2, asyncpg)
- Authentication (JWT, bcrypt, passlib)
- MCP SDK (Model Context Protocol)
- Core utilities (httpx, websockets, click, colorama)

### Optional Dependencies

Install only what you need from `optional-requirements.txt`:
```bash
# AI provider integrations
pip install openai anthropic google-generativeai

# Service integrations
pip install slack-sdk PyGithub jira

# Enhanced features
pip install rich aiohttp tiktoken
```

### Development Tools

For developers working on GiljoAI MCP:
```bash
pip install -r dev-requirements.txt
```

Includes: pytest, black, ruff, mypy, mkdocs

---

## Configuration

### First-Run Setup Wizard

The setup wizard (first run only) will guide you through:

1. **Admin Account Creation**
   - Username and password
   - Email (optional)

2. **Network Mode Selection**
   - Localhost: Single machine (default)
   - LAN: Team network access
   - WAN: Internet access (requires SSL)

3. **MCP Tool Configuration** (optional)
   - Claude Code integration
   - Codex CLI integration
   - Download configuration snippets

4. **Serena Integration** (optional)
   - Enable Serena MCP instructions

5. **Database Health Check**
   - Verify all systems operational

### Configuration Files

- **`config.yaml`** - Main configuration (auto-generated)
- **`.env`** - Database credentials (auto-generated)
- **`installer/cli/install.py`** - Legacy CLI installer

---

## Uninstallation

```bash
# Stop services
python startup.py  # Press Ctrl+C

# Remove virtual environment
rm -rf venv/

# Remove database (WARNING: destroys all data)
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# Remove installation directory
cd ..
rm -rf GiljoAI_MCP/
```

---

## Support

- **Documentation**: `docs/guides/STARTUP_SIMPLIFICATION.md`
- **Issues**: https://github.com/patrik-giljoai/GiljoAI-MCP/issues
- **Developer Guide**: `CLAUDE.md`

---

## Migration from v2.x

If upgrading from v2.x:

1. **Pull latest code**:
   ```bash
   git pull origin master
   ```

2. **Use new startup method**:
   ```bash
   python startup.py
   ```

3. **Old scripts deprecated** (but still work):
   - `install.bat` → Use `python startup.py`
   - `quickstart.sh` → Use `python startup.py`

See `docs/guides/STARTUP_SIMPLIFICATION.md` for complete migration guide.

---

**Installation Complete!** 🎉

Run `python startup.py` to launch GiljoAI MCP.
