#!/usr/bin/env python3
"""Reset PostgreSQL to fresh state - Delete all GiljoAI databases"""

import sys


try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True)
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connection details
HOST = "localhost"
PORT = 5432
USER = "postgres"
PASSWORD = "4010"

print("Connecting to PostgreSQL...")
print(f"Host: {HOST}:{PORT}")
print(f"User: {USER}")
print()

try:
    # Connect to postgres database (default)
    conn = psycopg2.connect(host=HOST, port=PORT, database="postgres", user=USER, password=PASSWORD)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Get list of all databases
    cursor.execute("""
        SELECT datname FROM pg_database
        WHERE datistemplate = false
        AND datname NOT IN ('postgres')
        ORDER BY datname;
    """)

    databases = [row[0] for row in cursor.fetchall()]

    if not databases:
        print("[OK] No user databases found - PostgreSQL is already clean!")
    else:
        print(f"Found {len(databases)} database(s) to remove:")
        for db in databases:
            print(f"  - {db}")

        print()
        response = input("Delete all these databases? [y/N]: ").strip().lower()

        if response == "y":
            print()
            for db in databases:
                print(f"Dropping database: {db}...")
                try:
                    # Terminate existing connections
                    cursor.execute(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = %s AND pid <> pg_backend_pid();
                    """,
                        (db,),
                    )

                    # Drop the database
                    cursor.execute('DROP DATABASE "%s"' % db)
                    print(f"  [OK] Dropped {db}")
                except Exception as e:
                    print(f"  [X] Failed to drop {db}: {e}")

            print()
            print("[OK] PostgreSQL reset complete!")
            print("[OK] Fresh install state - ready for new installation")
        else:
            print("Cancelled - no databases were deleted")

    cursor.close()
    conn.close()

except psycopg2.OperationalError as e:
    print(f"[X] Could not connect to PostgreSQL: {e}")
    print()
    print("Troubleshooting:")
    print("  1. Check PostgreSQL service is running")
    print("  2. Verify password is correct")
    print("  3. Check postgresql.conf allows local connections")
    sys.exit(1)

except Exception as e:
    print(f"[X] Error: {e}")
    sys.exit(1)
