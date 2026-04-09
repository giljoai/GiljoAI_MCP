#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Create a test API key for manual testing."""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.api_key_utils import generate_api_key, hash_api_key
from src.giljo_mcp.config_manager import ConfigManager
from src.giljo_mcp.models.auth import APIKey, User


async def create_test_key():
    """Create a test API key."""
    # Load config
    config = ConfigManager()
    db_url = config.get_database_url().replace("postgresql://", "postgresql+asyncpg://")

    # Create engine
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get the first active user
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.is_active == True).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            print("ERROR: No active users found!")
            return None

        print(f"Creating API key for user: {user.username}")

        # Generate API key
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_prefix = api_key[:15]

        # Create API key record
        api_key_record = APIKey(
            id=str(uuid.uuid4()),
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Test API Key for E2E Testing",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions={},
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        session.add(api_key_record)
        await session.commit()

        print("SUCCESS: API Key Created Successfully!")
        print(f"   User: {user.username}")
        print(f"   Tenant: {user.tenant_key}")
        print(f"   API Key: {api_key}")
        print(f"   Key ID: {api_key_record.id}")
        print()
        print("Use this API key for testing:")
        print(f'export TEST_API_KEY="{api_key}"')

        return api_key


if __name__ == "__main__":
    api_key = asyncio.run(create_test_key())
