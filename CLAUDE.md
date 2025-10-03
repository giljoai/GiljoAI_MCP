# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GiljoAI MCP Coding Orchestrator is a multi-agent orchestration system that transforms AI coding assistants into coordinated development teams. It breaks through context limits by orchestrating multiple specialized agents that work together on complex tasks.

## Development and Testing Environment

### Dual-Folder Setup with Symlinks

The project uses a sophisticated development workflow with two synchronized folders:

1. **Development Repository**: `C:\Projects\GiljoAI_MCP`
   - Primary development location
   - Where all code changes are made
   - Version controlled with Git
   - Claude Code operates from here

2. **Test Installation**: `C:\install_test\Giljo_MCP`
   - Clean installation for testing
   - Uses symlinks to dev repository for code directories
   - Separate configuration and runtime files
   - Where the server actually runs for testing

#### Symlinked Directories (instant updates)
All code directories are symlinked from test to dev, so changes are immediately reflected:
- `frontend` → `C:\Projects\GiljoAI_MCP\frontend`
- `api` → `C:\Projects\GiljoAI_MCP\api`
- `src` → `C:\Projects\GiljoAI_MCP\src`
- `installer` → `C:\Projects\GiljoAI_MCP\installer`
- `docs` → `C:\Projects\GiljoAI_MCP\docs`
- `tests` → `C:\Projects\GiljoAI_MCP\tests`

#### Separate Files (test-specific)
These remain independent in the test installation:
- `logs/` - Test-specific logs
- `venv/` - Test environment's virtual environment
- `config.yaml` - Test-specific configuration
- `__pycache__/` - Python cache
- `.env` - Environment variables
- Database files

### Workflow Benefits
- **Instant Updates**: Code changes in dev repo immediately available in test installation
- **Clean Testing**: Test installation remains uncluttered with development files
- **Service Restart Only**: Only need to restart services for Python changes
- **No File Copying**: No manual synchronization needed

## Standard Configuration

### Database
- **Type**: PostgreSQL 18 (exclusively)
- **Development Password**: `4010`
- **Default Database**: `giljo_mcp`
- **Connection**: `postgresql://postgres:***@localhost:5432/giljo_mcp`

### Port Standardization
The system uses a consistent port scheme:
- **7272**: Primary API port (FastAPI backend)
- **7273**: Secondary/fallback API port
- **7274**: Additional service port
- **5173**: Frontend development server (Vite)
- **5432**: PostgreSQL database (standard)

### Testing Workflow
1. Make code changes in `C:\Projects\GiljoAI_MCP` (dev repo)
2. Changes are instantly available via symlinks
3. Navigate to `C:\install_test\Giljo_MCP` (test installation)
4. Restart services if Python code changed:
   ```bash
   # In test installation folder
   python api/run_api.py  # Backend will run with verbose logging by default
   ```
5. Frontend changes are hot-reloaded automatically
6. Monitor verbose console output for debugging

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
python install.py       # Universal installer for all platforms

# Manual setup
pip install -r requirements.txt  # Install Python dependencies
python install.py       # Interactive CLI setup
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

**IMPORTANT**: The frontend MUST be accessed through the Vite dev server, NOT by opening index.html directly in the browser.

```bash
# Navigate to frontend directory first
cd frontend/

# Install dependencies (if not already installed)
npm install

# Development server
npm run dev                      # Start dev server at http://localhost:7274

# Access the frontend
# ✅ CORRECT:  http://localhost:7274
# ❌ WRONG:    Opening index.html directly in browser (causes module resolution errors)

# Production build
npm run build                    # Build for production

# Linting & formatting
npm run lint                     # Lint Vue/JS code
npm run format                   # Format with Prettier
```

### API Development

```bash
# Start API server (from test installation folder)
cd C:\install_test\Giljo_MCP
python api/run_api.py            # Start REST API (port 7272 by default)

# With specific options
python api/run_api.py --verbose  # Force verbose debug logging
python api/run_api.py --port 7273  # Use alternate port
python api/run_api.py --reload   # Enable auto-reload for development

# Development mode with uvicorn directly
uvicorn api.app:app --reload --port 7272 --log-level debug
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

[... Rest of the file remains the same ...]

## Important Coding Guidelines

- **No Emojis in Code**: Never use emojis in code unless specifically requested by the user or when the project has icon files to use as defaults
- **Professional Code**: Keep all code clean, professional, and emoji-free
- **File Creation**: Only create files when absolutely necessary; prefer editing existing files
- **Documentation**: Only create documentation files when explicitly requested