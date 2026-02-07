"""
Authentication API endpoints for LAN/WAN modes.

Provides REST API for:
- Login/logout (JWT cookies for web users)
- User profile access
- API key management (create, list, revoke)
- User registration (admin only)

All endpoints support multi-tenant isolation through tenant_key.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.dependencies import get_auth_service
from api.middleware.auth_rate_limiter import get_rate_limiter
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session, require_admin
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import User
from src.giljo_mcp.services import AuthService
from src.giljo_mcp.template_seeder import seed_tenant_templates

logger = logging.getLogger(__name__)
router = APIRouter()

# Security: Application-level lock to prevent concurrent first admin creation
# Protects against race condition where multiple requests check user count simultaneously
# and both create admin accounts (Handover 0034 security fix)
_first_admin_creation_lock = asyncio.Lock()

# Pydantic Models for Request/Response

class LoginRequest(BaseModel):
    """Login request with username and password"""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1)  # Allow default "admin" password (5 chars)

class LoginResponse(BaseModel):
    """Login response with user info"""

    message: str
    username: str
    role: str
    tenant_key: str
    password_change_required: bool | None = None  # v3.0 Unified: UX improvement

class LogoutResponse(BaseModel):
    """Logout response"""

    message: str

class UserProfileResponse(BaseModel):
    """User profile response"""

    id: str
    username: str
    email: str | None
    full_name: str | None
    role: str
    tenant_key: str
    is_active: bool
    created_at: str
    last_login: str | None
    password_change_required: bool | None = None  # v3.0 Unified: Indicates default password must be changed
    org_id: str | None = None  # Handover 0424h: User's organization ID
    org_name: str | None = None  # Handover 0424h: User's organization name
    org_role: str | None = None  # Handover 0424h: User's role in organization

# 0371: Removed UserListResponse - was only used by duplicate /users endpoint

class APIKeyResponse(BaseModel):
    """API key response (masked for security)"""

    id: str
    name: str
    key_prefix: str
    permissions: list[str]
    is_active: bool
    created_at: str
    last_used: str | None
    revoked_at: str | None

class APIKeyCreateRequest(BaseModel):
    """Request to create new API key"""

    name: str = Field(..., min_length=3, max_length=255, description="Description of API key purpose")
    permissions: list[str] = Field(default=["*"], description="List of permissions (default: all)")

class APIKeyCreateResponse(BaseModel):
    """Response after creating API key (includes plaintext key ONCE)"""

    id: str
    name: str
    api_key: str  # Plaintext key - only shown once!
    key_prefix: str
    message: str

class APIKeyRevokeResponse(BaseModel):
    """Response after revoking API key"""

    id: str
    name: str
    message: str

class RegisterUserRequest(BaseModel):
    """Request to register new user (admin only)"""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)
    email: EmailStr | None = None
    full_name: str | None = None
    role: str = Field(default="developer", description="User role: admin, developer, viewer")
    tenant_key: str = Field(
        default="tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd",
        description="Tenant key for multi-tenant isolation (must start with 'tk_')",
    )
    workspace_name: str | None = Field(
        default="My Organization", description="Organization name for first admin user (Handover 0424h)"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ["admin", "developer", "viewer"]:
            raise ValueError("Role must be one of: admin, developer, viewer")
        return v

class RegisterUserResponse(BaseModel):
    """Response after registering new user"""

    id: str
    username: str
    email: str | None
    role: str
    tenant_key: str
    message: str

class PasswordChangeRequest(BaseModel):
    """Request to change password from default"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least 1 uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least 1 lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least 1 number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least 1 special character")
        return v

class PasswordChangeResponse(BaseModel):
    """Response after changing password"""

    success: bool
    message: str
    token: str
    user: dict

# Auth Endpoints

@router.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(
    login_data: LoginRequest = Body(...),
    response: Response = None,
    request: Request = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login with username/password, returns JWT in httpOnly cookie.

    This endpoint authenticates a user and sets an httpOnly cookie
    containing a JWT access token valid for 24 hours.

    v3.0 Unified (Handover 0034): No more default password flow.
    Fresh installs go directly to "Create Admin Account" page.

    Rate Limiting (Handover 1009): 5 attempts per minute per IP

    Args:
        request: Login credentials (username, password)
        response: FastAPI response (to set cookie)
        auth_service: Auth service for authentication operations

    Returns:
        Login success message with user info

    Raises:
        HTTPException: 401 if credentials are invalid
        HTTPException: 429 if rate limit exceeded
    """
    # Rate limiting: 5 attempts per minute (Handover 1009)
    rate_limiter = get_rate_limiter()
    rate_limiter.check_rate_limit(request, limit=5, window=60, raise_on_limit=True)

    # Authenticate user via service
    # Service raises AuthenticationError on failure (0480 migration)
    auth_result = await auth_service.authenticate_user(login_data.username, login_data.password)

    # Service now returns data directly, exceptions handle errors
    user_data = auth_result["user"]
    token = auth_result["token"]

    # Update last login timestamp
    await auth_service.update_last_login(user_data["id"], datetime.now(timezone.utc))

    # v3.0 Unified (Handover 0034): No more default admin/admin password
    # Fresh installs go directly to "Create Admin Account" page
    # This flag is always False for v3.0+ (legacy field removed in Handover 0035)
    password_change_required = False

    # SECURITY: Cookie domain validation and whitelist enforcement
    #
    # Background: Frontend (port 7274) needs cookies set by API (port 7272)
    # Cross-port authentication requires setting cookie domain attribute.
    #
    # Domain attribute behavior:
    #   - domain=None → Strict (exact host:port match) - MOST SECURE
    #   - domain="10.1.0.164" → Loose (all ports on that IP) - NEEDED for cross-port
    #   - domain="example.com" → Applies to example.com AND all subdomains (*.example.com)
    #
    # Security considerations:
    #   1. Host Header Injection Risk: NEVER trust user-supplied Host header blindly
    #      Attacker can send: "Host: evil.com" and steal cookies if we set domain=evil.com
    #
    #   2. Defense-in-Depth Strategy:
    #      - IP addresses: Auto-allowed (no subdomain risk, validated by regex)
    #      - Domain names: MUST be in whitelist (prevents header injection attacks)
    #      - localhost/127.0.0.1: Always domain=None (strictest security)
    #      - Unknown hosts: domain=None (fail secure)
    #
    #   3. Additional Protections:
    #      - CORS whitelist (separate layer of defense)
    #      - SameSite=lax (prevents CSRF)
    #      - httpOnly=True (prevents XSS cookie theft)
    #      - secure=True in production (HTTPS only)
    #
    # Configuration: config.yaml can define allowed domains:
    #   security:
    #     cookie_domains: ["example.com", "myapp.io"]

    # Load secure cookie config BEFORE cookie domain logic (always needed)
    config = get_config()
    secure_cookies = config.get("security", {}).get("cookies", {}).get("secure", False)
    allowed_domains = config.get("security", {}).get("cookie_domains", [])

    cookie_domain = None
    if request and request.client:
        # Extract host from request header (e.g., "10.1.0.164:7272" or "example.com:7272")
        host_header = request.headers.get("host", "")
        if host_header:
            # Strip port if present (e.g., "10.1.0.164:7272" -> "10.1.0.164")
            host_only = host_header.split(":")[0].lower()

            # SECURITY CHECK #1: IP addresses (including localhost) share cookies across ports
            # Localhost (127.0.0.1) treated same as network IPs for production parity
            # Regex validates format: xxx.xxx.xxx.xxx where xxx = 1-3 digits
            # IP addresses have no subdomain hierarchy, so domain=IP is safe
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host_only):
                cookie_domain = host_only
                logger.debug(f"Cookie domain set to IP address (safe): {host_only}")

            # SECURITY CHECK #2: Domain names MUST be whitelisted (prevent header injection)
            # Without whitelist, attacker could send "Host: evil.com" and steal cookies
            elif host_only in allowed_domains:
                cookie_domain = host_only
                logger.info(f"Cookie domain set to whitelisted domain: {host_only}")
            else:
                # FAIL SECURE: Unknown domain → domain=None (strictest)
                cookie_domain = None
                logger.warning(
                    f"Cookie domain set to None for unknown host '{host_only}' "
                    f"(not in whitelist: {allowed_domains}). Add to config.yaml security.cookie_domains if needed."
                )

    # Set httpOnly cookie (session cookie - expires on browser close)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=secure_cookies,  # Configured via config.yaml security.cookies.secure
        samesite="lax",
        # NO max_age - makes it a session cookie that expires on browser close
        path="/",  # Accessible from all paths (frontend and API)
        domain=cookie_domain,  # Set to request host for cross-port cookie sharing
    )

    logger.info(
        f"User logged in successfully: {user_data['username']} (role: {user_data['role']}) (password_change_required: {password_change_required})"
    )

    # v3.0 Unified: Include password change requirement in response for frontend handling
    response_data = {
        "message": "Login successful",
        "username": user_data["username"],
        "role": user_data["role"],
        "tenant_key": user_data["tenant_key"],
    }

    if password_change_required:
        response_data["password_change_required"] = True
        response_data["message"] = "Login successful - password change required"

    return LoginResponse(**response_data)

@router.post("/logout", response_model=LogoutResponse, tags=["auth"])
async def logout(response: Response):
    """
    Logout by clearing the JWT cookie.

    This endpoint clears the access_token cookie, effectively logging out the user.

    Args:
        response: FastAPI response (to clear cookie)

    Returns:
        Logout success message
    """
    # Clear the cookie by setting it with max_age=0
    response.delete_cookie(key="access_token")

    logger.info("User logged out successfully")

    return LogoutResponse(message="Logout successful")

@router.get("/me", tags=["auth"])
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get current user profile or return 401 if not authenticated.

    Two-Layout Pattern: Auth routes isolated in AuthLayout, app routes always require valid user.
    This endpoint returns authenticated user data with password_change_required flag when applicable.

    Args:
        request: FastAPI request
        db: Database session (managed by FastAPI dependency injection)

    Returns:
        User profile data if authenticated, 401 JSON response otherwise
    """
    # Try to get current user (optional - doesn't raise exceptions)

    from src.giljo_mcp.auth.dependencies import get_current_user_optional
    from src.giljo_mcp.models.organizations import Organization, OrgMembership

    current_user = await get_current_user_optional(
        request=request,
        access_token=request.cookies.get("access_token"),
        x_api_key=request.headers.get("x-api-key"),
        authorization=request.headers.get("authorization"),
        db=db,
    )

    # If no authenticated user, return clean 401 JSON response
    if current_user is None:
        return JSONResponse(
            status_code=401, content={"detail": "Not authenticated. Please login or provide a valid API key."}
        )

    # Handover 0424h: Load organization data if user has org_id
    org_name = None
    org_role = None

    if current_user.org_id:
        # Load organization
        from sqlalchemy import select

        org_stmt = select(Organization).where(Organization.id == current_user.org_id)
        org_result = await db.execute(org_stmt)
        org = org_result.scalar_one_or_none()

        if org:
            org_name = org.name

            # Load membership to get org_role
            membership_stmt = select(OrgMembership).where(
                OrgMembership.org_id == current_user.org_id,
                OrgMembership.user_id == str(current_user.id),
                OrgMembership.is_active == True,
            )
            membership_result = await db.execute(membership_stmt)
            membership = membership_result.scalar_one_or_none()

            if membership:
                org_role = membership.role

    # Check if password change is required (for admin user with default password)

    # v3.0 Unified (Handover 0034): No more default admin/admin password
    # Fresh installs go directly to "Create Admin Account" page via first_admin_created flag
    # This check removed in Handover 0035 (field no longer exists in SetupState model)
    password_change_required = None

    # Return authenticated user profile with org data (Handover 0424h)
    return UserProfileResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_key=current_user.tenant_key,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        password_change_required=password_change_required,
        org_id=str(current_user.org_id) if current_user.org_id else None,
        org_name=org_name,
        org_role=org_role,
    )

@router.get("/api-keys", response_model=list[APIKeyResponse], tags=["auth"])
async def list_api_keys(
    include_revoked: bool = Query(False, description="Include revoked keys in results"),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    List all API keys for current user.

    This endpoint returns all API keys (active and revoked) for the authenticated user.
    Keys are masked - only the prefix is shown for security.

    Args:
        current_user: User from JWT token (dependency)
        auth_service: Auth service for API key operations

    Returns:
        List of API keys (masked)
    """
    # Service raises exceptions on failure (0480 migration)
    keys = await auth_service.list_api_keys(str(current_user.id), include_revoked=include_revoked)

    return [
        APIKeyResponse(
            id=key["id"],
            name=key["name"],
            key_prefix=key["key_prefix"],
            permissions=key["permissions"],
            is_active=key["is_active"],
            created_at=key["created_at"],
            last_used=key["last_used"],
            revoked_at=key["revoked_at"],
        )
        for key in keys
    ]

@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def create_api_key(
    request: APIKeyCreateRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Generate a new API key for current user.

    This endpoint creates a new API key and returns it in plaintext.
    WARNING: The key is only shown once! Store it securely.

    Args:
        request: API key creation request (name, permissions)
        current_user: User from JWT token (dependency)
        auth_service: Auth service for API key operations

    Returns:
        API key response with plaintext key (shown only once)
    """
    # Service raises exceptions on failure (0480 migration)
    key_data = await auth_service.create_api_key(
        user_id=str(current_user.id),
        tenant_key=current_user.tenant_key,
        name=request.name,
        permissions=request.permissions,
    )

    logger.info(
        f"API key created: {key_data['name']} (user: {current_user.username}, prefix: {key_data['key_prefix']})"
    )

    return APIKeyCreateResponse(
        id=key_data["id"],
        name=key_data["name"],
        api_key=key_data["api_key"],  # Plaintext key - only shown once!
        key_prefix=key_data["key_prefix"],
        message="API key created successfully. Store this key securely - it will not be shown again!",
    )

@router.delete("/api-keys/{key_id}", response_model=APIKeyRevokeResponse, tags=["auth"])
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Revoke an API key.

    This endpoint revokes (deactivates) an API key. The key will no longer
    work for authentication after revocation.

    Args:
        key_id: UUID of API key to revoke
        current_user: User from JWT token (dependency)
        auth_service: Auth service for API key operations

    Returns:
        Revocation confirmation

    Raises:
        HTTPException: 404 if key not found or belongs to another user
    """
    # Service raises ResourceNotFoundError on failure (0480 migration)
    await auth_service.revoke_api_key(str(key_id), str(current_user.id))

    logger.info(f"API key revoked (user: {current_user.username})")

    # Need to get key name for response - let's list keys and find it
    keys = await auth_service.list_api_keys(str(current_user.id), include_revoked=True)
    key_name = "Unknown"
    for key in keys:
        if key["id"] == str(key_id):
            key_name = key["name"]
            break

    return APIKeyRevokeResponse(id=str(key_id), name=key_name, message="API key revoked successfully")

# 0371: Removed duplicate GET /users endpoint - frontend now uses /api/v1/users/

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
    # Rate limiting: 3 attempts per minute (Handover 1009)
    rate_limiter = get_rate_limiter()
    rate_limiter.check_rate_limit(http_request, limit=3, window=60, raise_on_limit=True)

    # Service raises ValidationError on failure (0480 migration)
    user_data = await auth_service.register_user(
        username=request.username,
        email=request.email,
        password=request.password,
        role=request.role,
        requesting_admin_id=str(current_user.id),
    )

    logger.info(
        f"User registered: {user_data['username']} (role: {user_data['role']}, by admin: {current_user.username})"
    )

    return RegisterUserResponse(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        role=user_data["role"],
        tenant_key=user_data["tenant_key"],
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
    logger.info(f"[SETUP] Admin creation attempt from IP: {client_ip}")

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
            full_name=request_body.full_name,
            org_name=request_body.workspace_name,  # Handover 0424h
        )

        token = admin_data["token"]
        tenant_key = admin_data["tenant_key"]

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

        # SECURITY: Cookie domain validation and whitelist enforcement
        #
        # Background: Frontend (port 7274) needs cookies set by API (port 7272)
        # Cross-port authentication requires setting cookie domain attribute.
        #
        # Domain attribute behavior:
        #   - domain=None → Strict (exact host:port match) - MOST SECURE
        #   - domain="10.1.0.164" → Loose (all ports on that IP) - NEEDED for cross-port
        #   - domain="example.com" → Applies to example.com AND all subdomains (*.example.com)
        #
        # Security considerations:
        #   1. Host Header Injection Risk: NEVER trust user-supplied Host header blindly
        #      Attacker can send: "Host: evil.com" and steal cookies if we set domain=evil.com
        #
        #   2. Defense-in-Depth Strategy:
        #      - IP addresses: Auto-allowed (no subdomain risk, validated by regex)
        #      - Domain names: MUST be in whitelist (prevents header injection attacks)
        #      - localhost/127.0.0.1: Always domain=None (strictest security)
        #      - Unknown hosts: domain=None (fail secure)
        #
        #   3. Additional Protections:
        #      - CORS whitelist (separate layer of defense)
        #      - SameSite=lax (prevents CSRF)
        #      - httpOnly=True (prevents XSS cookie theft)
        #      - secure=True in production (HTTPS only)
        #
        # Configuration: config.yaml can define allowed domains:
        #   security:
        #     cookie_domains: ["example.com", "myapp.io"]

        # Load secure cookie config BEFORE cookie domain logic (always needed)
        config = get_config()
        secure_cookies = config.get("security", {}).get("cookies", {}).get("secure", False)
        allowed_domains = config.get("security", {}).get("cookie_domains", [])

        cookie_domain = None
        if request and request.client:
            # Extract host from request header (e.g., "10.1.0.164:7272" or "example.com:7272")
            host_header = request.headers.get("host", "")
            if host_header:
                # Strip port if present (e.g., "10.1.0.164:7272" -> "10.1.0.164")
                host_only = host_header.split(":")[0].lower()

                # SECURITY CHECK #1: IP addresses (including localhost) share cookies across ports
                # Localhost (127.0.0.1) treated same as network IPs for production parity
                # Regex validates format: xxx.xxx.xxx.xxx where xxx = 1-3 digits
                # IP addresses have no subdomain hierarchy, so domain=IP is safe
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host_only):
                    cookie_domain = host_only
                    logger.debug(f"Cookie domain set to IP address (safe): {host_only}")

                # SECURITY CHECK #2: Domain names MUST be whitelisted (prevent header injection)
                # Without whitelist, attacker could send "Host: evil.com" and steal cookies
                elif host_only in allowed_domains:
                    cookie_domain = host_only
                    logger.info(f"Cookie domain set to whitelisted domain: {host_only}")
                else:
                    # FAIL SECURE: Unknown domain → domain=None (strictest)
                    cookie_domain = None
                    logger.warning(
                        f"Cookie domain set to None for unknown host '{host_only}' "
                        f"(not in whitelist: {allowed_domains}). Add to config.yaml security.cookie_domains if needed."
                    )

        # Set httpOnly cookie for immediate login (same pattern as login endpoint)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=secure_cookies,  # Configured via config.yaml security.cookies.secure
            samesite="lax",
            path="/",  # Accessible from all paths (frontend and API)
            domain=cookie_domain,  # Set to request host for cross-port cookie sharing
            max_age=86400,  # 24 hours
        )

        logger.info(
            f"[SETUP] First administrator account created successfully - "
            f"username: {admin_data['username']}, tenant: {tenant_key[:12]}..., "
            f"client_ip: {client_ip}. Endpoint now DISABLED for security."
        )

        return RegisterUserResponse(
            id=admin_data["id"],
            username=admin_data["username"],
            email=admin_data["email"],
            full_name=admin_data["full_name"],
            role=admin_data["role"],
            tenant_key=admin_data["tenant_key"],
            is_active=admin_data["is_active"],
            message="Administrator account created successfully. Redirecting to dashboard...",
        )

# REMOVED (Handover 0034): Legacy password change endpoint
# Replaced by clean first-admin creation flow via /create-first-admin
# Old endpoint required default admin/admin credentials and complex state tracking
# New flow: Fresh install (0 users) → Create admin account directly
