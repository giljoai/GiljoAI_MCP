"""
Authentication API endpoints for LAN/WAN modes.

Provides REST API for:
- Login/logout (JWT cookies for web users)
- User profile access
- API key management (create, list, revoke)
- User registration (admin only)

All endpoints support multi-tenant isolation through tenant_key.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session, require_admin
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models import APIKey, User


logger = logging.getLogger(__name__)
router = APIRouter()


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
    tenant_key: str = Field(default="default", description="Tenant key for multi-tenant isolation")

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


# Auth Endpoints


@router.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(
    request: LoginRequest = Body(...), response: Response = None, db: AsyncSession = Depends(get_db_session)
):
    """
    Login with username/password, returns JWT in httpOnly cookie.

    This endpoint authenticates a user and sets an httpOnly cookie
    containing a JWT access token valid for 24 hours.

    If default_password_active is true, returns 403 error directing
    user to change password first.

    Args:
        request: Login credentials (username, password)
        response: FastAPI response (to set cookie)
        db: Database session

    Returns:
        Login success message with user info

    Raises:
        HTTPException: 401 if credentials are invalid
        HTTPException: 403 if default password must be changed
    """
    # Find user by username
    stmt = select(User).where(User.username == request.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.warning(f"Login failed for username: {request.username} (user not found or inactive)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password
    if not bcrypt.verify(request.password, user.password_hash):
        logger.warning(f"Login failed for username: {request.username} (invalid password)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check if default password is still active (for admin user) - v3.0 Unified UX
    from src.giljo_mcp.models import SetupState

    stmt_setup = select(SetupState).where(SetupState.tenant_key == user.tenant_key)
    result_setup = await db.execute(stmt_setup)
    setup_state = result_setup.scalar_one_or_none()

    # v3.0 Unified: Allow admin/admin login but indicate password change required
    # No longer block with 403 - that's terrible UX. Login succeeds, frontend handles redirect.
    password_change_required = setup_state and setup_state.default_password_active and user.username == "admin"

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
    )

    # Set httpOnly cookie (session cookie - expires on browser close)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        # NO max_age - makes it a session cookie that expires on browser close
        path="/api",  # Ensure cookie is sent to all API routes (v1, auth, etc.)
        domain=None,  # Allow cookie to work with both localhost and network IPs
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

    password_change_required = None
    if current_user.username == "admin":
        stmt_setup = select(SetupState).where(SetupState.tenant_key == current_user.tenant_key)
        result_setup = await db.execute(stmt_setup)
        setup_state = result_setup.scalar_one_or_none()

        if setup_state and setup_state.default_password_active:
            password_change_required = True

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


@router.post("/change-password", response_model=PasswordChangeResponse, tags=["auth"])
async def change_password(
    request_body: PasswordChangeRequest = Body(...),
    response: Response = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change password from default admin/admin.

    This endpoint allows changing the default admin password.
    Requirements:
    - Current password must be 'admin'
    - New password must meet complexity requirements (12+ chars, uppercase, lowercase, digit, special char)
    - Passwords must match
    - Sets default_password_active: false on success
    - Returns JWT token for immediate login

    Args:
        request: Password change request
        db: Database session

    Returns:
        Password change success with JWT token

    Raises:
        HTTPException: 400 if passwords don't match
        HTTPException: 401 if current password is incorrect
        HTTPException: 404 if admin user not found
    """
    from src.giljo_mcp.models import SetupState

    # Validate passwords match
    if request_body.new_password != request_body.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Get admin user
    stmt = select(User).where(User.username == "admin")
    result = await db.execute(stmt)
    admin_user = result.scalar_one_or_none()

    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    # SECURITY: Check if setup already completed (defense-in-depth)
    # This prevents attackers from accessing /welcome directly to trigger password reset
    stmt_setup = select(SetupState).where(SetupState.tenant_key == admin_user.tenant_key)
    result_setup = await db.execute(stmt_setup)
    setup_state = result_setup.scalar_one_or_none()

    if setup_state and not setup_state.default_password_active:
        logger.warning(f"Password change attempt after setup completed (user: {admin_user.username})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed. Password can only be changed during initial setup. Use 'Change Password' in user settings instead."
        )

    # Verify current password
    if not bcrypt.verify(request_body.current_password, admin_user.password_hash):
        logger.warning("Password change failed: incorrect current password")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    # Hash new password
    new_password_hash = bcrypt.hash(request_body.new_password)

    # Update user
    admin_user.password_hash = new_password_hash

    # Update setup state
    stmt_setup = select(SetupState).where(SetupState.tenant_key == admin_user.tenant_key)
    result_setup = await db.execute(stmt_setup)
    setup_state = result_setup.scalar_one_or_none()

    if setup_state:
        setup_state.default_password_active = False
        setup_state.password_changed_at = datetime.now(timezone.utc)
    else:
        # Create setup state if it doesn't exist
        from uuid import uuid4

        setup_state = SetupState(
            id=str(uuid4()),
            tenant_key=admin_user.tenant_key,
            database_initialized=True,
            default_password_active=False,
            password_changed_at=datetime.now(timezone.utc),
            setup_version="3.0.0",
        )
        db.add(setup_state)

    await db.commit()

    logger.info(f"Password changed successfully for user: {admin_user.username}")

    # Don't set cookie or return token - force proper login
    # This ensures user data is properly loaded after authentication
    return PasswordChangeResponse(
        success=True,
        message="Password changed successfully. Please login with your new credentials.",
        token="",  # No token - must login
        user={
            "id": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role,
            "tenant_key": admin_user.tenant_key,
        },
    )
