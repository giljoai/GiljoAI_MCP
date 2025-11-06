#!/usr/bin/env python3
"""
Migration Runner: Rename setup_state.completed to database_initialized

This script executes the SQL migration using Python's psycopg2 driver.
It's a helper for the SQL migration file in migrations/rename_completed_to_database_initialized.sql

Usage:
    python run_migration.py --forward   # Apply migration
    python run_migration.py --rollback  # Revert migration
    python run_migration.py --verify    # Verify current state

Database: giljo_mcp
User: postgres
Password: 4010 (development)
"""

import argparse
import sys

import psycopg2


def get_connection():
    """Create database connection."""
    try:
        conn = psycopg2.connect(host="localhost", port=5432, database="giljo_mcp", user="postgres", password="4010")
        return conn
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)


def execute_migration_forward(conn):
    """Execute forward migration."""
    print("=" * 80)
    print("FORWARD MIGRATION: Rename completed → database_initialized")
    print("=" * 80)

    cursor = conn.cursor()

    try:
        # Step 1: Rename columns
        print("\n[1/4] Renaming columns...")
        cursor.execute("""
            ALTER TABLE setup_state
                RENAME COLUMN completed TO database_initialized;
        """)
        cursor.execute("""
            ALTER TABLE setup_state
                RENAME COLUMN completed_at TO database_initialized_at;
        """)
        print("✓ Columns renamed successfully")

        # Step 2: Update constraint
        print("\n[2/4] Updating constraints...")
        cursor.execute("""
            ALTER TABLE setup_state
                DROP CONSTRAINT IF EXISTS ck_completed_at_required;
        """)
        cursor.execute("""
            ALTER TABLE setup_state
                ADD CONSTRAINT ck_database_initialized_at_required
                CHECK (
                    (database_initialized = false) OR
                    (database_initialized = true AND database_initialized_at IS NOT NULL)
                );
        """)
        print("✓ Constraints updated successfully")

        # Step 3: Rename indexes
        print("\n[3/4] Renaming indexes...")
        cursor.execute("""
            ALTER INDEX IF EXISTS idx_setup_completed
                RENAME TO idx_setup_database_initialized;
        """)
        cursor.execute("""
            ALTER INDEX IF EXISTS idx_setup_incomplete
                RENAME TO idx_setup_database_incomplete;
        """)
        print("✓ Indexes renamed successfully")

        # Step 4: Add comments
        print("\n[4/4] Adding column comments...")
        cursor.execute("""
            COMMENT ON COLUMN setup_state.database_initialized IS
                'True when database tables have been created by installer (NOT setup wizard completion)';
        """)
        cursor.execute("""
            COMMENT ON COLUMN setup_state.database_initialized_at IS
                'Timestamp when database tables were created and initialized';
        """)
        print("✓ Comments added successfully")

        # Commit transaction
        conn.commit()
        print("\n" + "=" * 80)
        print("✓ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        conn.rollback()
        print(f"\n✗ ERROR during migration: {e}")
        print("Transaction rolled back - no changes made")
        sys.exit(1)
    finally:
        cursor.close()


def execute_migration_rollback(conn):
    """Execute rollback migration."""
    print("=" * 80)
    print("ROLLBACK MIGRATION: Rename database_initialized → completed")
    print("=" * 80)

    cursor = conn.cursor()

    try:
        # Step 1: Rename columns back
        print("\n[1/4] Renaming columns back...")
        cursor.execute("""
            ALTER TABLE setup_state
                RENAME COLUMN database_initialized TO completed;
        """)
        cursor.execute("""
            ALTER TABLE setup_state
                RENAME COLUMN database_initialized_at TO completed_at;
        """)
        print("✓ Columns renamed back successfully")

        # Step 2: Update constraint back
        print("\n[2/4] Updating constraints back...")
        cursor.execute("""
            ALTER TABLE setup_state
                DROP CONSTRAINT IF EXISTS ck_database_initialized_at_required;
        """)
        cursor.execute("""
            ALTER TABLE setup_state
                ADD CONSTRAINT ck_completed_at_required
                CHECK (
                    (completed = false) OR
                    (completed = true AND completed_at IS NOT NULL)
                );
        """)
        print("✓ Constraints updated back successfully")

        # Step 3: Rename indexes back
        print("\n[3/4] Renaming indexes back...")
        cursor.execute("""
            ALTER INDEX IF EXISTS idx_setup_database_initialized
                RENAME TO idx_setup_completed;
        """)
        cursor.execute("""
            ALTER INDEX IF EXISTS idx_setup_database_incomplete
                RENAME TO idx_setup_incomplete;
        """)
        print("✓ Indexes renamed back successfully")

        # Step 4: Remove comments
        print("\n[4/4] Removing column comments...")
        cursor.execute("""
            COMMENT ON COLUMN setup_state.completed IS NULL;
        """)
        cursor.execute("""
            COMMENT ON COLUMN setup_state.completed_at IS NULL;
        """)
        print("✓ Comments removed successfully")

        # Commit transaction
        conn.commit()
        print("\n" + "=" * 80)
        print("✓ ROLLBACK COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        conn.rollback()
        print(f"\n✗ ERROR during rollback: {e}")
        print("Transaction rolled back - no changes made")
        sys.exit(1)
    finally:
        cursor.close()


def verify_migration(conn):
    """Verify current database state."""
    print("=" * 80)
    print("VERIFICATION: Current setup_state table structure")
    print("=" * 80)

    cursor = conn.cursor()

    try:
        # Check columns
        print("\n[1/4] Checking columns...")
        cursor.execute("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'setup_state'
                AND column_name LIKE '%completed%'
                OR column_name LIKE '%database_initialized%'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()

        if columns:
            print("\nFound columns:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        else:
            print("  No relevant columns found")

        # Check constraints
        print("\n[2/4] Checking constraints...")
        cursor.execute("""
            SELECT
                con.conname AS constraint_name,
                pg_get_constraintdef(con.oid) AS constraint_definition
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'setup_state'
                AND (con.conname LIKE '%completed%' OR con.conname LIKE '%database_initialized%');
        """)
        constraints = cursor.fetchall()

        if constraints:
            print("\nFound constraints:")
            for constraint in constraints:
                print(f"  - {constraint[0]}")
                print(f"    {constraint[1]}")
        else:
            print("  No relevant constraints found")

        # Check indexes
        print("\n[3/4] Checking indexes...")
        cursor.execute("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'setup_state'
                AND (indexname LIKE '%completed%' OR indexname LIKE '%database_initialized%');
        """)
        indexes = cursor.fetchall()

        if indexes:
            print("\nFound indexes:")
            for idx in indexes:
                print(f"  - {idx[0]}")
                print(f"    {idx[1]}")
        else:
            print("  No relevant indexes found")

        # Check sample data
        print("\n[4/4] Checking sample data...")
        cursor.execute("""
            SELECT
                id,
                tenant_key,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'setup_state' AND column_name = 'completed'
                    ) THEN 'OLD SCHEMA'
                    WHEN EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'setup_state' AND column_name = 'database_initialized'
                    ) THEN 'NEW SCHEMA'
                    ELSE 'UNKNOWN'
                END as schema_version
            FROM setup_state
            LIMIT 1;
        """)
        sample = cursor.fetchone()

        if sample:
            print(f"\nSchema version detected: {sample[2]}")
            print(f"  - Tenant: {sample[1]}")
        else:
            print("  No data in setup_state table")

        print("\n" + "=" * 80)
        print("✓ VERIFICATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ ERROR during verification: {e}")
        sys.exit(1)
    finally:
        cursor.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration: Rename setup_state.completed to database_initialized"
    )
    parser.add_argument(
        "--forward", action="store_true", help="Execute forward migration (rename to database_initialized)"
    )
    parser.add_argument("--rollback", action="store_true", help="Execute rollback migration (rename back to completed)")
    parser.add_argument("--verify", action="store_true", help="Verify current database state (no changes)")

    args = parser.parse_args()

    if not any([args.forward, args.rollback, args.verify]):
        parser.print_help()
        sys.exit(1)

    # Get database connection
    conn = get_connection()

    try:
        if args.forward:
            execute_migration_forward(conn)
        elif args.rollback:
            execute_migration_rollback(conn)
        elif args.verify:
            verify_migration(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
