#!/usr/bin/env python3
"""
Simple database migration script - rename completed to database_initialized
No fancy unicode characters for Windows compatibility
"""

import os

import psycopg2
from dotenv import load_dotenv


# Load environment
load_dotenv()

# Database connection
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    print("ERROR: DATABASE_URL not found in environment")
    exit(1)

# Parse DATABASE_URL (format: postgresql://user:pass@host:port/dbname)
parts = DB_URL.replace("postgresql://", "").split("@")
user_pass = parts[0].split(":")
host_port_db = parts[1].split("/")
host_port = host_port_db[0].split(":")

conn_params = {
    "user": user_pass[0],
    "password": user_pass[1],
    "host": host_port[0],
    "port": host_port[1],
    "database": host_port_db[1],
}

print("=" * 80)
print("DATABASE MIGRATION: Rename completed -> database_initialized")
print("=" * 80)

try:
    # Connect to database
    print("\n[1/6] Connecting to database...")
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = False
    cursor = conn.cursor()
    print("Connected successfully")

    # Step 1: Rename columns
    print("\n[2/6] Renaming columns...")
    cursor.execute("ALTER TABLE setup_state RENAME COLUMN completed TO database_initialized;")
    print("  - Renamed: completed -> database_initialized")

    cursor.execute("ALTER TABLE setup_state RENAME COLUMN completed_at TO database_initialized_at;")
    print("  - Renamed: completed_at -> database_initialized_at")

    # Step 2: Update constraint
    print("\n[3/6] Updating constraint...")
    cursor.execute("ALTER TABLE setup_state DROP CONSTRAINT IF EXISTS ck_completed_at_required;")
    print("  - Dropped old constraint: ck_completed_at_required")

    cursor.execute("""
        ALTER TABLE setup_state ADD CONSTRAINT ck_database_initialized_at_required
        CHECK ((database_initialized = false) OR (database_initialized = true AND database_initialized_at IS NOT NULL));
    """)
    print("  - Created new constraint: ck_database_initialized_at_required")

    # Step 3: Rename indexes
    print("\n[4/6] Renaming indexes...")
    cursor.execute("ALTER INDEX IF EXISTS idx_setup_completed RENAME TO idx_setup_database_initialized;")
    print("  - Renamed index: idx_setup_completed -> idx_setup_database_initialized")

    cursor.execute("ALTER INDEX IF EXISTS ix_setup_state_completed RENAME TO ix_setup_state_database_initialized;")
    print("  - Renamed index: ix_setup_state_completed -> ix_setup_state_database_initialized")

    # Step 4: Update column comments
    print("\n[5/6] Updating column comments...")
    cursor.execute("""
        COMMENT ON COLUMN setup_state.database_initialized IS
        'True if database tables have been initialized by install.py';
    """)
    cursor.execute("""
        COMMENT ON COLUMN setup_state.database_initialized_at IS
        'Timestamp when database was initialized';
    """)
    print("  - Updated column comments")

    # Commit transaction
    print("\n[6/6] Committing changes...")
    conn.commit()
    print("  - Transaction committed successfully")

    # Verify migration
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'setup_state'
        AND column_name LIKE '%database_initialized%'
        ORDER BY column_name;
    """)

    columns = cursor.fetchall()
    print("\nNew columns in setup_state table:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")

    cursor.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'setup_state'
        AND constraint_name LIKE '%database_initialized%';
    """)

    constraints = cursor.fetchall()
    print("\nNew constraints:")
    for const in constraints:
        print(f"  - {const[0]}")

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)

except Exception as e:
    print(f"\nERROR during migration: {e}")
    print("Rolling back transaction...")
    conn.rollback()
    exit(1)

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
