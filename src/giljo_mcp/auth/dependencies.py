"""
FastAPI dependencies for authentication.

This module provides dependency functions for extracting and validating
user authentication from JWT cookies or API key headers.

Authentication Methods:
1. JWT Cookie (web users): httpOnly cookie containing access token
2. API Key Header (MCP tools): X-API-Key header with gk_ prefixed key
3. Localhost Bypass: Requests from 127.0.0.1 bypass authentication

Multi-Tenant Isolation:
All authenticated users are scoped to a tenant_key, which is used to
filter database queries and ensure data isolation.

Usage Example:
    from fastapi import APIRouter, Depends
    from giljo_mcp.auth.dependencies import get_current_user, require_admin

    router = APIRouter()

    @router.get("/protected")
    async def protected_endpoint(user: User = Depends(get_current_user)):
        return {"message": f"Hello {user.username}"}

    @router.post("/admin-only")
    async def admin_only(user: User = Depends(require_admin)):
        return {"message": "Admin access granted"}
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.api_key_utils import verify_api_key
from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.models import APIKey, User


logger = logging.getLogger(__name__)


async def get_db_session():
    """Get database session dependency"""
    import os
    from giljo_mcp.database import DatabaseManager

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    async with db_manager.get_session_async() as session:
        yield session


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Get current user from JWT cookie or API key header.

    Authentication Priority:
    1. Check if localhost bypass (127.0.0.1 = no auth required)
    2. Try JWT cookie (web users)
    3. Try API key header (MCP tools)
    4. Return None if no valid authentication found

    Args:
        request: FastAPI request (to check client IP)
        access_token: JWT token from httpOnly cookie
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object if authenticated, None if localhost bypass

    Raises:
        HTTPException: 401 if authentication fails (not localhost)

    Example:
        >>> user = await get_current_user(request, access_token="jwt_token", ...)
        >>> user.username
        'admin'
    """
    # Check if localhost bypass (127.0.0.1 = no auth)
    client_host = request.client.host if request.client else None
    if client_host in ["127.0.0.1", "localhost", "::1"]:
        logger.debug(f"Localhost bypass: {client_host}")
        # Return None to indicate localhost bypass (no user required)
        # Endpoints can check `if user is None:` for localhost mode
        return None

    # Try JWT cookie first (web users)
    if access_token:
        try:
            payload = JWTManager.verify_token(access_token)
            user_id = payload["sub"]  # Keep as string - User.id is String(36), not UUID

            # Query user from database
            from sqlalchemy import select
            stmt = select(User).where(User.id == user_id, User.is_active == True)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.debug(f"Authenticated via JWT: {user.username}")
                return user
            else:
                logger.warning(f"JWT valid but user not found: {user_id}")
        except HTTPException:
            # Token verification failed - continue to API key check
            logger.debug("JWT verification failed, trying API key")
        except Exception as e:
            logger.error(f"JWT authentication error: {e}")

    # Try API key header (MCP tools)
    if x_api_key:
        try:
            # Query all active API keys (optimized with index)
            from sqlalchemy import select
            stmt = select(APIKey).where(APIKey.is_active == True)
            result = await db.execute(stmt)
            api_keys = result.scalars().all()

            # Verify key using constant-time comparison
            for key_record in api_keys:
                if verify_api_key(x_api_key, key_record.key_hash):
                    # Update last_used timestamp
                    key_record.last_used = datetime.now(timezone.utc)
                    await db.commit()

                    # Get associated user
                    stmt = select(User).where(User.id == key_record.user_id)
                    result = await db.execute(stmt)
                    user = result.scalar_one_or_none()

                    if user and user.is_active:
                        logger.debug(f"Authenticated via API key: {user.username} ({key_record.name})")
                        return user
                    else:
                        logger.warning(f"API key valid but user inactive: {key_record.user_id}")
                        break

            logger.warning(f"Invalid API key provided")
        except Exception as e:
            logger.error(f"API key authentication error: {e}")

    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please login or provide a valid API key.",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active.

    This dependency ensures user exists and is_active=True.
    Use this for endpoints that require a real user (not localhost bypass).

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object

    Raises:
        HTTPException: 401 if user is None (localhost) or inactive

    Example:
        @router.get("/api/me")
        async def get_me(user: User = Depends(get_current_active_user)):
            return user
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint requires authentication (not available in localhost mode)"
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require admin role for endpoint access.

    This dependency ensures user is authenticated and has admin role.

    Args:
        current_user: User from get_current_active_user dependency

    Returns:
        Admin user object

    Raises:
        HTTPException: 403 if user is not admin

    Example:
        @router.post("/api/users")
        async def create_user(user: User = Depends(require_admin)):
            # Only admins can create users
            pass
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Your role: " + current_user.role
        )
    return current_user


async def get_current_user_optional(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.

    This is a non-raising version of get_current_user for optional auth endpoints.

    Args:
        request: FastAPI request
        access_token: JWT token from cookie
        x_api_key: API key from header
        db: Database session

    Returns:
        User if authenticated, None otherwise

    Example:
        @router.get("/api/public-or-private")
        async def mixed_endpoint(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello {user.username}"}
            else:
                return {"message": "Hello anonymous"}
    """
    try:
        return await get_current_user(request, access_token, x_api_key, db)
    except HTTPException:
        return None
