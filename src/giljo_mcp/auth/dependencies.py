# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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
from datetime import UTC, datetime

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.principal import PrincipalValidationError, validate_principal
from giljo_mcp.models import APIKey, User


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

    Tenant carrier (BE6004C-2, RC-1 + RC-3): the session is opened with the
    tenant_key from ``request.state.tenant_key`` (set by AuthMiddleware), which
    survives the BaseHTTPMiddleware->endpoint task boundary unlike the ContextVar.
    This stamps ``session.info["tenant_key"]`` before any query runs.
    ``get_current_user`` (below) independently stamps the same key from the JWT on
    this session; the JWT tenant == request.state.tenant_key, so the two are
    consistent/idempotent. Public / unauthenticated requests have no
    ``request.state.tenant_key`` and open a no-tenant session.
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

    tenant_key = getattr(request.state, "tenant_key", None) if request is not None else None

    # Use the shared db_manager instance - get_session_async handles all cleanup
    # including GeneratorExit (BaseException) from FastAPI HTTPException
    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        # Per-endpoint attribution for audit-mode warnings (Slice 0 _audit_warn reads this).
        if request is not None:
            session.info["request_path"] = request.url.path
        yield session


async def _record_api_key_usage(db: AsyncSession, request: Request, api_key_id: str | None) -> None:
    """Record audit bookkeeping for a successful API-key auth (non-auth side effects).

    Updates ``api_keys.last_used`` and logs the client IP. These are audit
    concerns, not authentication — kept here (transport bookkeeping) rather than
    inside ``validate_principal`` (pure resolution). Best-effort: a failure here
    never fails an otherwise-valid authentication.
    """
    if not api_key_id:
        return
    # Best-effort audit only: a failure here must NEVER fail an otherwise-valid
    # authentication, so the whole block is swallowed (last_used + IP log are
    # bookkeeping, not an auth gate).
    try:
        # SEC-9093: target the raw table so the tenant guard injects the tenant_key
        # predicate. A mapped-class bulk UPDATE (update(APIKey)) wraps the table in an
        # AnnotatedTable the guard cannot identity-match, leaving the write unscoped;
        # update(APIKey.__table__) matches, so the guard scopes it to the session tenant.
        await db.execute(
            update(APIKey.__table__).where(APIKey.__table__.c.id == api_key_id).values(last_used=datetime.now(UTC))
        )
        await db.commit()

        from giljo_mcp.auth.ip_logger import log_api_key_ip

        client_ip = request.client.host if request.client else "unknown"
        await log_api_key_ip(db, str(api_key_id), client_ip)
    except Exception:  # noqa: BLE001 — audit bookkeeping must never fail auth
        logger.debug("API-key usage bookkeeping failed (non-blocking)", exc_info=True)


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(None),
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
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
    logger.debug(
        "[AUTH] get_current_user called - path: %s, cookie: %s, api_key: %s, auth_header: %s",
        request.url.path,
        bool(access_token),
        bool(x_api_key),
        bool(authorization),
    )

    # SEC-3004b: every credential is validated through the single
    # ``validate_principal`` pipeline (decode → revocation → is_active). This
    # dependency now keeps ONLY credential extraction + the historical priority
    # ordering: JWT cookie → Bearer JWT (when no cookie) → X-API-Key. A failure
    # on one credential falls through to the next, then to the 401 below —
    # mirroring the prior behavior where a revoked/invalid cookie still let a
    # Bearer/API-key on the same request authenticate.
    bearer_token: str | None = None
    if authorization and str(authorization).lower().startswith("bearer "):
        bearer_token = str(authorization).split(" ", 1)[1].strip()

    # BE-6063a: reuse the User the auth middleware already resolved + stashed so
    # a valid JWT does not force a second identical SELECT. validate_principal
    # re-asserts identity + is_active before trusting it.
    prefetched = getattr(getattr(request, "state", None), "auth_user", None)

    if access_token:
        try:
            principal = await validate_principal(db, jwt_token=access_token, prefetched_user=prefetched)
            logger.debug("[AUTH] JWT cookie SUCCESS - User: %s, Tenant: %s", principal.username, principal.tenant_key)
            _stamp_auth_credential(request, "cookie")
            return principal.user
        except PrincipalValidationError as exc:
            logger.warning("[AUTH] JWT cookie rejected (%s)", exc.reason.value)

    if bearer_token and not access_token:
        try:
            principal = await validate_principal(db, jwt_token=bearer_token, prefetched_user=prefetched)
            logger.debug("[AUTH] Bearer JWT SUCCESS - User: %s, Tenant: %s", principal.username, principal.tenant_key)
            _stamp_auth_credential(request, "bearer")
            return principal.user
        except PrincipalValidationError as exc:
            logger.warning("[AUTH] Bearer JWT rejected (%s)", exc.reason.value)

    if x_api_key:
        try:
            principal = await validate_principal(db, api_key=x_api_key)
        except PrincipalValidationError as exc:
            logger.warning("[AUTH] API key rejected (%s)", exc.reason.value)
            # BE-6060b/TSK-9021: throttle FAILED API-key auth per IP on the REST
            # path too, mirroring the WS/MCP-transport guard (a valid key never
            # reaches this arm). Under budget: records + falls through to the
            # 401 below. Over budget: raises HTTPException(429) directly — no
            # status translation needed here, unlike the WS/raw-ASGI call sites.
            from api.middleware.auth_rate_limiter import enforce_api_key_auth_failure

            await enforce_api_key_auth_failure(request)
        else:
            await _record_api_key_usage(db, request, principal.api_key_id)
            logger.debug("[AUTH] API key SUCCESS - User: %s, Tenant: %s", principal.username, principal.tenant_key)
            _stamp_auth_credential(request, "api_key")
            return principal.user

    # No valid authentication found. Two cases — log them at different levels
    # so the routine anonymous-probe traffic does not drown the real signal:
    #
    # 1. No cookie AND no api_key: expected anonymous probe (browser asking
    #    "am I logged in?", search-engine crawler, OG-image fetch, CDN cold
    #    load). Not an error. Logged at INFO so CE operators can still see
    #    it in journalctl, but the SDK's LoggingIntegration treats INFO as a
    #    breadcrumb and does NOT create a Sentry event for it (event_level
    #    defaults to ERROR). INF-5070 discovered this floods every mcp.example.com
    #    visit into Sentry's 5K/month free-tier quota.
    #
    # 2. Cookie or api_key supplied but failed verification: real security
    #    signal worth keeping visible (failed brute-force attempt, expired
    #    session, tampered token). Kept at WARNING — still becomes a Sentry
    #    breadcrumb, still emails on the legacy log-tail monitoring, but
    #    short of the ERROR threshold that auto-creates a Sentry issue.
    credentials_supplied = bool(access_token) or bool(x_api_key)
    if credentials_supplied:
        logger.warning(
            f"[AUTH] FAILED - credentials supplied but invalid (path: {request.url.path}, cookie: {bool(access_token)}, api_key: {bool(x_api_key)})"
        )
    else:
        logger.info(f"[AUTH] anonymous request to {request.url.path} (no cookie, no api_key)")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please login or provide a valid API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(current_user: User | None = Depends(get_current_user)) -> User:
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

    # INF-5063: tag Sentry scope with tenant_key for SaaS/Demo error tracking.
    # No-op in CE (set_tenant_context returns early when sentry_sdk isn't initialized).
    from api.observability.sentry_init import set_tenant_context

    set_tenant_context(tenant_key=current_user.tenant_key, user_id=str(current_user.id))

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


async def require_ce_mode() -> None:
    """
    Gate an endpoint so it is only exposed in CE mode.

    CE is represented by both ``""`` (default/unset) and ``"ce"`` — the canonical
    edition-gating idiom (matches ``downloads.py`` ``in ("", "ce")`` and the
    ``startup.py:1010`` precedent). Gating on ``== "ce"`` alone silently dropped
    these routes whenever ``GILJO_MODE=""`` (e.g. a self-hoster who never set the
    var, and the CI CE step which runs at ``GILJO_MODE=""``).

    SEC-0005a: Role and mode are orthogonal axes. Some endpoints (server-level
    config, DB password rotation, SSL cert upload, etc.) are CE-only and MUST NOT
    be exposed in demo/SaaS deployments even to admins of their own tenant.

    Raises:
        HTTPException: 404 when not in CE mode (hide endpoint existence; a 403
            would acknowledge the route is real).
    """
    from api.app_state import GILJO_MODE

    if GILJO_MODE not in ("", "ce"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# ── Credential-purpose gate (SEC-9170) ──────────────────────────────────────
# A leaked data-plane credential (an API key or an MCP OAuth Bearer) must not be
# able to mutate account-security fields or mint a new key — those require an
# interactive browser session. The signal is the credential type get_current_user
# already resolves by priority (cookie → bearer → api_key); it is surfaced on
# request.state.auth_method, mirroring the MCP transport's scope-state stamp.

# Account-security fields that only a browser session may write. Names match
# UserUpdate on PUT /api/v1/users/{id}.
SENSITIVE_ACCOUNT_FIELDS: frozenset[str] = frozenset({"password", "email", "is_active", "recovery_pin"})


def _stamp_auth_credential(request: Request, credential: str) -> None:
    """Record which credential authenticated the request on request.state.

    ``credential`` is ``"cookie"`` (browser session), ``"bearer"`` (an
    Authorization: Bearer / MCP OAuth token) or ``"api_key"``. Surfaces the
    priority-branch decision get_current_user already makes so the browser-session
    guards can read it, mirroring ``scope["state"]["auth_method"]`` on the MCP
    transport. Nothing else depends on it. Best-effort: a real Starlette request
    always has ``.state``; a bare stub (direct-call unit tests) may not, and a
    missing stamp simply fails the browser-session check closed.
    """
    if request is not None and hasattr(request, "state"):
        request.state.auth_method = credential


def is_browser_session(request: Request) -> bool:
    """True only when the access_token cookie authenticated the request.

    Fail-closed: an absent/unknown stamp is treated as non-browser.
    """
    return getattr(getattr(request, "state", None), "auth_method", None) == "cookie"


async def require_browser_session(request: Request, _user: User = Depends(get_current_active_user)) -> None:
    """Dependency: reject any non-cookie credential (SEC-9170 / SEC-9171 #3).

    Depends on get_current_active_user so the credential is validated and stamped
    before this reads it. Use on routes an API key / OAuth Bearer must never reach
    (e.g. minting a new API key).
    """
    if not is_browser_session(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an interactive browser session; API keys and OAuth tokens cannot perform it.",
        )


def enforce_sensitive_account_field_guard(request: Request, payload: object) -> None:
    """Guard a user-update payload (SEC-9170 + recovery_pin CE boundary).

    ``payload`` exposes the UserUpdate fields. If any account-security field is
    written (non-None) and the caller is not a browser session → 403. The
    recovery_pin write is additionally refused in hosted SaaS, which must never
    accept or persist a recovery PIN (2026-07-14 product boundary).
    """
    writing_sensitive = any(getattr(payload, field, None) is not None for field in SENSITIVE_ACCOUNT_FIELDS)
    if writing_sensitive and not is_browser_session(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password, email, and account-status changes require an interactive browser session; "
            "API keys and OAuth tokens cannot perform them.",
        )
    if getattr(payload, "recovery_pin", None) is not None:
        from api.app_state import GILJO_MODE

        if GILJO_MODE not in ("", "ce"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recovery PIN is not available in hosted mode.",
            )


async def get_current_user_optional(
    request: Request,
    access_token: str | None = Cookie(None),
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
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
