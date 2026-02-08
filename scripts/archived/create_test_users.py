#!/usr/bin/env python
"""
Create test users for authentication testing

Creates three test users:
- admin / admin123 (Admin role)
- developer / dev123 (Developer role)
- viewer / viewer123 (Viewer role)

Usage:
    python scripts/create_test_users.py
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


def create_test_users():
    """Create test users for authentication testing"""

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

    # Test users to create
    test_users = [
        {
            "username": "admin",
            "password": "admin123",
            "email": "admin@giljo.local",
            "full_name": "Admin User",
            "role": "admin",
        },
        {
            "username": "developer",
            "password": "dev123",
            "email": "dev@giljo.local",
            "full_name": "Developer User",
            "role": "developer",
        },
        {
            "username": "viewer",
            "password": "viewer123",
            "email": "viewer@giljo.local",
            "full_name": "Viewer User",
            "role": "viewer",
        },
    ]

    print("\n" + "=" * 60)
    print("Creating Test Users for Authentication Testing")
    print("=" * 60 + "\n")

    try:
        created_count = 0
        updated_count = 0

        for user_data in test_users:
            # Check if user already exists
            existing_user = session.query(User).filter(User.username == user_data["username"]).first()

            if existing_user:
                print(f"⚠️  User '{user_data['username']}' already exists")

                # Update password to ensure consistency
                existing_user.password_hash = bcrypt.hash(user_data["password"])
                existing_user.role = user_data["role"]
                existing_user.is_active = True
                updated_count += 1
                print(f"   ✅ Updated password and role to: {user_data['role']}")
            else:
                # Create new user
                new_user = User(
                    id=uuid4(),
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=bcrypt.hash(user_data["password"]),
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    is_active=True,
                    tenant_key="default",
                )

                session.add(new_user)
                created_count += 1
                print(f"✅ Created user: {user_data['username']} (role: {user_data['role']})")

        session.commit()

        print("\n" + "=" * 60)
        print("Test Users Setup Complete!")
        print(f"  Created: {created_count}")
        print(f"  Updated: {updated_count}")
        print("=" * 60)

        print("\nTest Credentials:")
        print("-" * 40)
        for user_data in test_users:
            print(f"  {user_data['username']:12} / {user_data['password']:12} ({user_data['role']})")
        print("-" * 40)

        print("\nLogin at: http://10.1.0.164:7274/login")
        print("Use the test checklist: tests/manual/test_auth_flows.md\n")

    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    create_test_users()
