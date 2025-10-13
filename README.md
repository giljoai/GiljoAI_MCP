# GiljoAI MCP Coding Orchestrator

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.0%2B-brightgreen)](https://vuejs.org/)
[![Security](https://img.shields.io/badge/Security-Scanned-success)](SECURITY.md)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Setup Time](https://img.shields.io/badge/Setup-5%20minutes-success)]()
[![Context](https://img.shields.io/badge/Context-Unlimited-orange)]()

**Break through AI context limits. Orchestrate teams of specialized AI agents.**

[**5-Minute Quick Start**](#5-minute-quick-start) | [**Features**](#key-features) | [**Architecture**](#architecture-overview) | [**Documentation**](#documentation)

</div>

---

## Quick Start

**NEW (v3.0+): Simplified Startup**

```bash
# Install and start GiljoAI MCP (one command for everything)
python startup.py
```

**What happens**:
- **First time**: Launches interactive setup wizard in your browser
- **Already configured**: Starts services and opens dashboard directly
- **No manual steps**: Everything is automatic

**That's it.** No complex installation. No platform-specific scripts. Just one command.

---

### Detailed Installation

For those who want to understand what's happening:

```bash
# 1. Clone and enter directory (30 seconds)
git clone https://github.com/patrik-giljoai/GiljoAI-MCP.git
cd GiljoAI_MCP

# 2. Run startup script (automatic first-run detection)
python startup.py

# First Run: Setup wizard opens in browser (v3.0)
# - Admin account creation (FIRST - required)
# - MCP tool integration (Claude Code, Cursor, Windsurf)
# - Serena enhancement (optional)
# - Database connectivity test (courtesy check)
# - Service startup

# Subsequent Runs: Dashboard opens directly
# - All services start automatically
# - Browser opens to dashboard
# - Ready to use immediately

# 3. Start orchestrating AI agents!
# ✨ Dashboard: http://localhost:7274
# ✨ API: http://localhost:7272
```

**Command-Line Options**:
```bash
python startup.py              # Auto-detect and run
python startup.py --setup      # Force setup wizard
python startup.py --dev        # Development mode (auto-reload)
python startup.py --no-browser # Skip browser auto-open
python startup.py --verbose    # Detailed logging
```

### What Just Happened?

`python startup.py` intelligently handles the entire process:

**First Run (Setup Mode)**:
1. **Environment Check**: Validates Python 3.10+, PostgreSQL 18, dependencies
2. **First-Run Detection**: Checks for admin user (none found = first run)
3. **Setup Wizard Launch**: Opens browser to http://localhost:7274/setup
4. **Interactive Configuration**: Guides you through all setup steps
5. **Service Startup**: Starts API and frontend automatically
6. **Dashboard Launch**: Opens to configured dashboard

**Subsequent Runs (Normal Mode)**:
1. **Environment Check**: Quick validation of prerequisites
2. **First-Run Detection**: Admin user found = skip setup wizard
3. **Service Startup**: Starts API (port 7272) and frontend (port 7274)
4. **Dashboard Launch**: Opens browser directly to dashboard
5. **Authentication**: Standard login required for all connections

**For complete details**, see [Startup Simplification Guide](docs/guides/STARTUP_SIMPLIFICATION.md)

### Architecture (v3.0)

GiljoAI MCP v3.0 uses a **unified architecture** with no deployment modes:

| Component      | Configuration                           | Access Control                        |
| -------------- | --------------------------------------- | ------------------------------------- |
| **API Server** | Always binds to `0.0.0.0` (all interfaces) | Controlled by OS firewall             |
| **Database**   | Always on `localhost` (never exposed)   | Local socket only (maximum security)  |
| **Auth**       | Always enabled                          | JWT authentication for all connections      |
| **Network**    | Firewall controls access                | Localhost-only by default, configurable for LAN/WAN |

**No deployment modes** - one codebase, all contexts. See [v3.0 Architecture](docs/VERIFICATION_OCT9.md) for details.

### Next Steps

```bash
# Watch your agents work
open http://localhost:7274

# Try a complex task
"Refactor my authentication system to use JWT tokens"

# See available MCP tools
python -m giljo_mcp tools

# Read the full documentation
python -m giljo_mcp docs
```

### Advanced Setup Options

```bash
# Force setup wizard (even if already configured)
python startup.py --setup

# Development mode with auto-reload
python startup.py --dev

# Headless installation (CI/CD, automated deployment)
python startup.py --config install_config.yaml --headless

# Custom ports
python startup.py --api-port 8000 --dashboard-port 8001

# Verbose logging for troubleshooting
python startup.py --verbose

# See all options
python startup.py --help
```

**Legacy Installation** (still supported):
```bash
# CLI installer (older method)
python installer/cli/install.py

# Platform-specific scripts
install.bat              # Windows
quickstart.sh            # Linux/macOS
```

### Linux Installer Package

```bash
# Dedicated Linux installer workflow
python Linux_Installer/linux_install.py
```

The `Linux_Installer/` directory mirrors the Windows installer flow with Linux-specific logic. It includes:
- `linux_install.py` – interactive CLI installer optimized for Linux environments
- `Linux_Installer/core/` – configuration and database setup modules reused by the installer
- `Linux_Installer/credentials/` and `Linux_Installer/scripts/` – runtime outputs (database credentials and elevated setup scripts)

Use this when you want a Linux-first installation experience without relying on the cross-platform bootstrapper.

[... rest of the README remains the same ...]
