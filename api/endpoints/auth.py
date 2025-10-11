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
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_current_user, require_admin, get_db_session
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models import APIKey, User


logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models for Request/Response

class LoginRequest(BaseModel):
    """Login request with username and password"""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    """Login response with user info"""
    message: str
    username: str
    role: str
    tenant_key: str


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


# Auth Endpoints

@router.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(
    request: LoginRequest = Body(...),
    response: Response = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Login with username/password, returns JWT in httpOnly cookie.

    This endpoint authenticates a user and sets an httpOnly cookie
    containing a JWT access token valid for 24 hours.

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
    stmt = select(User).where(User.username == request.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.warning(f"Login failed for username: {request.username} (user not found or inactive)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not bcrypt.verify(request.password, user.password_hash):
        logger.warning(f"Login failed for username: {request.username} (invalid password)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        tenant_key=user.tenant_key
    )

    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=86400  # 24 hours
    )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"User logged in successfully: {user.username} (role: {user.role})")

    return LoginResponse(
        message="Login successful",
        username=user.username,
        role=user.role,
        tenant_key=user.tenant_key
    )


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
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get current user profile from JWT or setup mode status.

    This endpoint returns:
    - Setup mode status if system is in setup mode
    - User profile if authenticated
    - Localhost dev user if in localhost mode (127.0.0.1) and NOT in setup mode

    Args:
        request: FastAPI request (to check setup mode)
        current_user: User from JWT token or None (localhost bypass)

    Returns:
        User profile data or setup mode status
    """
    # Check if system is in setup mode
    setup_mode = False
    try:
        # Get config from app state
        config = getattr(request.app.state, "api_state", None)
        if config:
            config = getattr(config, "config", None)
            if config:
                setup_mode = getattr(config, "setup_mode", False)
    except Exception as e:
        logger.warning(f"Could not check setup mode in /me endpoint: {e}")

    # If in setup mode, return setup mode status instead of fake user
    if setup_mode:
        return JSONResponse(
            status_code=200,
            content={
                "setup_mode": True,
                "message": "System in setup mode - authentication not available",
                "requires_setup": True
            }
        )

    # Localhost mode bypass - return default dev user (only when NOT in setup mode)
    if current_user is None:
        return UserProfileResponse(
            id="00000000-0000-0000-0000-000000000000",
            username="localhost",
            email=None,
            full_name="Localhost Developer",
            role="admin",
            tenant_key="default",
            is_active=True,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_login=None
        )

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
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


@router.get("/api-keys", response_model=List[APIKeyResponse], tags=["auth"])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    # Query user's API keys
    stmt = select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
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
            revoked_at=key.revoked_at.isoformat() if key.revoked_at else None
        )
        for key in api_keys
    ]


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def create_api_key(
    request: APIKeyCreateRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
        created_at=datetime.now(timezone.utc)
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
        message="API key created successfully. Store this key securely - it will not be shown again!"
    )


@router.delete("/api-keys/{key_id}", response_model=APIKeyRevokeResponse, tags=["auth"])
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or access denied"
        )

    # Revoke key
    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"API key revoked: {api_key.name} (user: {current_user.username})")

    return APIKeyRevokeResponse(
        id=str(api_key.id),
        name=api_key.name,
        message="API key revoked successfully"
    )


@router.post("/register", response_model=RegisterUserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register_user(
    request: RegisterUserRequest = Body(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' already exists"
        )

    # Check if email already exists (if provided)
    if request.email:
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        existing_email = result.scalar_one_or_none()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{request.email}' already exists"
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
        created_at=datetime.now(timezone.utc)
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
        message="User registered successfully"
    )
