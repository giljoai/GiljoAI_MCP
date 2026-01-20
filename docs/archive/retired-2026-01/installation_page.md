# GiljoAI MCP Server - Installation Page Content

**Purpose**: Reference content for the marketing/download website landing page

**Target Audience**: End users downloading from https://giljoai.com (or similar)

---

## Hero Section

```markdown
# GiljoAI MCP Server

**AI Agent Orchestration for Complex Software Development**

context prioritization and orchestration through intelligent multi-agent coordination

[Get Started Free]  [View Documentation]  [GitHub]
```

---

## Installation Section

### Simple One-Line Install

**Copy and paste one command to get started:**

**macOS / Linux**
```bash
curl -fsSL https://install.giljoai.com/install.sh | bash
```

**Windows (PowerShell)**
```powershell
irm https://install.giljoai.com/install.ps1 | iex
```

---

### What Happens During Installation?

The installation script will:

✓ **Check prerequisites** - Verifies Python 3.11+, PostgreSQL 14+, and Node.js 18+ are installed
✓ **Download latest release** - Gets the newest stable version from GitHub
✓ **Run setup wizard** - Interactive configuration for database and network settings
✓ **Configure database** - Sets up PostgreSQL with proper multi-tenant isolation
✓ **Build frontend** - Production-grade Vue.js dashboard with reliability checks
✓ **Create admin user** - Secure first-time user creation flow

**Installation takes approximately 2 minutes** on a fresh system with prerequisites installed.

---

## Prerequisites

Before installing GiljoAI MCP Server, ensure you have:

### 1. Python 3.11 or Higher

**Check if installed:**
```bash
python3 --version
```

**Install:**
- **macOS**: `brew install python@3.11`
- **Ubuntu**: `sudo apt install python3.11`
- **Windows**: [Download from python.org](https://www.python.org/downloads/)

### 2. PostgreSQL 14 or Higher

**Check if installed:**
```bash
psql --version
```

**Install:**
- **macOS**: `brew install postgresql@14`
- **Ubuntu**: `sudo apt install postgresql postgresql-contrib`
- **Windows**: [Download from postgresql.org](https://www.postgresql.org/download/windows/)

### 3. Node.js 18 or Higher

**Check if installed:**
```bash
node --version
```

**Install:**
- **macOS**: `brew install node@18`
- **Ubuntu**: [NodeSource Instructions](https://github.com/nodesource/distributions)
- **Windows**: [Download from nodejs.org](https://nodejs.org/)

**All prerequisites are free and take about 5 minutes to install.**

---

## Manual Installation (Advanced)

For developers or users who prefer manual control:

```bash
git clone https://github.com/patrik-giljoai/GiljoAI-MCP
cd GiljoAI-MCP
python install.py
```

Follow the interactive setup wizard to complete installation.

See [Installation Guide](https://github.com/patrik-giljoai/GiljoAI-MCP/blob/master/docs/INSTALLATION_FLOW_PROCESS.md) for detailed instructions.

---

## What's Included?

### Multi-Agent Orchestration
- **Project Orchestrators** - Manage entire software projects end-to-end
- **Specialized Agents** - Database experts, frontend testers, system architects, and more
- **Job Coordination** - Intelligent task distribution and workflow management

### Production Dashboard
- **Vue 3 + Vuetify** - Modern, responsive web interface
- **Real-time Updates** - WebSocket-powered live status monitoring
- **Multi-tenant Architecture** - Secure isolation for team collaboration

### MCP Integration
- **Claude Code** - Native MCP support
- **Codex CLI** - Native MCP support
- **Gemini CLI** - Native MCP support

### Database Management
- **PostgreSQL Backend** - Robust, production-grade data storage
- **Multi-tenant Isolation** - Zero cross-tenant data leakage
- **Automatic Migrations** - Schema updates handled seamlessly

---

## After Installation

### 1. Start the Server

```bash
cd ~/giljoai-mcp  # or C:\GiljoAI_MCP on Windows
python startup.py
```

### 2. Open Your Browser

Navigate to: **http://localhost:7272**

### 3. Complete Setup Wizard

Follow the web-based first-time setup:
- Create admin user
- Configure network settings (if needed for LAN/WAN access)
- Review security settings

### 4. Start Orchestrating

- Create your first product
- Define vision documents
- Launch project orchestrators
- Watch agents collaborate automatically

---

## System Requirements

**Minimum:**
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 2GB free space
- **OS**: Windows 10+, macOS 12+, Ubuntu 20.04+

**Recommended:**
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 10GB+ free space
- **Network**: Stable internet connection

---

## Deployment Options

### Local Development
Run on your laptop for personal projects and testing.

### LAN Access
Share with your team on the same network.

### WAN Access
Configure firewall and port forwarding for remote access.

**Security Note**: Authentication is always enabled. The first user is created during setup and has full admin privileges.

---

## Troubleshooting

### Installation Fails During Prerequisite Checks

**Problem**: Missing Python, PostgreSQL, or Node.js

**Solution**: Install the missing prerequisite (see links above) and re-run installation

---

### "Permission Denied" Error (macOS/Linux)

**Problem**: Script doesn't have execution permissions

**Solution**: The one-liner install handles this automatically. If running manually:
```bash
chmod +x install.sh
./install.sh
```

---

### PowerShell Execution Policy (Windows)

**Problem**: Script cannot run due to execution policy

**Solution**: Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then re-run the installation command.

---

### Database Connection Fails

**Problem**: Cannot connect to PostgreSQL

**Solution**: 
1. Verify PostgreSQL is running: `psql -U postgres -c "SELECT version();"`
2. Check PostgreSQL password (default: postgres)
3. Review installation logs: `cat ~/giljoai_install.log`

---

### Frontend Build Fails

**Problem**: npm installation errors during setup

**Solution**: Installation includes automatic retry logic. If persistent:
1. Check internet connection
2. Verify Node.js version: `node --version` (must be 18+)
3. Review logs: `cat logs/install_npm.log`

---

## Need Help?

**Documentation**: [Full Installation Guide](https://github.com/patrik-giljoai/GiljoAI-MCP/blob/master/docs/README_FIRST.md)

**Issues**: [GitHub Issues](https://github.com/patrik-giljoai/GiljoAI-MCP/issues)

**Support**: Contact via GitHub or [your support email]

---

## License

GiljoAI MCP Server is open-source software licensed under [LICENSE_TYPE].

---

## Privacy & Security

- **Local-First**: All data stored locally on your machine
- **No Telemetry**: Zero data collection or phone-home
- **Authentication Required**: Admin user creation mandatory
- **Multi-Tenant Isolation**: Enterprise-grade security boundaries

---

## Get Started Now

**macOS / Linux**:
```bash
curl -fsSL https://install.giljoai.com/install.sh | bash
```

**Windows**:
```powershell
irm https://install.giljoai.com/install.ps1 | iex
```

**Questions?** Check our [FAQ](https://github.com/patrik-giljoai/GiljoAI-MCP/blob/master/docs/FAQ.md) or [open an issue](https://github.com/patrik-giljoai/GiljoAI-MCP/issues).
