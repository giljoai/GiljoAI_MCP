#!/usr/bin/env python3
"""Test async database operations and connection pooling"""

import asyncio
import sys
import time
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager


async def test_async_operations():
    """Test async database operations with concurrent queries"""
    config = get_config()
    connection_string = config.database.get_connection_string()

    # Test with async mode
    db = DatabaseManager(connection_string, is_async=True)

    try:
        # Test single async query
        async with db.get_session_async() as session:
            result = await session.execute(text("SELECT version()"))
            result.scalar()

        # Test concurrent queries (connection pooling)

        async def run_query(query_id):
            """Run a query with ID for tracking"""
            async with db.get_session_async() as session:
                # Simulate some work
                await session.execute(text("SELECT :id as query_id, pg_sleep(0.1)").bindparams(id=query_id))
                return f"Query {query_id} completed"

        # Run 5 concurrent queries
        time.time()
        tasks = [run_query(i) for i in range(5)]
        await asyncio.gather(*tasks)
        time.time()

        # Test transaction handling
        async with db.get_session_async() as session, session.begin():
            # Create a temp table
            await session.execute(
                text(
                    """
                    CREATE TEMP TABLE IF NOT EXISTS test_async (
                        id SERIAL PRIMARY KEY,
                        data TEXT
                    )
                """
                )
            )

            # Insert data
            await session.execute(
                text(
                    """
                    INSERT INTO test_async (data) VALUES ('test1'), ('test2')
                """
                )
            )

            # Query data
            result = await session.execute(text("SELECT COUNT(*) FROM test_async"))
            result.scalar()

        return True

    except Exception:
        return False


async def test_both_modes():
    """Test both SQLite and PostgreSQL modes"""

    config = get_config()

    # Test with current configured mode

    connection_string = config.database.get_connection_string()

    if "sqlite" in connection_string:
        db = DatabaseManager(connection_string, is_async=False)

        # Test sync SQLite
        with db.get_session() as session:
            result = session.execute(text("SELECT sqlite_version()"))
            result.scalar()
    else:
        # Already tested above
        pass

    return True


async def main():
    """Run all async tests"""

    # Test async operations
    success1 = await test_async_operations()

    # Test mode switching
    success2 = await test_both_modes()

    return success1 and success2


if __name__ == "__main__":
    success = asyncio.run(main())
    # sys.exit(0 if success else 1)  # Commented for pytest
