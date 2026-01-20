# Database Backup - Quick Start Guide

## One-Line Backup

```python
from src.giljo_mcp.database_backup import create_database_backup

result = create_database_backup()
print(f"Backup created: {result['backup_dir']}")
```

## Prerequisites

1. PostgreSQL 14+ installed
2. PostgreSQL binaries in PATH
3. Database running and accessible

## Output Location

```
docs/archive/database_backups/2025-10-24_10-30-45/
├── giljo_mcp_backup.sql       # SQL dump file
└── backup_metadata.md         # Schema info and restore guide
```

## Common Use Cases

### Daily Automated Backup

```python
from src.giljo_mcp.database_backup import create_database_backup

try:
    result = create_database_backup()
    print(f"✓ Backup successful: {result['total_tables']} tables, {result['total_rows']:,} rows")
except Exception as e:
    print(f"✗ Backup failed: {e}")
```

### Before Major Changes

```python
# Create backup before running migrations
result = create_database_backup()
print(f"Safety backup: {result['backup_file']}")

# Now run your migrations
# ...
```

### Quick Backup (No Metadata)

```python
# Faster backup without metadata generation
result = create_database_backup(include_metadata=False)
```

## Restoring a Backup

```bash
# Restore to existing database
psql -h localhost -p 5432 -U postgres -d giljo_mcp -f giljo_mcp_backup.sql

# Full restore (drop + recreate)
dropdb -h localhost -p 5432 -U postgres giljo_mcp
createdb -h localhost -p 5432 -U postgres giljo_mcp
psql -h localhost -p 5432 -U postgres -d giljo_mcp -f giljo_mcp_backup.sql
```

## Troubleshooting

### PostgreSQL Not Found

```bash
# Windows
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin

# Linux/Mac
export PATH=$PATH:/usr/local/opt/postgresql@18/bin
```

### Connection Failed

Check `.env` file:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=giljo_mcp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=4010
```

## Complete Documentation

See `docs/DATABASE_BACKUP_UTILITY.md` for full documentation.

## Examples

Run example script:
```bash
python examples/database_backup_example.py
```
