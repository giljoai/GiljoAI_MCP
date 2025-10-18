"""
Security-focused setup status endpoint for fresh install attack prevention.

Minimal implementation that enhances v3.0 login flow with security detection
without restoring the deprecated setup wizard.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.models import SetupState, User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_setup_security_status(db: AsyncSession = Depends(get_db_session)):
    """
    Get setup status with enhanced security fields for fresh install attack prevention.
    
    This endpoint enhances the v3.0 unified login approach with security detection
    to distinguish between legitimate fresh installs and potential attack scenarios.
    
    Returns:
        - database_initialized: bool - Whether database is set up
        - default_password_active: bool - Whether admin still has default password  
        - admin_users_exist: bool - Whether any admin users exist in database
        - total_users_count: int - Total number of users
        - is_true_fresh_install: bool - True only for genuine fresh installs
    """
    try:
        # Get basic setup state (existing v3.0 logic)
        stmt = select(SetupState).where(SetupState.tenant_key == 'default')
        result = await db.execute(stmt)
        setup_state = result.scalar_one_or_none()

        # Enhanced security: Check if any admin users exist
        admin_count_stmt = select(func.count(User.id)).where(User.role == 'admin')
        admin_count_result = await db.execute(admin_count_stmt)
        admin_users_exist = admin_count_result.scalar() > 0

        # Get total user count for security analysis
        total_users_stmt = select(func.count(User.id))
        total_users_result = await db.execute(total_users_stmt)
        total_users_count = total_users_result.scalar()

        if setup_state:
            database_initialized = setup_state.database_initialized
            default_password_active = setup_state.default_password_active
        else:
            # No setup state found - assume fresh install
            database_initialized = False
            default_password_active = True

        # Security decision: Compute true fresh install
        is_true_fresh_install = (
            not database_initialized and 
            not admin_users_exist and 
            total_users_count == 0
        )

        # Security logging for audit trail
        if admin_users_exist and default_password_active:
            logger.warning(
                f"[SECURITY] Potential attack detected - admin users exist ({admin_users_exist}) "
                f"but default password active ({default_password_active}). "
                f"Total users: {total_users_count}, DB initialized: {database_initialized}"
            )
        
        if is_true_fresh_install:
            logger.info(
                f"[SECURITY] True fresh install confirmed - no admin users, "
                f"no database initialization, zero user count"
            )

        return {
            "database_initialized": database_initialized,
            "default_password_active": default_password_active,
            "admin_users_exist": admin_users_exist,
            "total_users_count": total_users_count,
            "is_true_fresh_install": is_true_fresh_install
        }

    except Exception as e:
        logger.error(f"Failed to get setup security status: {e}")
        # Conservative fallback - assume fresh install (secure default)
        return {
            "database_initialized": False,
            "default_password_active": True,
            "admin_users_exist": False,
            "total_users_count": 0,
            "is_true_fresh_install": True
        }