# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system being built using AKE-MCP server to orchestrate its own development through 20 focused projects over 4 weeks. The system transforms AI coding assistants into coordinated development teams that can tackle projects of unlimited complexity.

## Development Commands

### AKE-MCP Server (Orchestrator)
The project uses AKE-MCP server configured in `.mcp.json` for orchestration:
```bash
# AKE-MCP is already configured and runs via MCP protocol
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

### Key Features to Preserve from AKE-MCP
- Vision document chunking (50K+ tokens)
- Message acknowledgment arrays
- Dynamic discovery via Serena MCP
- Database-first message queue
- Orchestrator mission templates

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

Core entities: Project, Agent, Message, Task, Session, Vision, Configuration
- Projects have unique tenant keys for isolation
- Agents belong to projects with specific roles
- Messages enable inter-agent communication
- Tasks track work items across sessions

## Dependencies

Key packages (see requirements.txt):
- **fastmcp**: MCP server framework
- **fastapi**: REST API and WebSockets
- **sqlalchemy**: ORM with async support
- **httpx**: HTTP client for API calls
- **websockets**: WebSocket client support
- **pyyaml**: YAML configuration

## Testing Approach

When tests are implemented:
- Unit tests: `pytest tests/`
- Integration tests: `pytest tests/integration/`
- Always verify OS compatibility across Windows, Mac, Linux