"""
Database setup endpoints for setup wizard.

Handles:
- PostgreSQL connection testing
- Database creation and schema migration
- Database verification (reads from .env)
- Config file updates with validated credentials
"""

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter()
logger = logging.getLogger(__name__)


class DatabaseSetupRequest(BaseModel):
    """Request model for database setup."""

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    admin_user: str = Field(default="postgres", description="PostgreSQL admin username")
    admin_password: str = Field(..., description="PostgreSQL admin password")
    database_name: str = Field(default="giljo_mcp", description="Database name to create")


@router.post("/test-connection")
async def test_database_connection(request: DatabaseSetupRequest) -> dict:
    """
    Test connection to PostgreSQL server.

    Does NOT create database or make any changes.
    Used to validate credentials before proceeding with setup.

    Args:
        request: Database connection parameters

    Returns:
        Connection test result
    """
    try:
        import psycopg2

        # Attempt connection to postgres database (always exists)
        conn = psycopg2.connect(
            host=request.host,
            port=request.port,
            database="postgres",
            user=request.admin_user,
            password=request.admin_password,
            connect_timeout=5,
        )

        # Get PostgreSQL version
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version_string = cur.fetchone()[0]

            cur.execute("SHOW server_version_num;")
            version_num = int(cur.fetchone()[0])
            major_version = version_num // 10000

        conn.close()

        # Check if target database exists
        conn = psycopg2.connect(
            host=request.host,
            port=request.port,
            database="postgres",
            user=request.admin_user,
            password=request.admin_password,
            connect_timeout=5,
        )

        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (request.database_name,))
            database_exists = cur.fetchone() is not None

        conn.close()

        return {
            "success": True,
            "status": "connected",
            "message": "Successfully connected to PostgreSQL",
            "postgresql_version": major_version,
            "version_string": version_string,
            "database_exists": database_exists,
        }

    except psycopg2.OperationalError as e:
        error_msg = str(e).lower()
        if "password authentication failed" in error_msg:
            return {
                "success": False,
                "status": "auth_failed",
                "message": "Invalid PostgreSQL admin password",
            }
        if "could not connect" in error_msg or "connection refused" in error_msg:
            return {
                "success": False,
                "status": "connection_refused",
                "message": "Cannot connect to PostgreSQL server. Is PostgreSQL running?",
            }
        return {"success": False, "status": "error", "message": f"Connection failed: {e!s}"}

    except (ImportError, OSError, ValueError) as e:
        if isinstance(e, ImportError):
            raise HTTPException(status_code=500, detail="psycopg2 not installed") from None
        return {"success": False, "status": "error", "message": f"Connection test failed: {e!s}"}


@router.post("/setup")
async def setup_database(request: DatabaseSetupRequest) -> dict:
    """
    Set up PostgreSQL database for GiljoAI MCP.

    This endpoint:
    1. Tests connection to PostgreSQL with admin credentials
    2. Creates giljo_mcp database if it doesn't exist
    3. Creates database roles (giljo_owner, giljo_user)
    4. Runs Alembic migrations to create schema
    5. Updates config.yaml with validated credentials

    Args:
        request: Database setup parameters

    Returns:
        Setup result with success status, credentials, and any errors/warnings
    """
    from installer.core.database import DatabaseInstaller

    try:
        # Prepare settings for DatabaseInstaller
        settings = {
            "pg_host": request.host,
            "pg_port": request.port,
            "pg_user": request.admin_user,
            "pg_password": request.admin_password,
        }

        # Initialize database installer
        db_installer = DatabaseInstaller(settings)

        # Run database setup
        logger.info(f"Setting up database {request.database_name}...")
        setup_result = db_installer.setup()

        if not setup_result.get("success"):
            # Setup failed - return errors
            return {
                "success": False,
                "status": "error",
                "errors": setup_result.get("errors", ["Unknown error during database setup"]),
                "warnings": setup_result.get("warnings", []),
            }

        # Setup succeeded - run migrations
        logger.info("Running Alembic migrations...")
        alembic_ini = Path.cwd() / "alembic.ini"
        migration_result = db_installer.run_migrations(alembic_ini)

        if not migration_result.get("success"):
            logger.warning(f"Migrations failed: {migration_result.get('errors')}")
            # Continue anyway - database is created, migrations can be retried

        # Update config.yaml with validated credentials
        logger.info("Updating config.yaml with database credentials...")
        config_path = Path.cwd() / "config.yaml"

        if not config_path.exists():
            return {
                "success": False,
                "status": "error",
                "errors": ["config.yaml not found - cannot update credentials"],
            }

        # Read current config
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Update database section with application user credentials
        if "database" not in config_data:
            config_data["database"] = {}

        config_data["database"].update(
            {
                "type": "postgresql",
                "host": request.host,
                "port": request.port,
                "name": request.database_name,
                "user": "giljo_user",
                "password": setup_result["credentials"]["user_password"],
            }
        )

        # Remove setup_mode flag if present (allows backend to start normally)
        if "setup_mode" in config_data:
            del config_data["setup_mode"]

        # Write updated config
        backup_path = config_path.with_suffix(f".yaml.backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        shutil.copy(config_path, backup_path)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

        logger.info("Database setup completed successfully")

        return {
            "success": True,
            "status": "completed",
            "message": "Database created and configured successfully",
            "database": request.database_name,
            "host": request.host,
            "port": request.port,
            "credentials_file": setup_result.get("credentials_file"),
            "migrations": migration_result.get("success", False),
            "warnings": setup_result.get("warnings", []) + migration_result.get("warnings", []),
            "config_backup": str(backup_path),
        }

    except (ImportError, OSError, ValueError) as e:
        logger.error(f"Database setup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database setup failed: {e!s}") from e


@router.get("/verify")
async def verify_database_setup() -> dict:
    """
    Verify database setup from CLI installation.

    Reads credentials from .env file (server-side only, never sent to client).
    Tests connection to verify database exists and is accessible.
    Checks schema migration status.

    This endpoint is called by the wizard DatabaseStep to verify what
    the CLI installer already created. NO credential input from user.

    Security: Credentials are read from environment variables (loaded from .env
    at startup) and NEVER sent to the frontend. Only non-sensitive metadata
    (database name, host, port, version, table count) is returned.

    Returns:
        Verification result with connection status and database info
    """
    try:
        import psycopg2

        # Read credentials from environment (loaded from .env at startup)
        db_host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST")
        db_port = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT")
        db_name = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME")
        db_user = os.getenv("POSTGRES_USER") or os.getenv("DB_USER")
        db_password = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD")

        # Validate credentials exist
        if not all([db_host, db_port, db_name, db_user, db_password]):
            missing_vars = []
            if not db_host:
                missing_vars.append("POSTGRES_HOST/DB_HOST")
            if not db_port:
                missing_vars.append("POSTGRES_PORT/DB_PORT")
            if not db_name:
                missing_vars.append("POSTGRES_DB/DB_NAME")
            if not db_user:
                missing_vars.append("POSTGRES_USER/DB_USER")
            if not db_password:
                missing_vars.append("POSTGRES_PASSWORD/DB_PASSWORD")

            return {
                "success": False,
                "status": "missing_credentials",
                "message": "Database credentials not found in .env file. Please run CLI installer first.",
                "errors": [f"Missing environment variables: {', '.join(missing_vars)}"],
            }

        # Test connection using psycopg2 (raw connection test)
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=int(db_port),
                database=db_name,
                user=db_user,
                password=db_password,
                connect_timeout=5,
            )

            # Get PostgreSQL version
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version_string = cur.fetchone()[0]

                cur.execute("SHOW server_version_num;")
                version_num = int(cur.fetchone()[0])
                major_version = version_num // 10000

                # Count tables to verify schema migration
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                tables_count = cur.fetchone()[0]

            conn.close()

            # Verify schema is migrated (expect at least 10 tables from models.py)
            schema_migrated = tables_count >= 10

            logger.info(f"Database verification successful: {db_name}@{db_host}:{db_port}, {tables_count} tables")

            return {
                "success": True,
                "status": "verified",
                "message": "Database connection verified successfully",
                "database": db_name,
                "host": db_host,
                "port": int(db_port),
                "postgresql_version": major_version,
                "version_string": version_string,
                "schema_migrated": schema_migrated,
                "tables_count": tables_count,
            }

        except psycopg2.OperationalError as e:
            error_msg = str(e).lower()

            if "password authentication failed" in error_msg:
                return {
                    "success": False,
                    "status": "auth_failed",
                    "message": "Database authentication failed. Credentials in .env may be incorrect.",
                    "error": str(e),
                }
            if "database" in error_msg and "does not exist" in error_msg:
                return {
                    "success": False,
                    "status": "database_missing",
                    "message": f"Database '{db_name}' does not exist. Please run CLI installer first.",
                    "error": str(e),
                }
            if "could not connect" in error_msg or "connection refused" in error_msg:
                return {
                    "success": False,
                    "status": "connection_refused",
                    "message": "Cannot connect to PostgreSQL server. Is PostgreSQL running?",
                    "error": str(e),
                }
            return {
                "success": False,
                "status": "connection_error",
                "message": f"Database connection failed: {e!s}",
                "error": str(e),
            }

    except (ImportError, OSError, ValueError) as e:
        if isinstance(e, ImportError):
            raise HTTPException(status_code=500, detail="psycopg2 not installed") from None
        logger.error(f"Database verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database verification failed: {e!s}") from e
