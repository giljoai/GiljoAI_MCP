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

# 2. Run the CLI installer (3 minutes)
python install.py

# The installer will:
# ✅ Guide you through installation mode selection (localhost or server)
# ✅ Install PostgreSQL automatically (if needed)
# ✅ Create and configure all services
# ✅ Validate everything is working

# 3. Start using your AI orchestration team (30 seconds)
# Services are automatically started by the installer
# ✨ Dashboard available at http://localhost:6000
# ✨ API available at http://localhost:8000
```

### What Just Happened?

1. **Mode Selection**: You chose your installation mode (localhost or server)
2. **Dependency Installation**: PostgreSQL was automatically installed and configured
3. **Service Creation**: All services were registered with your OS and started
4. **Health Validation**: The installer verified everything is working correctly
5. **Ready to Use**: Your AI orchestration system is running and ready for tasks

### Installation Modes

Choose the mode that best fits your needs:

| Mode         | Best For                        | Database        | Auth      | Network            |
| ------------ | ------------------------------- | --------------- | --------- | ------------------ |
| **Localhost** | Individual development          | PostgreSQL 18   | None      | Localhost only     |
| **Server**   | Teams, LAN/WAN deployment       | PostgreSQL 18   | API Keys  | Network accessible |

### Next Steps

```bash
# Watch your agents work
open http://localhost:6000

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