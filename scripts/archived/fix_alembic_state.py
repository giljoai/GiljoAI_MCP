"""
Fix Alembic migration state by stamping database with current head
"""

import sys
from pathlib import Path


# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from alembic import command
from alembic.config import Config


def fix_alembic_state():
    """Stamp database with latest migration"""
    print("Fixing Alembic migration state...")

    # Load Alembic config
    alembic_cfg = Config("alembic.ini")

    # Check if alembic_version table exists and what's in it
    from sqlalchemy import text

    from src.giljo_mcp.database import DatabaseManager

    db_manager = DatabaseManager()

    async def check_and_stamp():
        async with db_manager.get_session_async() as session:
            # Check if alembic_version table exists
            result = await session.execute(
                text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'alembic_version'
                )
            """)
            )
            table_exists = result.scalar()

            if table_exists:
                # Check current version
                result = await session.execute(text("SELECT * FROM alembic_version"))
                rows = result.fetchall()
                print(f"Current alembic_version entries: {rows}")

                if not rows:
                    print("No version recorded. Stamping with f7f0422fda1e (latest before alias migration)")
                    command.stamp(alembic_cfg, "f7f0422fda1e")
                else:
                    print(f"Database is at version: {rows[0][0]}")
            else:
                print("alembic_version table doesn't exist. Creating and stamping...")
                command.stamp(alembic_cfg, "f7f0422fda1e")

    import asyncio

    asyncio.run(check_and_stamp())

    print("\nNow you can run: python run_alembic_migration.py upgrade")


if __name__ == "__main__":
    fix_alembic_state()
