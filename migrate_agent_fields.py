"""
Database migration script to increase Agent.name and Agent.role field lengths.

This script updates the agents table to support longer agent names and roles
(from 50/100 chars to 200 chars each).

Usage:
    python migrate_agent_fields.py
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.config import load_config
from giljo_mcp.database import DatabaseManager


async def migrate_database():
    """Run the database migration."""
    print("Starting database migration...")

    # Load config
    config = load_config()
    db_config = config.get("database", {})

    # Initialize database manager
    db_manager = DatabaseManager(db_config)

    # SQL migration commands
    migrations = [
        "ALTER TABLE agents ALTER COLUMN name TYPE VARCHAR(200);",
        "ALTER TABLE agents ALTER COLUMN role TYPE VARCHAR(200);",
    ]

    try:
        # Execute migrations using text() for raw SQL
        from sqlalchemy import text

        async with db_manager.get_session_async() as session:
            for migration_sql in migrations:
                print(f"Executing: {migration_sql}")
                await session.execute(text(migration_sql))
            await session.commit()
            print("  ✓ All migrations executed successfully")

        print("\n✅ Migration completed successfully!")
        print("\nAgent table columns updated:")
        print("  • name: VARCHAR(100) → VARCHAR(200)")
        print("  • role: VARCHAR(50) → VARCHAR(200)")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check config.yaml database settings")
        print("3. Verify database user has ALTER TABLE permissions")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(migrate_database())
