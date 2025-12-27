"""
Database migration to add MessageQueue fields to Message table
Run this migration to update existing database schema
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def upgrade(database_url: str):
    """
    Add new MessageQueue fields to the messages table

    Args:
        database_url: Database connection URL
    """
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session, session.begin():
            logger.info("Starting MessageQueue migration...")

            # Check if columns already exist
            check_query = text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'messages'
                    AND column_name IN (
                        'processing_started_at',
                        'retry_count',
                        'max_retries',
                        'backoff_seconds',
                        'circuit_breaker_status'
                    )
                """)

            result = await session.execute(check_query)
            existing_columns = [row[0] for row in result]

            # Add new columns if they don't exist
            if "processing_started_at" not in existing_columns:
                await session.execute(text("""
                        ALTER TABLE messages
                        ADD COLUMN processing_started_at TIMESTAMP WITH TIME ZONE
                    """))
                logger.info("Added processing_started_at column")

            if "retry_count" not in existing_columns:
                await session.execute(text("""
                        ALTER TABLE messages
                        ADD COLUMN retry_count INTEGER DEFAULT 0
                    """))
                logger.info("Added retry_count column")

            if "max_retries" not in existing_columns:
                await session.execute(text("""
                        ALTER TABLE messages
                        ADD COLUMN max_retries INTEGER DEFAULT 3
                    """))
                logger.info("Added max_retries column")

            if "backoff_seconds" not in existing_columns:
                await session.execute(text("""
                        ALTER TABLE messages
                        ADD COLUMN backoff_seconds INTEGER DEFAULT 60
                    """))
                logger.info("Added backoff_seconds column")

            if "circuit_breaker_status" not in existing_columns:
                await session.execute(text("""
                        ALTER TABLE messages
                        ADD COLUMN circuit_breaker_status VARCHAR(20)
                    """))
                logger.info("Added circuit_breaker_status column")

            # Add new indexes for queue performance
            await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_message_processing_started
                    ON messages(processing_started_at)
                    WHERE processing_started_at IS NOT NULL
                """))
            logger.info("Added index on processing_started_at")

            await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_message_retry_count
                    ON messages(retry_count)
                    WHERE retry_count > 0
                """))
            logger.info("Added index on retry_count")

            # Add partial index for dead letter queue
            await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_message_dead_letter
                    ON messages(status)
                    WHERE status = 'dead_letter'
                """))
            logger.info("Added dead letter queue index")

            # Update existing messages to have default values
            await session.execute(text("""
                    UPDATE messages
                    SET retry_count = 0,
                        max_retries = 3,
                        backoff_seconds = 60
                    WHERE retry_count IS NULL
                """))

            await session.commit()
            logger.info("Migration completed successfully!")

    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise
    finally:
        await engine.dispose()


async def downgrade(database_url: str):
    """
    Remove MessageQueue fields from the messages table

    Args:
        database_url: Database connection URL
    """
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session, session.begin():
            logger.info("Rolling back MessageQueue migration...")

            # Drop indexes
            await session.execute(text("""
                    DROP INDEX IF EXISTS idx_message_processing_started
                """))

            await session.execute(text("""
                    DROP INDEX IF EXISTS idx_message_retry_count
                """))

            await session.execute(text("""
                    DROP INDEX IF EXISTS idx_message_dead_letter
                """))

            # Drop columns
            await session.execute(text("""
                    ALTER TABLE messages
                    DROP COLUMN IF EXISTS processing_started_at,
                    DROP COLUMN IF EXISTS retry_count,
                    DROP COLUMN IF EXISTS max_retries,
                    DROP COLUMN IF EXISTS backoff_seconds,
                    DROP COLUMN IF EXISTS circuit_breaker_status
                """))

            await session.commit()
            logger.info("Rollback completed successfully!")

    except Exception as e:
        logger.exception(f"Rollback failed: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """
    Run the migration
    """
    import os
    import sys

    # Get database URL from environment or command line
    if len(sys.argv) > 2:
        database_url = sys.argv[1]
        action = sys.argv[2]
    else:
        # Default to SQLite for local development
        db_path = os.path.join(os.path.dirname(__file__), "..", "giljo_mcp.db")
    # SQLite fallback removed; migrations should target PostgreSQL only
    raise RuntimeError("SQLite fallback removed; use PostgreSQL database URL for migrations")
        action = "upgrade"

    if action == "upgrade":
        await upgrade(database_url)
    elif action == "downgrade":
        await downgrade(database_url)
    else:
        logger.error(f"Unknown action: {action}. Use 'upgrade' or 'downgrade'")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
