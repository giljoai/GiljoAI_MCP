"""
Shared Pydantic models for authentication endpoints.

Contains request/response models used across multiple auth-related endpoints:
- Password reset via recovery PIN
- First login setup
- Password change flows

Extracted from auth.py and auth_pin_recovery.py to eliminate duplication (Handover 0703).
"""

from pydantic import BaseModel, Field, field_validator


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
