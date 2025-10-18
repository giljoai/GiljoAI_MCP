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
- AI Tools Configurator (authenticated access)

All endpoints enforce role-based access control and multi-tenant isolation.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
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

    # Hash password
    password_hash = bcrypt.hash(user_data.password)

    # Create user (inherits tenant_key from admin)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=password_hash,
        role=user_data.role,
        is_active=user_data.is_active,
        tenant_key=current_user.tenant_key,  # Inherit tenant from admin
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


# AI Tools Configurator Endpoint (relocated from /setup/ai-tools)


@router.get("/ai-tools-configurator", response_class=PlainTextResponse)
async def ai_tools_configurator(
    request: Request,
    tool: Optional[str] = Query(None, description="AI tool type: claude-code, codex, gemini, cursor, continue"),
    user_agent: str = Header(None),
    current_user: User = Depends(get_current_active_user),
) -> str:
    """
    AI Tools Configurator - generates MCP configuration instructions for AI coding tools.
    
    This endpoint provides tailored configuration instructions based on the requesting AI tool.
    Can auto-detect tool type from User-Agent or use explicit tool parameter.
    
    Requires authentication - users must be logged in to access configurator.
    
    Args:
        request: FastAPI Request object
        tool: Optional explicit AI tool type
        user_agent: User-Agent header for auto-detection
        current_user: Authenticated user (from JWT/session)
    
    Returns:
        Plain text configuration instructions tailored to the AI tool
    """
    logger.info(f"User {current_user.username} accessing AI tools configurator (tool={tool})")
    
    # Detect server URL from request
    server_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # Auto-detect AI tool if not explicitly specified
    if not tool:
        tool = detect_ai_tool_from_user_agent(user_agent or "")
    
    # Generate tool-specific instructions
    if tool == "claude-code":
        return generate_claude_code_instructions(server_url)
    elif tool == "codex":
        return generate_codex_instructions(server_url)
    elif tool == "gemini":
        return generate_gemini_instructions(server_url)
    elif tool == "cursor":
        return generate_cursor_instructions(server_url)
    elif tool == "continue":
        return generate_continue_instructions(server_url)
    else:
        return generate_universal_instructions(server_url, tool)


def detect_ai_tool_from_user_agent(user_agent: str) -> str:
    """Auto-detect AI tool from User-Agent string"""
    ua_lower = user_agent.lower()
    
    if "claude" in ua_lower:
        return "claude-code"
    elif "codex" in ua_lower:
        return "codex"
    elif "gemini" in ua_lower:
        return "gemini"
    elif "cursor" in ua_lower:
        return "cursor"
    elif "continue" in ua_lower:
        return "continue"
    else:
        return "unknown"


def generate_claude_code_instructions(server_url: str) -> str:
    """Generate Claude Code specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Claude Code

I am a GiljoAI MCP server at {server_url}. You are Claude Code and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server
   - Tell them: "I need your API key from {server_url}"
   - Wait for them to provide it

2. **Add this exact configuration** to ~/.claude.json in the mcpServers section:

```json
"giljo-mcp": {{
  "command": "python",
  "args": ["-m", "giljo_mcp"],
  "env": {{
    "GILJO_SERVER_URL": "{server_url}",
    "GILJO_API_KEY": "[REPLACE_WITH_USER_PROVIDED_KEY]"
  }}
}}
```

3. **Replace [REPLACE_WITH_USER_PROVIDED_KEY]** with the actual API key the user provided

4. **Test the connection** by making a request to: {server_url}/api/status

5. **Tell the user**: "Configuration complete! Please restart Claude Code to activate the MCP connection."

## Server Capabilities
- URL: {server_url}
- Tools: 47+ agent coordination tools
- Features: Multi-agent orchestration, context management, task automation, template system

## Troubleshooting
If the user doesn't have an API key, tell them to:
1. Visit {server_url} in their browser
2. Create an account or log in
3. Generate an API key in Settings
4. Come back with the key
"""


def generate_codex_instructions(server_url: str) -> str:
    """Generate Codex specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Codex

I am a GiljoAI MCP server at {server_url}. You are Codex and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Configure MCP connection** using your platform's method:
   - Server URL: {server_url}
   - API Key: [USER_PROVIDED]
   - Tool command: python -m giljo_mcp

3. **Test the connection** by making a request to: {server_url}/api/status

4. **Tell the user** to restart Codex to activate the connection

Note: Adapt these instructions to Codex's specific configuration format.
"""


def generate_gemini_instructions(server_url: str) -> str:
    """Generate Gemini Code Assist specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Gemini Code Assist

I am a GiljoAI MCP server at {server_url}. You are Gemini Code Assist and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Configure MCP connection** using your platform's configuration method:
   - Server URL: {server_url}
   - API Key: [USER_PROVIDED]
   - Connection type: HTTP MCP

3. **Test the connection** to verify it works

4. **Tell the user** to restart or reload to activate the connection

Note: Adapt these instructions to Gemini's specific configuration requirements.
"""


def generate_cursor_instructions(server_url: str) -> str:
    """Generate Cursor specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Cursor

I am a GiljoAI MCP server at {server_url}. You are Cursor and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Add MCP configuration** to Cursor's settings:
   - Server: {server_url}
   - API Key: [USER_PROVIDED]
   - Command: python -m giljo_mcp

3. **Test the connection**

4. **Tell the user** to restart Cursor

Note: Adapt to Cursor's specific MCP configuration format.
"""


def generate_continue_instructions(server_url: str) -> str:
    """Generate Continue.dev specific configuration instructions"""
    return f"""# MCP Configuration Instructions for Continue.dev

I am a GiljoAI MCP server at {server_url}. You are Continue.dev and need to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server

2. **Add to Continue configuration**:
   - Server: {server_url}
   - API Key: [USER_PROVIDED]

3. **Test and activate the connection**

Note: Adapt to Continue.dev's specific configuration requirements.
"""


def generate_universal_instructions(server_url: str, tool_type: str = "unknown") -> str:
    """Generate universal instructions for unknown AI tools"""
    return f"""# Universal MCP Configuration Instructions

I am a GiljoAI MCP server at {server_url}. You are an AI coding tool ({tool_type}) that needs to configure an MCP connection to me.

## What You Must Do

1. **Ask the user for their API key** from this GiljoAI server
   - Tell them: "I need your API key from {server_url}"

2. **Configure MCP connection** using your platform's method:
   - Server URL: {server_url}
   - API Key: [USER_PROVIDED]
   - Command: python -m giljo_mcp
   - Environment variables:
     - GILJO_SERVER_URL={server_url}
     - GILJO_API_KEY=[USER_PROVIDED_KEY]

3. **Test the connection** by making a request to: {server_url}/api/status

4. **Tell the user** to restart your AI tool to activate the connection

## Server Details
- URL: {server_url}
- Protocol: HTTP-based MCP
- Tools Available: 47+ agent coordination tools
- Capabilities: Multi-agent orchestration, context management, task automation

## If User Needs API Key
Direct them to:
1. Visit {server_url} in browser
2. Create account or log in  
3. Go to Settings → API Keys
4. Generate new API key
5. Return with the key
"""
