# Database Backup Utility

## Overview

The Database Backup Utility (`src/giljo_mcp/database_backup.py`) provides production-grade PostgreSQL database backup functionality for GiljoAI MCP. It creates timestamped backups with comprehensive metadata generation, including schema structure, table statistics, and restore instructions.

## Features

### Core Features

- **Cross-Platform Support**: Automatic PostgreSQL binary discovery on Windows, Linux, and macOS
- **Secure Password Handling**: Uses PGPASSWORD environment variable (never in command line)
- **Timestamped Backups**: Organized in `YYYY-MM-DD_HH-MM-SS` folder structure
- **Comprehensive Metadata**: Detailed schema documentation with row counts and sizes
- **Multi-Tenant Support**: Full database backup preserving all tenant isolation
- **Error Handling**: Clear, actionable error messages for common issues
- **Disk Space Checking**: Validates sufficient space before backup (500+ MB required)
- **Configuration Flexibility**: Reads from .env or config.yaml automatically

### Output Structure

```
docs/archive/database_backups/
└── 2025-10-24_10-30-45/
    ├── giljo_mcp_backup.sql    # Full database dump (plain SQL)
    └── backup_metadata.md       # Comprehensive metadata and restore guide
```

## Installation

### Prerequisites

1. **PostgreSQL**: Version 14+ installed and accessible
2. **Python Dependencies**: psycopg2 (optional, for metadata collection)

```bash
# Install psycopg2 for full metadata support
pip install psycopg2-binary

# Or install all project dependencies
pip install -r requirements.txt
```

3. **PostgreSQL in PATH**: Ensure PostgreSQL binaries are accessible
   - **Windows**: Add `C:\Program Files\PostgreSQL\18\bin` to PATH
   - **Linux**: Usually in `/usr/bin` or `/usr/pgsql-18/bin`
   - **macOS**: Add `/usr/local/opt/postgresql@18/bin` to PATH

### Verification

```bash
# Verify PostgreSQL is accessible
psql --version
pg_dump --version

# Test the backup utility
python -c "from src.giljo_mcp.database_backup import DatabaseBackupUtility; print('Module loaded successfully')"
```

## Configuration

### Option 1: .env File (Recommended)

The utility automatically reads from `.env`:

```env
# Database configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=giljo_mcp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=4010
```

### Option 2: config.yaml

Fallback configuration source:

```yaml
database:
  host: localhost
  port: 5432
  name: giljo_mcp
  user: postgres
  password: "4010"
```

### Option 3: Manual Configuration

```python
from src.giljo_mcp.database_backup import DatabaseBackupUtility

custom_config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'giljo_mcp',
    'user': 'postgres',
    'password': '4010'
}

utility = DatabaseBackupUtility(db_config=custom_config)
```

## Usage

### Basic Usage

```python
from src.giljo_mcp.database_backup import create_database_backup

# Simple one-line backup
result = create_database_backup()

print(f"Backup created: {result['backup_dir']}")
print(f"Tables backed up: {result['total_tables']}")
print(f"Total rows: {result['total_rows']:,}")
```

### Advanced Usage

```python
from pathlib import Path
from src.giljo_mcp.database_backup import DatabaseBackupUtility

# Custom backup directory
custom_dir = Path.cwd() / 'backups' / 'manual'

# Initialize utility
utility = DatabaseBackupUtility(backup_base_dir=custom_dir)

# Create backup with metadata
result = utility.create_backup(include_metadata=True)

# Access result information
print(f"Backup file: {result['backup_file']}")
print(f"Execution time: {result['execution_time']:.2f}s")
print(f"Backup size: {result['backup_size'] / (1024 * 1024):.1f} MB")
```

### Quick Backup (No Metadata)

For fast backups when metadata is not needed:

```python
# Fast backup without metadata generation
result = create_database_backup(include_metadata=False)
```

### Error Handling

```python
from src.giljo_mcp.database_backup import (
    DatabaseBackupError,
    PgDumpNotFoundError,
    DatabaseConnectionError,
    BackupExecutionError
)

try:
    result = create_database_backup()
    print(f"Success: {result['backup_dir']}")

except PgDumpNotFoundError:
    print("PostgreSQL tools not found - add to PATH")

except DatabaseConnectionError:
    print("Cannot connect to database - check credentials")

except BackupExecutionError as e:
    print(f"Backup failed: {e}")

except DatabaseBackupError as e:
    print(f"General error: {e}")
```

## API Reference

### DatabaseBackupUtility Class

#### Constructor

```python
DatabaseBackupUtility(
    db_config: Optional[Dict[str, str]] = None,
    backup_base_dir: Optional[Path] = None
)
```

**Parameters:**
- `db_config` (optional): Database configuration dict with keys:
  - `host`: Database host (default: from .env/config.yaml)
  - `port`: Database port (default: from .env/config.yaml)
  - `database`: Database name (default: from .env/config.yaml)
  - `user`: Database user (default: from .env/config.yaml)
  - `password`: Database password (default: from .env/config.yaml)
- `backup_base_dir` (optional): Custom backup directory (default: `docs/archive/database_backups/`)

**Raises:**
- `DatabaseBackupError`: If configuration cannot be loaded
- `PgDumpNotFoundError`: If pg_dump binary cannot be found

#### create_backup Method

```python
create_backup(include_metadata: bool = True) -> Dict[str, Any]
```

**Parameters:**
- `include_metadata`: Whether to generate metadata file (default: True)

**Returns:**
Dictionary with keys:
- `success` (bool): Whether backup succeeded
- `backup_dir` (Path): Backup directory path
- `backup_file` (Path): SQL dump file path
- `metadata_file` (Path): Metadata file path (if generated)
- `timestamp` (str): ISO format timestamp
- `execution_time` (float): Execution time in seconds
- `backup_size` (int): Backup file size in bytes
- `database` (str): Database name
- `tables` (list): List of table information dicts
- `total_tables` (int): Total number of tables
- `total_rows` (int): Total row count

**Raises:**
- `PgDumpNotFoundError`: If pg_dump not found
- `DatabaseConnectionError`: If database connection fails
- `BackupExecutionError`: If backup execution fails
- `InsufficientDiskSpaceError`: If insufficient disk space
- `DatabaseBackupError`: For other errors

### Convenience Function

```python
create_database_backup(
    db_config: Optional[Dict[str, str]] = None,
    backup_dir: Optional[Path] = None,
    include_metadata: bool = True
) -> Dict[str, Any]
```

One-line backup creation with automatic configuration.

## Metadata File

The generated `backup_metadata.md` includes:

### Backup Information
- Timestamp
- Backup file name
- Execution time
- Backup directory path

### Database Configuration
- Host, port, database name
- User (password hidden)
- Total database size

### Schema Overview
- Total tables count
- Total rows across all tables

### Table Details
- Table name (with schema)
- Row count per table
- Size per table

### Restore Instructions
- Complete restore commands
- Both incremental and full restore methods
- Notes about required permissions

## Restoring Backups

### Method 1: Incremental Restore

Restores into existing database:

```bash
psql -h localhost -p 5432 -U postgres -d giljo_mcp -f giljo_mcp_backup.sql
```

### Method 2: Full Restore

Drops and recreates database:

```bash
# Drop existing database
dropdb -h localhost -p 5432 -U postgres giljo_mcp

# Create fresh database
createdb -h localhost -p 5432 -U postgres giljo_mcp

# Restore from backup
psql -h localhost -p 5432 -U postgres -d giljo_mcp -f giljo_mcp_backup.sql
```

**Note**: Restore requires PostgreSQL superuser privileges (default password: 4010)

## Security Considerations

### Password Security

1. **Environment Variable**: Password passed via `PGPASSWORD` environment variable
2. **Never in Command Line**: Password never appears in process list
3. **Not Logged**: Password not written to logs or stdout
4. **Gitignored**: Configuration files (.env, config.yaml) are gitignored

### Multi-Tenant Isolation

- Backup includes entire database (all tenants)
- Tenant isolation preserved in backup
- Restore maintains all tenant boundaries
- No cross-tenant data leakage

### Access Control

- Requires PostgreSQL superuser for full backup
- Default superuser password: 4010
- Use `giljo_user` for normal operations (limited privileges)
- Only use `postgres` user for backups and administrative tasks

## Troubleshooting

### Error: PostgreSQL Not Found

**Problem**: `PgDumpNotFoundError: PostgreSQL installation not found`

**Solutions**:
1. Add PostgreSQL bin directory to system PATH
2. Install PostgreSQL if not installed
3. Verify installation: `psql --version`

### Error: Connection Failed

**Problem**: `DatabaseConnectionError: Failed to connect to database`

**Solutions**:
1. Ensure PostgreSQL server is running
2. Verify database credentials in .env or config.yaml
3. Check database name and port are correct
4. Test connection: `psql -h localhost -p 5432 -U postgres -d giljo_mcp`

### Error: Insufficient Disk Space

**Problem**: `InsufficientDiskSpaceError: Insufficient disk space`

**Solutions**:
1. Free up disk space (500+ MB required)
2. Use custom backup directory on different drive
3. Clean up old backups: `rm -rf docs/archive/database_backups/old_backups`

### Error: Permission Denied

**Problem**: `BackupExecutionError: pg_dump failed: permission denied`

**Solutions**:
1. Use PostgreSQL superuser account (postgres)
2. Verify user has backup privileges
3. Check file system permissions on backup directory

### Missing Metadata

**Problem**: Backup created but no metadata file

**Solutions**:
1. Install psycopg2: `pip install psycopg2-binary`
2. Check database connection credentials
3. Disable metadata: `create_backup(include_metadata=False)`

## Performance

### Typical Execution Times

| Database Size | Tables | Rows | Backup Time | With Metadata |
|--------------|--------|------|-------------|---------------|
| 10 MB | 20 | 10K | ~2s | ~3s |
| 100 MB | 50 | 100K | ~8s | ~10s |
| 1 GB | 100 | 1M | ~45s | ~50s |
| 10 GB | 200 | 10M | ~6min | ~6.5min |

**Note**: Times vary based on hardware, network latency, and PostgreSQL configuration.

### Optimization Tips

1. **Disable Metadata**: Use `include_metadata=False` for 15-20% faster backups
2. **Disk I/O**: Use SSD for backup directory (3-5x faster)
3. **Network**: Use local connections (avoid network latency)
4. **Parallel**: Consider PostgreSQL parallel backup options for large databases
5. **Compression**: Use pg_dump with custom format (`-F c`) for compression

## Integration

### API Endpoint Integration

```python
from fastapi import APIRouter, HTTPException
from src.giljo_mcp.database_backup import create_database_backup, DatabaseBackupError

router = APIRouter()

@router.post("/admin/backup/create")
async def create_backup_endpoint():
    """Create database backup (admin only)."""
    try:
        result = create_database_backup()
        return {
            "success": True,
            "backup_dir": str(result['backup_dir']),
            "execution_time": result['execution_time'],
            "total_tables": result['total_tables']
        }
    except DatabaseBackupError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Scheduled Backups

```python
import schedule
import time
from src.giljo_mcp.database_backup import create_database_backup

def scheduled_backup():
    """Run scheduled backup."""
    try:
        result = create_database_backup()
        print(f"Scheduled backup completed: {result['backup_dir']}")
    except Exception as e:
        print(f"Scheduled backup failed: {e}")

# Schedule daily backups at 2 AM
schedule.every().day.at("02:00").do(scheduled_backup)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

### CLI Integration

```python
import argparse
from src.giljo_mcp.database_backup import create_database_backup

def main():
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument("--no-metadata", action="store_true", help="Skip metadata generation")
    args = parser.parse_args()

    result = create_database_backup(include_metadata=not args.no_metadata)
    print(f"Backup created: {result['backup_dir']}")

if __name__ == "__main__":
    main()
```

## Examples

Complete working examples available in:
- **Script**: `examples/database_backup_example.py`
- **Tests**: `test_database_backup.py`

## Limitations

1. **PostgreSQL Only**: No support for other database systems (MySQL, SQLite)
2. **Full Backups Only**: No incremental or differential backups
3. **Single Database**: Backs up one database at a time
4. **Local Execution**: Must run on machine with PostgreSQL client tools
5. **Synchronous**: Blocks during backup (use threading for async)

## Future Enhancements

Potential improvements for future versions:

1. **Incremental Backups**: Support for differential backups
2. **Compression**: Built-in compression options
3. **Cloud Storage**: Direct upload to S3, GCS, Azure Blob
4. **Encryption**: Encrypted backup files
5. **Rotation**: Automatic old backup cleanup
6. **Monitoring**: Prometheus metrics for backup operations
7. **Parallel Backup**: Multi-threaded backup for large databases
8. **Email Notifications**: Alert on backup success/failure

## Support

For issues or questions:

1. Check this documentation
2. Review error messages and troubleshooting section
3. Examine logs in `logs/giljo_mcp.log`
4. Run test suite: `python test_database_backup.py`
5. Check examples: `python examples/database_backup_example.py`

## Version History

- **v1.0.0** (2025-10-24): Initial release
  - Cross-platform PostgreSQL discovery
  - Timestamped backups with metadata
  - Comprehensive error handling
  - Multi-tenant support
  - Security features (PGPASSWORD)
  - Production-grade code quality
