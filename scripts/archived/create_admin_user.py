#!/usr/bin/env python
"""
Create the first admin user for LAN authentication

Usage:
    python scripts/create_admin_user.py
"""

import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from uuid import uuid4

from passlib.hash import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from giljo_mcp.config_manager import get_config
from giljo_mcp.models import User


def create_admin():
    """Create the first admin user"""

    # Get database URL from config
    config = get_config()
    db_config = config.database

    # Build connection URL
    db_url = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.name}"

    print(f"Connecting to database: {db_config.host}:{db_config.port}/{db_config.name}")

    # Create engine and session
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if admin already exists
        existing_admin = session.query(User).filter(User.username == "admin").first()

        if existing_admin:
            print(f"✅ Admin user already exists: {existing_admin.username} (role: {existing_admin.role})")

            # Ask if user wants to update password
            update = input("Do you want to update the password? (y/n): ")
            if update.lower() == "y":
                new_password = input("Enter new password: ")
                existing_admin.password_hash = bcrypt.hash(new_password)
                session.commit()
                print("✅ Password updated successfully!")
            return

        # Create new admin user
        print("\n" + "=" * 60)
        print("Create First Admin User")
        print("=" * 60)

        username = input("Username (default: admin): ").strip() or "admin"
        password = input("Password (default: admin123): ").strip() or "admin123"
        email = input("Email (optional): ").strip() or None
        full_name = input("Full name (optional): ").strip() or None

        # Create user
        admin_user = User(
            id=uuid4(),
            username=username,
            email=email,
            password_hash=bcrypt.hash(password),
            full_name=full_name,
            role="admin",
            is_active=True,
            tenant_key="default",
        )

        session.add(admin_user)
        session.commit()

        print("\n✅ Admin user created successfully!")
        print(f"   Username: {username}")
        print("   Role: admin")
        print("   Tenant: default")
        print("\nYou can now log in at: http://localhost:7274/login")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_admin()
