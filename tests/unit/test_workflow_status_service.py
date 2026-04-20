# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for WorkflowStatusService (Sprint 002e extraction).

Expanded from 1-function smoke test to meaningful coverage:
- Project not found (error path)
- Empty project (no executions)
- Mixed execution statuses and stage derivation
- exclude_job_id filtering
- caller_note text variants
- Progress percent calculation
"""

from unittest.mock import MagicMock

import pytest

from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.services.workflow_status_service import WorkflowStatusService


@pytest.fixture
def wf_service(db_session, test_tenant_key):
    """Create a WorkflowStatusService with a test session."""
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


@pytest.mark.asyncio
async def test_get_workflow_status_raises_for_missing_project(wf_service, test_tenant_key):
    """get_workflow_status raises ResourceNotFoundError for non-existent project."""
    with pytest.raises(ResourceNotFoundError):
        await wf_service.get_workflow_status("00000000-0000-0000-0000-000000000000", test_tenant_key)


@pytest.mark.asyncio
async def test_get_workflow_status_empty_project(db_session, db_manager, test_tenant_key):
    """A project with zero executions returns 'Not started' stage and 0 progress."""
    import uuid

    from giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Empty WF Project",
        description="No agents spawned",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        series_number=99001,
    )
    db_session.add(project)
    await db_session.commit()

    service = WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=MagicMock(),
        test_session=db_session,
    )
    result = await service.get_workflow_status(project.id, test_tenant_key)

    assert result.total_agents == 0
    assert result.active_agents == 0
    assert result.completed_agents == 0
    assert result.pending_agents == 0
    assert result.progress_percent == 0.0
    assert result.current_stage == "Not started"
    assert result.agents == []
    assert "included" in result.caller_note


@pytest.mark.asyncio
async def test_get_workflow_status_with_working_agents(db_session, db_manager, test_tenant_key):
    """Working agents produce 'In Progress' stage and 0% progress."""
    import uuid

    from giljo_mcp.models import AgentExecution, AgentJob, Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Working WF",
        description="Agents working",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        series_number=99002,
    )
    db_session.add(project)
    await db_session.flush()

    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=project.id,
        tenant_key=test_tenant_key,
        job_type="implementer",
        mission="Test mission",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        job_id=job_id,
        agent_id=agent_id,
        tenant_key=test_tenant_key,
        status="working",
        agent_name="test-impl",
        agent_display_name="implementer",
    )
    db_session.add(execution)
    await db_session.commit()

    service = WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=MagicMock(),
        test_session=db_session,
    )
    result = await service.get_workflow_status(project.id, test_tenant_key)

    assert result.total_agents == 1
    assert result.active_agents == 1
    assert result.completed_agents == 0
    assert result.progress_percent == 0.0
    assert result.current_stage == "In Progress"


@pytest.mark.asyncio
async def test_get_workflow_status_all_complete(db_session, db_manager, test_tenant_key):
    """All agents complete produces 'Completed' stage and 100% progress."""
    import uuid

    from giljo_mcp.models import AgentExecution, AgentJob, Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Done WF",
        description="All done",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        series_number=99003,
    )
    db_session.add(project)
    await db_session.flush()

    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=project.id,
        tenant_key=test_tenant_key,
        job_type="tester",
        mission="Test mission",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        job_id=job_id,
        agent_id=agent_id,
        tenant_key=test_tenant_key,
        status="complete",
        agent_name="test-tester",
        agent_display_name="tester",
    )
    db_session.add(execution)
    await db_session.commit()

    service = WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=MagicMock(),
        test_session=db_session,
    )
    result = await service.get_workflow_status(project.id, test_tenant_key)

    assert result.total_agents == 1
    assert result.completed_agents == 1
    assert result.progress_percent == 100.0
    assert result.current_stage == "Completed"


@pytest.mark.asyncio
async def test_get_workflow_status_blocked_stage(db_session, db_manager, test_tenant_key):
    """A blocked agent produces an 'In Progress (N blocked)' stage."""
    import uuid

    from giljo_mcp.models import AgentExecution, AgentJob, Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Blocked WF",
        description="Has blocked agent",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        series_number=99004,
    )
    db_session.add(project)
    await db_session.flush()

    job_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        project_id=project.id,
        tenant_key=test_tenant_key,
        job_type="reviewer",
        mission="Test mission",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        job_id=job_id,
        agent_id=agent_id,
        tenant_key=test_tenant_key,
        status="blocked",
        agent_name="test-reviewer",
        agent_display_name="reviewer",
    )
    db_session.add(execution)
    await db_session.commit()

    service = WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=MagicMock(),
        test_session=db_session,
    )
    result = await service.get_workflow_status(project.id, test_tenant_key)

    assert result.blocked_agents == 1
    assert "blocked" in result.current_stage.lower()


@pytest.mark.asyncio
async def test_get_workflow_status_exclude_job_id(db_session, db_manager, test_tenant_key):
    """exclude_job_id omits the specified job and changes caller_note."""
    import uuid

    from giljo_mcp.models import AgentExecution, AgentJob, Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Exclude WF",
        description="Exclude test",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        series_number=99005,
    )
    db_session.add(project)
    await db_session.flush()

    job_id_a = str(uuid.uuid4())
    job_id_b = str(uuid.uuid4())

    for jid, status in [(job_id_a, "working"), (job_id_b, "complete")]:
        job = AgentJob(
            job_id=jid,
            project_id=project.id,
            tenant_key=test_tenant_key,
            job_type="impl",
            mission="Test mission",
        )
        db_session.add(job)
        await db_session.flush()
        execution = AgentExecution(
            job_id=jid,
            agent_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            status=status,
            agent_name="agent",
            agent_display_name="agent",
        )
        db_session.add(execution)

    await db_session.commit()

    service = WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=MagicMock(),
        test_session=db_session,
    )

    result_with_exclude = await service.get_workflow_status(project.id, test_tenant_key, exclude_job_id=job_id_a)
    assert result_with_exclude.total_agents == 1
    assert "excluded" in result_with_exclude.caller_note


@pytest.mark.asyncio
async def test_get_workflow_status_tenant_isolation(db_session, db_manager, test_tenant_key):
    """A project created under one tenant_key is not visible to another."""
    import uuid

    from giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="Isolated WF",
        description="Belongs to specific tenant",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        series_number=99006,
    )
    db_session.add(project)
    await db_session.commit()

    other_tenant = "tk_otherTenantValue12345678901234"

    service = WorkflowStatusService(
        db_manager=db_manager,
        tenant_manager=MagicMock(),
        test_session=db_session,
    )

    with pytest.raises(ResourceNotFoundError):
        await service.get_workflow_status(project.id, other_tenant)
