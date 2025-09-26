# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system with complete standalone orchestration capabilities, built through 20 focused projects over 4 weeks. The system transforms AI coding assistants into coordinated development teams that can tackle projects of unlimited complexity.

## Installation System

### Phase 2 Complete: Advanced Installer with Dependency Management

```bash
# Single entry point for all platforms
python bootstrap.py
# OR platform-specific:
quickstart.bat        # Windows
./quickstart.sh       # Mac/Linux

# The installer now:
# ✅ Detects OS and GUI capability
# ✅ Launches profile-based installer (GUI or CLI)
# ✅ Actually installs dependencies (PostgreSQL, Redis, Docker)
# ✅ Creates and manages OS services
# ✅ Configures applications based on selected profile
# ✅ Validates health and provides service controls
```

### Installation Profiles Available

- **Developer Profile**: SQLite, local Redis, single-machine setup
- **Team Profile**: PostgreSQL, network-accessible, multi-user
- **Enterprise Profile**: Production-grade PostgreSQL, clustering-ready
- **Research Profile**: Flexible configuration for experimentation

## Development Commands

### GiljoAI MCP Server (Orchestrator)

The project has its own MCP server implementation configured in `.mcp.json`:

```bash
# GiljoAI MCP server runs via MCP protocol
# Active product: GiljoAI-MCP Coding Orchestrator
```

### Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (when implemented)
pytest tests/

# Code formatting
black src/

# Linting
ruff src/
```

## Architecture

### System Design

- **Local-First Philosophy**: SQLite for local development, PostgreSQL for scale
- **Multi-Tenant Architecture**: Project isolation via unique tenant keys
- **Progressive Enhancement**: Same codebase scales from laptop to cloud
- **OS-Neutral Code**: All paths use `pathlib.Path()`, never hardcoded separators

### Core Components

1. **API Layer**: MCP Protocol, REST API, WebSocket, Authentication
2. **Orchestration Core**: Project Manager, Agent Spawner, Message Router
3. **Data Layer**: SQLAlchemy ORM with SQLite/PostgreSQL support

### Deployment Modes

- **Local Mode**: SQLite, localhost only, zero configuration
- **LAN Mode**: PostgreSQL, API key auth, network accessible
- **WAN Mode**: PostgreSQL, OAuth/TLS, internet accessible

## Project Structure

```
giljo_mcp/
├── docs/              # All documentation
│   ├── Vision/        # Vision documents (highest priority)
│   ├── Sessions/      # Development session memories
│   └── devlog/        # Development logs
├── frontend/          # Vue 3 dashboard
│   └── public/        # Contains icons, mascot, favicon (PROVIDED)
├── src/               # Core application (to be created)
├── api/               # REST & WebSocket APIs (to be created)
├── tests/             # Test suite (to be created)
├── scripts/           # Setup utilities (to be created)
└── docker/            # Container definitions (to be created)
```

## Development Approach

### Current Phase: Foundation (Week 1)

Building using 20 orchestrated projects across 5 phases:

- Phase 1: Foundation & Database
- Phase 2: MCP Integration
- Phase 3: Orchestration Engine
- Phase 4: User Interface
- Phase 5: Deployment & Polish

### Key Features Implemented

- Vision document chunking (50K+ tokens)
- Message acknowledgment arrays
- Dynamic discovery via Serena MCP
- Database-first message queue
- Orchestrator mission templates (now database-backed via template_manager.py)

### UI Requirements

- Vue 3 + Vite with Vuetify 3
- Use color themes in `docs/color_themes.md`
- Use provided assets in `frontend/public/`
- Support dark/light mode
- WCAG 2.1 AA compliant

## Cross-Platform Requirements

Always use OS-neutral code:

```python
from pathlib import Path

# Good - OS neutral
config_dir = Path.home() / ".giljo-mcp"
config_file = config_dir / "config.yaml"

# Bad - OS specific
config_file = "~/.giljo-mcp/config.yaml"  # Unix only
```

## Database Schema

Core entities: Project, Agent, Message, Task, Session, Vision, Configuration, AgentTemplate, TemplateArchive

- Projects have unique tenant keys for isolation
- Agents belong to projects with specific roles
- Messages enable inter-agent communication
- Tasks track work items across sessions
- AgentTemplates provide database-backed mission templates with multi-tenant isolation
- TemplateArchives maintain version history for rollback capability

## Dependencies

Key packages (see requirements.txt):

- **fastmcp**: MCP server framework
- **fastapi**: REST API and WebSockets
- **sqlalchemy**: ORM with async support
- **httpx**: HTTP client for API calls
- **websockets**: WebSocket client support
- **pyyaml**: YAML configuration

## Template Management System

### Overview

Project 3.9.b consolidated three overlapping template systems into one unified solution:

- **Single Source**: `src/giljo_mcp/template_manager.py`
- **Database Storage**: SQLAlchemy models (AgentTemplate, TemplateArchive, etc.)
- **9 MCP Tools**: Complete template CRUD operations
- **Performance**: <0.08ms generation (exceeds <0.1ms requirement)

### Using Templates

```python
from giljo_mcp.template_manager import TemplateManager

# Get template with runtime augmentation
tm = TemplateManager(session, tenant_key, product_id)
mission = await tm.get_template(
    name="analyzer",
    augmentations="Focus on security",
    variables={"project_name": "GiljoAI"}
)
```

### Migration from Legacy

For backward compatibility during transition:

```python
from giljo_mcp.template_adapter import TemplateAdapter
adapter = TemplateAdapter(session, tenant_key, product_id)
# Use same interface as old mission_templates.py
```

See `docs/guides/template_migration.md` for complete migration guide.

## Testing Approach

When tests are implemented:

- Unit tests: `pytest tests/`
- Integration tests: `pytest tests/integration/`
- Template tests: `pytest tests/test_template_system.py`
- Always verify OS compatibility across Windows, Mac, Linux
