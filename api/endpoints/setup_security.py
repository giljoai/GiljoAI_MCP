# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Simple fresh install detection endpoint (Handover 0034).

Clean architecture based on user count:
- 0 users = Fresh install (show create admin account)
- 1+ users = Normal operation (show login)

Replaces complex legacy admin/admin password change flow.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_db_session
from src.giljo_mcp.models import User


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_setup_security_status(db: AsyncSession = Depends(get_db_session)):
    """
    Simple fresh install detection based on user count (Handover 0034).

    Replaces complex legacy logic with single source of truth: user count.

    Fresh install = 0 users exist
    Normal operation = 1+ users exist

    Returns:
        - is_fresh_install: bool - True when total_users_count == 0
        - total_users_count: int - Total number of users in database
        - requires_admin_creation: bool - Same as is_fresh_install
    """
    try:
        # Single source of truth: user count
        total_users_stmt = select(func.count(User.id))
        total_users_result = await db.execute(total_users_stmt)
        total_users_count = total_users_result.scalar()

        # Simple fresh install detection
        is_fresh_install = total_users_count == 0

        # Security logging
        if is_fresh_install:
            logger.info("[SETUP] Fresh install detected - no users exist. Will show create admin account flow.")
        else:
            logger.debug(f"[SETUP] Normal operation - {total_users_count} user(s) exist. Will show login flow.")

        return {
            "is_fresh_install": is_fresh_install,
            "total_users_count": total_users_count,
            "requires_admin_creation": is_fresh_install,
        }

    except (ValueError, KeyError):
        logger.exception("Failed to get setup status")
        # Conservative fallback - assume fresh install (allows account creation)
        return {"is_fresh_install": True, "total_users_count": 0, "requires_admin_creation": True}
