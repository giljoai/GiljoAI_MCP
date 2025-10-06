"""
Database setup endpoints for setup wizard.

Handles:
- PostgreSQL connection testing
- Database creation and schema migration
- Config file updates with validated credentials
"""

import logging
import shutil
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict

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
async def test_database_connection(request: DatabaseSetupRequest) -> Dict:
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
        elif "could not connect" in error_msg or "connection refused" in error_msg:
            return {
                "success": False,
                "status": "connection_refused",
                "message": "Cannot connect to PostgreSQL server. Is PostgreSQL running?",
            }
        else:
            return {"success": False, "status": "error", "message": f"Connection failed: {str(e)}"}

    except ImportError:
        raise HTTPException(status_code=500, detail="psycopg2 not installed") from None

    except Exception as e:
        return {"success": False, "status": "error", "message": f"Connection test failed: {str(e)}"}


@router.post("/setup")
async def setup_database(request: DatabaseSetupRequest) -> Dict:
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
        backup_path = config_path.with_suffix(f".yaml.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
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

    except Exception as e:
        logger.error(f"Database setup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database setup failed: {str(e)}") from e
