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
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import JSONResponse
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session, require_admin
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import APIKey, User
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
    password_change_required: Optional[bool] = None  # v3.0 Unified: UX improvement


class LogoutResponse(BaseModel):
    """Logout response"""

    message: str


class UserProfileResponse(BaseModel):
    """User profile response"""

    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    tenant_key: str
    is_active: bool
    created_at: str
    last_login: Optional[str]
    password_change_required: Optional[bool] = None  # v3.0 Unified: Indicates default password must be changed

class UserListResponse(BaseModel):
    """User list response for tenant users"""
    
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


class APIKeyResponse(BaseModel):
    """API key response (masked for security)"""

    id: str
    name: str
    key_prefix: str
    permissions: List[str]
    is_active: bool
    created_at: str
    last_used: Optional[str]
    revoked_at: Optional[str]


class APIKeyCreateRequest(BaseModel):
    """Request to create new API key"""

    name: str = Field(..., min_length=3, max_length=255, description="Description of API key purpose")
    permissions: List[str] = Field(default=["*"], description="List of permissions (default: all)")


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
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str = Field(default="developer", description="User role: admin, developer, viewer")
    tenant_key: str = Field(
        default="tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd",
        description="Tenant key for multi-tenant isolation (must start with 'tk_')"
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
    email: Optional[str]
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


class PinPasswordResetRequest(BaseModel):
    """Request to reset password using recovery PIN"""

    username: str = Field(..., min_length=3, max_length=64)
    recovery_pin: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")
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


class PinPasswordResetResponse(BaseModel):
    """Response after successful password reset via PIN"""

    message: str


class CheckFirstLoginRequest(BaseModel):
    """Request to check if first login is required"""

    username: str = Field(..., min_length=3, max_length=64)


class CheckFirstLoginResponse(BaseModel):
    """Response indicating if first login actions required"""

    must_change_password: bool
    must_set_pin: bool


class CompleteFirstLoginRequest(BaseModel):
    """Request to complete first login setup"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    recovery_pin: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")
    confirm_pin: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")

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


class CompleteFirstLoginResponse(BaseModel):
    """Response after completing first login"""

    message: str


# Auth Endpoints


@router.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(
    login_data: LoginRequest = Body(...), 
    response: Response = None, 
    request: Request = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Login with username/password, returns JWT in httpOnly cookie.

    This endpoint authenticates a user and sets an httpOnly cookie
    containing a JWT access token valid for 24 hours.

    v3.0 Unified (Handover 0034): No more default password flow.
    Fresh installs go directly to "Create Admin Account" page.

    Args:
        request: Login credentials (username, password)
        response: FastAPI response (to set cookie)
        db: Database session

    Returns:
        Login success message with user info

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Find user by username
    stmt = select(User).where(User.username == login_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.warning(f"Login failed for username: {login_data.username} (user not found or inactive)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password
    if not bcrypt.verify(login_data.password, user.password_hash):
        logger.warning(f"Login failed for username: {login_data.username} (invalid password)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check if default password is still active (for admin user) - v3.0 Unified UX
    from src.giljo_mcp.models import SetupState

    stmt_setup = select(SetupState).where(SetupState.tenant_key == user.tenant_key)
    result_setup = await db.execute(stmt_setup)
    setup_state = result_setup.scalar_one_or_none()

    # v3.0 Unified (Handover 0034): No more default admin/admin password
    # Fresh installs go directly to "Create Admin Account" page
    # This flag is always False for v3.0+ (legacy field removed in Handover 0035)
    password_change_required = False

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
    )

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
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host_only):
                cookie_domain = host_only
                logger.debug(f"Cookie domain set to IP address (safe): {host_only}")

            # SECURITY CHECK #2: Domain names MUST be whitelisted (prevent header injection)
            # Without whitelist, attacker could send "Host: evil.com" and steal cookies
            else:
                # Load whitelist from config (defaults to empty list if not configured)
                config = get_config()
                allowed_domains = config.get("security", {}).get("cookie_domains", [])

                if host_only in allowed_domains:
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
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        # NO max_age - makes it a session cookie that expires on browser close
        path="/",  # Accessible from all paths (frontend and API)
        domain=cookie_domain,  # Set to request host for cross-port cookie sharing
    )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"User logged in successfully: {user.username} (role: {user.role}) (password_change_required: {password_change_required})")

    # v3.0 Unified: Include password change requirement in response for frontend handling
    response_data = {
        "message": "Login successful",
        "username": user.username,
        "role": user.role,
        "tenant_key": user.tenant_key
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
async def get_me(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    Get current user profile or return 401 if not authenticated.

    Two-Layout Pattern: Auth routes isolated in AuthLayout, app routes always require valid user.
    This endpoint returns authenticated user data with password_change_required flag when applicable.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        User profile data if authenticated, 401 JSON response otherwise
    """
    # Try to get current user (optional - doesn't raise exceptions)
    from src.giljo_mcp.auth.dependencies import get_current_user_optional

    current_user = await get_current_user_optional(
        request=request,
        access_token=request.cookies.get("access_token"),
        x_api_key=request.headers.get("x-api-key"),
        db=db,
    )

    # If no authenticated user, return clean 401 JSON response
    if current_user is None:
        return JSONResponse(
            status_code=401, content={"detail": "Not authenticated. Please login or provide a valid API key."}
        )

    # Check if password change is required (for admin user with default password)
    from src.giljo_mcp.models import SetupState

    # v3.0 Unified (Handover 0034): No more default admin/admin password
    # Fresh installs go directly to "Create Admin Account" page via first_admin_created flag
    # This check removed in Handover 0035 (field no longer exists in SetupState model)
    password_change_required = None

    # Return authenticated user profile
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
    )


@router.get("/api-keys", response_model=List[APIKeyResponse], tags=["auth"])
async def list_api_keys(
    include_revoked: bool = Query(False, description="Include revoked keys in results"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all API keys for current user.

    This endpoint returns all API keys (active and revoked) for the authenticated user.
    Keys are masked - only the prefix is shown for security.

    Args:
        current_user: User from JWT token (dependency)
        db: Database session

    Returns:
        List of API keys (masked)
    """
    # Query user's API keys (active by default, include revoked when requested)
    if include_revoked:
        stmt = select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
    else:
        stmt = (
            select(APIKey)
            .where(APIKey.user_id == current_user.id, APIKey.is_active == True)
            .order_by(APIKey.created_at.desc())
        )
    result = await db.execute(stmt)
    api_keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=str(key.id),
            name=key.name,
            key_prefix=key.key_prefix,
            permissions=key.permissions or [],
            is_active=key.is_active,
            created_at=key.created_at.isoformat(),
            last_used=key.last_used.isoformat() if key.last_used else None,
            revoked_at=key.revoked_at.isoformat() if key.revoked_at else None,
        )
        for key in api_keys
    ]


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def create_api_key(
    request: APIKeyCreateRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate a new API key for current user.

    This endpoint creates a new API key and returns it in plaintext.
    WARNING: The key is only shown once! Store it securely.

    Args:
        request: API key creation request (name, permissions)
        current_user: User from JWT token (dependency)
        db: Database session

    Returns:
        API key response with plaintext key (shown only once)
    """
    # Generate new API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_prefix = get_key_prefix(api_key, length=12)

    # Create API key record
    new_key = APIKey(
        user_id=current_user.id,
        tenant_key=current_user.tenant_key,
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=request.permissions,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    logger.info(f"API key created: {new_key.name} (user: {current_user.username}, prefix: {key_prefix})")

    return APIKeyCreateResponse(
        id=str(new_key.id),
        name=new_key.name,
        api_key=api_key,  # Plaintext key - only shown once!
        key_prefix=key_prefix,
        message="API key created successfully. Store this key securely - it will not be shown again!",
    )


@router.delete("/api-keys/{key_id}", response_model=APIKeyRevokeResponse, tags=["auth"])
async def revoke_api_key(
    key_id: UUID, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Revoke an API key.

    This endpoint revokes (deactivates) an API key. The key will no longer
    work for authentication after revocation.

    Args:
        key_id: UUID of API key to revoke
        current_user: User from JWT token (dependency)
        db: Database session

    Returns:
        Revocation confirmation

    Raises:
        HTTPException: 404 if key not found or belongs to another user
    """
    # Query API key
    stmt = select(APIKey).where(APIKey.id == str(key_id), APIKey.user_id == current_user.id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found or access denied")

    # Revoke key
    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"API key revoked: {api_key.name} (user: {current_user.username})")

    return APIKeyRevokeResponse(id=str(api_key.id), name=api_key.name, message="API key revoked successfully")



@router.get("/users", response_model=List[UserListResponse], tags=["auth"])
async def list_users(
    current_user: User = Depends(get_current_active_user), 
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all users in the current tenant (admin only).
    
    This endpoint returns all users in the same tenant as the authenticated user.
    Only admins can list users.
    
    Args:
        current_user: User from JWT token (dependency)
        db: Database session
        
    Returns:
        List of users in the tenant
        
    Raises:
        HTTPException: 403 if user is not admin
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin access required"
        )
    
    # Query users in the same tenant
    stmt = select(User).where(
        User.tenant_key == current_user.tenant_key
    ).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [
        UserListResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )
        for user in users
    ]

@router.post("/register", response_model=RegisterUserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register_user(
    request: RegisterUserRequest = Body(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user (admin only).

    This endpoint creates a new user account. Only admins can create new users.

    Args:
        request: User registration data
        current_user: Admin user from JWT token (dependency)
        db: Database session

    Returns:
        New user info

    Raises:
        HTTPException: 400 if username/email already exists
        HTTPException: 403 if not admin
    """
    # Check if username already exists
    stmt = select(User).where(User.username == request.username)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username '{request.username}' already exists"
        )

    # Check if email already exists (if provided)
    if request.email:
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        existing_email = result.scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email '{request.email}' already exists"
            )

    # Hash password
    password_hash = bcrypt.hash(request.password)

    # Create new user
    new_user = User(
        username=request.username,
        email=request.email,
        full_name=request.full_name,
        password_hash=password_hash,
        role=request.role,
        tenant_key=request.tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"User registered: {new_user.username} (role: {new_user.role}, by admin: {current_user.username})")

    return RegisterUserResponse(
        id=str(new_user.id),
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        tenant_key=new_user.tenant_key,
        message="User registered successfully",
    )



@router.post("/create-first-admin", response_model=RegisterUserResponse, status_code=201, tags=["auth"])
async def create_first_admin_user(
    response: Response,
    request: Request,
    request_body: RegisterUserRequest = Body(...),
    db: AsyncSession = Depends(get_db_session)
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
        db: Database session

    Returns:
        RegisterUserResponse with user details and success message

    Raises:
        HTTPException 403: If users already exist (not fresh install)
        HTTPException 400: If password doesn't meet requirements
        HTTPException 503: If database check fails (fail-secure)
    """
    from uuid import uuid4
    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    # Log client IP for audit trail (LAN access allowed for remote setup)
    client_ip = request.client.host
    logger.info(f"[SETUP] Admin creation attempt from IP: {client_ip}")

    # CRITICAL SECURITY FIX (Handover 0034): Acquire lock to prevent race condition
    # Without this lock, multiple concurrent requests could all check user_count == 0
    # simultaneously and create multiple admin accounts
    async with _first_admin_creation_lock:
        # SECURITY CHECK #1: Check if endpoint is already disabled (first admin created)
        # This is the PRIMARY security gate - if first admin exists, endpoint is permanently disabled
        from src.giljo_mcp.models import SetupState

        try:
            setup_check_stmt = select(SetupState).where(SetupState.first_admin_created == True)
            setup_check_result = await db.execute(setup_check_stmt)
            existing_setup = setup_check_result.scalar_one_or_none()

            if existing_setup:
                logger.warning(
                    f"[SECURITY] BLOCKED admin creation attempt from {client_ip} - "
                    f"first admin already created on {existing_setup.first_admin_created_at.isoformat()}. "
                    f"This endpoint is permanently disabled."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Administrator account already exists. This setup endpoint has been disabled. "
                           "Please use the login page instead."
                )
        except HTTPException:
            raise  # Re-raise our 403
        except Exception as setup_error:
            # If SetupState check fails, fall through to user count check (backwards compatibility)
            logger.warning(f"[SETUP] SetupState check failed: {setup_error}. Falling back to user count check.")

        # SECURITY CHECK: Verify no users exist (fresh install only)
        # FAIL-SECURE: If database check fails, block admin creation
        try:
            user_count_stmt = select(func.count(User.id))
            result = await db.execute(user_count_stmt)
            total_users = result.scalar()
        except Exception as db_error:
            logger.error(
                f"[SECURITY] Admin creation BLOCKED - database check failed: {db_error}. "
                f"Failing secure to prevent potential bypass attacks."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System temporarily unavailable. Database connection error. Please try again in a moment."
            )

        if total_users > 0:
            logger.warning(
                f"[SECURITY] Blocked create-first-admin attempt - {total_users} users already exist. "
                "This may be an attack attempt."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator account already exists. Please use the login page instead."
            )

        # Validate password strength (enforce 12+ char minimum for admin)
        if len(request_body.password) < 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin password must be at least 12 characters long"
            )

        # Check password complexity
        has_upper = any(c.isupper() for c in request_body.password)
        has_lower = any(c.islower() for c in request_body.password)
        has_digit = any(c.isdigit() for c in request_body.password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in request_body.password)

        if not (has_upper and has_lower and has_digit and has_special):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain uppercase, lowercase, digit, and special character"
            )

        # Hash password
        password_hash = bcrypt.hash(request_body.password)

        # Generate secure tenant key
        tenant_key = TenantManager.generate_tenant_key(request_body.username)

        # Create first admin user (force admin role)
        admin_user = User(
            id=str(uuid4()),
            username=request_body.username,
            email=request_body.email,
            full_name=request_body.full_name or "Administrator",
            password_hash=password_hash,
            role='admin',  # FORCE admin role for first user
            tenant_key=tenant_key,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )

        db.add(admin_user)

        # Seed default agent templates for this tenant (Handover 0041 Phase 2)
        # CRITICAL: Templates are seeded with the user's tenant_key (not default_tenant_key)
        # This ensures templates appear in UI immediately after user creation
        try:
            template_count = await seed_tenant_templates(db, tenant_key)
            logger.info(f"[SETUP] Seeded {template_count} default agent templates for tenant {tenant_key[:12]}...")
        except Exception as e:
            # Non-blocking - templates can be added later via UI
            logger.warning(f"[SETUP] Template seeding failed (non-critical): {e}")
            template_count = 0

        try:
            await db.commit()
            await db.refresh(admin_user)
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Failed to create first admin user: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )

        # Generate JWT token for immediate login
        token = JWTManager.create_access_token(
            user_id=str(admin_user.id),
            username=admin_user.username,
            role=admin_user.role,
            tenant_key=admin_user.tenant_key
        )

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
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host_only):
                    cookie_domain = host_only
                    logger.debug(f"Cookie domain set to IP address (safe): {host_only}")

                # SECURITY CHECK #2: Domain names MUST be whitelisted (prevent header injection)
                # Without whitelist, attacker could send "Host: evil.com" and steal cookies
                else:
                    # Load whitelist from config (defaults to empty list if not configured)
                    config = get_config()
                    allowed_domains = config.get("security", {}).get("cookie_domains", [])

                    if host_only in allowed_domains:
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
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            path="/",  # Accessible from all paths (frontend and API)
            domain=cookie_domain,  # Set to request host for cross-port cookie sharing
            max_age=86400  # 24 hours
        )

        # SECURITY: Disable this endpoint permanently after first admin created
        # This prevents any future attempts to create additional admins via this endpoint
        from src.giljo_mcp.models import SetupState

        setup_state_stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        setup_result = await db.execute(setup_state_stmt)
        setup_state = setup_result.scalar_one_or_none()

        if setup_state:
            setup_state.first_admin_created = True
            setup_state.first_admin_created_at = datetime.now(timezone.utc)
        else:
            # Create SetupState if it doesn't exist
            setup_state = SetupState(
                id=str(uuid4()),
                tenant_key=tenant_key,
                database_initialized=True,
                database_initialized_at=datetime.now(timezone.utc),
                first_admin_created=True,
                first_admin_created_at=datetime.now(timezone.utc)
            )
            db.add(setup_state)

        await db.commit()

        logger.info(
            f"[SETUP] First administrator account created successfully - "
            f"username: {admin_user.username}, tenant: {tenant_key[:12]}..., "
            f"client_ip: {client_ip}. Endpoint now DISABLED for security."
        )

        return RegisterUserResponse(
            id=str(admin_user.id),
            username=admin_user.username,
            email=admin_user.email,
            full_name=admin_user.full_name,
            role=admin_user.role,
            tenant_key=admin_user.tenant_key,
            is_active=admin_user.is_active,
        message="Administrator account created successfully. Redirecting to dashboard..."
    )


# REMOVED (Handover 0034): Legacy password change endpoint
# Replaced by clean first-admin creation flow via /create-first-admin
# Old endpoint required default admin/admin credentials and complex state tracking
# New flow: Fresh install (0 users) → Create admin account directly
