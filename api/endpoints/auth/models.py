# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Pydantic request/response models for the auth endpoints.

Extracted verbatim from api/endpoints/auth.py (BE-6042f route-group split).
Field names, validators, and defaults are unchanged — these models define the
public request/response contract of the /api/auth surface.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator

from api.endpoints.auth_models import validate_password_strength


class LoginRequest(BaseModel):
    """Login request with username/email identifier and password."""

    username: str = Field(..., min_length=3, max_length=255)
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
    first_name: str | None = None
    last_name: str | None = None
    # full_name retained for one release as a derived display field.
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
    setup_complete: bool = False  # Handover 0855a: Setup wizard completed
    setup_selected_tools: list[str] | None = None  # Handover 0855a: Selected AI coding agents
    setup_step_completed: int = 0  # Handover 0855a: Last completed wizard step
    learning_complete: bool = False  # How to Use guide completed


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
    expires_at: str | None


class APIKeyCreateRequest(BaseModel):
    """Request to create new API key"""

    name: str = Field(..., min_length=3, max_length=255, description="Description of API key purpose")
    permissions: list[str] = Field(default=["*"], description="List of permissions (default: all)")


class SetupStateUpdate(BaseModel):
    """Request model for updating setup wizard state (Handover 0855a)"""

    setup_selected_tools: list[str] | None = None
    setup_step_completed: int | None = Field(None, ge=0, le=4)
    setup_complete: bool | None = None
    learning_complete: bool | None = None


class APIKeyCreateResponse(BaseModel):
    """Response after creating API key (includes plaintext key ONCE)"""

    id: str
    name: str
    api_key: str  # Plaintext key - only shown once!
    key_prefix: str
    message: str
    expires_at: str | None


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
    first_name: str | None = Field(default=None, min_length=1, max_length=255, description="Given name")
    last_name: str | None = Field(default=None, max_length=255, description="Family name (optional)")
    role: str = Field(default="developer", description="User role: admin, developer, viewer")
    tenant_key: str | None = Field(
        default=None,
        description="Tenant key for multi-tenant isolation (resolved from config if not provided)",
    )
    workspace_name: str | None = Field(
        default="My Organization", description="Organization name for first admin user (Handover 0424h)"
    )
    recovery_pin: str | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        pattern="^[0-9]{4}$",
        description="4-digit recovery PIN for password reset",
    )
    confirm_pin: str | None = Field(
        default=None,
        min_length=4,
        max_length=4,
        pattern="^[0-9]{4}$",
        description="Confirm recovery PIN",
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
    first_name: str | None = None
    last_name: str | None = None
    # full_name retained for one release as a derived/legacy display field.
    full_name: str | None = None
    role: str
    tenant_key: str
    is_active: bool = True
    message: str


class PasswordChangeRequest(BaseModel):
    """Request to change password from default"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def _check_password_strength(cls, v):
        return validate_password_strength(v)


class PasswordChangeResponse(BaseModel):
    """Response after changing password"""

    success: bool
    message: str
    token: str
    user: dict
