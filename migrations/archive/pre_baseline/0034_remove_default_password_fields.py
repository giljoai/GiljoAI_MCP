"""
Database Migration: Remove default_password_active and password_changed_at columns
Handover 0034 - Eliminate admin/admin Legacy Pattern

Revision: 0034_remove_default_password_fields
Date: 2025-10-18
Author: Claude Code (Handover 0034)

Changes:
- Remove default_password_active column from setup_state table
- Remove password_changed_at column from setup_state table
- Optional: Clean up legacy admin/admin users (if desired)

Applies to: GiljoAI MCP v3.0+
"""

import asyncio
import logging
import sys
from pathlib import Path


# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def upgrade():
    """
    Apply migration: Remove default password tracking fields
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    # Convert to async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info("Starting migration 0034: Remove default_password_active fields")
    logger.info(f"Database URL: {database_url.split('@')[0]}@...")

    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        # Check if columns exist before attempting to drop
        logger.info("Checking if columns exist...")

        result = await conn.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'setup_state'
            AND column_name IN ('default_password_active', 'password_changed_at')
        """)
        )

        existing_columns = [row[0] for row in result.fetchall()]
        logger.info(f"Found existing columns: {existing_columns}")

        # Drop default_password_active column
        if "default_password_active" in existing_columns:
            logger.info("Dropping column: default_password_active")
            await conn.execute(
                text("""
                ALTER TABLE setup_state
                DROP COLUMN IF EXISTS default_password_active
            """)
            )
            logger.info("✓ Dropped default_password_active column")
        else:
            logger.info("Column default_password_active does not exist (already removed)")

        # Drop password_changed_at column
        if "password_changed_at" in existing_columns:
            logger.info("Dropping column: password_changed_at")
            await conn.execute(
                text("""
                ALTER TABLE setup_state
                DROP COLUMN IF EXISTS password_changed_at
            """)
            )
            logger.info("✓ Dropped password_changed_at column")
        else:
            logger.info("Column password_changed_at does not exist (already removed)")

        # Optional: Remove legacy admin/admin user (COMMENTED OUT - User decision)
        # Uncomment this section if you want to clean up the default admin user
        """
        logger.info("Checking for legacy admin/admin user...")

        result = await conn.execute(text('''
            SELECT id, username, role
            FROM users
            WHERE username = 'admin'
            AND role = 'admin'
            LIMIT 1
        '''))

        admin_user = result.fetchone()

        if admin_user:
            user_id, username, role = admin_user
            logger.warning(f"Found legacy admin user: {username} (ID: {user_id})")
            logger.warning("SKIPPING automatic deletion - manual cleanup recommended")
            logger.warning("To delete: DELETE FROM users WHERE id = '{user_id}'")

            # Uncomment to auto-delete:
            # await conn.execute(text(f"DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
            # logger.info("✓ Deleted legacy admin/admin user")
        else:
            logger.info("No legacy admin/admin user found")
        """

    await engine.dispose()

    logger.info("=" * 70)
    logger.info("Migration 0034 completed successfully!")
    logger.info("Schema changes:")
    logger.info("  - Removed: setup_state.default_password_active")
    logger.info("  - Removed: setup_state.password_changed_at")
    logger.info("=" * 70)


async def downgrade():
    """
    Rollback migration: Restore default password tracking fields

    WARNING: This is for emergency rollback only. Data will be initialized to defaults.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.warning("ROLLBACK: Restoring default_password_active fields")

    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        # Re-add default_password_active column
        logger.info("Adding column: default_password_active")
        await conn.execute(
            text("""
            ALTER TABLE setup_state
            ADD COLUMN IF NOT EXISTS default_password_active BOOLEAN DEFAULT FALSE NOT NULL
        """)
        )
        logger.info("✓ Added default_password_active column (default: FALSE)")

        # Re-add password_changed_at column
        logger.info("Adding column: password_changed_at")
        await conn.execute(
            text("""
            ALTER TABLE setup_state
            ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE
        """)
        )
        logger.info("✓ Added password_changed_at column (default: NULL)")

    await engine.dispose()

    logger.warning("=" * 70)
    logger.warning("Migration 0034 ROLLED BACK")
    logger.warning("Restored columns with default values:")
    logger.warning("  - default_password_active: FALSE (password not active)")
    logger.warning("  - password_changed_at: NULL")
    logger.warning("=" * 70)


def main():
    """
    Run migration

    Usage:
        python migrations/0034_remove_default_password_fields.py upgrade
        python migrations/0034_remove_default_password_fields.py downgrade
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrations/0034_remove_default_password_fields.py upgrade")
        print("  python migrations/0034_remove_default_password_fields.py downgrade")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        print("Use 'upgrade' or 'downgrade'")
        sys.exit(1)


if __name__ == "__main__":
    main()
