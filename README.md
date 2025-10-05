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

[... previous content remains the same until the "Install and Run" section ...]

### Install and Run

```bash
# 1. Clone and enter directory (30 seconds)
git clone https://github.com/patrik-giljoai/GiljoAI-MCP.git
cd GiljoAI_MCP

# 2. Run the CLI installer (3-5 minutes)
python install.py
# or on Windows:
install.bat

# The CLI installer will:
# ✅ Detect your system and requirements
# ✅ Install PostgreSQL 18 automatically (if needed)
# ✅ Create Python virtual environment
# ✅ Install all dependencies
# ✅ Configure database and services
# ✅ Start backend and frontend
# ✅ Open dashboard in browser

# 3. Complete setup wizard (3-5 minutes)
# After installer finishes, setup wizard opens automatically
# http://localhost:7274/setup
#
# The Setup Wizard guides you through:
# ✅ Database connection verification
# ✅ Deployment mode selection (Localhost/LAN/WAN)
# ✅ Admin account creation (if LAN/WAN)
# ✅ AI tool integration (Claude Code, Cline, Cursor)
# ✅ Firewall configuration (if LAN/WAN)
# ✅ Final system verification

# 4. Start using your AI orchestration team!
# ✨ Dashboard: http://localhost:7274
# ✨ API: http://localhost:7272
```

### What Just Happened?

**Phase 1 - CLI Installer**:
1. **System Detection**: Identified your OS and existing software
2. **PostgreSQL Setup**: Installed and configured PostgreSQL 18
3. **Environment Setup**: Created isolated Python environment with all dependencies
4. **Service Startup**: Started backend API and frontend dashboard

**Phase 2 - Setup Wizard**:
5. **Database Verified**: Tested and confirmed database connection
6. **Mode Configured**: Selected deployment mode for your use case
7. **Tools Integrated**: Connected your AI coding tools (Claude Code, etc.)
8. **System Ready**: All services verified and ready for use

### Installation Modes

Choose the mode that best fits your needs:

| Mode         | Best For                        | Database        | Auth      | Network            |
| ------------ | ------------------------------- | --------------- | --------- | ------------------ |
| **Localhost** | Individual development          | PostgreSQL 18   | None      | Localhost only     |
| **Server**   | Teams, LAN/WAN deployment       | PostgreSQL 18   | API Keys  | Network accessible |

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
# Server setup with PostgreSQL
python install.py --server

# Development mode with hot reload
python -m giljo_mcp dev
```

[... rest of the README remains the same ...]