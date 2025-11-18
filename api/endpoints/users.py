"""
User Management API endpoints.

Provides REST API for comprehensive user CRUD operations:
- List all users (admin only, filtered by tenant)
- Create new user (admin only)
- Get user details (admin or self)
- Update user profile (admin or self)
- Soft-delete user (admin only)
- Change user role (admin only)
- Change password (self or admin)
- Field Priority Configuration (Handover 0048):
  - GET /me/field-priority: Get user's config or defaults
  - PUT /me/field-priority: Update user's field priority config
  - POST /me/field-priority/reset: Reset to system defaults

All endpoints enforce role-based access control and multi-tenant isolation.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

# REMOVED: PlainTextResponse import (no longer needed)
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import (
    get_current_active_user,
    get_db_session,
    require_admin,
)
from src.giljo_mcp.models import User
from api.dependencies.websocket import get_websocket_dependency


logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic Models for Request/Response


class UserCreate(BaseModel):
    """Request model for creating a new user"""

    username: str = Field(..., min_length=3, max_length=64, description="Unique username")
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    role: str = Field("developer", description="User role: admin, developer, viewer")
    is_active: bool = Field(default=True, description="Whether user account is active")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of allowed values"""
        allowed_roles = ["admin", "developer", "viewer"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UserUpdate(BaseModel):
    """Request model for updating user profile"""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for user data (password excluded)"""

    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    tenant_key: str
    is_active: bool
    created_at: str
    last_login: Optional[str]


class PasswordChange(BaseModel):
    """Request model for password change"""

    old_password: Optional[str] = Field(None, min_length=8, description="Current password (required for non-admin)")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class RoleChange(BaseModel):
    """Request model for role change"""

    role: str = Field(..., description="New role: admin, developer, viewer")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of allowed values"""
        allowed_roles = ["admin", "developer", "viewer"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class UserDeleteResponse(BaseModel):
    """Response model for user deletion"""

    message: str
    user_id: str
    username: str


class RoleChangeResponse(BaseModel):
    """Response model for role change"""

    message: str
    user_id: str
    username: str
    role: str


class PasswordChangeResponse(BaseModel):
    """Response model for password change"""

    message: str


class FieldPriorityConfig(BaseModel):
    """
    Request/Response model for field priority configuration v2.0.

    Handover 0313: Priority System Refactor
    - v1.0: Priority = token reduction level (10/7/4/0)
    - v2.0: Priority = fetch order / mandatory flag (1/2/3/4)

    Valid categories: product_core, vision_documents, agent_templates,
                     project_context, memory_360, git_history

    Valid priorities:
    - 1: CRITICAL (always fetch, highest priority)
    - 2: IMPORTANT (fetch if budget allows)
    - 3: NICE_TO_HAVE (fetch if budget remaining)
    - 4: EXCLUDED (never fetch)
    """

    priorities: dict[str, int] = Field(
        ...,
        description="Category names mapped to priority (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED)"
    )
    version: str = Field("2.0", description="Config schema version")

    @field_validator("priorities")
    @classmethod
    def validate_priority_values(cls, v: dict[str, int]) -> dict[str, int]:
        """
        Validate priority configuration.

        Rules:
        1. Priority values must be in range [1, 4]
        2. At least one category must have Priority 1 (CRITICAL)
        3. Cannot have all categories as EXCLUDED (Priority 4)
        4. Valid categories only: product_core, vision_documents, agent_templates,
                                  project_context, memory_360, git_history
        """
        valid_priorities = {1, 2, 3, 4}
        valid_categories = {
            "product_core",
            "vision_documents",
            "agent_templates",
            "project_context",
            "memory_360",
            "git_history",
        }

        # Validate priority range
        for category, priority in v.items():
            if priority not in valid_priorities:
                raise ValueError(
                    f"Invalid priority {priority} for category '{category}'. "
                    f"Must be one of: 1 (CRITICAL), 2 (IMPORTANT), 3 (NICE_TO_HAVE), 4 (EXCLUDED)"
                )

        # Validate category names
        invalid_categories = set(v.keys()) - valid_categories
        if invalid_categories:
            raise ValueError(
                f"Invalid category names: {invalid_categories}. "
                f"Valid categories: {valid_categories}"
            )

        # Ensure at least one CRITICAL category
        critical_categories = [cat for cat, pri in v.items() if pri == 1]
        if not critical_categories:
            raise ValueError("At least one category must have Priority 1 (CRITICAL)")

        # Ensure not all EXCLUDED
        all_excluded = all(pri == 4 for pri in v.values())
        if all_excluded:
            raise ValueError("Cannot exclude all categories. At least one must be Priority 1, 2, or 3")

        return v


# Helper Functions


def user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse (excludes password)"""
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_key=user.tenant_key,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


# API Endpoints


@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db_session)
) -> list[UserResponse]:
    """
    List all users in current tenant.

    Requires admin role. Returns all users filtered by tenant_key for multi-tenant isolation.

    Args:
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        List of UserResponse objects (passwords excluded)

    Raises:
        HTTPException: 403 if user is not admin
    """
    logger.debug(f"Admin {current_user.username} listing users for tenant {current_user.tenant_key}")

    # Query users filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.tenant_key == current_user.tenant_key).order_by(User.created_at)
    result = await db.execute(stmt)
    users = result.scalars().all()

    logger.info(f"Found {len(users)} users for tenant {current_user.tenant_key}")
    return [user_to_response(user) for user in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Create a new user.

    Requires admin role. New user inherits tenant_key from admin.

    Args:
        user_data: User creation data
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Created user data (password excluded)

    Raises:
        HTTPException: 400 if username or email already exists
        HTTPException: 403 if user is not admin
    """
    logger.debug(f"Admin {current_user.username} creating user: {user_data.username}")

    # Check for duplicate username (global uniqueness)
    stmt = select(User).where(User.username == user_data.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' already exists",
        )

    # Check for duplicate email if provided
    if user_data.email:
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' already exists",
            )

    # Hash default password 'GiljoMCP' (Handover 0023)
    password_hash = bcrypt.hash("GiljoMCP")

    # Create user (inherits tenant_key from admin)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=password_hash,
        role=user_data.role,
        is_active=user_data.is_active,
        tenant_key=current_user.tenant_key,  # Inherit tenant from admin
        must_change_password=True,  # Force password change on first login
        must_set_pin=True,  # Force PIN setup on first login
        recovery_pin_hash=None,  # No PIN set initially
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"Created user: {new_user.username} (role: {new_user.role}) in tenant {new_user.tenant_key}")
    return user_to_response(new_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Get user details by ID.

    Admin can view any user in their tenant. Non-admin can only view themselves.

    Args:
        user_id: UUID of user to retrieve
        current_user: Current authenticated user
        db: Database session

    Returns:
        User data (password excluded)

    Raises:
        HTTPException: 403 if non-admin tries to view other users
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"User {current_user.username} retrieving user {user_id}")

    # Query user filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.id == str(user_id), User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Authorization: admin can view any user, non-admin can only view self
    if current_user.role != "admin" and user.id != current_user.id:
        logger.warning(f"Non-admin {current_user.username} tried to view user {user.username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' profiles")

    return user_to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Update user profile.

    Admin can update any user in their tenant. Non-admin can only update themselves.

    Args:
        user_id: UUID of user to update
        user_data: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user data (password excluded)

    Raises:
        HTTPException: 400 if email already exists
        HTTPException: 403 if non-admin tries to update other users
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"User {current_user.username} updating user {user_id}")

    # Query user filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.id == str(user_id), User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Authorization: admin can update any user, non-admin can only update self
    if current_user.role != "admin" and user.id != current_user.id:
        logger.warning(f"Non-admin {current_user.username} tried to update user {user.username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update other users' profiles")

    # Check for duplicate email if changing email
    if user_data.email and user_data.email != user.email:
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' already exists",
            )

    # Update fields (only update non-None values)
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    logger.info(f"Updated user: {user.username}")
    return user_to_response(user)


@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> UserDeleteResponse:
    """
    Soft-delete user by deactivating account.

    Requires admin role. Sets is_active=False instead of hard deletion for audit trail.

    Args:
        user_id: UUID of user to deactivate
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Deletion confirmation message

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"Admin {current_user.username} deactivating user {user_id}")

    # Query user filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.id == str(user_id), User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Soft delete: deactivate instead of hard delete
    user.is_active = False
    await db.commit()

    logger.info(f"Deactivated user: {user.username}")
    return UserDeleteResponse(message="User deactivated successfully", user_id=str(user.id), username=user.username)


@router.put("/{user_id}/role", response_model=RoleChangeResponse)
async def change_user_role(
    user_id: UUID,
    role_data: RoleChange,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> RoleChangeResponse:
    """
    Change user role.

    Requires admin role. Admin cannot change their own role (prevent lockout).

    Args:
        user_id: UUID of user to change role
        role_data: New role data
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Role change confirmation with new role

    Raises:
        HTTPException: 400 if admin tries to change their own role
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"Admin {current_user.username} changing role for user {user_id} to {role_data.role}")

    # Query user filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.id == str(user_id), User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-demotion (admin cannot change their own role)
    if user.id == current_user.id:
        logger.warning(f"Admin {current_user.username} tried to change their own role")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role (prevents lockout)",
        )

    # Update role
    old_role = user.role
    user.role = role_data.role
    await db.commit()

    logger.info(f"Changed role for user {user.username}: {old_role} -> {user.role}")
    return RoleChangeResponse(
        message="User role updated successfully",
        user_id=str(user.id),
        username=user.username,
        role=user.role,
    )


@router.put("/{user_id}/password", response_model=PasswordChangeResponse)
async def change_password(
    user_id: UUID,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> PasswordChangeResponse:
    """
    Change user password.

    Users can change their own password (requires old password verification).
    Admin can change any user's password (no old password required).

    Args:
        user_id: UUID of user to change password
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Password change confirmation

    Raises:
        HTTPException: 400 if old password is incorrect
        HTTPException: 403 if non-admin tries to change other users' passwords
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"User {current_user.username} changing password for user {user_id}")

    # Query user filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.id == str(user_id), User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Authorization: admin can change any password, non-admin can only change own
    if current_user.role != "admin" and user.id != current_user.id:
        logger.warning(f"Non-admin {current_user.username} tried to change password for {user.username}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change other users' passwords")

    # If user is changing their own password, verify old password
    if user.id == current_user.id and current_user.role != "admin":
        if not password_data.old_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change your password",
            )

        # Verify old password
        if not bcrypt.verify(password_data.old_password, user.password_hash):
            logger.warning(f"User {user.username} provided incorrect current password")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Admin changing other user's password doesn't require old password
    # (password reset scenario)

    # Hash and update password
    user.password_hash = bcrypt.hash(password_data.new_password)
    await db.commit()

    logger.info(f"Password changed for user: {user.username}")
    return PasswordChangeResponse(message="Password updated successfully")


@router.post("/{user_id}/reset-password", response_model=PasswordChangeResponse)
async def reset_password(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PasswordChangeResponse:
    """
    Reset user password to default 'GiljoMCP' (Handover 0023).

    Requires admin role. Admin can reset any user's password including their own.
    Resets password to default 'GiljoMCP' and sets must_change_password=True.
    Keeps recovery_pin_hash unchanged and clears PIN lockout.

    Args:
        user_id: UUID of user to reset password
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Password reset confirmation

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"Admin {current_user.username} resetting password for user {user_id}")

    # Query user filtered by tenant_key (multi-tenant isolation)
    stmt = select(User).where(User.id == str(user_id), User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Reset password to default 'GiljoMCP'
    user.password_hash = bcrypt.hash("GiljoMCP")

    # Set must_change_password flag
    user.must_change_password = True

    # Keep recovery_pin_hash unchanged (user retains PIN)

    # Clear PIN lockout
    user.failed_pin_attempts = 0
    user.pin_lockout_until = None

    await db.commit()

    logger.info(f"Admin {current_user.username} reset password for user: {user.username}")
    return PasswordChangeResponse(message="Password reset successful")


# Field Priority Configuration Endpoints (Handover 0048)


@router.get("/me/field-priority", response_model=FieldPriorityConfig)
async def get_field_priority_config(
    current_user: User = Depends(get_current_active_user),
) -> FieldPriorityConfig:
    """
    Get user's field priority configuration or default (v2.0).

    Returns the authenticated user's custom field priority configuration if set,
    otherwise returns the system default v2.0 configuration.

    Handover 0313: Priority System Refactor (v1.0 → v2.0)
    - v1.0: Priority = token reduction level (10/7/4/0)
    - v2.0: Priority = fetch order / mandatory flag (1/2/3/4)

    Args:
        current_user: Current authenticated user

    Returns:
        FieldPriorityConfig: User's custom config or system defaults (v2.0)

    Example Response (v2.0):
        {
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 2,
                "project_context": 2,
                "memory_360": 3,
                "git_history": 4
            }
        }
    """
    logger.debug(f"User {current_user.username} retrieving field priority config")

    # Return user's custom config if set
    if current_user.field_priority_config:
        logger.debug(f"Returning custom field priority config for user {current_user.username}")
        return FieldPriorityConfig(**current_user.field_priority_config)

    # Return system defaults if no custom config (v2.0)
    logger.debug(f"Returning default field priority config for user {current_user.username}")
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    return FieldPriorityConfig(**DEFAULT_FIELD_PRIORITY)


@router.put("/me/field-priority", response_model=FieldPriorityConfig)
async def update_field_priority_config(
    config: FieldPriorityConfig,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dependency: "WebSocketDependency" = Depends(get_websocket_dependency),
) -> FieldPriorityConfig:
    """
    Update user's field priority configuration (v2.0).

    Validates category names and priority values before saving. Emits WebSocket
    event for real-time UI synchronization across clients.

    Handover 0313: Priority System Refactor (v1.0 → v2.0)
    - v1.0 removed: field validation, token budget validation
    - v2.0 added: category validation, CRITICAL requirement, WebSocket emission

    Args:
        config: New field priority configuration (v2.0)
        current_user: Current authenticated user
        db: Database session
        ws_dependency: WebSocket manager for event emission

    Returns:
        FieldPriorityConfig: Updated configuration

    Raises:
        HTTPException: 422 if Pydantic validation fails (invalid priority, no CRITICAL, etc.)

    Example Request (v2.0):
        {
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 2,
                "project_context": 2,
                "memory_360": 3,
                "git_history": 4
            }
        }
    """
    logger.debug(
        f"User {current_user.username} updating field priority config to v{config.version}",
        extra={"user_id": str(current_user.id), "tenant_key": current_user.tenant_key, "config_version": config.version},
    )

    # Pydantic validation already enforced (1-4 range, CRITICAL requirement, valid categories)
    # No additional validation needed - Pydantic schema handles all rules

    # Update user's config (store as dict for JSONB column)
    current_user.field_priority_config = config.model_dump()
    await db.commit()
    await db.refresh(current_user)

    logger.info(
        f"Updated field priority config for user: {current_user.username}",
        extra={
            "user_id": str(current_user.id),
            "tenant_key": current_user.tenant_key,
            "priorities": config.priorities,
        },
    )

    # Emit WebSocket event for real-time UI synchronization
    try:
        await ws_dependency.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="priority_config_updated",
            data={
                "user_id": str(current_user.id),
                "timestamp": current_user.updated_at.isoformat() if current_user.updated_at else None,
                "priorities": config.priorities,
                "version": config.version,
            },
            schema_version="2.0",
        )
        logger.debug(
            f"WebSocket event 'priority_config_updated' emitted for user {current_user.username}",
            extra={"user_id": str(current_user.id), "tenant_key": current_user.tenant_key},
        )
    except Exception as e:
        # Don't fail request if WebSocket emission fails
        logger.warning(
            f"Failed to emit WebSocket event for priority config update: {e}",
            extra={"user_id": str(current_user.id), "tenant_key": current_user.tenant_key, "error": str(e)},
        )

    return config


@router.post("/me/field-priority/reset", response_model=FieldPriorityConfig)
async def reset_field_priority_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> FieldPriorityConfig:
    """
    Reset field priority configuration to system defaults.

    Clears user's custom configuration and returns system defaults.
    Useful for reverting customizations.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        FieldPriorityConfig: System default configuration

    Example Response:
        {
            "version": "1.0",
            "token_budget": 1500,
            "fields": {
                "tech_stack.languages": 1,
                "tech_stack.backend": 1,
                ...
            }
        }
    """
    logger.debug(f"User {current_user.username} resetting field priority config to defaults")

    # Clear user's custom config
    current_user.field_priority_config = None
    await db.commit()
    await db.refresh(current_user)

    logger.info(f"Reset field priority config to defaults for user: {current_user.username}")

    # Return system defaults
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    return FieldPriorityConfig(**DEFAULT_FIELD_PRIORITY)


# AI Tools Configurator Endpoint (relocated from /setup/ai-tools)


# REMOVED: ai_tools_configurator endpoint
# This backend approach has been deprecated in favor of Project 0031's
# frontend-only dynamic mini-wizard that eliminates backend complexity.


# REMOVED: detect_ai_tool_from_user_agent function (deprecated)


# REMOVED: generate_claude_code_instructions function (deprecated)


# REMOVED: generate_codex_instructions function (deprecated)


# REMOVED: generate_gemini_instructions function (deprecated)


# REMOVED: generate_cursor_instructions function (deprecated)


# REMOVED: generate_continue_instructions function (deprecated)


# REMOVED: generate_universal_instructions function (deprecated)
