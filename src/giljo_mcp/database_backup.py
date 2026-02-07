"""
Database backup utility for GiljoAI MCP Server.

Creates PostgreSQL database backups using pg_dump with comprehensive metadata generation.
Supports multi-tenant backup (entire database) with detailed schema documentation.

Features:
- Cross-platform pg_dump discovery (reuses PostgreSQLDiscovery)
- Timestamped backup folders with .sql dumps and .md metadata
- Schema introspection (tables, row counts, constraints, indexes)
- Secure password handling via PGPASSWORD environment variable
- Comprehensive error handling and logging
- Configuration from .env or config.yaml
"""

import logging
import os
import shutil
import subprocess  # nosec B404
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


try:
    import psycopg2
    from psycopg2 import sql

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from installer.shared.postgres import PostgreSQLDiscovery


logger = logging.getLogger(__name__)


class DatabaseBackupError(Exception):
    """Base exception for database backup errors."""


class PgDumpNotFoundError(DatabaseBackupError):
    """Raised when pg_dump binary cannot be found."""


class DatabaseConnectionError(DatabaseBackupError):
    """Raised when database connection fails."""


class BackupExecutionError(DatabaseBackupError):
    """Raised when backup execution fails."""


class InsufficientDiskSpaceError(DatabaseBackupError):
    """Raised when insufficient disk space for backup."""


class DatabaseBackupUtility:
    """
    Database backup utility for PostgreSQL.

    Handles full database backups with metadata generation including
    table information, row counts, and schema structure.

    Attributes:
        db_config: Database configuration dict
        backup_base_dir: Base directory for backups
        pg_dump_path: Path to pg_dump binary
    """

    # Minimum free disk space required (500 MB)
    MIN_FREE_SPACE_MB = 500

    def __init__(self, db_config: dict[str, str | None] = None, backup_base_dir: Path | None = None):
        """
        Initialize database backup utility.

        Args:
            db_config: Optional database configuration. If not provided,
                      will be loaded from .env or config.yaml
            backup_base_dir: Optional custom backup directory.
                            Defaults to docs/archive/database_backups/

        Raises:
            DatabaseBackupError: If configuration cannot be loaded
            PgDumpNotFoundError: If pg_dump binary cannot be found
        """
        self.db_config = db_config or self._load_db_config()
        self.backup_base_dir = backup_base_dir or self._get_default_backup_dir()
        self.pg_dump_path = self._find_pg_dump()

        logger.info(
            f"DatabaseBackupUtility initialized: "
            f"database={self.db_config['database']}, "
            f"backup_dir={self.backup_base_dir}"
        )

    def _load_db_config(self) -> dict[str, str]:
        """
        Load database configuration from .env or config.yaml.

        Priority:
        1. .env file (POSTGRES_* variables)
        2. config.yaml (database section)

        Returns:
            Dict with keys: host, port, database, user, password

        Raises:
            DatabaseBackupError: If configuration cannot be loaded
        """
        config = {}

        # Try .env first
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            logger.debug(f"Loading database config from {env_file}")
            try:
                with open(env_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()

                            # Map environment variables to config keys
                            if key == "POSTGRES_HOST":
                                config["host"] = value
                            elif key == "POSTGRES_PORT":
                                config["port"] = value
                            elif key == "POSTGRES_DB":
                                config["database"] = value
                            elif key == "POSTGRES_USER":
                                config["user"] = value
                            elif key == "POSTGRES_PASSWORD":
                                config["password"] = value

                # Validate we have minimum required config
                if all(k in config for k in ["host", "port", "database"]):
                    logger.info("Database config loaded from .env")
                    return config

            except (OSError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse .env file: {e}")

        # Try config.yaml as fallback
        config_file = Path.cwd() / "config.yaml"
        if config_file.exists():
            logger.debug(f"Loading database config from {config_file}")
            try:
                with open(config_file, encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)

                db_section = yaml_config.get("database", {})
                config["host"] = db_section.get("host", "localhost")
                config["port"] = str(db_section.get("port", 5432))
                config["database"] = db_section.get("name", "giljo_mcp")
                config["user"] = db_section.get("user", "postgres")
                config["password"] = db_section.get("password", "")

                logger.info("Database config loaded from config.yaml")
                return config

            except (OSError, yaml.YAMLError, KeyError, ValueError) as e:
                logger.warning(f"Failed to parse config.yaml: {e}")

        raise DatabaseBackupError("Could not load database configuration from .env or config.yaml")

    def _get_default_backup_dir(self) -> Path:
        """
        Get default backup directory path.

        Returns:
            Path to docs/archive/database_backups/
        """
        return Path.cwd() / "docs" / "archive" / "database_backups"

    def _find_pg_dump(self) -> Path:
        """
        Find pg_dump binary using PostgreSQLDiscovery.

        Returns:
            Path to pg_dump binary

        Raises:
            PgDumpNotFoundError: If pg_dump cannot be found
        """
        logger.info("Searching for pg_dump binary...")

        # Use PostgreSQLDiscovery to find PostgreSQL installation
        discovery = PostgreSQLDiscovery()
        result = discovery.discover()

        if not result["found"]:
            raise PgDumpNotFoundError(
                "PostgreSQL installation not found. Cannot locate pg_dump. "
                "Please ensure PostgreSQL is installed and in system PATH."
            )

        # psql_path points to psql binary, we need pg_dump in same directory
        psql_path = result["psql_path"]
        pg_dump_path = psql_path.parent / ("pg_dump.exe" if os.name == "nt" else "pg_dump")

        if not pg_dump_path.exists():
            raise PgDumpNotFoundError(
                f"pg_dump not found at {pg_dump_path}. Found PostgreSQL at {psql_path.parent} but pg_dump is missing."
            )

        logger.info(f"Found pg_dump at: {pg_dump_path}")
        return pg_dump_path

    def _check_disk_space(self, path: Path) -> None:
        """
        Check if sufficient disk space is available.

        Args:
            path: Path to check disk space for

        Raises:
            InsufficientDiskSpaceError: If insufficient disk space
        """
        try:
            stat = shutil.disk_usage(path.parent if path.exists() else path.parent.parent)
            free_mb = stat.free / (1024 * 1024)

            if free_mb < self.MIN_FREE_SPACE_MB:
                raise InsufficientDiskSpaceError(
                    f"Insufficient disk space: {free_mb:.1f} MB available, {self.MIN_FREE_SPACE_MB} MB required"
                )

            logger.debug(f"Disk space check passed: {free_mb:.1f} MB available")

        except InsufficientDiskSpaceError:
            raise
        except OSError as e:
            logger.warning(f"Could not check disk space: {e}")

    def _get_database_metadata(self) -> dict[str, Any]:
        """
        Query database for schema metadata.

        Returns:
            Dict containing:
            - tables: List of dicts with table info (name, row_count, size)
            - total_tables: Total number of tables
            - total_rows: Total row count across all tables
            - database_size: Total database size

        Raises:
            DatabaseConnectionError: If connection fails
        """
        if not PSYCOPG2_AVAILABLE:
            logger.warning("psycopg2 not available, skipping metadata collection")
            return {
                "tables": [],
                "total_tables": 0,
                "total_rows": 0,
                "database_size": "Unknown",
                "error": "psycopg2 not installed",
            }

        metadata = {"tables": [], "total_tables": 0, "total_rows": 0, "database_size": "Unknown"}

        try:
            # Connect to database
            conn = psycopg2.connect(
                host=self.db_config["host"],
                port=self.db_config["port"],
                database=self.db_config["database"],
                user=self.db_config.get("user", "postgres"),
                password=self.db_config.get("password", ""),
                connect_timeout=10,
            )

            with conn.cursor() as cursor:
                # Get database size
                cursor.execute(sql.SQL("SELECT pg_size_pretty(pg_database_size(%s))"), [self.db_config["database"]])
                result = cursor.fetchone()
                if result:
                    metadata["database_size"] = result[0]

                # Get table information with row counts and sizes
                cursor.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename
                """)

                tables_info = cursor.fetchall()

                for schema, table, size in tables_info:
                    full_table_name = f"{schema}.{table}"

                    # Get row count
                    try:
                        cursor.execute(
                            sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))
                        )
                        row_count = cursor.fetchone()[0]
                    except psycopg2.Error as e:
                        logger.warning(f"Could not get row count for {full_table_name}: {e}")
                        row_count = 0

                    metadata["tables"].append(
                        {
                            "schema": schema,
                            "name": table,
                            "full_name": full_table_name,
                            "row_count": row_count,
                            "size": size,
                        }
                    )

                    metadata["total_rows"] += row_count

                metadata["total_tables"] = len(metadata["tables"])

            conn.close()
            logger.info(f"Collected metadata: {metadata['total_tables']} tables, {metadata['total_rows']} total rows")

        except psycopg2.OperationalError as e:
            raise DatabaseConnectionError(f"Failed to connect to database: {e}") from e
        except psycopg2.Error as e:
            logger.exception("Error collecting database metadata")
            metadata["error"] = str(e)

        return metadata

    def _generate_metadata_file(
        self, backup_dir: Path, backup_file: Path, metadata: dict[str, Any], execution_time: float
    ) -> Path:
        """
        Generate markdown metadata file for backup.

        Args:
            backup_dir: Backup directory path
            backup_file: Backup SQL file path
            metadata: Database metadata dict
            execution_time: Backup execution time in seconds

        Returns:
            Path to generated metadata file
        """
        metadata_file = backup_dir / "backup_metadata.md"

        # Format timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Build markdown content
        content = f"""# Database Backup Metadata

## Backup Information

- **Timestamp**: {timestamp}
- **Backup File**: `{backup_file.name}`
- **Execution Time**: {execution_time:.2f} seconds
- **Backup Directory**: `{backup_dir}`

## Database Configuration

- **Host**: {self.db_config["host"]}
- **Port**: {self.db_config["port"]}
- **Database**: {self.db_config["database"]}
- **User**: {self.db_config.get("user", "postgres")}
- **Database Size**: {metadata.get("database_size", "Unknown")}

## Schema Overview

- **Total Tables**: {metadata.get("total_tables", 0)}
- **Total Rows**: {metadata.get("total_rows", 0):,}

"""

        # Add table details
        if metadata.get("tables"):
            content += "## Table Details\n\n"
            content += "| Schema | Table Name | Row Count | Size |\n"
            content += "|--------|------------|-----------|------|\n"

            for table in metadata["tables"]:
                content += f"| {table['schema']} | {table['name']} | {table['row_count']:,} | {table['size']} |\n"

        # Add error information if present
        if metadata.get("error"):
            content += "\n## Metadata Collection Errors\n\n"
            content += f"```\n{metadata['error']}\n```\n"

        content += f"""

## Backup Process

This backup was created using `pg_dump` with the following configuration:

- **Format**: Plain SQL (text)
- **pg_dump Path**: `{self.pg_dump_path}`
- **Multi-Tenant**: Yes (entire database backed up)

## Restore Instructions

To restore this backup:

```bash
# Method 1: Using psql
psql -h {self.db_config["host"]} -p {self.db_config["port"]} -U postgres -d {self.db_config["database"]} -f {backup_file.name}

# Method 2: Drop and recreate database (full restore)
dropdb -h {self.db_config["host"]} -p {self.db_config["port"]} -U postgres {self.db_config["database"]}
createdb -h {self.db_config["host"]} -p {self.db_config["port"]} -U postgres {self.db_config["database"]}
psql -h {self.db_config["host"]} -p {self.db_config["port"]} -U postgres -d {self.db_config["database"]} -f {backup_file.name}
```

**Note**: Restore requires PostgreSQL superuser privileges (default password: 4010)

---

Generated by GiljoAI MCP Database Backup Utility
"""

        # Write metadata file
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated metadata file: {metadata_file}")
        return metadata_file

    def create_backup(self, include_metadata: bool = True) -> dict[str, Any]:
        """
        Create full database backup with optional metadata.

        Args:
            include_metadata: Whether to generate metadata file (default: True)

        Returns:
            Dict containing:
            - backup_dir: Path to backup directory
            - backup_file: Path to SQL dump file
            - metadata_file: Path to metadata file (if generated)
            - timestamp: Backup timestamp
            - execution_time: Backup execution time in seconds
            - success: Whether backup succeeded

        Raises:
            DatabaseBackupError: If backup fails
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting database backup...")

        # Create timestamped backup directory
        timestamp_str = start_time.strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = self.backup_base_dir / timestamp_str

        try:
            # Check disk space
            self._check_disk_space(self.backup_base_dir)

            # Create backup directory
            backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created backup directory: {backup_dir}")

            # Define backup file path
            backup_file = backup_dir / f"{self.db_config['database']}_backup.sql"

            # Prepare pg_dump command
            pg_dump_cmd = [
                str(self.pg_dump_path),
                "-h",
                self.db_config["host"],
                "-p",
                self.db_config["port"],
                "-U",
                self.db_config.get("user", "postgres"),
                "-d",
                self.db_config["database"],
                "-F",
                "p",  # Plain text format
                "-f",
                str(backup_file),
                "--verbose",
            ]

            # Prepare environment with password (secure)
            env = os.environ.copy()
            if self.db_config.get("password"):
                env["PGPASSWORD"] = self.db_config["password"]

            logger.info(f"Executing pg_dump to {backup_file}")
            logger.debug(f"Command: {' '.join(pg_dump_cmd[:-1])} [password hidden]")

            # Execute pg_dump
            result = subprocess.run(  # noqa: S603 - pg_dump_path validated via PostgreSQLDiscovery
                pg_dump_cmd,
                shell=False,
                check=False,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                raise BackupExecutionError(
                    f"pg_dump failed with exit code {result.returncode}:\n"
                    f"STDERR: {result.stderr}\n"
                    f"STDOUT: {result.stdout}"
                )

            # Verify backup file was created and has content
            if not backup_file.exists():
                raise BackupExecutionError(f"Backup file not created at {backup_file}")

            backup_size = backup_file.stat().st_size
            if backup_size == 0:
                raise BackupExecutionError(f"Backup file is empty: {backup_file}")

            logger.info(f"Backup created successfully: {backup_file} ({backup_size / 1024:.1f} KB)")

            # Collect metadata
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            metadata = {}
            metadata_file = None

            if include_metadata:
                try:
                    metadata = self._get_database_metadata()
                    metadata_file = self._generate_metadata_file(backup_dir, backup_file, metadata, execution_time)
                except (psycopg2.Error, OSError):
                    logger.exception("Failed to generate metadata")
                    # Continue without metadata - backup is more important

            result_info = {
                "success": True,
                "backup_dir": backup_dir,
                "backup_file": backup_file,
                "metadata_file": metadata_file,
                "timestamp": start_time.isoformat(),
                "execution_time": execution_time,
                "backup_size": backup_size,
                "database": self.db_config["database"],
                "tables": metadata.get("tables", []),
                "total_tables": metadata.get("total_tables", 0),
                "total_rows": metadata.get("total_rows", 0),
            }

            logger.info(f"Database backup completed successfully in {execution_time:.2f}s: {backup_dir}")

            return result_info

        except subprocess.TimeoutExpired as e:
            raise BackupExecutionError(
                "pg_dump timed out after 10 minutes. Database may be too large or server is unresponsive."
            ) from e
        except (PgDumpNotFoundError, DatabaseConnectionError, BackupExecutionError, InsufficientDiskSpaceError):
            raise
        except Exception as e:
            raise DatabaseBackupError(f"Unexpected error during backup: {e!s}") from e


def create_database_backup(
    db_config: dict[str, str | None] = None, backup_dir: Path | None = None, include_metadata: bool = True
) -> dict[str, Any]:
    """
    Convenience function to create a database backup.

    Args:
        db_config: Optional database configuration
        backup_dir: Optional custom backup directory
        include_metadata: Whether to generate metadata file

    Returns:
        Backup result dict from DatabaseBackupUtility.create_backup()

    Raises:
        DatabaseBackupError: If backup fails
    """
    utility = DatabaseBackupUtility(db_config=db_config, backup_base_dir=backup_dir)
    return utility.create_backup(include_metadata=include_metadata)


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        # Create backup using configuration from .env or config.yaml
        result = create_database_backup()

        print("\nBackup completed successfully!")
        print(f"Backup directory: {result['backup_dir']}")
        print(f"Backup file: {result['backup_file']}")
        print(f"Execution time: {result['execution_time']:.2f}s")
        print(f"Database size: {result['backup_size'] / 1024:.1f} KB")
        print(f"Tables backed up: {result['total_tables']}")
        print(f"Total rows: {result['total_rows']:,}")

    except DatabaseBackupError as e:
        print(f"\nBackup failed: {e}")
        exit(1)
