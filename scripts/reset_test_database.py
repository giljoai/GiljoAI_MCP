"""
Script to reset the test database schema.

This drops and recreates the test database with the current SQLAlchemy models.
Use this when the test database schema gets out of sync with the models.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.helpers.test_db_helper import PostgreSQLTestHelper
from src.giljo_mcp.database import DatabaseManager


async def reset_test_database():
    """Drop and recreate the test database with current schema."""
    print("[1/3] Dropping test database...")
    try:
        await PostgreSQLTestHelper.drop_test_database()
        print("      SUCCESS: Test database dropped")
    except Exception as e:
        print(f"      WARNING: Error dropping test database (may not exist): {e}")

    print("\n[2/3] Creating test database...")
    try:
        await PostgreSQLTestHelper.ensure_test_database_exists()
        print("      SUCCESS: Test database created")
    except Exception as e:
        print(f"      ERROR: Error creating test database: {e}")
        return False

    print("\n[3/3] Creating tables from SQLAlchemy models...")
    try:
        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        await PostgreSQLTestHelper.create_test_tables(db_manager)
        await db_manager.close_async()
        print("      SUCCESS: Tables created")
    except Exception as e:
        print(f"      ERROR: Error creating tables: {e}")
        return False

    print("\n===== Test database reset complete! =====")
    return True


if __name__ == "__main__":
    success = asyncio.run(reset_test_database())
    sys.exit(0 if success else 1)
