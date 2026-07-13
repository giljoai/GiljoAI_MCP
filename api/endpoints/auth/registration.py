# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""User-registration endpoints: admin-only register + first-admin bootstrap.

Extracted verbatim from api/endpoints/auth.py (BE-6042f route-group split).
The in-function imports of ``member_management_enabled`` / ``GILJO_MODE`` from
api.app_state are PRESERVED on purpose — the edition-gate tests rebind those
symbols via patch/importlib.reload, which only works if they are imported at
call time, not module load time.
"""

import asyncio
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status

from api.endpoints.dependencies import get_auth_service
from api.middleware.auth_rate_limiter import get_rate_limiter
from api.middleware.auth_rate_limits import limit_for
from giljo_mcp.auth.dependencies import require_admin
from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import User
from giljo_mcp.services import AuthService
from giljo_mcp.template_seeder import seed_tenant_templates
from giljo_mcp.utils.log_sanitizer import sanitize

from .models import RegisterUserRequest, RegisterUserResponse
from .session import _build_cookie_params


logger = logging.getLogger(__name__)
router = APIRouter()

# Security: Application-level lock to prevent concurrent first admin creation
# Protects against race condition where multiple requests check user count simultaneously
# and both create admin accounts (Handover 0034 security fix)
_first_admin_creation_lock = asyncio.Lock()


# TENANT-LEVEL: per-user tenancy — admin creates new user, AuthService.register_user
# generates a fresh tenant_key per registrant via TenantManager.generate_tenant_key(username).
# Hidden today for both CE (single-user license) and SaaS Solo (single-user plan);
# forward-looking scaffolding to re-open for the SaaS Team tier (see GILJO_MODE gate below).
@router.post("/register", response_model=RegisterUserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register_user(
    http_request: Request,
    request: RegisterUserRequest = Body(...),
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user (admin only).

    This endpoint creates a new user account. Only admins can create new users.

    Rate Limiting (Handover 1009): 3 attempts per minute per IP

    Args:
        http_request: FastAPI request object
        request: User registration data
        current_user: Admin user from JWT token (dependency)
        auth_service: Auth service for user registration

    Returns:
        New user info

    Raises:
        HTTPException: 400 if username/email already exists
        HTTPException: 403 if not admin
        HTTPException: 429 if rate limit exceeded
    """
    # IMP-5042: multi-user creation is gated to editions that support it. No
    # shipping edition does today (CE single-user license, SaaS Solo single-seat),
    # so this 403s — matching POST /api/v1/users/ and the hidden dashboard "Add
    # User" button. Re-opens automatically for the future SaaS Team tier via the
    # single edition-policy flip point member_management_enabled(). Gate before
    # spending rate-limit budget on a permanently-unavailable feature.
    from api.app_state import member_management_enabled

    if not member_management_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Adding additional users isn't available on this plan.",
        )

    # Rate limiting: 3 attempts per minute (Handover 1009)
    rate_limiter = get_rate_limiter()
    await rate_limiter.check_rate_limit(http_request, limit=limit_for("register"), window=60, raise_on_limit=True)

    # BE-6109: capture client IP (proxy-aware) for audit / abuse signal.
    forwarded = http_request.headers.get("X-Forwarded-For")
    if forwarded:
        registration_ip: str | None = forwarded.split(",")[0].strip()
    else:
        registration_ip = http_request.headers.get("X-Real-IP") or (
            http_request.client.host if http_request.client else None
        )

    # Service raises ValidationError on failure (0480 migration)
    user_data = await auth_service.register_user(
        username=request.username,
        email=request.email,
        password=request.password,
        role=request.role,
        requesting_admin_id=str(current_user.id),
        registration_ip=registration_ip,
    )

    logger.info(
        f"User registered: {sanitize(user_data.username)} (role: {sanitize(user_data.role)}, by admin: {sanitize(current_user.username)})"
    )

    return RegisterUserResponse(
        id=user_data.id,
        username=user_data.username,
        email=user_data.email,
        role=user_data.role,
        tenant_key=user_data.tenant_key,
        message="User registered successfully",
    )


@router.post("/create-first-admin", response_model=RegisterUserResponse, status_code=201, tags=["auth"])
async def create_first_admin_user(
    response: Response,
    request: Request,
    request_body: RegisterUserRequest = Body(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Create first administrator account on fresh install (Handover 0034).

    Security:
    - LAN ACCESS ALLOWED: Can be accessed remotely for initial setup
    - ENDPOINT DISABLED AFTER FIRST ADMIN: Automatically locked down after creation
    - Only works when total_users_count == 0 (fresh install)
    - Enforces strong password requirements (12+ chars, complexity)
    - Auto-generates secure tenant_key
    - Forces role='admin' for first user
    - Returns JWT token for immediate login via httpOnly cookie
    - Logs admin creation event for audit trail (including IP address)

    Replaces legacy admin/admin default password flow.

    Args:
        request: FastAPI request object (for IP logging)
        request_body: User registration request with username, password, optional email/full_name
        response: FastAPI response object for setting cookies
        auth_service: Auth service for first admin creation

    Returns:
        RegisterUserResponse with user details and success message

    Raises:
        HTTPException 403: If users already exist (not fresh install)
        HTTPException 400: If password doesn't meet requirements
        HTTPException 503: If database check fails (fail-secure)
    """
    # Log client IP for audit trail (LAN access allowed for remote setup)
    client_ip = request.client.host
    logger.info(f"[SETUP] Admin creation attempt from IP: {sanitize(client_ip)}")

    # IMP-0011: Gate the unauthenticated admin-creation endpoint to CE mode.
    # In SaaS mode this endpoint must refuse -- operators bootstrap the
    # admin user out-of-band via `python -m giljo_mcp.saas.cli.admin_bootstrap`.
    from api.app_state import GILJO_MODE

    # CE is "" (default/unset) OR "ce" — canonical edition idiom (downloads.py
    # `in ("", "ce")`, startup.py:1010). `!= "ce"` alone wrongly 403'd a CE
    # self-hoster on GILJO_MODE="" and could not bootstrap their first admin.
    if GILJO_MODE not in ("", "ce"):
        logger.warning(
            "[SETUP] /auth/create-first-admin refused in mode=%s from IP=%s",
            GILJO_MODE,
            sanitize(client_ip),
        )
        raise HTTPException(
            status_code=403,
            detail=(
                "Admin bootstrap is disabled in this deployment mode. "
                "Operators must create the first admin via the CLI bootstrap tool."
            ),
        )

    # BE-6063f: this is an unauthenticated POST that mints an admin + tenant +
    # seeds templates. Rate-limit per IP so a fresh install can't be hammered.
    # (CE localhost is exempt inside check_rate_limit, so the operator's own
    # setup from 127.0.0.1 is never throttled.)
    rate_limiter = get_rate_limiter()
    await rate_limiter.check_rate_limit(request, limit=limit_for("create_first_admin"), window=60, raise_on_limit=True)

    # CRITICAL SECURITY FIX (Handover 0034): Acquire lock to prevent race condition
    # Without this lock, multiple concurrent requests could all check user_count == 0
    # simultaneously and create multiple admin accounts
    async with _first_admin_creation_lock:
        # Create first admin via service (includes all security checks)
        # Service raises ValidationError on failure (0480 migration)
        admin_data = await auth_service.create_first_admin(
            username=request_body.username,
            email=request_body.email,
            password=request_body.password,
            full_name=None,
            first_name=request_body.first_name,
            last_name=request_body.last_name,
            org_name=request_body.workspace_name,  # Handover 0424h
        )

        token = admin_data.token
        tenant_key = admin_data.tenant_key

        # Save recovery PIN if provided during admin creation
        if request_body.recovery_pin:
            if request_body.recovery_pin != request_body.confirm_pin:
                raise HTTPException(status_code=400, detail="Recovery PINs do not match")

            import bcrypt

            from api.endpoints.dependencies import get_db_manager
            from giljo_mcp.models.auth import User

            db_manager = await get_db_manager()
            async with db_manager.get_session_async() as db:
                from sqlalchemy import select

                # Tenant-scoped: under the fail-closed isolation guard, every ORM
                # statement touching User requires tenant *context* (not just a
                # predicate). Use the just-created admin's tenant_key (mirrors the
                # refresh handler above). Without this the lookup raised
                # TenantIsolationError -> HTTP 500 and the PIN was silently never
                # saved, because auth_service.create_first_admin already committed
                # the admin row before this block runs.
                with tenant_session_context(db, tenant_key):
                    stmt = select(User).where(User.username == request_body.username)
                    result = await db.execute(stmt)
                    user = result.scalar_one_or_none()
                    if user:
                        user.recovery_pin_hash = bcrypt.hashpw(
                            request_body.recovery_pin.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")
                        await db.commit()
                        logger.info(f"[SETUP] Recovery PIN set for admin user: {sanitize(request_body.username)}")

        # Seed default agent templates for this tenant (Handover 0041 Phase 2)
        # CRITICAL: Templates are seeded with the user's tenant_key (not default_tenant_key)
        # This ensures templates appear in UI immediately after user creation
        try:
            # Need to get db session for template seeding

            from api.endpoints.dependencies import get_db_manager

            db_manager = await get_db_manager()
            async with db_manager.get_session_async() as db:
                template_count = await seed_tenant_templates(db, tenant_key)
                await db.commit()  # Ensure templates are persisted
            logger.info(f"[SETUP] Seeded {template_count} default agent templates for tenant {tenant_key[:12]}...")
        except (ImportError, ValueError) as e:
            # Non-blocking - templates can be added later via UI
            logger.warning(f"[SETUP] Template seeding failed (non-critical): {e}")
            template_count = 0

        # Set httpOnly cookie for immediate login (same pattern as login endpoint)
        cookie_params = _build_cookie_params(request)
        response.set_cookie(value=token, **cookie_params)

        logger.info(
            f"[SETUP] First administrator account created successfully - "
            f"username: {admin_data.username}, tenant: {tenant_key[:12]}..., "
            f"client_ip: {client_ip}. Endpoint now DISABLED for security."
        )

        return RegisterUserResponse(
            id=admin_data.user_id,
            username=admin_data.username,
            email=admin_data.email,
            first_name=admin_data.first_name,
            last_name=admin_data.last_name,
            full_name=admin_data.full_name,
            role=admin_data.role,
            tenant_key=admin_data.tenant_key,
            is_active=admin_data.is_active,
            message="Administrator account created successfully. Redirecting to dashboard...",
        )
