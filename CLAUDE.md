# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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