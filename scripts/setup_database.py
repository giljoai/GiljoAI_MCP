#!/usr/bin/env python
"""
Database setup script for GiljoAI MCP v3.0
Creates database, users, and grants necessary permissions
"""

import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql


# Database configuration
DB_NAME = "giljo_mcp"
DB_USER = "giljo_user"
DB_OWNER = "giljo_owner"
USER_PASSWORD = "4010"
ADMIN_PASSWORD = "4010"


def create_database_and_users():
    """Create the giljo_mcp database and required users."""

    print("=" * 60)
    print("  GiljoAI MCP Database Setup")
    print("=" * 60)

    try:
        # Connect as postgres admin
        print("\n[1] Connecting to PostgreSQL as admin...")
        conn = psycopg2.connect(
            host="localhost", port=5432, database="postgres", user="postgres", password=ADMIN_PASSWORD
        )
        conn.autocommit = True
        cur = conn.cursor()
        print("[SUCCESS] Connected to PostgreSQL")

        # Check if database exists
        print("\n[2] Checking if database exists...")
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone()

        if exists:
            print(f"[SUCCESS] Database '{DB_NAME}' already exists")
        else:
            print(f"Creating database '{DB_NAME}'...")
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"[SUCCESS] Database '{DB_NAME}' created successfully")

        # Check and create users
        print("\n[3] Setting up database users...")

        # Check if giljo_user exists
        cur.execute("SELECT 1 FROM pg_user WHERE usename = %s", (DB_USER,))
        if cur.fetchone():
            print(f"[SUCCESS] User '{DB_USER}' already exists")
            # Update password to ensure it's correct
            cur.execute(sql.SQL("ALTER USER {} WITH PASSWORD %s").format(sql.Identifier(DB_USER)), (USER_PASSWORD,))
            print(f"[SUCCESS] Password updated for '{DB_USER}'")
        else:
            cur.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(DB_USER)), (USER_PASSWORD,))
            print(f"[SUCCESS] User '{DB_USER}' created")

        # Check if giljo_owner exists
        cur.execute("SELECT 1 FROM pg_user WHERE usename = %s", (DB_OWNER,))
        if cur.fetchone():
            print(f"[SUCCESS] User '{DB_OWNER}' already exists")
            # Update password
            cur.execute(sql.SQL("ALTER USER {} WITH PASSWORD %s").format(sql.Identifier(DB_OWNER)), (USER_PASSWORD,))
            print(f"[SUCCESS] Password updated for '{DB_OWNER}'")
        else:
            cur.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(DB_OWNER)), (USER_PASSWORD,))
            print(f"[SUCCESS] User '{DB_OWNER}' created")

        # Grant privileges on database
        print("\n[4] Granting database privileges...")
        cur.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(DB_NAME), sql.Identifier(DB_OWNER)
            )
        )
        print(f"[SUCCESS] Granted all privileges on '{DB_NAME}' to '{DB_OWNER}'")

        cur.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(DB_NAME), sql.Identifier(DB_USER))
        )
        print(f"[SUCCESS] Granted connect privilege on '{DB_NAME}' to '{DB_USER}'")

        # Close connection to postgres database
        cur.close()
        conn.close()

        # Connect to giljo_mcp database to set schema permissions
        print("\n[5] Setting schema permissions...")
        conn = psycopg2.connect(host="localhost", port=5432, database=DB_NAME, user="postgres", password=ADMIN_PASSWORD)
        conn.autocommit = True
        cur = conn.cursor()

        # Grant schema permissions
        cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(DB_USER)))
        cur.execute(sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(sql.Identifier(DB_USER)))
        cur.execute(sql.SQL("GRANT ALL ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(DB_USER)))
        cur.execute(sql.SQL("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO {}").format(sql.Identifier(DB_USER)))

        # Set default privileges for future objects
        cur.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {}").format(
                sql.Identifier(DB_USER)
            )
        )
        cur.execute(
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {}").format(
                sql.Identifier(DB_USER)
            )
        )

        print(f"[SUCCESS] Schema permissions granted to '{DB_USER}'")

        # Test connection as giljo_user
        print("\n[6] Testing connection as giljo_user...")
        cur.close()
        conn.close()

        test_conn = psycopg2.connect(
            host="localhost", port=5432, database=DB_NAME, user=DB_USER, password=USER_PASSWORD
        )
        test_conn.close()
        print(f"[SUCCESS] Successfully connected as '{DB_USER}'")

        print("\n" + "=" * 60)
        print("  Database setup completed successfully!")
        print("=" * 60)
        print(f"\nDatabase: {DB_NAME}")
        print(f"Users: {DB_USER}, {DB_OWNER}")
        print(f"Password: {USER_PASSWORD}")
        print("\nThe backend should now be able to connect to the database.")

        return True

    except psycopg2.Error as e:
        print(f"\n[ERROR] Database error: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False


def check_requirements():
    """Check if requirements.txt has the necessary dependencies."""
    print("\n[7] Checking requirements.txt...")
    req_file = Path(__file__).parent.parent / "requirements.txt"

    if not req_file.exists():
        print("[ERROR] requirements.txt not found!")
        return False

    content = req_file.read_text()
    missing = []

    # Check for required packages
    if "PyJWT" not in content:
        missing.append("PyJWT>=2.8.0")
    if "watchdog" not in content:
        missing.append("watchdog>=3.0.0")
    if "aiohttp" not in content:
        missing.append("aiohttp>=3.8.0")

    if missing:
        print(f"[ERROR] Missing dependencies in requirements.txt: {', '.join(missing)}")
        print("Adding missing dependencies...")

        with open(req_file, "a") as f:
            for dep in missing:
                f.write(f"\n{dep}")
        print("[SUCCESS] Added missing dependencies to requirements.txt")
    else:
        print("[SUCCESS] All required dependencies present in requirements.txt")

    return True


if __name__ == "__main__":
    print("\nGiljoAI MCP Database Setup Script")
    print("-" * 35)

    success = create_database_and_users()
    check_requirements()

    if success:
        print("\n[SUCCESS] Database setup complete. You can now start the backend.")
        sys.exit(0)
    else:
        print("\n[ERROR] Database setup failed. Please check the error messages above.")
        sys.exit(1)
