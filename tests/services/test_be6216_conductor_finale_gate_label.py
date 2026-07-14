# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6216 (1) — the conductor finale gate must NOT silently drop a sub-orch escalation.

BE-6213 P0 broadened the conductor's completion-gate self-exclusion to BOTH its
``agent_id`` and its label identities {agent_display_name, agent_name}. But the
conductor's ``agent_display_name`` is the GENERIC, non-unique "orchestrator"
(conductor_job_minter.py), and every sub-orchestrator posts its Hub escalations to the
conductor's NULL-project thread under ``from_agent="orchestrator"`` too. So a genuine
sub-orch escalation authored under "orchestrator" was matched by the conductor's
self-exclusion and SILENTLY DROPPED at the finale gate -- neither blocking the
conductor's complete_job nor surfacing as work it owed. The escalation sink swallowed
its own escalations.

BE-6216 narrows the conductor self-exclusion to its UNIQUE label only
(agent_name, e.g. "Chain Conductor"), so:
  - a DISTINCT agent posting from_agent="orchestrator" an ACTION-REQUIRED escalation
    MUST still BLOCK (BE-9012b/D7 keys the gate on requires_action; the retired
    acknowledge_messages_on_complete flag no longer drains it); and
  - the conductor's OWN self-post under its unique label still does NOT block
    (self-exclusion of the unique label preserved; BE-6213 green path).

RED before the narrowing: the "orchestrator" post is excluded, complete_job succeeds,
the escalation is lost. GREEN after: it blocks. Failing layer = the completion gate
in JobCompletionService._validate_completion_requirements.

Edition Scope: CE.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.tasks import Message, MessageRecipient
from giljo_mcp.services.job_completion_service import JobCompletionService


@pytest.fixture
def completion_service(db_session: AsyncSession, test_tenant_key: str) -> JobCompletionService:
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return JobCompletionService(
        db_manager=MagicMock(),
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


async def _seed_conductor(
    db_session: AsyncSession,
    tenant_key: str,
    *,
    display_name: str = "orchestrator",
    agent_name: str = "Chain Conductor",
) -> tuple[AgentJob, AgentExecution]:
    """Seed a project-less chain conductor (project_id None + chain_conductor metadata).

    Mirrors conductor_job_minter.mint_conductor_job: the GENERIC display name
    "orchestrator" (shared by every sub-orch) and the UNIQUE label "Chain Conductor".
    """
    job_id = str(uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=None,
        job_type="orchestrator",
        mission="drive the chain",
        status="active",
        job_metadata={"chain_conductor": True, "run_id": str(uuid4())},
    )
    db_session.add(job)
    execution = AgentExecution(
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name=display_name,
        agent_name=agent_name,
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)
    return job, execution


async def _add_pending_message(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: str | None,
    from_agent_id: str,
    to_agent_id: str,
) -> None:
    msg = Message(
        tenant_key=tenant_key,
        project_id=project_id,
        from_agent_id=from_agent_id,
        content="BLOCKER: chain-level decision needed",
        status="pending",
        # BE-9012b (D7): a genuine escalation is action-required; the reframed gate
        # keys on requires_action. A self-authored one is still excluded (row 14).
        requires_action=True,
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(msg)
    await db_session.flush()
    db_session.add(MessageRecipient(message_id=msg.id, agent_id=to_agent_id, tenant_key=tenant_key))
    await db_session.commit()


@pytest.mark.asyncio
async def test_distinct_suborch_post_under_orchestrator_still_blocks_conductor(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
):
    """The core regression: a DISTINCT sub-orchestrator escalating under the generic
    from_agent="orchestrator" to the conductor's NULL-project Hub thread MUST still arm
    the conductor's finale gate. (RED before BE-6216: the generic display-name exclusion
    dropped it and the conductor self-completed, losing the escalation.)"""
    job, execution = await _seed_conductor(db_session, test_tenant_key)
    # A real sub-orch posts its blocker under the SHARED generic label, NOT the
    # conductor's unique "Chain Conductor" label.
    await _add_pending_message(db_session, test_tenant_key, None, "orchestrator", execution.agent_id)

    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "chain done"},
            tenant_key=test_tenant_key,
        )
    assert exc_info.value.error_code == "COMPLETION_BLOCKED"
    assert (exc_info.value.context or {}).get("unread_messages") == 1


@pytest.mark.asyncio
async def test_distinct_suborch_post_still_blocks_even_with_retired_ack_flag(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
):
    """BE-9012b (D7, §6 row 3): the sub-orch "orchestrator" escalation is real
    cross-agent action-required work. The acknowledge_messages_on_complete escape
    hatch is RETIRED (accepted-and-ignored), so passing it no longer lets the
    conductor drain-and-skip a genuine escalation — it STILL blocks. The conductor
    must actually resolve the escalation, not acknowledge past it."""
    job, execution = await _seed_conductor(db_session, test_tenant_key)
    await _add_pending_message(db_session, test_tenant_key, None, "orchestrator", execution.agent_id)

    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "chain done"},
            tenant_key=test_tenant_key,
            acknowledge_messages_on_complete=True,  # retired: accepted but no longer drains
        )
    assert exc_info.value.error_code == "COMPLETION_BLOCKED"
    assert (exc_info.value.context or {}).get("unread_messages") == 1


@pytest.mark.asyncio
async def test_conductor_self_post_under_unique_label_does_not_block(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
):
    """The narrowing preserves the BE-6213 green path: the conductor's OWN Hub post,
    authored under its UNIQUE label "Chain Conductor" (per CH_CHAIN_DRIVE prose) and
    fanned back to itself, is still self-excluded and must NOT block its finale."""
    job, execution = await _seed_conductor(db_session, test_tenant_key)
    await _add_pending_message(db_session, test_tenant_key, None, execution.agent_name, execution.agent_id)

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "chain done"},
        tenant_key=test_tenant_key,
    )
    assert result.status == "success"
