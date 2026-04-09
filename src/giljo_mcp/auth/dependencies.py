# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
FastAPI dependencies for authentication.

This module provides dependency functions for extracting and validating
user authentication from JWT cookies or API key headers.

Authentication Methods (v3.0 Unified):
1. JWT Cookie (web users): httpOnly cookie containing access token
2. API Key Header (MCP tools): X-API-Key header with gk_ prefixed key

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

from src.giljo_mcp.api_key_utils import verify_api_key
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models import APIKey, User

logger = logging.getLogger(__name__)


async def get_db_session(request: Request = None):
    """Get database session dependency from app state

    Args:
        request: FastAPI request (to access app state)

    Yields:
        Database session from shared app state db_manager

    Raises:
        HTTPException: 503 if database not initialized (setup mode)

    Note:
        This dependency properly handles GeneratorExit when HTTPException
        is raised in endpoints, ensuring database sessions are always
        cleaned up and returned to the connection pool.
    """
    # Get db_manager from app state (shared instance)
    try:
        db_manager = request.app.state.api_state.db_manager
    except AttributeError as e:
        # Fallback if app state not available
        logger.exception("db_manager not available in app state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized - system may be in setup mode",
        ) from e

    if db_manager is None:
        logger.error("db_manager is None - setup mode active")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized - complete setup wizard first",
        )

    # Use the shared db_manager instance - get_session_async handles all cleanup
    # including GeneratorExit (BaseException) from FastAPI HTTPException
    async with db_manager.get_session_async() as session:
        yield session


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Get current user from JWT cookie or API key header.

    Authentication Priority (v3.0 Unified):
    1. Try JWT cookie (web users)
    2. Try API key header (MCP tools)
    3. Return 401 if no valid authentication found

    Args:
        request: FastAPI request (to check client IP)
        access_token: JWT token from httpOnly cookie
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: 401 if authentication fails

    Example:
        >>> user = await get_current_user(request, access_token="jwt_token", ...)
        >>> user.username
        'admin'
    """
    # DIAGNOSTIC: Log incoming auth attempt
    logger.info(
        "[AUTH] get_current_user called - path: %s, cookie: %s, api_key: %s, auth_header: %s",
        request.url.path,
        bool(access_token),
        bool(x_api_key),
        bool(authorization),
    )

    # Try JWT cookie first (web users)
    if access_token:
        logger.info("[AUTH] Attempting JWT cookie authentication")
        try:
            payload = JWTManager.verify_token(access_token)
            user_id = payload["sub"]  # Keep as string - User.id is String(36), not UUID
            logger.info(f"[AUTH] JWT valid - user_id: {user_id}")

            # Query user from database
            from sqlalchemy import select

            stmt = select(User).where(User.id == user_id, User.is_active)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.info(f"[AUTH] JWT SUCCESS - User: {user.username}, Tenant: {user.tenant_key}")
                return user
            logger.warning(f"[AUTH] JWT FAILED - User not found: {user_id}")
        except HTTPException as e:
            # Token verification failed - continue to API key check
            logger.warning(f"[AUTH] JWT verification failed: {e.detail}")
        except (ValueError, KeyError) as e:
            logger.error(f"[AUTH] JWT authentication error: {e}", exc_info=True)

    # Try Authorization: Bearer <token> header (CLI / API clients)
    bearer_token: Optional[str] = None
    if authorization and str(authorization).lower().startswith("bearer "):
        bearer_token = str(authorization).split(" ", 1)[1].strip()

    if bearer_token and not access_token:
        logger.info("[AUTH] Attempting Authorization Bearer JWT authentication")
        try:
            payload = JWTManager.verify_token(bearer_token)
            user_id = payload["sub"]
            from sqlalchemy import select

            stmt = select(User).where(User.id == user_id, User.is_active)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.info("[AUTH] Bearer JWT SUCCESS - User: %s, Tenant: %s", user.username, user.tenant_key)
                return user
            logger.warning("[AUTH] Bearer JWT FAILED - User not found: %s", user_id)
        except HTTPException as e:
            logger.warning("[AUTH] Bearer JWT verification failed: %s", e.detail)
        except (ValueError, KeyError) as e:
            logger.error("[AUTH] Bearer JWT authentication error: %s", e, exc_info=True)

    # Try API key header (MCP tools)
    if x_api_key:
        try:
            # Query all active, non-expired API keys (optimized with index)
            from sqlalchemy import func, or_, select

            stmt = select(APIKey).where(
                APIKey.is_active, or_(APIKey.expires_at > func.now(), APIKey.expires_at.is_(None))
            )
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
                        # Log IP address for security tracking (passive, non-blocking)
                        try:
                            from api.endpoints.mcp_session import MCPSessionManager

                            ip_logger = MCPSessionManager(db)
                            client_ip = request.client.host if request.client else "unknown"
                            await ip_logger.log_ip(str(key_record.id), client_ip)
                        except (ImportError, AttributeError, OSError):
                            logger.debug("IP logging failed for API key auth (non-blocking)")
                        return user
                    logger.warning(f"API key valid but user inactive: {key_record.user_id}")
                    break

            logger.warning("Invalid API key provided")
        except (ValueError, KeyError):
            logger.exception("API key authentication error")

    # No valid authentication found
    logger.error(
        f"[AUTH] FAILED - No valid authentication found (path: {request.url.path}, cookie: {bool(access_token)}, api_key: {bool(x_api_key)})"
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please login or provide a valid API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """
    Get current user and verify they are active.

    This dependency ensures user exists and is_active=True.
    Use this for endpoints that require an authenticated user.

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
            detail="This endpoint requires authentication (not available in localhost mode)",
        )

    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    return current_user


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
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
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required. Your role: " + current_user.role
        )
    return current_user


async def get_current_user_optional(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.

    This is a non-raising version of get_current_user for optional auth endpoints.

    Args:
        request: FastAPI request
        access_token: JWT token from cookie
        x_api_key: API key from header
        authorization: Authorization: Bearer <token> header
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
        return await get_current_user(
            request=request,
            access_token=access_token,
            x_api_key=x_api_key,
            authorization=authorization,
            db=db,
        )
    except HTTPException:
        return None
