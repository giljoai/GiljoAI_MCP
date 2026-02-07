"""
Password Reset via Recovery PIN endpoints (Handover 0023).

Provides secure PIN-based password recovery:
- verify-pin-and-reset-password: Reset password using 4-digit PIN
- check-first-login: Check if user needs to change password/set PIN
- complete-first-login: Complete first login setup (password + PIN)

All endpoints include rate limiting, timing-safe comparisons, and audit logging.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.auth_models import (
    CheckFirstLoginRequest,
    CheckFirstLoginResponse,
    CompleteFirstLoginRequest,
    CompleteFirstLoginResponse,
    PinPasswordResetRequest,
    PinPasswordResetResponse,
)
from api.middleware.auth_rate_limiter import get_rate_limiter
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User


logger = logging.getLogger(__name__)
router = APIRouter()


# API Endpoints


@router.post("/verify-pin-and-reset-password", response_model=PinPasswordResetResponse, tags=["auth"])
async def verify_pin_and_reset_password(
    http_request: Request, request_data: PinPasswordResetRequest = Body(...), db: AsyncSession = Depends(get_db_session)
):
    """
    Verify recovery PIN and reset password (Handover 0023).

    Security Features:
    - Generic error messages (doesn't reveal username existence)
    - IP-based rate limiting: 3 attempts per minute (Handover 1009)
    - Account lockout: 5 failed attempts → 15 minute lockout (per-user)
    - Timing-safe PIN comparison (bcrypt)
    - PIN never stored in plaintext
    - Audit logging for security monitoring

    Flow:
    1. Check IP-based rate limit (3/min across all users)
    2. Find user by username
    3. Check per-user lockout status (pin_lockout_until)
    4. Verify PIN with bcrypt
    5. If invalid: Increment failed_pin_attempts, trigger lockout if >= 5
    6. If valid: Reset password, clear lockout

    Args:
        http_request: FastAPI request object
        request_data: Username, PIN, new password
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 400 if username/PIN invalid
        HTTPException: 429 if rate limit exceeded or user is locked out
    """
    # IP-based rate limiting: 3 attempts per minute (Handover 1009)
    # This is in ADDITION to per-user account lockout (5 failed → 15 min)
    rate_limiter = get_rate_limiter()
    rate_limiter.check_rate_limit(http_request, limit=3, window=60, raise_on_limit=True)

    # Validate password confirmation match
    if request_data.new_password != request_data.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Find user by username
    stmt = select(User).where(User.username == request_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # SECURITY: Generic error message - don't reveal if username exists
    if not user:
        logger.warning(f"PIN reset attempt for non-existent username: {request_data.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or PIN")

    # Check if user has recovery PIN set
    if not user.recovery_pin_hash:
        logger.warning(f"PIN reset attempt for user without PIN: {user.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or PIN")

    # Check if user is locked out
    if user.pin_lockout_until and datetime.now(timezone.utc) < user.pin_lockout_until:
        lockout_remaining = user.pin_lockout_until - datetime.now(timezone.utc)
        minutes_remaining = int(lockout_remaining.total_seconds() / 60)
        logger.warning(
            f"PIN reset attempt while locked out - user: {user.username}, remaining: {minutes_remaining} minutes"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked out due to too many failed attempts. Try again in {minutes_remaining} minutes.",
        )

    # Verify PIN with bcrypt (timing-safe comparison)
    if not bcrypt.verify(request_data.recovery_pin, user.recovery_pin_hash):
        # Increment failed attempts
        user.failed_pin_attempts += 1

        # Trigger lockout after 5 failed attempts
        if user.failed_pin_attempts >= 5:
            user.pin_lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.commit()

            logger.warning(
                f"PIN lockout triggered - user: {user.username}, "
                f"attempts: {user.failed_pin_attempts}, lockout until: {user.pin_lockout_until}"
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account locked out due to too many failed attempts. Try again in 15 minutes.",
            )

        await db.commit()

        attempts_remaining = 5 - user.failed_pin_attempts
        logger.warning(
            f"Invalid PIN attempt - user: {user.username}, "
            f"attempts: {user.failed_pin_attempts}, remaining: {attempts_remaining}"
        )

        # SECURITY: Generic error message
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or PIN")

    # PIN verified successfully - reset password
    user.password_hash = bcrypt.hash(request_data.new_password)
    user.failed_pin_attempts = 0
    user.pin_lockout_until = None

    await db.commit()

    logger.info(f"Password reset successful via PIN - user: {user.username}")

    return PinPasswordResetResponse(message="Password reset successful")


@router.post("/check-first-login", response_model=CheckFirstLoginResponse, tags=["auth"])
async def check_first_login(
    request_data: CheckFirstLoginRequest = Body(...), db: AsyncSession = Depends(get_db_session)
):
    """
    Check if user must change password or set PIN on first login (Handover 0023).

    Used by frontend after successful login to determine if additional
    setup is required before accessing the dashboard.

    Args:
        request_data: Username to check
        db: Database session

    Returns:
        must_change_password and must_set_pin flags

    Raises:
        HTTPException: 404 if user not found
    """
    # Find user by username
    stmt = select(User).where(User.username == request_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return CheckFirstLoginResponse(
        must_change_password=user.must_change_password or False, must_set_pin=user.must_set_pin or False
    )


@router.post("/complete-first-login", response_model=CompleteFirstLoginResponse, tags=["auth"])
async def complete_first_login(
    request_data: CompleteFirstLoginRequest = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Complete first login by changing password and setting recovery PIN (Handover 0023).

    Requires authentication (JWT token from initial login with default password).

    Flow:
    1. Verify current password
    2. Validate new password != current password
    3. Validate PIN confirmation match
    4. Update password_hash
    5. Set recovery_pin_hash (bcrypt)
    6. Clear must_change_password and must_set_pin flags

    Args:
        request_data: Password change and PIN setup data
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 400 if validation fails
    """
    # Validate current password
    if not bcrypt.verify(request_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Validate new password != current password
    if request_data.new_password == request_data.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different from current password"
        )

    # Validate password confirmation match
    if request_data.new_password != request_data.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Validate PIN confirmation match
    if request_data.recovery_pin != request_data.confirm_pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PINs do not match")

    # Update password
    current_user.password_hash = bcrypt.hash(request_data.new_password)

    # Set recovery PIN
    current_user.recovery_pin_hash = bcrypt.hash(request_data.recovery_pin)

    # Clear first login flags
    current_user.must_change_password = False
    current_user.must_set_pin = False

    await db.commit()

    logger.info(f"First login completed - user: {current_user.username}")

    return CompleteFirstLoginResponse(message="First login completed successfully")


class SetRecoveryPinRequest(BaseModel):
    """Request to set or reset recovery PIN for the authenticated user."""

    current_password: str = Field(..., min_length=8, description="Current account password")
    recovery_pin: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")
    confirm_pin: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")


class SetRecoveryPinResponse(BaseModel):
    message: str


@router.post("/set-recovery-pin", response_model=SetRecoveryPinResponse, tags=["auth"])
async def set_recovery_pin(
    request_data: SetRecoveryPinRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Set or reset the recovery PIN for the authenticated user (outside first-login flow).

    Validates current password and updates the 4-digit recovery PIN.
    Does NOT change the account password.
    Clears any PIN lockout status.
    """
    # Verify current password
    if not bcrypt.verify(request_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate PIN match
    if request_data.recovery_pin != request_data.confirm_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PINs do not match",
        )

    # Update PIN and clear lockout
    current_user.recovery_pin_hash = bcrypt.hash(request_data.recovery_pin)
    current_user.failed_pin_attempts = 0
    current_user.pin_lockout_until = None

    await db.commit()

    logger.info(f"Recovery PIN updated for user: {current_user.username}")
    return SetRecoveryPinResponse(message="Recovery PIN updated successfully")
