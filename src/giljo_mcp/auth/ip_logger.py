# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
API Key IP address logging.

Extracted from api/endpoints/mcp_session.MCPSessionManager.log_ip (Sprint 003a)
to eliminate the backward import from src/giljo_mcp/auth/dependencies.py.

This is a standalone async function with no api/ dependencies.
"""

import logging

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


async def log_api_key_ip(db: AsyncSession, api_key_id: str, ip_address: str) -> None:
    """Log IP address for API key usage tracking (passive, non-blocking).

    Uses PostgreSQL upsert (INSERT ... ON CONFLICT) to either create a new
    entry or increment the request_count and update last_seen_at for an
    existing api_key + ip_address pair.

    This function is designed to never raise exceptions. All errors are
    caught and logged as warnings so that IP logging never blocks or
    slows down the authentication flow.

    Args:
        db: Async database session
        api_key_id: The ID of the API key that was used.
        ip_address: The client IP address (IPv4/IPv6 or 'unknown').
    """
    try:
        from uuid import uuid4

        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from giljo_mcp.models.auth import ApiKeyIpLog

        stmt = (
            pg_insert(ApiKeyIpLog)
            .values(
                id=str(uuid4()),
                api_key_id=api_key_id,
                ip_address=ip_address,
            )
            .on_conflict_do_update(
                constraint="uq_api_key_ip",
                set_={
                    "last_seen_at": func.now(),
                    "request_count": ApiKeyIpLog.request_count + 1,
                },
            )
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as e:  # noqa: BLE001 - API boundary: non-fatal IP logging
        logger.warning("Failed to log IP for API key: %s", e)
