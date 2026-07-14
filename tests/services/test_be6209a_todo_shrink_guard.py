# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6209a: report_progress guard against a silent todo-list wipe.

Field report friction #4: ``todo_items`` REPLACES the entire persisted TODO list
on every call, so a PARTIAL list silently drops the missing rows. The pre-existing
completed-regression guard only catches the case where the COMPLETED count
shrinks — it misses an agent that re-sends only its still-pending items (or only
its finished items) while preserving the completed count, which quietly wipes the
rest.

These tests pin the new guard at the write layer (ProgressService._process_todo_items,
exercised through the OrchestrationService.report_progress facade, the same path the
existing 0827d tests use):
  - a SHORTER todo_items list is rejected (no silent drop) unless replace=True;
  - a full-list call that does NOT shrink still works (backward compatible);
  - replace=True allows a genuine destructive shrink.

Parallel-safe: uses the shared transactional db_session fixture, no module-level
mutable state, no test-ordering dependencies. CE / tenant-scoped.
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.tenant import TenantManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def shrink_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name=f"BE-6209a Product {uuid4().hex[:6]}",
        description="Product for BE-6209a shrink-guard tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def shrink_project(
    db_session: AsyncSession,
    test_tenant_key: str,
    shrink_product: Product,
) -> Project:
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=shrink_product.id,
        name="BE-6209a Shrink Guard Project",
        description="Test project for BE-6209a",
        mission="Guard report_progress against silent todo wipe",
        status="active",
        created_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def agent_with_mixed_todos(
    db_session: AsyncSession,
    test_tenant_key: str,
    shrink_project: Project,
) -> AgentJob:
    """A working agent with 5 todos: 2 completed + 3 pending.

    The 2-completed / 3-pending split is the crux: re-sending only the 2 completed
    keeps the completed count identical (so the old completed-regression guard does
    NOT fire) while dropping the 3 pending — exactly the silent wipe BE-6209a fixes.
    """
    job_id = str(uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=test_tenant_key,
        project_id=shrink_project.id,
        job_type="implementer",
        mission="Mixed-todo agent",
        status="active",
    )
    db_session.add(job)

    now = datetime.now(UTC)
    agent = AgentExecution(
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_display_name="Mixed-Todo-Agent",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=now - timedelta(minutes=2),
        completed_at=None,
        accumulated_duration_seconds=0.0,
        reactivation_count=0,
    )
    db_session.add(agent)

    seeded = [
        ("Step 1: Setup", "completed"),
        ("Step 2: Implement", "completed"),
        ("Step 3: Test", "pending"),
        ("Step 4: Refactor", "pending"),
        ("Step 5: Document", "pending"),
    ]
    for seq, (content, status) in enumerate(seeded):
        db_session.add(
            AgentTodoItem(
                job_id=job_id,
                tenant_key=test_tenant_key,
                content=content,
                status=status,
                sequence=seq,
            )
        )

    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def orchestration_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    test_tenant_key: str,
) -> OrchestrationService:
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    tenant_manager = MagicMock(spec=TenantManager)
    tenant_manager.get_current_tenant.return_value = test_tenant_key

    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    websocket_manager = MagicMock()
    websocket_manager.broadcast_to_tenant = AsyncMock()

    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
        websocket_manager=websocket_manager,
    )


async def _todos(db_session: AsyncSession, job_id: str, tenant_key: str) -> list[AgentTodoItem]:
    result = await db_session.execute(
        select(AgentTodoItem)
        .where(AgentTodoItem.job_id == job_id)
        .where(AgentTodoItem.tenant_key == tenant_key)
        .order_by(AgentTodoItem.sequence)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_partial_todo_items_rejected_without_replace(
    db_session: AsyncSession,
    orchestration_service: OrchestrationService,
    agent_with_mixed_todos: AgentJob,
    test_tenant_key: str,
):
    """A shorter todo_items list must be REJECTED (not silently wipe the rest).

    Re-sends only the 2 completed items. Completed count is preserved (2 == 2),
    so the old completed-regression guard does NOT catch this — the new shrink
    guard must. Without it, the 3 pending items would be silently deleted.
    """
    job = agent_with_mixed_todos

    with pytest.raises(ValidationError, match="SHRINK"):
        await orchestration_service.report_progress(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            todo_items=[
                {"content": "Step 1: Setup", "status": "completed"},
                {"content": "Step 2: Implement", "status": "completed"},
            ],
        )

    # The persisted list is untouched — all 5 items survive.
    items = await _todos(db_session, job.job_id, test_tenant_key)
    assert len(items) == 5
    assert sum(1 for i in items if i.status == "pending") == 3


@pytest.mark.asyncio
async def test_full_list_status_update_still_works(
    db_session: AsyncSession,
    orchestration_service: OrchestrationService,
    agent_with_mixed_todos: AgentJob,
    test_tenant_key: str,
):
    """Backward compat: a full (non-shrinking) list still updates normally.

    Sends all 5 items, advancing one pending item to in_progress. Same length,
    completed count preserved -> no guard fires, write succeeds.
    """
    job = agent_with_mixed_todos

    result = await orchestration_service.report_progress(
        job_id=job.job_id,
        tenant_key=test_tenant_key,
        todo_items=[
            {"content": "Step 1: Setup", "status": "completed"},
            {"content": "Step 2: Implement", "status": "completed"},
            {"content": "Step 3: Test", "status": "in_progress"},
            {"content": "Step 4: Refactor", "status": "pending"},
            {"content": "Step 5: Document", "status": "pending"},
        ],
    )

    assert result.status == "success"
    items = await _todos(db_session, job.job_id, test_tenant_key)
    assert len(items) == 5
    assert items[2].status == "in_progress"


@pytest.mark.asyncio
async def test_partial_todo_items_allowed_with_replace(
    db_session: AsyncSession,
    orchestration_service: OrchestrationService,
    agent_with_mixed_todos: AgentJob,
    test_tenant_key: str,
):
    """replace=True opts into a genuine destructive shrink."""
    job = agent_with_mixed_todos

    result = await orchestration_service.report_progress(
        job_id=job.job_id,
        tenant_key=test_tenant_key,
        replace=True,
        todo_items=[
            {"content": "Step 1: Setup", "status": "completed"},
            {"content": "Step 2: Implement", "status": "completed"},
        ],
    )

    assert result.status == "success"
    items = await _todos(db_session, job.job_id, test_tenant_key)
    assert len(items) == 2
    assert all(i.status == "completed" for i in items)
