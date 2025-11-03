#!/usr/bin/env python3
"""
Migration Script for Handover 0088 - Thin Client Architecture

Adds job_metadata JSONB column to mcp_agent_jobs table.
Safe to run multiple times (idempotent).

Usage:
    python migrate_0088.py

Prerequisites:
    - PostgreSQL server running
    - Database 'giljo_mcp' exists
    - .env file configured (or environment variables set)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncpg
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_migration():
    """Run Handover 0088 database migration."""

    # Load environment variables
    load_dotenv()

    # Get database connection details
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'giljo_mcp')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD')

    if not db_password:
        logger.error("❌ DB_PASSWORD not set in environment or .env file")
        return False

    logger.info("=" * 60)
    logger.info("HANDOVER 0088 - THIN CLIENT ARCHITECTURE MIGRATION")
    logger.info("=" * 60)
    logger.info("")

    try:
        # Connect to database
        logger.info(f"📡 Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}...")
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )
        logger.info("✅ Connected successfully")
        logger.info("")

        # Check if column already exists
        logger.info("🔍 Checking if job_metadata column exists...")
        existing_column = await conn.fetchrow("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'mcp_agent_jobs'
            AND column_name = 'job_metadata'
        """)

        if existing_column:
            logger.info("✅ job_metadata column already exists - migration complete!")
            logger.info("")

            # Verify index
            logger.info("🔍 Checking GIN index...")
            existing_index = await conn.fetchrow("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'mcp_agent_jobs'
                AND indexname = 'idx_mcp_agent_jobs_job_metadata'
            """)

            if existing_index:
                logger.info("✅ GIN index exists")
            else:
                logger.info("⚠️  GIN index missing - creating now...")
                await conn.execute("""
                    CREATE INDEX idx_mcp_agent_jobs_job_metadata
                    ON mcp_agent_jobs USING gin(job_metadata)
                """)
                logger.info("✅ GIN index created")

            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ MIGRATION COMPLETE (Already Applied)")
            logger.info("=" * 60)

            await conn.close()
            return True

        # Add job_metadata column
        logger.info("📝 Adding job_metadata JSONB column...")
        await conn.execute("""
            ALTER TABLE mcp_agent_jobs
            ADD COLUMN job_metadata JSONB DEFAULT '{}'::jsonb NOT NULL
        """)
        logger.info("✅ Column added successfully")
        logger.info("")

        # Create GIN index for performance
        logger.info("📝 Creating GIN index for JSONB queries...")
        await conn.execute("""
            CREATE INDEX idx_mcp_agent_jobs_job_metadata
            ON mcp_agent_jobs USING gin(job_metadata)
        """)
        logger.info("✅ GIN index created successfully")
        logger.info("")

        # Migrate existing thin client data from handover_summary
        logger.info("📝 Migrating existing thin client data...")
        result = await conn.execute("""
            UPDATE mcp_agent_jobs
            SET job_metadata = COALESCE(handover_summary, '{}'::jsonb)
            WHERE job_metadata = '{}'::jsonb
            AND handover_summary IS NOT NULL
            AND (
                handover_summary ? 'field_priorities' OR
                handover_summary ? 'user_id' OR
                handover_summary ? 'tool' OR
                handover_summary ? 'created_via'
            )
        """)

        rows_affected = int(result.split()[-1])
        if rows_affected > 0:
            logger.info(f"✅ Migrated {rows_affected} rows with thin client data")
        else:
            logger.info("ℹ️  No existing thin client data to migrate")
        logger.info("")

        # Verify column was created
        logger.info("🔍 Verifying migration...")
        verify = await conn.fetchrow("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'mcp_agent_jobs'
            AND column_name = 'job_metadata'
        """)

        if verify:
            logger.info("✅ Verification successful:")
            logger.info(f"   - Column: {verify['column_name']}")
            logger.info(f"   - Type: {verify['data_type']}")
            logger.info(f"   - Nullable: {verify['is_nullable']}")
            logger.info(f"   - Default: {verify['column_default']}")
        else:
            logger.error("❌ Verification failed - column not found")
            await conn.close()
            return False

        logger.info("")

        # Close connection
        await conn.close()
        logger.info("✅ Database connection closed")
        logger.info("")

        logger.info("=" * 60)
        logger.info("✅ MIGRATION COMPLETE - Handover 0088")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Start the application: python startup.py")
        logger.info("2. Test thin client: Navigate to project → Stage Project")
        logger.info("3. Verify ~10 line prompts (not 3000 lines)")
        logger.info("")

        return True

    except asyncpg.exceptions.PostgresError as e:
        logger.error(f"❌ PostgreSQL Error: {e}")
        logger.error("")
        logger.error("Troubleshooting:")
        logger.error("1. Verify PostgreSQL is running")
        logger.error("2. Check connection details in .env file")
        logger.error("3. Ensure database 'giljo_mcp' exists")
        logger.error("4. Verify user has ALTER TABLE permissions")
        return False

    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        logger.error("")
        logger.error("Please check:")
        logger.error("1. .env file exists and is configured")
        logger.error("2. asyncpg is installed: pip install asyncpg")
        logger.error("3. Database is accessible")
        return False


def main():
    """Main entry point."""
    print("")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   HANDOVER 0088 - THIN CLIENT MIGRATION                  ║")
    print("║   Adds job_metadata JSONB column to mcp_agent_jobs       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print("")

    # Check if asyncpg is installed
    try:
        import asyncpg
    except ImportError:
        logger.error("❌ asyncpg not installed")
        logger.error("")
        logger.error("Install with: pip install asyncpg")
        logger.error("Or run: python install.py (full installation)")
        sys.exit(1)

    # Check if .env exists
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        logger.warning("⚠️  .env file not found")
        logger.warning("   Migration will use default values")
        logger.warning("   Ensure DB_PASSWORD is set in environment")
        print("")

    # Run migration
    success = asyncio.run(run_migration())

    if success:
        logger.info("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed")
        logger.error("   See errors above for details")
        sys.exit(1)


if __name__ == '__main__':
    main()
