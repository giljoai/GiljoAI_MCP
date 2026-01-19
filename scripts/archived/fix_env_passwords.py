#!/usr/bin/env python3
"""
Quick fix script to update .env with correct database passwords from credentials file.
This fixes the authentication error by syncing .env with the actual database passwords.
"""

import sys
from datetime import datetime
from pathlib import Path


def read_latest_credentials():
    """Read the most recent database credentials file."""
    try:
        credentials_dir = Path("installer/credentials")

        if not credentials_dir.exists():
            print(f"ERROR: Credentials directory not found: {credentials_dir}")
            return None

        # Find all credential files
        credential_files = list(credentials_dir.glob("db_credentials_*.txt"))

        if not credential_files:
            print("ERROR: No credential files found in installer/credentials/")
            return None

        # Get the most recent file
        latest_file = max(credential_files, key=lambda p: p.stat().st_mtime)
        print(f"Reading credentials from: {latest_file}")

        # Parse the credentials file
        credentials = {}
        with open(latest_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    credentials[key.strip()] = value.strip()

        return credentials

    except Exception as e:
        print(f"ERROR: Failed to read credentials: {e}")
        return None


def update_env_file(credentials):
    """Update .env file with correct passwords."""
    try:
        env_file = Path(".env")

        if not env_file.exists():
            print("ERROR: .env file not found")
            return False

        # Read current .env
        with open(env_file) as f:
            lines = f.readlines()

        # Get passwords from credentials
        owner_password = credentials.get("OWNER_PASSWORD")
        user_password = credentials.get("USER_PASSWORD")

        if not owner_password or not user_password:
            print("ERROR: Could not find passwords in credentials file")
            return False

        print("\nUpdating .env with:")
        print(f"  OWNER_PASSWORD: {owner_password}")
        print(f"  USER_PASSWORD: {user_password}")

        # Create backup
        backup_file = Path(f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        with open(backup_file, "w") as f:
            f.writelines(lines)
        print(f"\nBackup created: {backup_file}")

        # Update lines
        updated_lines = []
        updates_made = []

        for line in lines:
            original_line = line

            # Update password lines
            if line.startswith("POSTGRES_PASSWORD="):
                line = f"POSTGRES_PASSWORD={user_password}\n"
                updates_made.append("POSTGRES_PASSWORD")
            elif line.startswith("POSTGRES_OWNER_PASSWORD="):
                line = f"POSTGRES_OWNER_PASSWORD={owner_password}\n"
                updates_made.append("POSTGRES_OWNER_PASSWORD")
            elif line.startswith("DB_PASSWORD="):
                line = f"DB_PASSWORD={user_password}\n"
                updates_made.append("DB_PASSWORD")
            elif line.startswith("DATABASE_URL="):
                # Update the full connection string
                db_host = credentials.get("DATABASE_HOST", "localhost")
                db_port = credentials.get("DATABASE_PORT", "5432")
                db_name = credentials.get("DATABASE_NAME", "giljo_mcp")
                line = f"DATABASE_URL=postgresql://giljo_user:{user_password}@{db_host}:{db_port}/{db_name}\n"
                updates_made.append("DATABASE_URL")

            updated_lines.append(line)

        # Write updated .env
        with open(env_file, "w") as f:
            f.writelines(updated_lines)

        print("\n[OK] Updated .env successfully!")
        print(f"  Changed: {', '.join(set(updates_made))}")

        return True

    except Exception as e:
        print(f"ERROR: Failed to update .env: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("=" * 70)
    print("  GiljoAI MCP - Fix .env Database Passwords")
    print("=" * 70)
    print()

    # Read credentials
    credentials = read_latest_credentials()
    if not credentials:
        print("\nFailed to read credentials file.")
        return 1

    # Update .env
    if update_env_file(credentials):
        print("\n" + "=" * 70)
        print("  SUCCESS!")
        print("=" * 70)
        print()
        print("Your .env file has been updated with the correct database passwords.")
        print("You can now start the backend server successfully.")
        print()
        print("Try running: python start_backend.bat")
        print()
        return 0
    print("\nFailed to update .env file.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
