# GiljoAI MCP Dependencies - September 2025

## Core Python Dependencies
- Python 3.10+
- SQLAlchemy 2.0.x (Async ORM)
- psycopg2-binary 2.9.x (PostgreSQL Adapter)
- asyncpg 0.28.x (Async PostgreSQL Driver)
- FastAPI 0.109.x
- Pydantic 2.6.x
- uvicorn 0.27.x

## Database Requirements
- PostgreSQL 18 (Exclusively Supported)
- PostGIS Extension (Optional, for Geospatial Features)

## Development & Testing
- pytest 8.x
- ruff 0.3.x (Linting)
- black 24.x (Formatting)
- mypy 1.9.x (Type Checking)

## Optional Components
- websockets 12.x (WebSocket Support)
- aiofiles 23.x (Async File Handling)

## Deprecated Dependencies
- sqlite3 (Removed)
- mysql-connector (Removed)
- aiopostgresql (Removed)

## Installation Methods
1. Standard Installation:
   ```bash
   pip install -r requirements.txt
   ```

2. Development Installation:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Compatibility Notes
- Strictly tested on PostgreSQL 18
- Minimal external dependency footprint
- Performance-optimized library selection

## Dependency Management Strategy
- Quarterly dependency review
- Security patch tracking
- Minimal external library reliance
