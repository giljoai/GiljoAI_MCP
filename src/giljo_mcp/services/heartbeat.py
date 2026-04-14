# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Server-side heartbeat: update last_activity_at on authenticated MCP calls.

Debounces writes to avoid excessive DB updates on rapid-fire tool calls.
Only updates if the current last_activity_at is older than DEBOUNCE_SECONDS.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution


logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 30


async def touch_heartbeat(session: AsyncSession, job_id: str, tenant_key: str = "") -> None:
    """Update last_activity_at for the agent execution tied to job_id.

    Debounce: skips the write if last_activity_at is less than
    DEBOUNCE_SECONDS old, avoiding a DB write on every rapid-fire call.

    Uses flush() to stage the change; the caller's session context manager
    handles the final commit. This matches the pattern used by auto_clear_silent.

    This is fire-and-forget; callers should catch exceptions externally.

    Args:
        session: Async database session.
        job_id: The job_id from the MCP tool call.
        tenant_key: Tenant isolation key.
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=DEBOUNCE_SECONDS)

    # Single UPDATE with WHERE clause for debounce -- no SELECT needed.
    # Only writes if last_activity_at is NULL or older than threshold.
    conditions = [
        AgentExecution.job_id == job_id,
        AgentExecution.status.notin_(["complete", "closed", "decommissioned"]),
        ((AgentExecution.last_activity_at.is_(None)) | (AgentExecution.last_activity_at < threshold)),
    ]
    if tenant_key:
        conditions.append(AgentExecution.tenant_key == tenant_key)

    result = await session.execute(update(AgentExecution).where(and_(*conditions)).values(last_activity_at=now))
    if result.rowcount:
        await session.flush()
        logger.debug("Heartbeat updated for job_id=%s", job_id)
