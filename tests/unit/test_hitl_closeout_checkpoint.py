# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for HITL Closeout Checkpoint feature.

Covers:
- closeout_checklist added to complete_job() for orchestrator jobs
- closeout_mode config option in general settings
- Orchestrator protocol text references closeout checklist
- write_360_memory() callable after complete_job()
- _resolve_git_commits() helper extraction
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from giljo_mcp.models import AgentExecution, AgentJob
from giljo_mcp.services.job_completion_service import JobCompletionService


@pytest.fixture
def completion_service(db_session, test_tenant_key):
    """Create a JobCompletionService with a test session."""
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


@pytest_asyncio.fixture
async def orchestrator_job(db_session, test_tenant_key, test_project_id):
    """Create an orchestrator job + execution for testing."""
    job_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=str(test_project_id),
        mission="Test orchestrator mission",
        job_type="orchestrator",
        status="active",
        tenant_key=test_tenant_key,
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        id=str(uuid.uuid4()),
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_name="orchestrator",
        agent_display_name="orchestrator",
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.commit()
    return job


@pytest_asyncio.fixture
async def implementer_job(db_session, test_tenant_key, test_project_id):
    """Create an implementer (non-orchestrator) job + execution for testing."""
    job_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=str(test_project_id),
        mission="Test implementer mission",
        job_type="implementer",
        status="active",
        tenant_key=test_tenant_key,
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        id=str(uuid.uuid4()),
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_name="implementer",
        agent_display_name="implementer-backend",
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.commit()
    return job


# ---- Task 1: closeout_checklist in complete_job() response ----


@pytest.mark.asyncio
async def test_complete_job_orchestrator_includes_closeout_checklist(
    completion_service, orchestrator_job, test_tenant_key
):
    """Orchestrator complete_job() returns closeout_checklist in response."""
    result = await completion_service.complete_job(
        job_id=orchestrator_job.job_id,
        result={"summary": "Project completed successfully"},
        tenant_key=test_tenant_key,
    )
    # HITL mode (default) returns "blocked_hitl"; autonomous returns "success"
    assert result.status in ("success", "blocked_hitl")
    assert hasattr(result, "closeout_checklist")
    assert result.closeout_checklist is not None

    checklist = result.closeout_checklist
    assert "action_required_tags" in checklist
    assert "follow_up_items" in checklist
    assert "user_approval_required" in checklist
    assert "instruction" in checklist
    assert isinstance(checklist["user_approval_required"], bool)


@pytest.mark.asyncio
async def test_complete_job_orchestrator_checklist_defaults_to_hitl(
    completion_service, orchestrator_job, test_tenant_key
):
    """HITL mode with no deferred findings skips approval (smart HITL)."""
    result = await completion_service.complete_job(
        job_id=orchestrator_job.job_id,
        result={"summary": "Done"},
        tenant_key=test_tenant_key,
    )
    # No deferred_findings or action_required_tags → approval not required
    assert result.closeout_checklist["user_approval_required"] is False


@pytest.mark.asyncio
async def test_complete_job_orchestrator_hitl_with_deferred_findings(
    completion_service, orchestrator_job, test_tenant_key
):
    """HITL mode WITH deferred findings requires approval."""
    result = await completion_service.complete_job(
        job_id=orchestrator_job.job_id,
        result={"summary": "Done", "deferred_findings": ["Reviewer found unused import"]},
        tenant_key=test_tenant_key,
    )
    assert result.closeout_checklist["user_approval_required"] is True


@pytest.mark.asyncio
async def test_complete_job_orchestrator_hitl_with_action_required_tags(
    completion_service, orchestrator_job, test_tenant_key
):
    """HITL mode WITH action_required_tags requires approval."""
    result = await completion_service.complete_job(
        job_id=orchestrator_job.job_id,
        result={"summary": "Done", "action_required_tags": ["action_required:fix auth"]},
        tenant_key=test_tenant_key,
    )
    assert result.closeout_checklist["user_approval_required"] is True


@pytest.mark.asyncio
async def test_complete_job_non_orchestrator_no_checklist(completion_service, implementer_job, test_tenant_key):
    """Non-orchestrator complete_job() does NOT include closeout_checklist."""
    result = await completion_service.complete_job(
        job_id=implementer_job.job_id,
        result={"summary": "Implementation done"},
        tenant_key=test_tenant_key,
    )
    assert result.status == "success"
    assert result.closeout_checklist is None


# ---- Task 2: closeout_mode config ----


@pytest.mark.asyncio
async def test_closeout_mode_autonomous_sets_user_approval_false(db_session, orchestrator_job, test_tenant_key):
    """When closeout_mode='autonomous', user_approval_required is False."""
    from giljo_mcp.models.settings import Settings

    # Insert general settings with closeout_mode = autonomous
    settings = Settings(
        tenant_key=test_tenant_key,
        category="general",
        settings_data={"closeout_mode": "autonomous"},
    )
    db_session.add(settings)
    await db_session.commit()

    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    svc = JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    result = await svc.complete_job(
        job_id=orchestrator_job.job_id,
        result={"summary": "Done"},
        tenant_key=test_tenant_key,
    )
    assert result.closeout_checklist["user_approval_required"] is False


# ---- Task 4: Protocol text includes closeout checklist reference ----


def test_orchestrator_protocol_references_closeout_checklist():
    """Orchestrator protocol text references closeout_checklist."""
    from giljo_mcp.services.protocol_sections.agent_lifecycle import (
        _build_orchestrator_protocol_body,
    )

    body = _build_orchestrator_protocol_body(
        job_id="test-job",
        tenant_key="test-tenant",
        executor_id="test-executor",
        wake_pattern="test-wake",
    )
    assert "closeout_checklist" in body
    assert "user_approval_required" in body
    assert "action_required" in body


# ---- Task 5: write_360_memory works after complete_job ----


@pytest_asyncio.fixture
async def linked_project(db_session, test_tenant_key, test_product):
    """Create a project linked to a product (required by write_360_memory)."""
    import random

    from giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Test Linked Project",
        description="Project linked to product for closeout testing",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest.mark.asyncio
async def test_write_360_memory_callable_after_complete_job(db_session, test_tenant_key, test_product, linked_project):
    """Verify write_360_memory() succeeds after complete_job() for an orchestrator.

    The sequence is: complete_job() -> write_360_memory() -> close_project_and_update_memory().
    All three must succeed in order.
    """
    project_id = str(linked_project.id)

    # Create orchestrator job + execution
    job_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=project_id,
        mission="Test orchestrator mission",
        job_type="orchestrator",
        status="active",
        tenant_key=test_tenant_key,
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        id=str(uuid.uuid4()),
        job_id=job_id,
        tenant_key=test_tenant_key,
        agent_name="orchestrator",
        agent_display_name="orchestrator",
        status="working",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.commit()

    # Step 1: complete_job()
    db_manager = MagicMock()
    db_manager.get_session_async = MagicMock(return_value=AsyncMock())
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    svc = JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    complete_result = await svc.complete_job(
        job_id=job_id,
        result={"summary": "All work done"},
        tenant_key=test_tenant_key,
    )
    # HITL mode (default) returns "blocked_hitl"; autonomous returns "success"
    assert complete_result.status in ("success", "blocked_hitl")

    # Step 2: write_360_memory() after job is complete
    from giljo_mcp.tools.write_360_memory import write_360_memory

    mock_db_manager = MagicMock()

    # Patch tuning staleness check (unrelated side effect, needs full service stack)
    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        memory_result = await write_360_memory(
            project_id=project_id,
            tenant_key=test_tenant_key,
            summary="Sprint completed with HITL closeout",
            key_outcomes=["Implemented closeout checklist"],
            decisions_made=["Used HITL mode by default"],
            entry_type="handover_closeout",
            author_job_id=job_id,
            git_commits=[],
            tags=["action_required:review closeout patterns"],
            db_manager=mock_db_manager,
            session=db_session,
        )
    assert memory_result.get("entry_id") is not None
    assert memory_result.get("sequence_number") is not None

    # Simulate HITL user approval: advance the orchestrator execution to 'complete'
    # so close_project_and_update_memory(force=True) doesn't hit the self-decommission guard.
    # In production, this transition is triggered by the user clicking "Approve" in the UI.
    from sqlalchemy import select as sa_select

    from giljo_mcp.models.agent_identity import AgentExecution as AgentExecutionModel

    exec_stmt = sa_select(AgentExecutionModel).where(
        AgentExecutionModel.job_id == job_id, AgentExecutionModel.tenant_key == test_tenant_key
    )
    exec_res = await db_session.execute(exec_stmt)
    exec_obj = exec_res.scalar_one_or_none()
    if exec_obj and exec_obj.status in ("blocked", "working"):
        exec_obj.status = "complete"
        exec_obj.progress = 100
        await db_session.commit()

    # Step 3: close_project_and_update_memory() after write_360_memory
    from giljo_mcp.tools.project_closeout import close_project_and_update_memory

    closeout_result = await close_project_and_update_memory(
        project_id=project_id,
        summary="Final project closeout",
        key_outcomes=["All tasks complete"],
        decisions_made=["HITL mode used"],
        tenant_key=test_tenant_key,
        db_manager=mock_db_manager,
        session=db_session,
        force=True,
        git_commits=[{"sha": "abc123", "message": "test commit", "author": "test"}],
    )
    assert closeout_result.get("entry_id") is not None
    assert closeout_result.get("message") is not None


# ---- Bonus: _resolve_git_commits helper ----


def test_resolve_git_commits_helper_exists():
    """Verify _resolve_git_commits is importable as a standalone helper."""
    from giljo_mcp.tools.project_closeout import _resolve_git_commits

    assert callable(_resolve_git_commits)
