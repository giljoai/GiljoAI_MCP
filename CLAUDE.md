# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<<<<<<< HEAD
## CRITICAL: Multi-Environment Development Setup

**IMPORTANT**: This project is developed across multiple systems with different paths and configurations:

- **System 1 (Dev/Localhost)**: `C:\Projects\GiljoAI_MCP` - Primary development, localhost mode
- **System 2 (Test/Server)**: `F:\GiljoAI_MCP` - LAN/server mode testing
- **Both systems**: Use same GitHub repo, different environment configs

### Environment-Specific Files (NEVER COMMIT)

The following files are **machine-specific** and ignored by git:
- `.env` - Database credentials, API keys, environment variables
- `config.yaml` - Installation paths, ports, mode (localhost vs server)
- `install_config.yaml` - User installation preferences
- `data/` - Runtime database files
- `logs/` - Application logs
- `uploads/` - User-uploaded files

**Template files** (committed to git):
- `.env.example` - Used by installer as template
- `config.yaml.example` - Used by installer as template
- These are referenced during installation, not for development

### Cross-Platform & Path Flexibility Rules

**ALWAYS follow these coding standards:**

1. **Use `pathlib.Path()` for ALL file paths** - Never hardcode separators
   ```python
   # ✅ CORRECT
   config_path = Path.cwd() / "config.yaml"
   install_dir = Path(settings.get('install_dir', Path.cwd()))

   # ❌ WRONG
   config_path = "C:\\Projects\\config.yaml"
   config_path = install_dir + "/config.yaml"
   ```

2. **Auto-detect paths dynamically** - Never hardcode absolute paths
   ```python
   # ✅ CORRECT
   install_dir = Path.cwd()  # Current working directory
   install_dir = Path(__file__).parent  # Relative to script

   # ❌ WRONG
   install_dir = "C:\\Projects\\GiljoAI_MCP"
   ```

3. **Read from config.yaml or .env** - Let installer handle paths
   ```python
   # ✅ CORRECT
   with open("config.yaml") as f:
       config = yaml.safe_load(f)
       db_path = Path(config['database']['path'])

   # ❌ WRONG
   db_path = "C:\\Projects\\data\\giljo_mcp.db"
   ```

4. **OS-specific logic using platform.system()**
   ```python
   # ✅ CORRECT
   if platform.system() == "Windows":
       launcher = "start_giljo.bat"
   else:
       launcher = "start_giljo.sh"
   ```

### Development Workflow Across Multiple Systems

1. **On System 1 (C:\Projects\GiljoAI_MCP)**
   - Make code changes to core files (src/, api/, installer/, frontend/, tests/)
   - Test in localhost mode
   - Commit and push to GitHub
   ```bash
   git add .
   git commit -m "Feature: description"
   git push
   ```

2. **On System 2 (F:\GiljoAI_MCP)**
   - Pull latest changes from GitHub
   - Test in server/LAN mode
   - Make additional fixes if needed
   - Commit and push back
   ```bash
   git pull
   # Test and make changes
   git add .
   git commit -m "Fix: description"
   git push
   ```

3. **What Gets Synced vs What Doesn't**
   - ✅ **Code files**: All Python, JS, batch/shell scripts sync via git
   - ✅ **Templates**: `.example` files sync (installer uses them)
   - ❌ **Environment configs**: `.env` and `config.yaml` stay local (gitignored)
   - ❌ **Runtime data**: `data/`, `logs/`, `uploads/` stay local

4. **After Each Pull**
   - Your local `.env` and `config.yaml` remain unchanged
   - No need to reconfigure - paths stay machine-specific
   - Just test that new code works with your local config

### Backup & Maintenance

**Project Backup:**
=======
## CRITICAL: Multi-System Development Workflow

**GiljoAI MCP Development Environment Strategy**

We use a **multi-system development workflow** to test different deployment modes simultaneously:

### Development Systems

**System 1 - C: Drive (Windows - Localhost Mode)**
- **Location**: `C:\Projects\GiljoAI_MCP`
- **Purpose**: Development and localhost mode testing
- **Mode**: `localhost` in config.yaml
- **Database**: PostgreSQL on localhost
- **Binding**: API binds to `127.0.0.1` (localhost only)
- **Auth**: No API key required
- **Use Case**: Individual developer, rapid iteration, testing

**System 2 - F: Drive (Windows - Server/LAN Mode)**
- **Location**: `F:\GiljoAI_MCP`
- **Purpose**: LAN/server mode testing and multi-client scenarios
- **Mode**: `server` in config.yaml
- **Database**: PostgreSQL on localhost (security: database always localhost-only)
- **Binding**: API binds to `0.0.0.0` (network accessible)
- **Auth**: API key required
- **Use Case**: Team deployment testing, network access validation

### Git Workflow (MANDATORY)

**Both systems use the SAME GitHub repository**

>>>>>>> 08da038e5ba14362276cf990e0ad7f6712dc1818
```bash
# Always pull before starting work
git pull

# Work on code (any system)
# Make changes to src/, api/, installer/, frontend/, tests/

# Commit from whichever system you're on
git add .
git commit -m "feat: [description]"
git push

# Other system pulls the changes
git pull
```

### Environment-Specific Files (NEVER COMMIT)

These files are **gitignored** and stay local to each system:

- `.env` - Environment variables (database credentials, ports, API keys)
- `config.yaml` - System-specific configuration (mode, paths, ports)
- `install_config.yaml` - User-generated installer config (via --generate-config)
- `data/` - Database data and uploads
- `logs/` - Application logs
- `temp/` - Temporary files
- `venv/` - Python virtual environment
- `node_modules/` - NPM dependencies

### Code Syncs Automatically

These files/folders **DO sync via git** to both systems:

- `src/` - Core application code
- `api/` - API endpoints and middleware
- `installer/` - Installation scripts
- `frontend/` - Vue.js dashboard
- `tests/` - Test suites
- `scripts/` - Utility scripts
- `docs/` - Documentation
- `examples/` - Example configurations

### Cross-Platform Coding Standards

**CRITICAL**: All code must work on both systems (and Linux/macOS):

```python
# ✅ CORRECT - Cross-platform
from pathlib import Path
data_dir = Path.cwd() / 'data'
log_file = Path('logs') / 'app.log'

# ❌ WRONG - Windows-specific
data_dir = 'C:\\Projects\\data'
log_file = 'C:/logs/app.log'
```

**Always use:**
- `pathlib.Path()` for all file paths
- `Path.cwd()` for current directory
- Relative paths in config files (`./data`, not `C:/Projects/data`)
- Config-driven differences (mode: localhost vs server)

## Project Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system that transforms AI coding assistants into coordinated development teams. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks.

## Deployment Modes

The system supports two deployment configurations:

1. **Localhost Mode** (System 1 - C: Drive)
   - PostgreSQL 18 database with local configuration
   - Preconfigured development credentials
   - Localhost access only (127.0.0.1)
   - No API key authentication
   - Up to 20 concurrent agents
   - Ideal for individual developers and testing

2. **Server Mode** (System 2 - F: Drive, or production)
   - PostgreSQL 18 database with secure network configuration
   - API key authentication required
   - Full network accessibility (LAN/WAN)
   - Binds to 0.0.0.0 (all interfaces)
   - Up to 20 concurrent agents per deployment
   - Scalable architecture
   - Designed for team environments

## Development Commands

### Installation & Setup

```bash
# CLI installer - single command
python installer/cli/install.py       # Universal installer for all platforms

# Generate config file for automated install
python installer/cli/install.py --generate-config install_config.yaml
python installer/cli/install.py --config install_config.yaml

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
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l

# List all databases
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "\l"

# Connect to giljo_mcp database
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp

# Check if giljo_mcp database exists
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -l | grep giljo

# Drop database (for testing)
PGPASSWORD=4010 "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"
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
  mode: localhost  # or 'server' for LAN/network deployment

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user

services:
  api:
    host: 127.0.0.1  # localhost mode: 127.0.0.1, server mode: 0.0.0.0
    port: 7272       # Auto-detected by PortManager
  frontend:
    port: 7274

security:
  cors:
    allowed_origins:
      - http://127.0.0.1:7274
      - http://localhost:7274
      # Add specific LAN IPs for server mode
  api_keys:
    require_for_modes:
      - server
      - lan
      - wan
  rate_limiting:
    enabled: true
    requests_per_minute: 60
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
- **Cross-Platform**: All paths must use `pathlib.Path()`, never hardcoded separators or drive letters
- **Database**: PostgreSQL is required - no SQLite support
- **Template System**: Use `template_manager.py` (new) not `mission_templates.py` (deprecated)
- **Mode-Aware Code**: Use `config.yaml` mode setting for localhost vs server behavior
- **Never Hardcode Paths**: Use `Path.cwd()`, `Path('relative/path')`, config-driven paths

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

- **`docs/README_FIRST.md`** - Project index and navigation
- **`docs/TECHNICAL_ARCHITECTURE.md`** - System architecture
- **`docs/manuals/`** - Reference manuals for MCP tools and testing
- **`docs/devlog/`** - Development logs and completion reports
- **`docs/sessions/`** - Agent session memories
- **`docs/deployment/`** - LAN/WAN deployment guides and checklists

## Available Resources

### Documentation (`docs/`)
- Architecture documentation and technical specifications
- MCP tools manual and API reference
- Development logs tracking project evolution
- Session memories from previous agent interactions
- LAN deployment guides and security checklists

### Scripts (`scripts/`)
- Database management scripts
- Deployment automation
- Testing utilities
- Migration helpers

### Examples (`examples/`)
- Example project setups
- Configuration templates
- Use case demonstrations

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

## Multi-System Coordination

### Before Starting Work on Either System

```bash
# ALWAYS pull first
git pull
```

### After Making Changes

```bash
# Check what changed
git status
git diff

# Commit and push
git add .
git commit -m "feat: [clear description]"
git push
```

### Switching Between Systems

1. Commit and push from current system
2. Switch to other system
3. `git pull` to get latest changes
4. Your local .env and config.yaml stay intact (gitignored)
5. Continue working

### When Config Changes Are Needed

If you need to update how config.yaml is generated:
1. Edit `installer/core/config.py`
2. Test the installer: `python installer/cli/install.py --dry-run`
3. Commit the installer changes
4. Both systems pull and regenerate configs as needed

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

### Git Conflicts with Environment Files

If .env or config.yaml accidentally got committed:
```bash
# Remove from git but keep local file
git rm --cached .env
git rm --cached config.yaml

# Verify .gitignore has these files
cat .gitignore | grep -E "\.env|config\.yaml"

# Commit the removal
git commit -m "fix: Remove environment files from git tracking"
git push
```

## System-Specific Notes

### System 1 (C: Drive - Localhost Mode)

- Uses default localhost configuration
- No API key authentication
- API binds to 127.0.0.1 only
- Perfect for rapid development and testing
- No network security concerns

### System 2 (F: Drive - Server Mode)

- Uses server configuration for LAN testing
- Requires API key authentication
- API binds to 0.0.0.0 (network accessible)
- Tests multi-client scenarios
- Validates security features

Both systems share the same codebase via GitHub, but maintain their own deployment-specific configurations.
