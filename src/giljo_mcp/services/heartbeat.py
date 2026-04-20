# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Server-side heartbeat: update last_activity_at on authenticated MCP calls.

Debounces writes to avoid excessive DB updates on rapid-fire tool calls.
Only updates if the current last_activity_at is older than DEBOUNCE_SECONDS.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.repositories.agent_operations_repository import AgentOperationsRepository


logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 30


async def touch_heartbeat(session: AsyncSession, job_id: str, tenant_key: str) -> None:
    """Update last_activity_at for the agent execution tied to job_id.

    Debounce: skips the write if last_activity_at is less than
    DEBOUNCE_SECONDS old, avoiding a DB write on every rapid-fire call.

    Uses flush() to stage the change; the caller's session context manager
    handles the final commit. This matches the pattern used by auto_clear_silent.

    This is fire-and-forget; callers should catch exceptions externally.

    Args:
        session: Async database session.
        job_id: The job_id from the MCP tool call.
        tenant_key: Tenant isolation key (required, no default).
    """
    repo = AgentOperationsRepository()
    updated = await repo.touch_heartbeat(session, job_id, tenant_key, DEBOUNCE_SECONDS)
    if updated:
        logger.debug("Heartbeat updated for job_id=%s", job_id)
