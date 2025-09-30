# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system that transforms AI coding assistants into coordinated development teams. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks.

## Deployment Modes

The system supports two deployment modes:

1. **Local Development Mode**
   - SQLite database (zero configuration)
   - No authentication required
   - Localhost only (secure by default)
   - Up to 20 concurrent agents
   - Perfect for single developers

2. **Server Deployment Mode**
   - PostgreSQL or SQLite database
   - API key authentication
   - Network accessible (LAN/WAN)
   - Up to 20 concurrent agents
   - For teams or network access

## Development Commands

### Installation & Setup

```bash
# Quick start - automatic installer with GUI
python bootstrap.py              # Universal
quickstart.bat                   # Windows
./quickstart.sh                  # Mac/Linux

# Manual setup
pip install -r requirements.txt  # Install Python dependencies
python setup.py                  # Interactive setup
```

### Python Development

```bash
# Linting
ruff src/                        # Fast Python linter
ruff src/ --fix                  # Auto-fix linting issues

# Formatting
black src/                       # Format Python code
black src/ --check               # Check formatting without changes

# Type checking
mypy src/                        # Type check Python code

# Testing
pytest tests/                    # Run all tests
pytest tests/unit/               # Run unit tests only
pytest tests/integration/        # Run integration tests
pytest tests/ -m "not slow"      # Skip slow tests
pytest tests/ --cov=giljo_mcp    # Run with coverage
pytest -xvs tests/test_file.py   # Run specific test with verbose output
```

### Frontend Development

```bash
# Navigate to frontend directory first
cd frontend/

# Install dependencies
npm install

# Development server
npm run dev                      # Start dev server at http://localhost:5173

# Production build
npm run build                    # Build for production

# Linting & formatting
npm run lint                     # Lint Vue/JS code
npm run format                   # Format with Prettier
```

### API Development

```bash
# Start API server
python -m giljo_mcp              # Start MCP server
python api/run_api.py            # Start REST API (port 8000)

# Development mode with auto-reload
uvicorn api.app:app --reload --port 8000
```

### Docker Commands

```bash
# Development
docker-compose -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.prod.yml up -d

# Standard
docker-compose up -d
```

## High-Level Architecture

### Multi-Agent Orchestration System

The core innovation is breaking through AI context limits by coordinating multiple specialized agents:

```
User Request → Orchestrator → Multiple Specialized Agents → Coordinated Response
                    ↓
            Database (Persistent State)
                    ↓
            Message Queue (Agent Communication)
```

**Key Components:**

1. **Orchestrator** (`src/giljo_mcp/orchestrator.py`): Brain of the system that spawns and coordinates agents
2. **Message Queue** (`src/giljo_mcp/message_queue.py`): Database-backed queue for reliable agent communication
3. **Template Manager** (`src/giljo_mcp/template_manager.py`): Unified template system for agent missions
4. **Discovery System** (`src/giljo_mcp/discovery.py`): Dynamic codebase exploration
5. **WebSocket Manager** (`api/websocket.py`): Real-time communication layer

### Database Architecture

Multi-tenant system with complete isolation between projects:

- **SQLAlchemy ORM** with async support
- **SQLite** for local development (zero config)
- **PostgreSQL** for production (scale)
- **Tenant Isolation**: Each project has unique tenant_key
- **Product Isolation**: Multiple products per tenant

### API Layers

1. **MCP Protocol** (`src/giljo_mcp/server.py`): 20+ tools for agent operations
2. **REST API** (`api/app.py`): External integration endpoints
3. **WebSocket API** (`api/websocket.py`): Real-time updates

### Template System

Consolidated template management (Project 3.9.b achievement):
- Single source of truth in `template_manager.py`
- Database-backed with version history
- <0.08ms performance for template generation
- Runtime augmentation capabilities

## Project Structure

```
giljo_mcp/
├── src/giljo_mcp/         # Core orchestration engine
│   ├── orchestrator.py    # Main orchestrator
│   ├── message_queue.py   # Agent communication
│   ├── template_manager.py # Template system
│   ├── models.py          # Database models
│   └── tools/             # MCP tool implementations
├── api/                   # REST & WebSocket APIs
│   ├── app.py            # FastAPI application
│   ├── websocket.py      # WebSocket manager
│   └── endpoints/        # API endpoints
├── frontend/             # Vue 3 dashboard
│   ├── src/             # Vue source code
│   └── public/          # Static assets
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test fixtures
├── installer/          # Installation system
└── docs/              # Documentation
```

## Key Architectural Decisions

### Cross-Platform Path Handling

Always use `pathlib.Path` for OS-neutral paths:

```python
from pathlib import Path

# GOOD - Works on all platforms
config_dir = Path.home() / ".giljo-mcp"
config_file = config_dir / "config.yaml"

# BAD - Platform-specific
config_file = "~/.giljo-mcp/config.yaml"
```

### Database Session Management

Use async context managers for database operations:

```python
async with DatabaseManager() as db:
    async with db.session() as session:
        # Perform database operations
        await session.commit()
```

### Template Usage Pattern

Templates are database-backed and support runtime augmentation:

```python
from giljo_mcp.template_manager import TemplateManager

async with db.session() as session:
    tm = TemplateManager(session, tenant_key, product_id)
    mission = await tm.get_template(
        name="analyzer",
        augmentations="Focus on performance",
        variables={"target": "authentication"}
    )
```

### Message Queue Pattern

Reliable agent communication through database-backed queue:

```python
from giljo_mcp.message_queue import MessageQueue

queue = MessageQueue(session, tenant_key)
await queue.push({
    "from_agent": agent_id,
    "to_agent": target_id,
    "content": message_content
})
```

## Testing Strategy

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete workflows
- **Performance Tests**: Validate performance requirements

### Running Specific Test Categories

```bash
pytest tests/ -m unit           # Unit tests only
pytest tests/ -m integration    # Integration tests only
pytest tests/ -m e2e           # End-to-end tests only
pytest tests/ -m "not slow"    # Skip slow tests
```

### Key Test Files

- `tests/test_orchestrator.py`: Core orchestrator tests
- `tests/test_message_queue.py`: Message queue reliability
- `tests/test_template_system.py`: Template management
- `tests/test_websocket_integration.py`: WebSocket communication
- `tests/test_multi_tenant_comprehensive.py`: Tenant isolation

## Current Development Status

**Phase 3 Complete**: Orchestration Engine
- ✅ Template system consolidated (<0.08ms performance)
- ✅ Database-backed message queue
- ✅ Multi-tenant isolation
- ✅ 20+ MCP tools implemented
- ✅ WebSocket real-time updates

**Next Phase**: User Interface (Phase 4)
- Vue 3 dashboard implementation
- Real-time monitoring
- Visual orchestration control

## Important Coding Guidelines

- **No Emojis in Code**: Never use emojis in code unless specifically requested by the user or when the project has icon files to use as defaults
- **Professional Code**: Keep all code clean, professional, and emoji-free
- **File Creation**: Only create files when absolutely necessary; prefer editing existing files
- **Documentation**: Only create documentation files when explicitly requested
