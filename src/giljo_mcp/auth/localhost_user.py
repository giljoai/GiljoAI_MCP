"""
Localhost user management for legacy auth compatibility.

DEPRECATED: This module provides backward compatibility for the localhost_user
functionality that was removed in v3.0 unified architecture.

In v3.0, all connections require proper authentication credentials.
However, this module maintains the ensure_localhost_user function
for legacy auth_legacy.py compatibility.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import User

logger = logging.getLogger(__name__)


async def ensure_localhost_user(session: AsyncSession) -> Optional[User]:
    """
    Ensure localhost user exists for legacy auth compatibility.
    
    DEPRECATED: In v3.0 unified architecture, all users should use proper
    authentication. This function exists only for legacy compatibility.
    
    Args:
        session: Async database session
        
    Returns:
        User object for localhost user, or None if creation fails
    """
    try:
        # Try to find existing localhost user
        stmt = select(User).where(User.username == "localhost")
        result = await session.execute(stmt)
        localhost_user = result.scalar_one_or_none()
        
        if localhost_user:
            logger.debug("Found existing localhost user")
            return localhost_user
            
        # Create localhost user if it doesn't exist
        logger.info("Creating localhost user for legacy compatibility")
        localhost_user = User(
            username="localhost",
            email="localhost@system.local",
            is_active=True,
            is_system_user=True,  # Mark as system user
            role="admin",  # Give admin role for localhost
            tenant_key="default",  # Default tenant
            # Note: password_hash is None for system users
        )
        
        session.add(localhost_user)
        await session.commit()
        await session.refresh(localhost_user)
        
        logger.info(f"Created localhost user: {localhost_user.username}")
        return localhost_user
        
    except Exception as e:
        logger.error(f"Failed to ensure localhost user: {e}", exc_info=True)
        await session.rollback()
        return None