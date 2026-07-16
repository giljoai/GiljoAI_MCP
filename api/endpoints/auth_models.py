# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Shared Pydantic models for authentication endpoints.

Contains request/response models used across multiple auth-related endpoints:
- Password reset via recovery PIN
- First login setup
- Password change flows

Extracted from auth.py and auth_pin_recovery.py to eliminate duplication (Handover 0703).
"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator

from giljo_mcp.utils.password_helper import BCRYPT_MAX_PASSWORD_BYTES


def validate_password_byte_length(v: str) -> str:
    """Reject passwords bcrypt cannot hash (BE-9176).

    bcrypt >= 4 raises ValueError on any secret over 72 UTF-8 BYTES, while
    schema length caps count CHARACTERS — so a multibyte password can fit the
    advertised max_length and still be unhashable, surfacing as a 500 at
    async_hash_password. Every password-set schema calls this (directly or via
    validate_password_strength) so the reject is a clean 422 at the validation
    boundary. The VERIFY side fails closed separately (SEC-9174 #6).
    """
    if len(v.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes when encoded as UTF-8")
    return v


# BE-9176: the reusable password-SET field type — min 8, advertised cap 72 chars,
# plus the UTF-8 byte check. Use it for every field that ends up bcrypt-hashed and
# has no strength validator of its own (strength-checked fields get the byte check
# via validate_password_strength above).
BoundedPassword = Annotated[
    str,
    StringConstraints(min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES),
    AfterValidator(validate_password_byte_length),
]


def validate_password_strength(v: str) -> str:
    """Validate password meets security requirements.

    BE-8000d dup-4: the single owning implementation of the password-strength
    policy, shared by every password-set flow (PIN reset, first-login setup,
    password change). All three field_validator methods below and in
    api/endpoints/auth/models.py delegate here.
    """
    validate_password_byte_length(v)
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


class PinPasswordResetRequest(BaseModel):
    """Request to reset password using recovery PIN"""

    username: str = Field(..., min_length=3, max_length=255)
    recovery_pin: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")
    new_password: str = Field(..., min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)
    confirm_password: str = Field(..., min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)

    @field_validator("new_password")
    @classmethod
    def _check_password_strength(cls, v):
        return validate_password_strength(v)


class PinPasswordResetResponse(BaseModel):
    """Response after successful password reset via PIN"""

    message: str


class CheckFirstLoginRequest(BaseModel):
    """Request to check if first login is required"""

    username: str = Field(..., min_length=3, max_length=255)


class CheckFirstLoginResponse(BaseModel):
    """Response indicating if first login actions required"""

    must_change_password: bool
    must_set_pin: bool


class CompleteFirstLoginRequest(BaseModel):
    """Request to complete first login setup"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)
    confirm_password: str = Field(..., min_length=8, max_length=BCRYPT_MAX_PASSWORD_BYTES)
    # PIN is CE-only (self-hosted has no email recovery). SaaS uses email-based
    # password reset and omit these fields.
    recovery_pin: str | None = Field(default=None, min_length=4, max_length=4, pattern="^[0-9]{4}$")
    confirm_pin: str | None = Field(default=None, min_length=4, max_length=4, pattern="^[0-9]{4}$")

    @field_validator("new_password")
    @classmethod
    def _check_password_strength(cls, v):
        return validate_password_strength(v)


class CompleteFirstLoginResponse(BaseModel):
    """Response after completing first login"""

    message: str
