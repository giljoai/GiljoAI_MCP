# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Test Environment Workflow

**THIS IS A TEST INSTALLATION FOLDER, NOT THE DEV REPOSITORY**

You are currently working in: `C:\install_test\Giljo_MCP`

This is an isolated test environment that simulates a real product installation (release variant). While we develop and fix issues here, all code changes must be synchronized back to the main development repository.

### Development Workflow (MANDATORY)

1. **Work in Test Folder** (`C:\install_test\Giljo_MCP`)
   - Make code changes to core files (src/, api/, installer/, frontend/, tests/, etc.)
   - Test in real deployment environment
   - Verify everything works
   - Do NOT modify environment-specific files (.env, config.yaml) in the dev repo

2. **Push Changes to Dev Repo** (After testing)
   ```bash
   cd C:\install_test\Giljo_MCP

   # Preview changes before copying
   python push_to_dev.py --dry-run

   # Copy all code changes (excludes .env, config.yaml, data/, logs/, etc.)
   python push_to_dev.py

   # Copy specific file if needed
   python push_to_dev.py --file api/app.py
   ```

3. **Commit from Dev Repo**
   ```bash
   cd C:\Projects\GiljoAI_MCP
   git status
   git add .
   git commit -m "Fix: [description]"
   git push
   ```

### Backup & Maintenance

**Project Backup:**
```bash
cd C:\Projects\GiljoAI_MCP

# Create timestamped backup (excludes venv, node_modules, caches)
python backup.py              # Interactive mode
python backup.py --quick      # Exclude logs, data, temp files (smaller backup)
python backup.py --no-git     # Exclude .git directory
python backup.py --auto       # Skip confirmation prompts
```

Backups are saved to: `C:\Projects\Backups\[YYYY-MM-DD_HH-MM-SS]_Backup\`

**Clear Python Cache:**
```bash
# Safe to run periodically - Python regenerates automatically
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### Important Notes

- **Test folder**: `C:\install_test\Giljo_MCP` - Isolated test environment with its own .env and config.yaml
- **Dev repo**: `C:\Projects\GiljoAI_MCP` - Git repository, contains project history and additional knowledge
- **Symlinked folders**: The following folders are symlinked to the dev repo (DO NOT modify these - they are shared resources):
  - `/docs/` → `C:\Projects\GiljoAI_MCP\docs` - Documentation, manuals, devlogs, session memories
  - `/scripts/` → `C:\Projects\GiljoAI_MCP\scripts` - Utility scripts and automation tools
  - `/examples/` → `C:\Projects\GiljoAI_MCP\examples` - Example configurations and use cases
- **Files to sync**: All code directories (src/, api/, installer/, frontend/, tests/) and script files
- **Files to exclude**: .env, config.yaml, data/, logs/, uploads/, temp/, venv/, node_modules/

**ALWAYS use `push_to_dev.py` to sync changes before committing to git.**

## Project Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system that transforms AI coding assistants into coordinated development teams. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks.

## Deployment Modes

The system supports two deployment configurations:

1. **Localhost Mode**
   - PostgreSQL 18 database with local configuration
   - Preconfigured development credentials
   - Localhost access only
   - Up to 20 concurrent agents
   - Ideal for individual developers and testing

2. **Server Mode**
   - PostgreSQL 18 database with secure network configuration
   - API key authentication
   - Full network accessibility (LAN/WAN)
   - Up to 20 concurrent agents per deployment
   - Scalable architecture
   - Designed for team environments

## Development Commands

### Installation & Setup

```bash
# CLI installer - single command
python installer/cli/install.py       # Universal installer for all platforms

# Manual setup
pip install -r requirements.txt  # Install Python dependencies
python installer/cli/install.py  # Interactive CLI setup
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
python api/run_api.py            # Start REST API (auto-detects port from config.yaml)

# Development mode with auto-reload
python api/run_api.py --reload --log-level debug

# Specify custom port
python api/run_api.py --port 7272
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

### Database Access

#### PostgreSQL 18 Connection

**Development Password**: `4010`

```bash
# Windows - Access PostgreSQL via psql
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l

# List all databases
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "\l"

# Connect to giljo_mcp database
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp

# Check if giljo_mcp database exists
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l | grep giljo

# Drop database (for testing)
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
```

## Architecture Overview

### Core Components

1. **Orchestrator** (`src/giljo_mcp/orchestrator.py`)
   - Central orchestration engine managing project lifecycle
   - Agent spawning with role templates
   - Intelligent handoff mechanism
   - Context usage tracking
   - Multi-project support with tenant isolation

2. **Database Layer** (`src/giljo_mcp/database.py`)
   - PostgreSQL-only architecture (required for all modes)
   - Connection pooling via SQLAlchemy
   - Multi-tenant isolation through filtered queries
   - Async and sync session support

3. **MCP Tools** (`src/giljo_mcp/tools/`)
   - 20+ MCP tools for agent coordination
   - Project management (`project.py`)
   - Agent management (`agent.py`)
   - Message passing (`message.py`)
   - Task management (`task.py`, `task_templates.py`)
   - Context management (`context.py`, `chunking.py`)
   - Template management (`template.py`)
   - Git integration (`git.py`)

4. **API Layer** (`api/`)
   - FastAPI application (`app.py`)
   - REST endpoints for all resources
   - WebSocket support for real-time updates
   - API key authentication for server mode

5. **Frontend** (`frontend/`)
   - Vue 3 + Vuetify dashboard
   - Real-time agent monitoring
   - Project and task management UI
   - WebSocket integration for live updates

### Key Architectural Patterns

- **Multi-tenant isolation**: All database queries filtered by `tenant_key`
- **Template system**: Unified database-backed templates (`template_manager.py`) replacing legacy file-based system (`mission_templates.py` - deprecated)
- **Message queue**: Priority-based inter-agent messaging
- **Context chunking**: Vision document chunking for large files
- **Progressive enhancement**: Features activate based on deployment mode

## Configuration

### Config File Structure

Configuration is stored in `config.yaml` at the project root:

```yaml
installation:
  mode: localhost  # or 'server'

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user

services:
  api:
    host: 127.0.0.1
    port: 7272  # Auto-detected by PortManager
  frontend:
    port: 7274
```

### Port Management

The system uses centralized port management via `PortManager` (`src/giljo_mcp/port_manager.py`):

- API server auto-detects available ports from config.yaml
- Falls back to environment variables (`GILJO_PORT`, `GILJO_API_PORT`)
- Ultimate fallback: 7272

## Important Coding Guidelines

- **No Emojis in Code**: Never use emojis in code unless specifically requested by the user
- **Professional Code**: Keep all code clean, professional, and emoji-free
- **File Creation**: Only create files when absolutely necessary; prefer editing existing files
- **Documentation**: Only create documentation files when explicitly requested
- **Cross-Platform**: All paths must use `pathlib.Path()`, never hardcoded separators
- **Database**: PostgreSQL is required - no SQLite support
- **Template System**: Use `template_manager.py` (new) not `mission_templates.py` (deprecated)

## Testing Strategy

### Test Organization

- **Unit tests**: `tests/unit/` - Test individual components
- **Integration tests**: `tests/integration/` - Test component interactions
- **Performance tests**: `tests/performance/` - Load and stress testing

### Running Tests

```bash
# All tests
pytest tests/

# Specific test markers
pytest tests/ -m unit           # Unit tests only
pytest tests/ -m integration    # Integration tests only
pytest tests/ -m "not slow"     # Skip slow tests

# With coverage
pytest tests/ --cov=giljo_mcp --cov-report=html
```

## Common Development Tasks

### Adding a New MCP Tool

1. Create tool file in `src/giljo_mcp/tools/`
2. Implement tool function with proper decorators
3. Register in `src/giljo_mcp/tools/__init__.py`
4. Add tests in `tests/unit/test_tools_*.py`
5. Update `docs/manuals/MCP_TOOLS_MANUAL.md`

### Adding a New API Endpoint

1. Create endpoint in `api/endpoints/` directory
2. Import and include router in `api/app.py`
3. Add request/response models using Pydantic
4. Implement database operations in endpoint
5. Add integration tests in `tests/integration/`

### Modifying Database Schema

1. Update models in `src/giljo_mcp/models.py`
2. Create Alembic migration: `alembic revision --autogenerate -m "description"`
3. Review and edit migration file
4. Test migration: `alembic upgrade head`
5. Update relevant API endpoints and tools

## Documentation Structure

All documentation is symlinked from the dev repo at `C:\Projects\GiljoAI_MCP\docs`:

- **`docs/README_FIRST.md`** - Project index and navigation
- **`docs/TECHNICAL_ARCHITECTURE.md`** - System architecture
- **`docs/manuals/`** - Reference manuals for MCP tools and testing
- **`docs/devlog/`** - Development logs and completion reports
- **`docs/sessions/`** - Agent session memories

## Available Resources (Symlinked from Dev Repo)

### Documentation (`docs/`)
Complete documentation is available via symlink to the dev repo. Use these resources for reference:
- Architecture documentation and technical specifications
- MCP tools manual and API reference
- Development logs (`docs/devlog/`) tracking project evolution
- Session memories (`docs/sessions/`) from previous agent interactions

### Scripts (`scripts/`)
Utility scripts and automation tools available via symlink:
- Database management scripts
- Deployment automation
- Testing utilities
- Migration helpers

### Examples (`examples/`)
Reference implementations and sample configurations:
- Example project setups
- Configuration templates
- Use case demonstrations

**Note**: These symlinked folders are shared with the dev repo. Changes made here will affect the dev repo directly.

## Sub-Agent Architecture (Claude Code Integration)

GiljoAI-MCP serves as the **persistent brain** while Claude Code provides the **execution engine**:

- **Before**: Complex multi-terminal orchestration
- **After**: Elegant sub-agent delegation
- **Result**: 70% token reduction, 95% reliability, 30% less code

The orchestrator manages state, memory, and coordination, while Claude Code spawns specialized sub-agents for execution.

## Service Management

### Windows

```bash
# Start services
start_giljo.bat              # Start API + Frontend
start_backend.bat            # API only
start_frontend.bat           # Frontend only

# Stop services
stop_giljo.bat               # Stop all
```

### Cross-Platform

```bash
# Python launcher
python start_giljo.py        # Start all services
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check credentials in config.yaml
- Test connection: `psql -U postgres -l`

### Port Conflicts

- Check `config.yaml` for port settings
- Use `--port` flag to override: `python api/run_api.py --port 7272`
- PortManager will auto-select alternative ports

### Frontend Build Issues

```bash
cd frontend/
rm -rf node_modules/
npm install
npm run build
```
