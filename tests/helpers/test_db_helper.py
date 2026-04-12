# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
PostgreSQL Test Database Helper

Provides utilities for managing PostgreSQL test databases with proper isolation.
Each test gets a clean database state through transaction rollback.

CRITICAL SAFETY: This module includes guards to prevent accidental production database access.
"""

import asyncio
import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Base


# =============================================================================
# PRODUCTION DATABASE SAFETY GUARD
# =============================================================================
# CRITICAL: These checks prevent tests from ever connecting to production.
# DO NOT REMOVE OR BYPASS THESE CHECKS.

PRODUCTION_DB_NAME = "giljo_mcp"
TEST_DB_SUFFIX = "_test"
ALLOWED_TEST_DBS = {
    "giljo_mcp_test",
    "giljo_test",
    "postgres",
}  # postgres needed for admin operations, giljo_test for CI


def validate_database_name(database: str) -> None:
    """
    Validate that a database name is safe for testing.

    RAISES RuntimeError if database name matches production.
    This is a CRITICAL safety guard.

    Args:
        database: Database name to validate

    Raises:
        RuntimeError: If database name appears to be production
    """
    if database == PRODUCTION_DB_NAME:
        raise RuntimeError(
            f"SAFETY GUARD TRIGGERED: Attempted to connect to production database '{database}'!\n"
            f"Tests must ONLY use '{PRODUCTION_DB_NAME}{TEST_DB_SUFFIX}' or other test databases.\n"
            f"This check exists to prevent accidental data loss."
        )

    # Also check connection strings
    if f"/{PRODUCTION_DB_NAME}" in database and TEST_DB_SUFFIX not in database:
        raise RuntimeError(
            f"SAFETY GUARD TRIGGERED: Connection string appears to target production!\n"
            f"Found: '{database}'\n"
            f"Tests must ONLY connect to databases ending with '{TEST_DB_SUFFIX}'."
        )


def validate_connection_string(url: str) -> None:
    """
    Validate that a connection string targets a test database.

    RAISES RuntimeError if connection string targets production.

    Args:
        url: Database connection URL

    Raises:
        RuntimeError: If URL targets production database
    """
    # Extract database name from URL patterns like:
    # postgresql://user:pass@host:port/dbname
    # postgresql+asyncpg://user:pass@host:port/dbname
    match = re.search(r"/([^/?]+)(?:\?|$)", url)
    if match:
        db_name = match.group(1)
        validate_database_name(db_name)


class PostgreSQLTestHelper:
    """
    Helper for managing PostgreSQL test databases.

    Features:
    - Transaction-based test isolation (rollback after each test)
    - Automatic database creation/cleanup
    - Schema-based isolation for parallel tests when needed
    - Performance optimized for test suites
    """

    # Default test database configuration (local dev).
    # CI overrides via DATABASE_URL env var.
    DEFAULT_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "database": "giljo_mcp_test",
        "username": "postgres",
        "password": "4010",
    }

    @staticmethod
    def _config_from_env() -> dict | None:
        """Parse DATABASE_URL env var into config dict if set."""
        import os

        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            return None
        # Parse: postgresql://user:pass@host:port/dbname
        match = re.match(
            r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+?)(?:\?|$)",
            db_url,
        )
        if not match:
            return None
        return {
            "username": match.group(1),
            "password": match.group(2),
            "host": match.group(3),
            "port": int(match.group(4)),
            "database": match.group(5),
        }

    @staticmethod
    def get_test_db_url(database: str = "giljo_mcp_test", async_driver: bool = True) -> str:
        """
        Build PostgreSQL test database URL.

        Uses DATABASE_URL env var if set (CI), otherwise falls back to
        DEFAULT_CONFIG (local development).

        SAFETY: Validates database name to prevent production access.

        Args:
            database: Database name (default: giljo_mcp_test)
            async_driver: Use async driver (asyncpg) vs sync (psycopg2)

        Returns:
            PostgreSQL connection URL

        Raises:
            RuntimeError: If database name matches production
        """
        # CRITICAL SAFETY CHECK - prevent production database access
        if database not in ALLOWED_TEST_DBS:
            validate_database_name(database)

        # Use DATABASE_URL env var if available (CI), else local defaults
        env_config = PostgreSQLTestHelper._config_from_env()
        config = env_config if env_config else PostgreSQLTestHelper.DEFAULT_CONFIG.copy()
        config["database"] = database

        url = (
            (
                f"postgresql+asyncpg://{config['username']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['database']}"
            )
            if async_driver
            else (
                f"postgresql://{config['username']}:{config['password']}"
                f"@{config['host']}:{config['port']}/{config['database']}"
            )
        )

        return url

    @staticmethod
    async def ensure_test_database_exists():
        """
        Ensure the test database exists, create if it doesn't.

        This connects to the default 'postgres' database to create
        the test database if needed.
        """
        # Connect to default postgres database to create test database
        admin_url = PostgreSQLTestHelper.get_test_db_url(database="postgres")
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")

        try:
            async with admin_engine.connect() as conn:
                # Check if test database exists
                result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp_test'"))
                exists = result.scalar()

                if not exists:
                    # Create test database
                    await conn.execute(text("CREATE DATABASE giljo_mcp_test"))
        finally:
            await admin_engine.dispose()

    @staticmethod
    async def drop_test_database():
        """
        Drop the test database completely.

        USE WITH CAUTION - This removes all test data.
        Only use for cleanup after test runs.
        """
        admin_url = PostgreSQLTestHelper.get_test_db_url(database="postgres")
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")

        try:
            async with admin_engine.connect() as conn:
                # Terminate all connections to the test database
                await conn.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = 'giljo_mcp_test'
                        AND pid <> pg_backend_pid()
                        """
                    )
                )

                # Drop the database
                await conn.execute(text("DROP DATABASE IF EXISTS giljo_mcp_test"))
        finally:
            await admin_engine.dispose()

    @staticmethod
    async def create_test_tables(db_manager: DatabaseManager):
        """
        Create all tables in the test database.

        Args:
            db_manager: DatabaseManager instance for the test database
        """
        await db_manager.create_tables_async()

    @staticmethod
    async def drop_test_tables(db_manager: DatabaseManager):
        """
        Drop all tables in the test database.

        Args:
            db_manager: DatabaseManager instance for the test database
        """
        await db_manager.drop_tables_async()

    @staticmethod
    async def clean_all_tables(session: AsyncSession):
        """
        Clean all data from all tables (fast alternative to drop/recreate).

        This is faster than dropping and recreating tables.
        Uses TRUNCATE for speed.

        Args:
            session: Database session
        """
        # Get all table names
        table_names = [table.name for table in Base.metadata.sorted_tables]

        if table_names:
            # Disable foreign key checks, truncate all tables, re-enable
            await session.execute(text("SET session_replication_role = 'replica'"))

            for table_name in table_names:
                await session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))

            await session.execute(text("SET session_replication_role = 'origin'"))
            await session.commit()


class TransactionalTestContext:
    """
    Context manager for transactional test isolation.

    Each test runs in a transaction that is rolled back at the end,
    ensuring clean state for the next test.

    Usage:
        async with TransactionalTestContext(db_manager) as session:
            # Run test with session
            # Changes will be rolled back automatically
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize transactional context.

        Args:
            db_manager: DatabaseManager for test database
        """
        self.db_manager = db_manager
        self.connection = None
        self.transaction = None
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        """Start connection, transaction and return session."""
        # Get a connection from the engine
        self.connection = await self.db_manager.async_engine.connect()

        # Start a transaction on the connection
        self.transaction = await self.connection.begin()

        # Create session bound to this connection
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False)

        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Rollback transaction and close connection."""
        # Close session first
        if self.session:
            try:
                await self.session.close()
            except Exception:
                pass  # Ignore session close errors
            finally:
                self.session = None

        # Then rollback transaction
        if self.transaction:
            try:
                # Always rollback - this ensures clean state
                await self.transaction.rollback()
            except Exception:
                pass  # Ignore rollback errors
            finally:
                self.transaction = None

        # Finally close connection
        if self.connection:
            try:
                await self.connection.close()
            except Exception:
                pass  # Ignore connection close errors
            finally:
                self.connection = None


async def wait_for_database_ready(max_attempts: int = 30, delay: float = 1.0) -> bool:
    """
    Wait for PostgreSQL database to be ready.

    Useful for CI/CD environments where database may be starting up.

    Args:
        max_attempts: Maximum number of connection attempts
        delay: Delay between attempts in seconds

    Returns:
        True if database is ready, False if timeout
    """
    test_url = PostgreSQLTestHelper.get_test_db_url(database="postgres")

    for attempt in range(max_attempts):
        try:
            engine = create_async_engine(test_url)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            return True
        except Exception:
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
            continue

    return False
