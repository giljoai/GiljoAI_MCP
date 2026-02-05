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
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

# REMOVED: PlainTextResponse import (no longer needed)
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from api.endpoints.dependencies import get_user_service
from src.giljo_mcp.auth.dependencies import (
    get_current_active_user,
    require_admin,
)
from src.giljo_mcp.models import User
from src.giljo_mcp.services import UserService


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
    password: Optional[str] = Field(None, min_length=8, description="New password (min 8 chars)")


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
                     project_description, memory_360, git_history

    Valid priorities:
    - 1: CRITICAL (always fetch, highest priority)
    - 2: IMPORTANT (fetch if budget allows)
    - 3: NICE_TO_HAVE (fetch if budget remaining)
    - 4: EXCLUDED (never fetch)
    """

    priorities: dict[str, int] = Field(
        ..., description="Category names mapped to priority (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED)"
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
                                  project_description, memory_360, git_history,
                                  tech_stack, architecture, testing
        """
        valid_priorities = {1, 2, 3, 4}
        valid_categories = {
            "product_core",
            "vision_documents",
            "agent_templates",
            "project_description",
            "memory_360",
            "git_history",
            "tech_stack",
            "architecture",
            "testing",
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
            raise ValueError(f"Invalid category names: {invalid_categories}. " f"Valid categories: {valid_categories}")

        # Ensure at least one CRITICAL category
        critical_categories = [cat for cat, pri in v.items() if pri == 1]
        if not critical_categories:
            raise ValueError("At least one category must have Priority 1 (CRITICAL)")

        # Ensure not all EXCLUDED
        all_excluded = all(pri == 4 for pri in v.values())
        if all_excluded:
            raise ValueError("Cannot exclude all categories. At least one must be Priority 1, 2, or 3")

        return v


class ExecutionModeUpdate(BaseModel):
    """Request model for updating execution mode."""

    execution_mode: Literal["claude_code", "multi_terminal"] = Field(
        ..., description="Execution mode: claude_code or multi_terminal"
    )


class DepthConfig(BaseModel):
    """
    Depth configuration for context extraction granularity (Handovers 0314, 0347d, 0347e).

    Controls HOW MUCH detail to extract from each context source.
    Orthogonal to priority system (which controls WHAT to fetch).

    Valid values per field:
    - vision_documents: none, optional, light, medium, full (0347e)
    - memory_last_n_projects: 1, 3, 5, 10
    - git_commits: 10, 25, 50, 100
    - agent_templates: type_only, full (0347d)
    - tech_stack_sections: required, all
    - architecture_depth: overview, detailed
    """

    vision_documents: Literal["none", "optional", "light", "medium", "full"] = Field(
        default="medium", description="Vision document depth level: none/optional/light/medium/full (Handover 0347e)"
    )
    memory_last_n_projects: Literal[1, 3, 5, 10] = Field(
        default=3, description="Number of recent projects to include in 360 memory"
    )
    git_commits: Literal[5, 10, 25, 50, 100] = Field(default=25, description="Number of recent git commits to include")
    agent_templates: Literal["type_only", "full"] = Field(
        default="type_only", description="Detail level for agent templates: type_only/full (Handover 0347d)"
    )
    tech_stack_sections: Literal["required", "all"] = Field(default="all", description="Tech stack sections to include")
    architecture_depth: Literal["overview", "detailed"] = Field(
        default="overview", description="Architecture documentation depth"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vision_documents": "medium",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_templates": "type_only",
                "tech_stack_sections": "all",
                "architecture_depth": "overview",
            }
        }
    )


class UpdateDepthConfigRequest(BaseModel):
    """Request to update user depth configuration."""

    depth_config: DepthConfig


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


def migrate_project_context_to_description(user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old 'project_context' field name to 'project_description'.

    Handles backward compatibility for existing user configurations created
    before Handover 0350c renamed this field.

    Args:
        user_config: User's field priority configuration dict

    Returns:
        Updated config with project_context renamed to project_description
    """
    if "priorities" in user_config:
        priorities = user_config["priorities"]
        if "project_context" in priorities and "project_description" not in priorities:
            priorities["project_description"] = priorities.pop("project_context")
    elif "project_context" in user_config and "project_description" not in user_config:
        user_config["project_description"] = user_config.pop("project_context")
    return user_config


# API Endpoints


@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin), user_service: UserService = Depends(get_user_service)
) -> list[UserResponse]:
    """
    List all users (admin cross-tenant view).

    Requires admin role. Returns all users across all tenants so admins can manage
    users they created (per-user tenancy means each user has their own tenant_key).

    Args:
        current_user: Current authenticated admin user
        user_service: User service for database operations

    Returns:
        List of UserResponse objects (passwords excluded)

    Raises:
        HTTPException: 403 if user is not admin
    """
    logger.debug(f"Admin {current_user.username} listing all users (cross-tenant admin view)")

    # Admin sees all users across all tenants for user management
    result = await user_service.list_users(include_all_tenants=True)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.info(f"Found {len(result['data'])} users (all tenants)")

    # Convert service response to UserResponse objects
    return [
        UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            tenant_key=user["tenant_key"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user["last_login"],
        )
        for user in result["data"]
    ]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Create a new user.

    Requires admin role. New user inherits tenant_key from admin.

    Args:
        user_data: User creation data
        current_user: Current authenticated admin user
        user_service: User service for database operations

    Returns:
        Created user data (password excluded)

    Raises:
        HTTPException: 400 if username or email already exists
        HTTPException: 403 if user is not admin
    """
    logger.debug(f"Admin {current_user.username} creating user: {user_data.username}")

    result = await user_service.create_user(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password=None,  # Use default password 'GiljoMCP'
        role=user_data.role,
        is_active=user_data.is_active,
    )

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.info(f"Created user: {user_data.username} (role: {user_data.role}) in tenant {current_user.tenant_key}")

    user = result["user"]
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        tenant_key=user["tenant_key"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=None,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Get user details by ID.

    Admin can view any user across all tenants (per-user tenancy design).
    Non-admin can only view themselves.

    Args:
        user_id: UUID of user to retrieve
        current_user: Current authenticated user
        user_service: User service for database operations

    Returns:
        User data (password excluded)

    Raises:
        HTTPException: 403 if non-admin tries to view other users
        HTTPException: 404 if user not found
    """
    logger.debug(f"User {current_user.username} retrieving user {user_id}")

    # Admin can access users across all tenants for user management
    is_admin = current_user.role == "admin"
    result = await user_service.get_user(str(user_id), include_all_tenants=is_admin)

    if not result["success"]:
        logger.warning(f"User {user_id} not found" + ("" if is_admin else f" in tenant {current_user.tenant_key}"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    user = result["user"]

    # Authorization: admin can view any user, non-admin can only view self
    if not is_admin and user["id"] != str(current_user.id):
        logger.warning(f"Non-admin {current_user.username} tried to view user {user['username']}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' profiles")

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        tenant_key=user["tenant_key"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user["last_login"],
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Update user profile.

    Admin can update any user in their tenant. Non-admin can only update themselves.

    Args:
        user_id: UUID of user to update
        user_data: Fields to update
        current_user: Current authenticated user
        user_service: User service for database operations

    Returns:
        Updated user data (password excluded)

    Raises:
        HTTPException: 400 if email already exists
        HTTPException: 403 if non-admin tries to update other users
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"User {current_user.username} updating user {user_id}")

    # Admin can access users across all tenants for user management
    is_admin = current_user.role == "admin"

    # Authorization: admin can update any user, non-admin can only update self
    get_result = await user_service.get_user(str(user_id), include_all_tenants=is_admin)
    if not get_result["success"]:
        logger.warning(f"User {user_id} not found" + ("" if is_admin else f" in tenant {current_user.tenant_key}"))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_result["error"])

    user = get_result["user"]
    if not is_admin and user["id"] != str(current_user.id):
        logger.warning(f"Non-admin {current_user.username} tried to update user {user['username']}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update other users' profiles")

    # Build updates dict (only include non-None values)
    updates = {}
    if user_data.email is not None:
        updates["email"] = user_data.email
    if user_data.full_name is not None:
        updates["full_name"] = user_data.full_name
    if user_data.is_active is not None:
        updates["is_active"] = user_data.is_active
    if user_data.password is not None:
        updates["password"] = user_data.password

    result = await user_service.update_user(str(user_id), include_all_tenants=is_admin, **updates)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.info(f"Updated user: {user['username']}")

    updated_user = result["user"]
    return UserResponse(
        id=updated_user["id"],
        username=updated_user["username"],
        email=updated_user["email"],
        full_name=updated_user["full_name"],
        role=updated_user["role"],
        tenant_key=current_user.tenant_key,
        is_active=updated_user["is_active"],
        created_at=user["created_at"],  # Use original created_at
        last_login=user["last_login"],
    )


@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserDeleteResponse:
    """
    Soft-delete user by deactivating account.

    Requires admin role. Sets is_active=False instead of hard deletion for audit trail.

    Args:
        user_id: UUID of user to deactivate
        current_user: Current authenticated admin user
        user_service: User service for database operations

    Returns:
        Deletion confirmation message

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"Admin {current_user.username} deactivating user {user_id}")

    result = await user_service.delete_user(str(user_id))

    if not result["success"]:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    logger.info(f"Deactivated user: {result['username']}")
    return UserDeleteResponse(message=result["message"], user_id=result["user_id"], username=result["username"])


@router.put("/{user_id}/role", response_model=RoleChangeResponse)
async def change_user_role(
    user_id: UUID,
    role_data: RoleChange,
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> RoleChangeResponse:
    """
    Change user role.

    Requires admin role. Admin cannot change their own role (prevent lockout).

    Args:
        user_id: UUID of user to change role
        role_data: New role data
        current_user: Current authenticated admin user
        user_service: User service for database operations

    Returns:
        Role change confirmation with new role

    Raises:
        HTTPException: 400 if admin tries to change their own role
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"Admin {current_user.username} changing role for user {user_id} to {role_data.role}")

    # Prevent self-demotion (admin cannot change their own role)
    if str(user_id) == str(current_user.id):
        logger.warning(f"Admin {current_user.username} tried to change their own role")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role (prevents lockout)",
        )

    result = await user_service.change_role(str(user_id), role_data.role)

    if not result["success"]:
        logger.warning(f"Failed to change role for user {user_id}: {result['error']}")
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    user = result["user"]
    logger.info(f"Changed role for user {user['username']} to {user['role']}")

    return RoleChangeResponse(
        message="User role updated successfully",
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )


@router.put("/{user_id}/password", response_model=PasswordChangeResponse)
async def change_password(
    user_id: UUID,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> PasswordChangeResponse:
    """
    Change user password.

    Users can change their own password (requires old password verification).
    Admin can change any user's password (no old password required).

    Args:
        user_id: UUID of user to change password
        password_data: Password change data
        current_user: Current authenticated user
        user_service: User service for database operations

    Returns:
        Password change confirmation

    Raises:
        HTTPException: 400 if old password is incorrect
        HTTPException: 403 if non-admin tries to change other users' passwords
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"User {current_user.username} changing password for user {user_id}")

    # Authorization: admin can change any password, non-admin can only change own
    if current_user.role != "admin" and str(user_id) != str(current_user.id):
        logger.warning(f"Non-admin {current_user.username} tried to change password for user {user_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change other users' passwords")

    # Determine if admin is bypassing old password check
    is_admin = current_user.role == "admin" and str(user_id) != str(current_user.id)

    result = await user_service.change_password(
        str(user_id),
        old_password=password_data.old_password,
        new_password=password_data.new_password,
        is_admin=is_admin,
    )

    if not result["success"]:
        logger.warning(f"Failed to change password for user {user_id}: {result['error']}")
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.info(f"Password changed for user: {user_id}")
    return PasswordChangeResponse(message=result["message"])


@router.post("/{user_id}/reset-password", response_model=PasswordChangeResponse)
async def reset_password(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> PasswordChangeResponse:
    """
    Reset user password to default 'GiljoMCP' (Handover 0023).

    Requires admin role. Admin can reset any user's password including their own.
    Resets password to default 'GiljoMCP' and sets must_change_password=True.
    Keeps recovery_pin_hash unchanged and clears PIN lockout.

    Args:
        user_id: UUID of user to reset password
        current_user: Current authenticated admin user
        user_service: User service for database operations

    Returns:
        Password reset confirmation

    Raises:
        HTTPException: 403 if user is not admin
        HTTPException: 404 if user not found or in different tenant
    """
    logger.debug(f"Admin {current_user.username} resetting password for user {user_id}")

    result = await user_service.reset_password(str(user_id))

    if not result["success"]:
        logger.warning(f"User {user_id} not found in tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])

    logger.info(f"Admin {current_user.username} reset password for user: {user_id}")
    return PasswordChangeResponse(message=result["message"])


# Field Priority Configuration Endpoints (Handover 0048)


@router.get("/me/field-priority", response_model=FieldPriorityConfig)
async def get_field_priority_config(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
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
        user_service: User service for database operations

    Returns:
        FieldPriorityConfig: User's custom config or system defaults (v2.0)

    Example Response (v2.0):
        {
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 2,
                "project_description": 2,
                "memory_360": 3,
                "git_history": 4
            }
        }
    """
    logger.debug(f"User {current_user.username} retrieving field priority config")

    result = await user_service.get_field_priority_config(str(current_user.id))

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.debug(f"Returning field priority config for user {current_user.username}")
    return FieldPriorityConfig(**result["config"])


@router.put("/me/field-priority", response_model=FieldPriorityConfig)
async def update_field_priority_config(
    config: FieldPriorityConfig,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
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
        user_service: User service for database operations

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
                "project_description": 2,
                "memory_360": 3,
                "git_history": 4
            }
        }
    """
    logger.debug(
        f"User {current_user.username} updating field priority config to v{config.version}",
        extra={
            "user_id": str(current_user.id),
            "tenant_key": current_user.tenant_key,
            "config_version": config.version,
        },
    )

    # Pydantic validation already enforced (1-4 range, CRITICAL requirement, valid categories)
    # Update via service (service handles WebSocket emission)
    result = await user_service.update_field_priority_config(str(current_user.id), config.model_dump())

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result["error"])

    logger.info(
        f"Updated field priority config for user: {current_user.username}",
        extra={
            "user_id": str(current_user.id),
            "tenant_key": current_user.tenant_key,
            "priorities": config.priorities,
        },
    )

    return config


@router.post("/me/field-priority/reset", response_model=FieldPriorityConfig)
async def reset_field_priority_config(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> FieldPriorityConfig:
    """
    Reset field priority configuration to system defaults.

    Clears user's custom configuration and returns system defaults.
    Useful for reverting customizations.

    Args:
        current_user: Current authenticated user
        user_service: User service for database operations

    Returns:
        FieldPriorityConfig: System default configuration

    Example Response:
        {
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                ...
            }
        }
    """
    logger.debug(f"User {current_user.username} resetting field priority config to defaults")

    result = await user_service.reset_field_priority_config(str(current_user.id))

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.info(f"Reset field priority config to defaults for user: {current_user.username}")

    # Return system defaults
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    return FieldPriorityConfig(**DEFAULT_FIELD_PRIORITY)


# Depth Configuration Endpoints (Handover 0314)


@router.get("/me/context/depth", response_model=Dict[str, Any])
async def get_depth_config(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> Dict[str, Any]:
    """
    Get user's depth configuration.

    Returns the authenticated user's depth configuration (or defaults).

    Handover 0314: Context Management v2.0 - Depth Controls
    - Controls HOW MUCH detail to extract from each context source
    - Orthogonal to priority system (which controls WHAT to fetch)

    Args:
        current_user: Current authenticated user
        user_service: User service for database operations

    Returns:
        Dict with depth_config field

    Example Response:
        {
            "depth_config": {
                "vision_documents": "medium",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_templates": "type_only",
                "tech_stack_sections": "all",
                "architecture_depth": "overview"
            }
        }
    """
    logger.debug(f"User {current_user.username} retrieving depth config")

    result = await user_service.get_depth_config(str(current_user.id))

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    logger.debug(f"Returning depth config for user {current_user.username}")

    return {"depth_config": result["config"]}


@router.put("/me/context/depth", response_model=Dict[str, Any])
async def update_depth_config(
    depth_request: UpdateDepthConfigRequest,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> Dict[str, Any]:
    """
    Update user's depth configuration.

    Validates depth settings via Pydantic schema and saves to database.
    Emits WebSocket event for real-time UI synchronization.

    Handover 0314: Context Management v2.0 - Depth Controls

    Args:
        depth_request: New depth configuration
        current_user: Current authenticated user
        user_service: User service for database operations

    Returns:
        Dict with updated depth_config

    Raises:
        HTTPException: 422 if Pydantic validation fails (invalid depth values)

    Example Request:
        {
            "depth_config": {
                "vision_documents": "full",
                "memory_last_n_projects": 5,
                "git_commits": 50,
                "agent_templates": "full",
                "tech_stack_sections": "all",
                "architecture_depth": "detailed"
            }
        }
    """
    logger.debug(
        f"User {current_user.username} updating depth config",
        extra={"user_id": str(current_user.id), "tenant_key": current_user.tenant_key},
    )

    result = await user_service.update_depth_config(str(current_user.id), depth_request.depth_config.model_dump())

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result["error"])

    logger.info(
        f"Updated depth config for user: {current_user.username}",
        extra={"user_id": str(current_user.id), "tenant_key": current_user.tenant_key},
    )

    # Get updated config from service result
    get_result = await user_service.get_depth_config(str(current_user.id))
    if not get_result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=get_result["error"])

    return {"depth_config": get_result["config"]}

# ---------------------------------------------------------------------------
# Execution mode settings (0248c)
# ---------------------------------------------------------------------------


@router.get("/me/settings/execution_mode")
async def get_execution_mode(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> Dict[str, str]:
    """Get the current user's execution mode."""
    result = await user_service.get_execution_mode(str(current_user.id))
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return {"execution_mode": result["execution_mode"]}


@router.put("/me/settings/execution_mode")
async def update_execution_mode(
    payload: ExecutionModeUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> Dict[str, str]:
    """Update the current user's execution mode."""
    result = await user_service.update_execution_mode(
        user_id=str(current_user.id),
        execution_mode=payload.execution_mode,
    )
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return {"execution_mode": result["execution_mode"]}


