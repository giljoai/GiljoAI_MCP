"""
Database migration to add 'tool' column to agent_templates table.

Handover 0045 - Multi-Tool Agent Orchestration System
Phase 1: Database Schema Changes

This migration adds the 'tool' column to enable tool-based routing
(claude | codex | gemini) for agent templates.

Features:
- Idempotent (safe to run multiple times)
- Zero data loss (existing records get default='claude')
- Indexed for query performance
- Multi-tenant isolation maintained

Run: python -m scripts.migrate_add_tool_column
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def upgrade(database_url: str) -> None:
    """
    Add 'tool' column to agent_templates table.

    Steps:
    1. Check if column already exists (idempotent)
    2. Add column with default='claude'
    3. Create index for filtering performance
    4. Update any NULL values to 'claude' (safety)

    Args:
        database_url: PostgreSQL connection URL

    Raises:
        RuntimeError: If migration fails
    """
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session, session.begin():
            logger.info("=" * 80)
            logger.info("Starting tool column migration (Handover 0045)...")
            logger.info("=" * 80)

            # Check if column already exists (idempotent)
            check_query = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'agent_templates'
                AND column_name = 'tool'
            """)

            result = await session.execute(check_query)
            existing_columns = [row[0] for row in result]

            if "tool" in existing_columns:
                logger.info("Column 'tool' already exists - skipping creation")
                logger.info("Migration is idempotent - safe to run multiple times")
            else:
                # Add column with default value
                logger.info("Adding 'tool' column to agent_templates...")
                await session.execute(
                    text("""
                    ALTER TABLE agent_templates
                    ADD COLUMN tool VARCHAR(50) NOT NULL DEFAULT 'claude'
                """)
                )
                logger.info("Successfully added 'tool' column")

                # Update any existing records (belt and suspenders)
                update_result = await session.execute(
                    text("""
                    UPDATE agent_templates
                    SET tool = 'claude'
                    WHERE tool IS NULL
                """)
                )
                rows_updated = update_result.rowcount
                if rows_updated > 0:
                    logger.info(f"Updated {rows_updated} existing records with default tool='claude'")

            # Check if index exists
            check_index_query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'agent_templates'
                AND indexname = 'idx_template_tool'
            """)

            result = await session.execute(check_index_query)
            existing_indexes = [row[0] for row in result]

            if "idx_template_tool" in existing_indexes:
                logger.info("Index 'idx_template_tool' already exists - skipping creation")
            else:
                # Create index for tool-based filtering
                logger.info("Creating index on 'tool' column...")
                await session.execute(
                    text("""
                    CREATE INDEX idx_template_tool ON agent_templates(tool)
                """)
                )
                logger.info("Successfully created index 'idx_template_tool'")

            # Verify migration
            logger.info("")
            logger.info("Verifying migration...")

            # Count records by tool
            count_query = text("""
                SELECT tool, COUNT(*) as count
                FROM agent_templates
                GROUP BY tool
                ORDER BY tool
            """)
            result = await session.execute(count_query)
            tool_counts = list(result)

            if tool_counts:
                logger.info("Agent templates by tool:")
                for tool, count in tool_counts:
                    logger.info(f"  - {tool}: {count} templates")
            else:
                logger.info("  - No templates found (empty database)")

            # Verify index
            verify_index_query = text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'agent_templates'
                AND indexname = 'idx_template_tool'
            """)
            result = await session.execute(verify_index_query)
            index_info = result.fetchone()

            if index_info:
                logger.info(f"Index verified: {index_info[0]}")
                logger.info(f"Definition: {index_info[1]}")
            else:
                logger.error("Index verification failed!")

            await session.commit()
            logger.info("")
            logger.info("=" * 80)
            logger.info("Migration completed successfully!")
            logger.info("=" * 80)

    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise RuntimeError(f"Migration failed: {e}") from e
    finally:
        await engine.dispose()


async def downgrade(database_url: str) -> None:
    """
    Remove 'tool' column from agent_templates table.

    WARNING: This will delete data! Use only for rollback.

    Args:
        database_url: PostgreSQL connection URL

    Raises:
        RuntimeError: If rollback fails
    """
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session, session.begin():
            logger.warning("=" * 80)
            logger.warning("Rolling back tool column migration...")
            logger.warning("WARNING: This will delete the 'tool' column and its data!")
            logger.warning("=" * 80)

            # Drop index first
            logger.info("Dropping index 'idx_template_tool'...")
            await session.execute(
                text("""
                DROP INDEX IF EXISTS idx_template_tool
            """)
            )
            logger.info("Index dropped")

            # Drop column
            logger.info("Dropping 'tool' column...")
            await session.execute(
                text("""
                ALTER TABLE agent_templates
                DROP COLUMN IF EXISTS tool
            """)
            )
            logger.info("Column dropped")

            await session.commit()
            logger.info("")
            logger.info("=" * 80)
            logger.info("Rollback completed successfully!")
            logger.info("=" * 80)

    except Exception as e:
        logger.exception(f"Rollback failed: {e}")
        raise RuntimeError(f"Rollback failed: {e}") from e
    finally:
        await engine.dispose()


def get_database_url() -> str:
    """
    Get database URL from config.yaml or environment.

    Returns:
        PostgreSQL connection URL

    Raises:
        RuntimeError: If database URL cannot be determined
    """
    import os

    import yaml

    # Try environment variable first
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        logger.info("Using DATABASE_URL from environment")
        return db_url

    # Try config.yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                db_config = config.get("database", {})

                host = db_config.get("host", "localhost")
                port = db_config.get("port", 5432)
                database = db_config.get("database", "giljo_mcp")
                user = db_config.get("user", "postgres")
                password = db_config.get("password", "")

                db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
                logger.info(f"Using database URL from config.yaml: {host}:{port}/{database}")
                return db_url
        except Exception as e:
            logger.warning(f"Failed to read config.yaml: {e}")

    # Default fallback
    db_url = "postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp"
    logger.info("Using default database URL: localhost:5432/giljo_mcp")
    return db_url


async def main():
    """
    Run the migration script.

    Usage:
        python -m scripts.migrate_add_tool_column              # Upgrade
        python -m scripts.migrate_add_tool_column upgrade      # Upgrade
        python -m scripts.migrate_add_tool_column downgrade    # Rollback
    """
    # Determine action
    action = "upgrade"
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action not in ["upgrade", "downgrade"]:
            logger.error(f"Unknown action: {action}. Use 'upgrade' or 'downgrade'")
            sys.exit(1)

    # Get database URL
    try:
        database_url = get_database_url()
    except Exception as e:
        logger.error(f"Failed to get database URL: {e}")
        logger.error("Set DATABASE_URL environment variable or ensure config.yaml exists")
        sys.exit(1)

    # Run migration
    try:
        if action == "upgrade":
            await upgrade(database_url)
        elif action == "downgrade":
            # Confirm rollback
            logger.warning("")
            logger.warning("=" * 80)
            logger.warning("WARNING: You are about to ROLLBACK the migration!")
            logger.warning("This will DELETE the 'tool' column and all its data!")
            logger.warning("=" * 80)
            logger.warning("")
            confirm = input("Type 'yes' to confirm rollback: ")
            if confirm.lower() != "yes":
                logger.info("Rollback cancelled")
                sys.exit(0)
            await downgrade(database_url)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
