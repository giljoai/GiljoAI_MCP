# AGENT INSTRUCTIONS - Critical Information for All Development Agents

## ⚠️ PORT CONFIGURATION

**CRITICAL**: GiljoAI MCP runs independently. Use these ports:

### Reserved Ports (Legacy Compatibility):

- **5000** - Reserved
- **5001** - Reserved
- **5002** - Reserved
- **5432** - PostgreSQL (SHARED - OK to use)

### GiljoAI MCP Port Assignments (USE THESE):

- **6000** - GiljoAI Dashboard
- **6001** - GiljoAI MCP Server (FastMCP)
- **6002** - GiljoAI REST API
- **6003** - GiljoAI WebSocket
- **5173** - Vite Dev Server (Vue dashboard)

### Configuration Files:

- Port settings: `/config.yaml`
- Environment overrides: `.env` (copy from `.env.example`)
- Check conflicts: `python scripts/check_ports.py`

## 📂 PROJECT STRUCTURE

```
F:\GiljoAI_MCP\
├── config.yaml              # ✅ CREATED - Port configuration
├── .env.example            # ✅ CREATED - Environment template
├── scripts/
│   └── check_ports.py      # ✅ CREATED - Port conflict checker
├── docs/
│   ├── Vision/             # Vision documents (READ FIRST)
│   ├── Sessions/           # Development memories
│   ├── PROJECT_CARDS.md   # Project missions
│   └── color_themes.md    # MANDATORY UI colors
├── frontend/public/        # ✅ PROVIDED assets
│   ├── favicon.ico
│   ├── icons/
│   └── mascot/
└── venv/                   # ✅ CREATED - Virtual environment with Serena
```

## 🔧 DEVELOPMENT ENVIRONMENT

### Python Environment:

- Virtual environment: `F:\GiljoAI_MCP\venv\`
- Python version: 3.11
- Serena MCP: Installed locally (isolated to this project)

### Key Dependencies Installed:

- serena-agent (for codebase discovery)
- fastmcp (for MCP server)
- sqlalchemy (for ORM)
- pydantic (for validation)
- All in `venv\` - use `./venv/Scripts/python.exe`

## 🎯 CRITICAL REQUIREMENTS

### 1. OS-Neutral Code (MANDATORY)

```python
# GOOD - OS neutral
from pathlib import Path
config_dir = Path.home() / ".giljo-mcp"

# BAD - OS specific
config_dir = "~/.giljo-mcp"  # Unix only
```

### 2. Multi-Tenant Architecture

- EVERY table must have `tenant_key` field
- ALL queries must filter by tenant_key
- NO single-product limitations
- Support unlimited concurrent products

### 3. Database Design

- Dual support: SQLite (local) AND PostgreSQL (production)
- Use SQLAlchemy ORM for abstraction
- Connection pooling required
- Migration support with Alembic

### 4. UI/UX Requirements

- **MUST use `/docs/color_themes.md` colors**
- Vue 3 + Vuetify 3 (not React)
- Dark/light mode with smooth transitions
- Use provided assets in `/frontend/public/`
- WCAG 2.1 AA accessibility

### 5. Core Features Implemented

- Vision document chunking (50K+ tokens)
- Message acknowledgment arrays (PostgreSQL)
- Dynamic discovery (no static indexing)
- Database-first message queue
- Serena MCP integration

## 📋 PROJECT PHASES

Refer to `/docs/PROJECT_CARDS.md` for detailed missions:

1. **Foundation (Projects 1-4)**: Database, multi-tenant, config, auth
2. **MCP Tools (Projects 5-8)**: Vision chunking, messaging, handoff, discovery
3. **Orchestration (Projects 9-12)**: Engine, lifecycle, mission templates, health
4. **UI/Dashboard (Projects 13-16)**: REST API, Vue dashboard, WebSocket, charts
5. **Deployment (Projects 17-20)**: Setup, Docker, testing, documentation

## 🚨 COMMON PITFALLS TO AVOID

1. **Port Conflicts**: Always use 6000-6003 range, not 5000-5002
2. **Path Separators**: Use pathlib.Path(), never hardcode / or \
3. **Single Tenant**: Design for multi-tenant from start
4. **Static Indexing**: Use dynamic discovery instead
5. **Creating New Icons**: Use provided assets in `/frontend/public/`

## 📝 WHEN STARTING A NEW PROJECT

1. Read the mission from `/docs/PROJECT_CARDS.md`
2. Check dependencies in `/docs/PROJECT_FLOW_VISUAL.md`
3. Review this file for port/config requirements
4. Use virtual environment: `./venv/Scripts/python.exe`
5. Test with: `python scripts/check_ports.py`
6. Follow OS-neutral coding patterns
7. Include tenant_key in all database operations

## 🔄 TESTING YOUR WORK

```bash
# Check for port conflicts
./venv/Scripts/python.exe scripts/check_ports.py

# Run your service (example)
./venv/Scripts/python.exe src/giljo_mcp/server.py

# Dashboard will be at:
http://localhost:6000  # NOT 5000!

# API will be at:
http://localhost:6002  # NOT 5001!
```

## 📞 QUICK REFERENCE

- **GiljoAI Dashboard**: http://localhost:6000
- **Config**: `/config.yaml` and `.env`
- **Port Checker**: `scripts/check_ports.py`
- **Virtual Env**: `./venv/Scripts/python.exe`
- **Project Missions**: `/docs/PROJECT_CARDS.md`
- **UI Colors**: `/docs/color_themes.md`

---

**REMEMBER**: GiljoAI MCP is now fully independent with its own orchestration capabilities.
