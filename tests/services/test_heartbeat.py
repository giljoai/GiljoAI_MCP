# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for server-side heartbeat (WI-1 of CE-OPT-003).

Covers:
- Authenticated MCP call updates last_activity_at
- Debounce: rapid calls within 30s do NOT re-write
- Terminal-status agents are NOT updated
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.services.heartbeat import DEBOUNCE_SECONDS, touch_heartbeat


@pytest_asyncio.fixture
async def job_with_execution(db_session, test_tenant_key):
    """Create an AgentJob + AgentExecution pair in 'working' status."""
    job_id = str(uuid4())
    agent_id = str(uuid4())

    job = AgentJob(
        job_id=job_id,
        tenant_key=test_tenant_key,
        mission="heartbeat test",
        job_type="implementer",
        status="active",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_display_name="test-agent",
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.flush()
    return job_id, agent_id, test_tenant_key


@pytest.mark.asyncio
async def test_heartbeat_sets_last_activity(db_session, job_with_execution):
    """First MCP call should set last_activity_at from NULL."""
    job_id, _, tenant_key = job_with_execution

    await touch_heartbeat(db_session, job_id, tenant_key=tenant_key)

    result = await db_session.execute(select(AgentExecution.last_activity_at).where(AgentExecution.job_id == job_id))
    ts = result.scalar_one()
    assert ts is not None
    assert (datetime.now(timezone.utc) - ts).total_seconds() < 5


@pytest.mark.asyncio
async def test_heartbeat_debounce_skips_recent(db_session, job_with_execution):
    """If last_activity_at is recent (< 30s), heartbeat should NOT update."""
    job_id, _, tenant_key = job_with_execution

    recent_ts = datetime.now(timezone.utc) - timedelta(seconds=10)
    result = await db_session.execute(select(AgentExecution).where(AgentExecution.job_id == job_id))
    execution = result.scalar_one()
    execution.last_activity_at = recent_ts
    await db_session.flush()

    await touch_heartbeat(db_session, job_id, tenant_key=tenant_key)

    await db_session.refresh(execution)
    # Should still be the old timestamp (within 1s tolerance for rounding)
    assert abs((execution.last_activity_at - recent_ts).total_seconds()) < 2


@pytest.mark.asyncio
async def test_heartbeat_updates_stale(db_session, job_with_execution):
    """If last_activity_at is older than debounce window, heartbeat should update."""
    job_id, _, tenant_key = job_with_execution

    old_ts = datetime.now(timezone.utc) - timedelta(seconds=DEBOUNCE_SECONDS + 10)
    result = await db_session.execute(select(AgentExecution).where(AgentExecution.job_id == job_id))
    execution = result.scalar_one()
    execution.last_activity_at = old_ts
    await db_session.flush()

    await touch_heartbeat(db_session, job_id, tenant_key=tenant_key)

    await db_session.refresh(execution)
    assert (datetime.now(timezone.utc) - execution.last_activity_at).total_seconds() < 5


@pytest.mark.asyncio
async def test_heartbeat_skips_terminal_status(db_session, test_tenant_key):
    """Completed/closed agents should NOT get heartbeat updates."""
    job_id = str(uuid4())
    agent_id = str(uuid4())

    job = AgentJob(
        job_id=job_id,
        tenant_key=test_tenant_key,
        mission="terminal test",
        job_type="implementer",
        status="completed",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_display_name="test-agent",
        status="complete",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.flush()

    await touch_heartbeat(db_session, job_id, tenant_key=test_tenant_key)

    await db_session.refresh(execution)
    assert execution.last_activity_at is None


@pytest.mark.asyncio
async def test_heartbeat_nonexistent_job_is_noop(db_session, test_tenant_key):
    """touch_heartbeat with a job_id that has no matching execution should be a silent no-op."""
    fake_job_id = str(uuid4())
    # Should not raise -- fire-and-forget semantics
    await touch_heartbeat(db_session, fake_job_id, tenant_key=test_tenant_key)


@pytest.mark.asyncio
async def test_heartbeat_skips_closed_status(db_session, test_tenant_key):
    """Closed agents should NOT get heartbeat updates (covers 'closed' in terminal list)."""
    job_id = str(uuid4())
    agent_id = str(uuid4())

    job = AgentJob(
        job_id=job_id,
        tenant_key=test_tenant_key,
        mission="closed test",
        job_type="implementer",
        status="completed",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_display_name="test-agent",
        status="closed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.flush()

    await touch_heartbeat(db_session, job_id, tenant_key=test_tenant_key)

    await db_session.refresh(execution)
    assert execution.last_activity_at is None


@pytest.mark.asyncio
async def test_heartbeat_skips_decommissioned_status(db_session, test_tenant_key):
    """Decommissioned agents should NOT get heartbeat updates."""
    job_id = str(uuid4())
    agent_id = str(uuid4())

    job = AgentJob(
        job_id=job_id,
        tenant_key=test_tenant_key,
        mission="decom test",
        job_type="implementer",
        status="completed",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_display_name="test-agent",
        status="decommissioned",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.flush()

    await touch_heartbeat(db_session, job_id, tenant_key=test_tenant_key)

    await db_session.refresh(execution)
    assert execution.last_activity_at is None
