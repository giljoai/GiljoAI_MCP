"""
Localhost user management for zero-click authentication.

This module provides functionality to create and manage the system "localhost" user,
which is automatically authenticated for requests from 127.0.0.1 or ::1.

This enables zero-click authentication for local development and single-user setups,
matching the legacy LOCAL mode behavior from the 3-mode architecture.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User


logger = logging.getLogger(__name__)


async def ensure_localhost_user(db: AsyncSession) -> User:
    """
    Create or retrieve the system localhost user.

    This user is auto-logged in for requests from 127.0.0.1/::1.
    Idempotent - safe to call multiple times.

    The localhost user has the following characteristics:
    - Username: "localhost"
    - Email: "localhost@local"
    - No password (password_hash is None)
    - Admin role (full permissions)
    - System user flag set to True
    - Default tenant key

    Args:
        db: Async database session

    Returns:
        User: The localhost user instance

    Raises:
        Exception: If database operations fail
    """
    # Check if localhost user already exists
    user = await get_localhost_user(db)

    if user:
        logger.debug("Localhost user already exists")
        return user

    # Create new localhost user
    logger.info("Creating localhost system user")

    user = User(
        username="localhost",
        email="localhost@local",
        password_hash=None,  # No password - auto-login only
        role="admin",
        is_system_user=True,
        is_active=True,
        tenant_key="default",  # Use default tenant
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Localhost user created successfully (ID: {user.id})")

    return user


async def get_localhost_user(db: AsyncSession) -> Optional[User]:
    """
    Retrieve the localhost user if exists.

    Args:
        db: Async database session

    Returns:
        User | None: The localhost user or None if not found
    """
    result = await db.execute(select(User).where(User.username == "localhost"))
    return result.scalar_one_or_none()
