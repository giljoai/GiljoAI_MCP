# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
`acknowledge_messages_on_complete` is RETIRED (BE-9012b, D7, §6 row 3).

Originally an escape hatch that DRAINED unread messages before the completion
gate, for agents stuck in the reactivation-on-stale-message loop. D7 dissolves
that loop at the source: the gate now blocks ONLY on genuine ``requires_action``,
non-``auto_generated`` posts, so an informational message never blocks and there
is nothing to drain past. The flag is now accepted-and-ignored (kept on the
signature so in-flight callers do not 422); passing it neither drains messages nor
lets an agent skip a genuine action-required post.

These tests now assert that retirement:
- With the flag, a genuine action-required post STILL blocks (not drained).
- An informational post does not block (and is not drained — it stays pending).
- The TODOs gate is unaffected; cross-tenant messages are never touched.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.models.tasks import Message, MessageAcknowledgment, MessageRecipient
from giljo_mcp.services.job_completion_service import JobCompletionService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Messages Ack Test Product",
        description="Product for messages-ack tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def active_project(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> Project:
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Messages Ack Test Project",
        description="Test project for messages ack",
        mission="Test message acknowledgement",
        status="active",
        created_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def completion_service(db_session: AsyncSession, test_tenant_key: str) -> JobCompletionService:
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


async def _seed_orchestrator(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: str,
    todos: list[dict] | None = None,
) -> tuple[AgentJob, AgentExecution]:
    """Seed an orchestrator job + working execution + optional todos."""
    job_id = str(uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type="orchestrator",
        mission="Coordinate messages-ack tests",
        status="active",
    )
    db_session.add(job)

    now = datetime.now(UTC)
    execution = AgentExecution(
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=now - timedelta(minutes=5),
    )
    db_session.add(execution)

    if todos:
        for seq, item in enumerate(todos):
            db_session.add(
                AgentTodoItem(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    content=item["content"],
                    status=item["status"],
                    sequence=seq,
                )
            )

    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)
    return job, execution


async def _seed_unread_message(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: str,
    recipient_agent_id: str,
    *,
    requires_action: bool = False,
    content: str = "Hello, please read me",
) -> Message:
    """Insert a pending Message with one MessageRecipient row."""
    msg = Message(
        tenant_key=tenant_key,
        project_id=project_id,
        from_agent_id=str(uuid4()),
        content=content,
        status="pending",
        requires_action=requires_action,
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(msg)
    await db_session.flush()
    db_session.add(
        MessageRecipient(
            message_id=msg.id,
            agent_id=recipient_agent_id,
            tenant_key=tenant_key,
        )
    )
    await db_session.commit()
    await db_session.refresh(msg)
    return msg


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_acknowledge_messages_flag_is_retired_no_drain(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    active_project: Project,
):
    """BE-9012b (D7): the retired flag no longer drains. A genuine action-required
    post STILL blocks even with the flag; the informational post neither blocks nor
    is drained. Neither message is marked acknowledged and no junction rows appear."""
    job, execution = await _seed_orchestrator(
        db_session,
        test_tenant_key,
        active_project.id,
    )
    msg_info = await _seed_unread_message(
        db_session,
        test_tenant_key,
        active_project.id,
        execution.agent_id,
        requires_action=False,
        content="info-only progress update",
    )
    msg_action = await _seed_unread_message(
        db_session,
        test_tenant_key,
        active_project.id,
        execution.agent_id,
        requires_action=True,
        content="please review",
    )

    # The action-required post still blocks; the retired flag does not drain it.
    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "should still block"},
            tenant_key=test_tenant_key,
            acknowledge_messages_on_complete=True,
        )
    assert exc_info.value.error_code == "COMPLETION_BLOCKED"
    # Only the action-required post gates (informational is not "unread work").
    assert (exc_info.value.context or {}).get("unread_messages") == 1

    # Nothing was drained: both messages stay pending, no acknowledgment junction rows.
    refreshed = (
        (
            await db_session.execute(
                select(Message).where(
                    Message.id.in_([msg_info.id, msg_action.id]),
                    Message.tenant_key == test_tenant_key,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(refreshed) == 2
    assert all(m.status == "pending" for m in refreshed)

    ack_rows = (
        (
            await db_session.execute(
                select(MessageAcknowledgment).where(
                    MessageAcknowledgment.tenant_key == test_tenant_key,
                    MessageAcknowledgment.agent_id == execution.agent_id,
                    MessageAcknowledgment.message_id.in_([msg_info.id, msg_action.id]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(ack_rows) == 0


@pytest.mark.asyncio
async def test_complete_job_without_flag_still_blocks_unread(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    active_project: Project,
):
    """Regression guard: omitting the flag preserves existing behavior — unread blocks completion."""
    job, execution = await _seed_orchestrator(
        db_session,
        test_tenant_key,
        active_project.id,
    )
    await _seed_unread_message(
        db_session,
        test_tenant_key,
        active_project.id,
        execution.agent_id,
        requires_action=True,
        content="please review",
    )

    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "should fail"},
            tenant_key=test_tenant_key,
        )
    err = exc_info.value
    assert err.error_code == "COMPLETION_BLOCKED"
    ctx = err.context or {}
    assert ctx.get("unread_messages") == 1


@pytest.mark.asyncio
async def test_acknowledge_messages_does_not_bypass_todos_gate(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    active_project: Project,
):
    """ack_messages=True with incomplete non-closeout TODO -> still blocks via TODO gate."""
    job, execution = await _seed_orchestrator(
        db_session,
        test_tenant_key,
        active_project.id,
        todos=[
            {"content": "Refactor login flow", "status": "in_progress"},
        ],
    )
    await _seed_unread_message(
        db_session,
        test_tenant_key,
        active_project.id,
        execution.agent_id,
        requires_action=False,
    )

    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "blocked by todos"},
            tenant_key=test_tenant_key,
            acknowledge_messages_on_complete=True,
        )
    err = exc_info.value
    assert err.error_code == "COMPLETION_BLOCKED"
    ctx = err.context or {}
    assert ctx.get("incomplete_todos") == 1
    # The informational message never gated (D7 keys on requires_action), so it is
    # not counted in the block — the TODO is the sole blocker.
    assert ctx.get("unread_messages") == 0


@pytest.mark.asyncio
async def test_acknowledge_messages_does_not_bypass_closeout_todos_gate_combined(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    active_project: Project,
):
    """Both flags can be passed; behavior is conjunctive (each gate uses its own flag)."""
    job, execution = await _seed_orchestrator(
        db_session,
        test_tenant_key,
        active_project.id,
        todos=[
            {"content": "Closeout: complete orchestrator job", "status": "in_progress"},
        ],
    )
    await _seed_unread_message(
        db_session,
        test_tenant_key,
        active_project.id,
        execution.agent_id,
        requires_action=False,
    )

    # Both flags True: closeout TODO + unread message both drain -> success.
    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "both drained"},
        tenant_key=test_tenant_key,
        acknowledge_closeout_todo=True,
        acknowledge_messages_on_complete=True,
    )
    assert result.status == "success"


@pytest.mark.asyncio
async def test_retired_flag_leaves_messages_untouched_across_tenants(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    other_tenant_key: str,
    active_project: Project,
):
    """BE-9012b (D7): the retired flag drains nothing. An informational own-tenant
    message does not block completion (D7) and is left PENDING (not drained); a
    cross-tenant message is likewise never touched (tenant isolation preserved)."""
    job, execution = await _seed_orchestrator(
        db_session,
        test_tenant_key,
        active_project.id,
    )
    # Own-tenant message (will be drained).
    own_msg = await _seed_unread_message(
        db_session,
        test_tenant_key,
        active_project.id,
        execution.agent_id,
        requires_action=False,
    )

    # Other tenant: full row chain (Product -> Project -> Message) so the FK to
    # projects holds. The message's recipient agent_id collides with our own
    # agent_id intentionally — this is the guard for tenant_key filtering.
    other_product = Product(
        id=str(uuid4()),
        tenant_key=other_tenant_key,
        name="Other Tenant Product",
        description="Cross-tenant guard product",
        product_memory={},
    )
    db_session.add(other_product)
    await db_session.flush()
    other_project = Project(
        id=str(uuid4()),
        tenant_key=other_tenant_key,
        product_id=other_product.id,
        name="Other Tenant Project",
        description="Cross-tenant guard project",
        mission="cross-tenant",
        status="active",
        created_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(other_project)
    await db_session.flush()
    other_msg = Message(
        tenant_key=other_tenant_key,
        project_id=other_project.id,
        from_agent_id=str(uuid4()),
        content="cross-tenant — must NOT be drained",
        status="pending",
        requires_action=False,
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(other_msg)
    await db_session.flush()
    db_session.add(
        MessageRecipient(
            message_id=other_msg.id,
            agent_id=execution.agent_id,
            tenant_key=other_tenant_key,
        )
    )
    await db_session.commit()

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "tenant-isolated drain"},
        tenant_key=test_tenant_key,
        acknowledge_messages_on_complete=True,
    )
    assert result.status == "success"

    with tenant_session_context(db_session, test_tenant_key):
        refreshed_own = (
            await db_session.execute(
                select(Message).where(Message.id == own_msg.id, Message.tenant_key == test_tenant_key)
            )
        ).scalar_one()
    with tenant_session_context(db_session, other_tenant_key):
        refreshed_other = (
            await db_session.execute(
                select(Message).where(Message.id == other_msg.id, Message.tenant_key == other_tenant_key)
            )
        ).scalar_one()

    assert refreshed_own.status == "pending", "Retired flag must NOT drain — informational own message stays pending"
    assert refreshed_other.status == "pending", "Cross-tenant message must remain pending — tenant isolation regression"
