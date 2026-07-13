# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
WebSocket Authentication Utilities (Phase 2 - Unified Auth)

Simplified authentication WITHOUT IP-based auto-login:
- During setup mode: Allow connections without auth (for progress updates)
- After setup: Require credentials for ALL connections (localhost and network treated identically)
"""

import logging
from typing import Any

from fastapi import HTTPException, WebSocket, WebSocketException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


async def get_setup_state(db: AsyncSession = None) -> dict[str, Any]:
    """
    Get current setup state from database.

    Returns:
        dict with database_initialized flag
    """
    if not db:
        # If no database session, assume database not initialized
        return {"database_initialized": False}

    try:
        from sqlalchemy import select

        from giljo_mcp.database import tenant_isolation_bypass
        from giljo_mcp.models import SetupState

        # This setup-state probe runs on the WebSocket auth path BEFORE any JWT is
        # decoded (the WS scope bypasses the HTTP AuthMiddleware entirely), so no
        # tenant context exists yet. Reading the tenant-scoped SetupState singleton
        # here is a deliberate pre-auth, cross-tenant probe — authorize it with a
        # scoped bypass rather than a JWT-derived tenant context.
        with tenant_isolation_bypass(
            db,
            reason="pre-auth setup-state probe precedes tenant resolution",
            models=(SetupState,),
        ):
            # Prefer explicit 'default' tenant row when present
            stmt_default = select(SetupState).where(SetupState.tenant_key == "default")
            result_default = await db.execute(stmt_default)
            setup_state = result_default.scalar_one_or_none()

            if setup_state is not None:
                return {"database_initialized": bool(getattr(setup_state, "database_initialized", False))}

            # Fallback: derive initialization from any SetupState row
            # Order by database_initialized desc so True wins
            stmt_any = select(SetupState.database_initialized).order_by(SetupState.database_initialized.desc()).limit(1)
            result_any = await db.execute(stmt_any)
            any_flag = result_any.scalar_one_or_none()
        if any_flag is not None:
            return {"database_initialized": bool(any_flag)}

        # Final fallback: no SetupState rows yet, but DB session exists → treat as initialized
        # Rationale: avoid incorrectly enabling setup-mode for authenticated environments
        logger.warning("[WS SETUP DEBUG] No SetupState rows found; treating database as initialized")
        return {"database_initialized": True}

    except (SQLAlchemyError, ValueError):
        # SEC-3001a item 5: fail CLOSED on a DB error. Returning
        # database_initialized=False here would route authenticate_websocket
        # into the unauthenticated setup-mode branch, so a transient DB fault on
        # a fully-initialized install would grant an unauth WS connection.
        # Treat as initialized -> credentials are required. The genuine-setup
        # path (db session absent) is handled by the `if not db` branch above
        # and is unaffected.
        logger.exception("Failed to get setup state; failing closed (require auth)")
        return {"database_initialized": True}


async def authenticate_websocket(websocket: WebSocket, db: AsyncSession = None) -> dict[str, Any]:
    """
    Authenticate WebSocket connection with unified logic.

    Phase 2: NO IP-based auto-login
    - During setup mode: Allow connection without auth (for progress updates)
    - After setup: Require credentials for ALL connections

    Args:
        websocket: WebSocket connection
        db: Optional database session

    Returns:
        dict with authentication result:
            - authenticated: bool
            - context: str (e.g., 'setup')
            - user: dict (if authenticated with credentials)

    Raises:
        WebSocketException: If authentication fails
    """
    # Check setup state
    setup_state = await get_setup_state(db)
    database_initialized = setup_state.get("database_initialized", True)
    logger.info(f"[WS SETUP DEBUG] db={db}, setup_state={setup_state}, database_initialized={database_initialized}")

    # Allow connection without auth during initial setup (database not initialized)
    # REMOVED (Handover 0035): Password change phase check (default_password_active field no longer exists)
    # v3.0+ goes directly from fresh install → Create Admin Account (no password change phase)
    if not database_initialized:
        logger.info("WebSocket connection allowed: initial setup mode (database not initialized)")
        return {"authenticated": True, "context": "setup"}

    # Post-setup: Require credentials for ALL connections
    # Extract credentials from query params, cookies, or headers
    token = websocket.query_params.get("token")
    api_key = websocket.query_params.get("api_key")

    # Check cookies if not in query params (PRIMARY AUTH METHOD)
    if not token and not api_key:
        # Extract cookies from Cookie header
        headers = dict(websocket.headers)
        cookie_header = headers.get("cookie", "")

        # Parse access_token from cookies (httpOnly cookie set by /api/auth/login)
        if cookie_header:
            cookies = {}
            for cookie_str in cookie_header.split(";"):
                cookie_clean = cookie_str.strip()
                if "=" in cookie_clean:
                    key, value = cookie_clean.split("=", 1)
                    cookies[key.strip()] = value.strip()

            # Get access_token from cookies
            token = cookies.get("access_token")
            if token:
                logger.debug("WebSocket: Found JWT token in httpOnly cookie")

    # Check Authorization header if not in cookies/query params
    if not token and not api_key:
        headers = dict(websocket.headers)
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove 'Bearer ' prefix

        api_key = headers.get("x-api-key")

    # No credentials provided - reject
    if not token and not api_key:
        logger.warning("WebSocket connection rejected: no credentials provided (post-setup)")
        raise WebSocketException(
            code=1008,  # Policy violation
            reason="Authentication required",
        )

    # Validate token (JWT)
    if token:
        validated_user = await validate_jwt_token(token, db)
        if validated_user:
            logger.info(f"WebSocket authenticated via JWT: {validated_user.get('user_id')}")
            return {"authenticated": True, "user": validated_user}

    # Validate API key
    if api_key:
        validated_key = await validate_api_key(api_key, db)
        if validated_key:
            logger.info("WebSocket authenticated via API key")
            return {
                "authenticated": True,
                "user": {
                    "user_id": validated_key.get("name"),
                    "tenant_key": validated_key["tenant_key"],
                    "permissions": validated_key.get("permissions", ["*"]),
                },
            }

        # BE-8000h: throttle FAILED API-key auth per IP over the WS handshake,
        # mirroring the REST/MCP-transport guard (BE-6060b's
        # enforce_api_key_auth_failure) so brute-forcing a key cannot dodge the
        # lockout just by moving to the WS path. A valid key returns above and
        # never reaches this call. WebSocketException has no HTTP status, so the
        # shared limiter's 429 is translated to the same 1008 policy-violation
        # close code this function already uses for a plain bad key.
        from api.middleware.auth_rate_limiter import enforce_api_key_auth_failure

        try:
            await enforce_api_key_auth_failure(websocket)
        except HTTPException as rl_exc:
            if rl_exc.status_code == 429:
                logger.warning("WebSocket connection rejected: API-key auth rate-limited")
                raise WebSocketException(code=1008, reason="Too many requests") from rl_exc
            raise

    # Invalid credentials - reject
    logger.warning("WebSocket connection rejected: invalid credentials")
    raise WebSocketException(
        code=1008,  # Policy violation
        reason="Invalid credentials",
    )


async def validate_jwt_token(token: str, db: AsyncSession = None) -> dict[str, Any] | None:
    """
    Validate a JWT for the WebSocket handshake.

    SEC-3004c: when a session is available (the production handshake always
    passes one), validation runs through the single ``validate_principal``
    pipeline — decode → revocation → is_active. This closes the WS drift where
    a JWT authenticated on claims alone, with NO jti-revocation and NO is_active
    enforcement (a revoked token or a deactivated user kept connecting).

    Args:
        token: JWT token string
        db: Database session. ``None`` only in contexts with no session (unit
            tests / pre-DB), where revocation + is_active cannot be consulted and
            a claims-only decode is the best available check.

    Returns:
        User info dict if valid, None otherwise
    """
    if db is not None:
        from giljo_mcp.auth.principal import PrincipalValidationError, validate_principal

        try:
            principal = await validate_principal(db, jwt_token=token)
        except PrincipalValidationError:
            return None
        return {
            "user_id": principal.username,
            "tenant_key": principal.tenant_key,
            "role": principal.role,
            "permissions": ["*"],  # JWT users have full permissions
        }

    # No session: claims-only decode (cannot reach the revocation/is_active DB
    # reads). Used only where no session exists; production WS always has one.
    try:
        from giljo_mcp.auth.jwt_manager import JWTManager

        payload = JWTManager.verify_token(token)
        if not payload:
            return None
        if "tenant_key" not in payload:
            logger.warning("JWT rejected: missing tenant_key claim")
            return None
        return {
            "user_id": payload.get("username"),
            "tenant_key": payload["tenant_key"],
            "role": payload.get("role"),
            "permissions": ["*"],
        }
    except (ImportError, ValueError, KeyError):
        logger.exception("JWT validation failed")
        return None


async def validate_api_key(api_key: str, db: AsyncSession = None) -> dict[str, Any] | None:
    """
    Validate an API key for the WebSocket handshake.

    SEC-3004c: delegates to the single ``_resolve_api_key`` loop (the one place
    the prefix-narrowed, off-loop bcrypt verify lives, shared with the REST and
    MCP transports). This also closes the WS drift where the owning user's
    ``is_active`` was never checked — ``_resolve_api_key`` rejects a key whose
    user is inactive or in a different tenant.

    Args:
        api_key: API key string
        db: Database session (required — the key resolves a tenant from the DB).

    Returns:
        Key info dict if valid, None otherwise
    """
    if not db:
        logger.warning("API key validation requires database session")
        return None

    try:
        from giljo_mcp.auth.principal import _resolve_api_key

        resolved = await _resolve_api_key(db, api_key)
    except (ImportError, SQLAlchemyError, ValueError):
        logger.exception("API key validation failed")
        return None

    if resolved is None:
        return None
    key, _user = resolved
    return {"name": key.name, "tenant_key": key.tenant_key, "permissions": key.permissions or ["*"]}


def check_subscription_permission(
    auth_context: dict[str, Any], entity_type: str, entity_id: str, tenant_key: str | None = None
) -> bool:
    """
    Check if a WebSocket client has permission to subscribe to an entity.

    Multi-tenant isolation:
    - Clients can only subscribe to entities in their tenant
    - During setup mode (context='setup'), allow all subscriptions
    - Check user permissions for fine-grained access control

    Args:
        auth_context: Authentication context from WebSocket connection
        entity_type: Type of entity (e.g., 'project', 'agent', 'message')
        entity_id: ID of the entity
        tenant_key: Tenant key of the entity (for multi-tenant isolation)

    Returns:
        True if subscription is allowed, False otherwise
    """
    # Setup mode: Allow all subscriptions (no tenant isolation during setup)
    if auth_context.get("context") == "setup":
        return True

    # No auth context: Deny (shouldn't happen if authenticate_websocket was called)
    if not auth_context:
        logger.warning(f"Subscription denied: no auth context for {entity_type}:{entity_id}")
        return False

    # Get user info from auth context
    user_info = auth_context.get("user", {})
    user_tenant_key = user_info.get("tenant_key")

    # Reject subscription if tenant_key is missing (Handover 0054)
    if not user_tenant_key:
        logger.warning(f"Subscription denied: missing tenant_key in user info for {entity_type}:{entity_id}")
        return False

    # Multi-tenant isolation: Check tenant_key match
    if tenant_key and user_tenant_key != tenant_key:
        logger.warning(
            f"Subscription denied: tenant mismatch "
            f"(user: {user_tenant_key}, entity: {tenant_key}) "
            f"for {entity_type}:{entity_id}"
        )
        return False

    # Check permissions (if implemented)
    user_permissions = user_info.get("permissions", [])

    # Wildcard permission grants all access
    if "*" in user_permissions:
        return True

    # Entity-specific permissions (future enhancement)
    # For now, all authenticated users in the same tenant can subscribe
    # Future: Check for specific permissions like 'read:projects', 'read:agents', etc.

    return True
