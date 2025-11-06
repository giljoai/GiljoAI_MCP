#!/usr/bin/env python3
"""
Test script to verify Alembic migration execution during installation.

This script simulates the installation flow:
1. Create fresh database
2. Run create_tables_async() (what install.py does)
3. Run Alembic migrations (new functionality)
4. Verify migration columns and constraints exist

Usage:
    python test_migration_execution.py
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def test_migration_execution():
    """Test that migrations run correctly after table creation."""
    print("\n" + "=" * 70)
    print("Testing Migration Execution During Installation")
    print("=" * 70 + "\n")

    # Use test database
    test_db_url = "postgresql://postgres:4010@localhost:5432/test_migration_execution"

    print(f"📋 Database URL: {test_db_url}\n")

    # Drop test database if exists
    print("🗑️  Dropping test database if exists...")
    try:
        admin_url = "postgresql://postgres:4010@localhost:5432/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            # Terminate connections first
            conn.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'test_migration_execution'
                  AND pid <> pg_backend_pid();
            """))
            # Drop database
            conn.execute(text("DROP DATABASE IF EXISTS test_migration_execution"))
        admin_engine.dispose()
        print("✅ Dropped existing test database\n")
    except Exception as e:
        print(f"⚠️  Could not drop database: {e}\n")

    # Create fresh test database
    print("🔨 Creating fresh test database...")
    try:
        admin_url = "postgresql://postgres:4010@localhost:5432/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text("CREATE DATABASE test_migration_execution"))
        admin_engine.dispose()
        print("✅ Created fresh test database\n")
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        return False

    # Step 1: Create tables using create_all (simulating install.py)
    print("📋 Step 1: Creating tables via Base.metadata.create_all()...")
    try:
        from src.giljo_mcp.database import DatabaseManager

        async def create_tables():
            db_manager = DatabaseManager(test_db_url, is_async=True)
            await db_manager.create_tables_async()
            await db_manager.close_async()

        asyncio.run(create_tables())
        print("✅ Tables created successfully\n")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

    # Step 2: Verify tables exist but migration columns do NOT
    print("🔍 Step 2: Verifying tables exist (pre-migration)...")
    try:
        engine = create_engine(test_db_url)
        inspector = inspect(engine)

        # Check agent_templates table exists
        tables = inspector.get_table_names()
        if 'agent_templates' not in tables:
            print("❌ agent_templates table not found")
            return False

        columns_before = {col['name'] for col in inspector.get_columns('agent_templates')}
        print(f"✅ agent_templates table exists")
        print(f"   Columns: {sorted(columns_before)}")

        # At this point, cli_tool and background_color should NOT exist
        # (they're added by migration 6adac1467121)
        if 'cli_tool' in columns_before:
            print("⚠️  WARNING: cli_tool column already exists (unexpected)")
        else:
            print("✅ cli_tool column NOT present (expected - added by migration)")

        if 'background_color' in columns_before:
            print("⚠️  WARNING: background_color column already exists (unexpected)")
        else:
            print("✅ background_color column NOT present (expected - added by migration)")

        engine.dispose()
        print()
    except Exception as e:
        print(f"❌ Failed to inspect tables: {e}")
        return False

    # Step 3: Run Alembic migrations (simulating new install.py functionality)
    print("🔄 Step 3: Running Alembic migrations (alembic upgrade head)...")
    try:
        # Set DATABASE_URL for alembic
        original_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = test_db_url

        # Run alembic upgrade head
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path.cwd())
        )

        # Restore original DATABASE_URL
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        else:
            os.environ.pop("DATABASE_URL", None)

        if proc.returncode == 0:
            print("✅ Migrations completed successfully")

            # Parse migration output
            migrations_applied = []
            for line in proc.stdout.split('\n'):
                if 'Running upgrade' in line:
                    migrations_applied.append(line.strip())
                    print(f"   {line.strip()}")

            if not migrations_applied:
                print("   No new migrations to apply (database already up to date)")
            print()
        else:
            print(f"❌ Migration failed")
            print(f"STDOUT: {proc.stdout}")
            print(f"STDERR: {proc.stderr}")
            return False

    except Exception as e:
        print(f"❌ Failed to run migrations: {e}")
        return False

    # Step 4: Verify migration columns and constraints now exist
    print("✅ Step 4: Verifying migration artifacts exist (post-migration)...")
    try:
        engine = create_engine(test_db_url)
        inspector = inspect(engine)

        # Check columns
        columns_after = {col['name'] for col in inspector.get_columns('agent_templates')}
        print(f"   Columns after migration: {sorted(columns_after)}")

        if 'cli_tool' not in columns_after:
            print("❌ FAILED: cli_tool column missing after migration")
            return False
        print("✅ cli_tool column exists")

        if 'background_color' not in columns_after:
            print("❌ FAILED: background_color column missing after migration")
            return False
        print("✅ background_color column exists")

        # Check CHECK constraint
        constraints = inspector.get_check_constraints('agent_templates')
        constraint_names = {c['name'] for c in constraints}

        if 'check_cli_tool' not in constraint_names:
            print("❌ FAILED: check_cli_tool constraint missing")
            return False
        print("✅ check_cli_tool constraint exists")

        # Verify alembic_version table
        if 'alembic_version' not in inspector.get_table_names():
            print("❌ FAILED: alembic_version table missing")
            return False
        print("✅ alembic_version table exists")

        # Check version is set
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            if not version:
                print("❌ FAILED: alembic_version is empty")
                return False
            print(f"✅ Current migration version: {version}")

        engine.dispose()
        print()
    except Exception as e:
        print(f"❌ Failed to verify migration artifacts: {e}")
        return False

    print("=" * 70)
    print("✅ ALL TESTS PASSED - Migration execution works correctly!")
    print("=" * 70 + "\n")

    # Cleanup
    print("🧹 Cleaning up test database...")
    try:
        admin_url = "postgresql://postgres:4010@localhost:5432/postgres"
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'test_migration_execution'
                  AND pid <> pg_backend_pid();
            """))
            conn.execute(text("DROP DATABASE IF EXISTS test_migration_execution"))
        admin_engine.dispose()
        print("✅ Test database cleaned up\n")
    except Exception as e:
        print(f"⚠️  Could not cleanup database: {e}\n")

    return True


if __name__ == "__main__":
    success = test_migration_execution()
    sys.exit(0 if success else 1)
