# GiljoAI MCP Dependencies Guide

Complete guide to all dependencies used in GiljoAI MCP Orchestrator, their purposes, and installation requirements.

## Overview

GiljoAI MCP uses a carefully curated set of dependencies to provide robust multi-agent orchestration capabilities. All dependencies are automatically installed during setup.

## Core Runtime Dependencies

### WebSocket & Communication

| Package        | Version  | Purpose                                            | Used By                                                             |
| -------------- | -------- | -------------------------------------------------- | ------------------------------------------------------------------- |
| **aiohttp**    | >=3.8.0  | WebSocket client for real-time agent communication | `src/giljo_mcp/websocket_client.py`, `src/giljo_mcp/tools/agent.py` |
| **websockets** | >=12.0   | WebSocket protocol implementation                  | FastAPI WebSocket endpoints                                         |
| **httpx**      | >=0.25.0 | HTTP client for external API calls                 | API integrations, health checks                                     |

**Critical:** `aiohttp` is essential for the orchestration system's real-time communication. Without it, agents cannot broadcast events or coordinate work.

### Web Framework & API

| Package               | Version   | Purpose                                 | Used By                 |
| --------------------- | --------- | --------------------------------------- | ----------------------- |
| **fastapi**           | >=0.100.0 | REST API server and WebSocket endpoints | Main application server |
| **uvicorn[standard]** | >=0.23.0  | ASGI server for running FastAPI         | Application startup     |
| **python-multipart**  | >=0.0.6   | Form data support for file uploads      | API endpoints           |

### Data & Validation

| Package               | Version | Purpose                           | Used By                   |
| --------------------- | ------- | --------------------------------- | ------------------------- |
| **pydantic**          | >=2.0.0 | Data validation and serialization | Configuration, API models |
| **pydantic-settings** | >=2.0.0 | Settings management               | Configuration system      |

## Database Dependencies

### ORM & Migrations

| Package        | Version  | Purpose                | Used By                  |
| -------------- | -------- | ---------------------- | ------------------------ |
| **sqlalchemy** | >=2.0.0  | ORM with async support | Database models, queries |
| **alembic**    | >=1.12.0 | Database migrations    | Schema versioning        |

### Database Drivers

| Package             | Version  | Purpose                              | Used By                     |
| ------------------- | -------- | ------------------------------------ | --------------------------- |
| **aiopostgresql**       | >=0.19.0 | Async PostgreSQL driver (default)        | Local development           |
| **asyncpg**         | >=0.29.0 | PostgreSQL async driver (production) | Team/Enterprise deployments |
| **psycopg2-binary** | >=2.9.0  | PostgreSQL sync driver (backup)      | Fallback connections        |

## Authentication & Security

| Package                       | Version | Purpose                 | Used By               |
| ----------------------------- | ------- | ----------------------- | --------------------- |
| **python-jose[cryptography]** | >=3.3.0 | JWT token handling      | Authentication system |
| **passlib[bcrypt]**           | >=1.7.4 | Secure password hashing | User management       |

## AI Integration Dependencies

### AI Provider APIs

| Package                 | Version | Purpose                         | Used By             |
| ----------------------- | ------- | ------------------------------- | ------------------- |
| **openai**              | >=1.0.0 | OpenAI API integration          | GPT model access    |
| **anthropic**           | >=0.8.0 | Claude API integration          | Claude model access |
| **google-generativeai** | >=0.3.0 | Google Gemini integration       | Gemini model access |
| **tiktoken**            | >=0.5.0 | Token counting and optimization | Context management  |

### External Integrations

| Package       | Version  | Purpose             | Used By           |
| ------------- | -------- | ------------------- | ----------------- |
| **slack-sdk** | >=3.23.0 | Slack notifications | Alert system      |
| **PyGithub**  | >=2.1.0  | GitHub integration  | Repository access |
| **jira**      | >=3.5.0  | Jira connector      | Issue tracking    |

## Utility Dependencies

### Configuration & Environment

| Package           | Version  | Purpose                      | Used By            |
| ----------------- | -------- | ---------------------------- | ------------------ |
| **python-dotenv** | >=1.0.0  | Environment variable loading | Configuration      |
| **pyyaml**        | >=6.0.0  | YAML configuration parsing   | Config files       |
| **click**         | >=8.1.0  | CLI interface                | Command-line tools |
| **rich**          | >=13.0.0 | Beautiful terminal output    | User interface     |

### Monitoring & Metrics

| Package               | Version  | Purpose        | Used By                |
| --------------------- | -------- | -------------- | ---------------------- |
| **prometheus-client** | >=0.19.0 | Metrics export | Performance monitoring |

## Development Dependencies

### Testing Framework

| Package            | Version  | Purpose            | Used By       |
| ------------------ | -------- | ------------------ | ------------- |
| **pytest**         | >=7.4.0  | Testing framework  | Test suite    |
| **pytest-asyncio** | >=0.21.0 | Async test support | Async tests   |
| **pytest-cov**     | >=4.1.0  | Coverage reporting | Test coverage |

### Code Quality

| Package   | Version  | Purpose        | Used By         |
| --------- | -------- | -------------- | --------------- |
| **black** | >=23.0.0 | Code formatter | Development     |
| **ruff**  | >=0.1.0  | Fast linter    | Code quality    |
| **mypy**  | >=1.5.0  | Type checking  | Type validation |

## Platform-Specific Dependencies

### Windows

| Package     | Version | Purpose                    | Used By           |
| ----------- | ------- | -------------------------- | ----------------- |
| **pywin32** | >=306   | Windows service management | Service installer |

### Production Services

| Package      | Version  | Purpose                | Used By                |
| ------------ | -------- | ---------------------- | ---------------------- |
| **gunicorn** | >=21.0.0 | Production WSGI server | Production deployment  |
| **redis**    | >=5.0.0  | Redis cache/queue      | Caching, message queue |
| **celery**   | >=5.3.0  | Optional task queue    | Background tasks       |
| **docker**   | >=6.0.0  | Docker API integration | Container management   |

## Installation Methods

### Automatic Installation (Recommended)

```bash
# Run the installer - handles all dependencies
python bootstrap.py
```

### Manual Installation

```bash
# Install core dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt  # If exists
```

### Verification

```bash
# Verify key dependencies are installed
python -c "import aiohttp, fastapi, sqlalchemy; print('✅ Core dependencies OK')"
python -c "import websockets, httpx, pydantic; print('✅ Communication dependencies OK')"
```

## Troubleshooting

### Common Issues

#### aiohttp Installation Failed

```bash
# Windows: Install Visual C++ Build Tools
# Or use pre-compiled wheel:
pip install aiohttp --only-binary=all
```

#### PostgreSQL Driver Issues

```bash
# Install PostgreSQL development headers
# Ubuntu/Debian:
sudo apt-get install libpq-dev python3-dev

# RedHat/CentOS:
sudo yum install postgresql-devel python3-devel
```

#### Windows Service Dependencies

```bash
# Install Windows-specific packages
pip install pywin32
python Scripts/pywin32_postinstall.py -install
```

### Dependency Conflicts

If you encounter dependency conflicts:

1. Use a virtual environment:

```bash
python -m venv giljo_env
source giljo_env/bin/activate  # Linux/Mac
giljo_env\Scripts\activate     # Windows
```

2. Update pip and setuptools:

```bash
python -m pip install --upgrade pip setuptools
```

3. Install with specific versions:

```bash
pip install -r requirements.txt --force-reinstall
```

## Version Compatibility

### Python Versions

- **Minimum:** Python 3.8
- **Recommended:** Python 3.10+
- **Tested:** Python 3.8, 3.9, 3.10, 3.11, 3.12

### Database Versions

- **PostgreSQL:** 3.35+ (built into Python)
- **PostgreSQL:** 12+
- **Redis:** 6.0+ (optional)

## Security Considerations

### Package Security

All dependencies are regularly scanned for vulnerabilities using:

- GitHub Dependabot
- Safety checks during CI/CD
- Regular security audits

### Production Recommendations

1. Pin exact versions in production
2. Use private package index for sensitive deployments
3. Regular security updates
4. Monitor for CVEs in dependencies

## Contributing

When adding new dependencies:

1. Update `requirements.txt` with exact version
2. Update this documentation
3. Add to appropriate installer checks
4. Test across all supported platforms
5. Update Docker configurations if needed

## See Also

- [Installation Guide](../README.md#5-minute-quick-start)
- [Configuration Guide](./configuration.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Security Guide](../SECURITY.md)
