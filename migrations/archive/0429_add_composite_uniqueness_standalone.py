"""
Migration 0429: Add composite uniqueness for agent_id + instance_number.

Handover 0429: Allow same agent_id across multiple instances for succession.

Changes:
1. Add new 'id' column as primary key (UUID)
2. Remove primary key from 'agent_id' (keep as indexed column)
3. Add unique constraint on (agent_id, instance_number)

CRITICAL: This is a breaking schema change. Backup database before running.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy import text

from src.giljo_mcp.database import DatabaseManager


async def run_migration(database="giljo_mcp"):
    """Run the migration to add composite uniqueness."""
    print(f"Starting migration 0429 on {database}: Add composite uniqueness...")

    # Use hardcoded test database URL (password: 4010)
    db_url = f"postgresql://postgres:***@localhost:5432/{database}"

    db_manager = DatabaseManager(database_url=db_url, is_async=True)

    try:
        async with db_manager.get_session_async() as session:
            # Step 1: Add new 'id' column (not null, with default)
            print("Step 1: Adding 'id' column as new primary key...")
            await session.execute(
                text(
                    """
                    ALTER TABLE agent_executions
                    ADD COLUMN id VARCHAR(36) DEFAULT gen_random_uuid()::text NOT NULL;
                    """
                )
            )
            await session.commit()

            # Step 2: Drop old primary key on agent_id
            print("Step 2: Dropping old primary key on agent_id...")
            await session.execute(
                text(
                    """
                    ALTER TABLE agent_executions
                    DROP CONSTRAINT agent_executions_pkey;
                    """
                )
            )
            await session.commit()

            # Step 3: Add new primary key on 'id'
            print("Step 3: Adding new primary key on 'id' column...")
            await session.execute(
                text(
                    """
                    ALTER TABLE agent_executions
                    ADD CONSTRAINT agent_executions_pkey PRIMARY KEY (id);
                    """
                )
            )
            await session.commit()

            # Step 4: Create index on agent_id (no longer primary key)
            print("Step 4: Creating index on agent_id...")
            await session.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_agent_executions_agent_id
                    ON agent_executions(agent_id);
                    """
                )
            )
            await session.commit()

            # Step 5: Add unique constraint on (agent_id, instance_number)
            print("Step 5: Adding unique constraint on (agent_id, instance_number)...")
            await session.execute(
                text(
                    """
                    ALTER TABLE agent_executions
                    ADD CONSTRAINT uq_agent_instance UNIQUE (agent_id, instance_number);
                    """
                )
            )
            await session.commit()

            print("Migration 0429 completed successfully!")
            return True

    except Exception as e:
        print(f"Migration 0429 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    # Support running on both main and test databases
    database = sys.argv[1] if len(sys.argv) > 1 else "giljo_mcp"
    success = asyncio.run(run_migration(database))
    sys.exit(0 if success else 1)
