"""
Quick fix script to create database tables and setup_state record.
This is needed because the installer didn't create the tables, causing the API to start in setup mode.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Import database manager and models
from passlib.hash import bcrypt

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import SetupState, User


async def main():
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env file")
        sys.exit(1)

    print("Connecting to database...")
    db_manager = DatabaseManager(db_url, is_async=True)

    # STEP 1: Create all tables
    print("\n1. Creating database tables...")
    try:
        await db_manager.create_tables_async()
        print("[OK] All tables created successfully")
    except Exception as e:
        print(f"ERROR creating tables: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # STEP 2: Check if admin user exists, create if not
    print("\n2. Checking admin user...")
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select

        stmt = select(User).where(User.username == "admin")
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print("  Creating admin user (username: admin, password: admin)...")
            admin_user = User(
                id=str(uuid4()),
                username="admin",
                email=None,
                full_name="Administrator",
                password_hash=bcrypt.hash("admin"),
                role="admin",
                tenant_key="default",
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            session.add(admin_user)
            await session.commit()
            print("[OK] Admin user created")
        else:
            print(f"[OK] Admin user already exists: {admin_user.username}")

    # STEP 3: Check if setup_state exists, create if not
    print("\n3. Checking setup_state...")
    async with db_manager.get_session_async() as session:
        stmt = select(SetupState).where(SetupState.tenant_key == "default")
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print("[OK] setup_state record already exists:")
            print(f"  - completed: {existing.completed}")
            print(f"  - default_password_active: {existing.default_password_active}")
            print(f"  - setup_version: {existing.setup_version}")
        else:
            print("  Creating setup_state record...")
            setup_state = SetupState(
                id=str(uuid4()),
                tenant_key="default",
                completed=False,  # Not completed yet - needs password change
                default_password_active=True,  # Default password (admin/admin) is active
                password_changed_at=None,
                setup_version="3.0.0",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            session.add(setup_state)
            await session.commit()

            print("[OK] Created setup_state record:")
            print("  - tenant_key: default")
            print("  - completed: False")
            print("  - default_password_active: True")
            print("  - setup_version: 3.0.0")

    # Clean up
    await db_manager.close_async()

    print("\n[SUCCESS] Database setup complete! You can now:")
    print("   1. Restart the API server")
    print("   2. Visit http://localhost:7274")
    print("   3. Login with admin/admin")
    print("   4. Change the default password")
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
