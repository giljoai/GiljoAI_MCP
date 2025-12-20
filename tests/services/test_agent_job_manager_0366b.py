"""
Tests for AgentJobManager with dual-model CRUD (Handover 0366b).

These tests are written FIRST (TDD RED phase) to define expected behavior:
1. Spawning an agent creates BOTH job and execution
2. Updating execution status does NOT change job status
3. Completing a job decommissions all its executions
4. Query operations return appropriate model (job or execution)

Test Coverage:
- spawn_agent() creates job + execution
- update_agent_status() updates execution (not job)
- complete_job() marks job complete and decommissions executions
- Query methods return correct models
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.agent_job_manager import AgentJobManager


@pytest_asyncio.fixture
async def test_project_0366b_ajm(db_session):
    """Create test project for 0366b agent job manager tests."""
    project = Project(
        id="project-123",
        tenant_key="tenant-abc",
        name="Test Project 0366b Agent Job Manager",
        description="Test project for agent job manager",
        mission="Build authentication system",
        status="active"
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest.mark.asyncio
async def test_spawn_agent_creates_job_and_execution(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Spawning an agent creates BOTH job and execution.

    This is the fundamental coordinated CRUD operation:
    - AgentJob: Work order (mission, scope)
    - AgentExecution: First executor (instance_number=1)
    """
    # Act: Spawn new agent
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    result = await manager.spawn_agent(
        project_id="project-123",
        agent_type="analyzer",
        mission="Analyze codebase for security vulnerabilities",
        tenant_key="tenant-abc"
    )

    # Assert: Both job and execution created
    assert result["success"] is True
    assert "job_id" in result  # Work order ID
    assert "agent_id" in result  # Executor ID
    assert result["job_id"] != result["agent_id"]  # Different UUIDs

    # Validate database - job exists
    job = await db_session.execute(
        select(AgentJob).where(AgentJob.job_id == result["job_id"])
    )
    job = job.scalar_one()

    assert job.mission == "Analyze codebase for security vulnerabilities"
    assert job.job_type == "analyzer"
    assert job.status == "active"

    # Validate database - execution exists
    execution = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == result["agent_id"])
    )
    execution = execution.scalar_one()

    assert execution.job_id == job.job_id  # Linked to job
    assert execution.agent_type == "analyzer"
    assert execution.instance_number == 1  # First instance
    assert execution.status == "waiting"


@pytest.mark.asyncio
async def test_update_execution_status_not_job_status(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Updating execution status does NOT change job status.

    Scenario: Execution completes, job remains active (awaiting next execution or completion).
    """
    # Setup: Create job + execution
    job = AgentJob(
        job_id="job-status-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"  # Job is active
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )
    db_session.add(execution)
    await db_session.commit()

    # Act: Update execution status to "complete"
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    await manager.update_agent_status(
        agent_id="agent-001",
        status="complete",
        tenant_key="tenant-abc"
    )

    # Assert: Execution complete, job STILL active
    job_result = await db_session.execute(
        select(AgentJob).where(AgentJob.job_id == "job-status-test")
    )
    job = job_result.scalar_one()

    execution_result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == "agent-001")
    )
    execution = execution_result.scalar_one()

    assert execution.status == "complete"
    assert job.status == "active"  # Job persists


@pytest.mark.asyncio
async def test_complete_job_decommissions_all_executions(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Completing a job decommissions all its executions.

    Scenario: Job has 3 executions (succession chain).
    complete_job() marks job complete AND decommissions all 3 executions.
    """
    # Setup: Create job with 3 executions (succession chain)
    job = AgentJob(
        job_id="job-complete-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete"
    )
    exec2 = AgentExecution(
        agent_id="agent-002",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=2,
        status="complete"
    )
    exec3 = AgentExecution(
        agent_id="agent-003",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=3,
        status="working"  # Active
    )
    db_session.add_all([exec1, exec2, exec3])
    await db_session.commit()

    # Act: Complete the job
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    await manager.complete_job(
        job_id="job-complete-test",
        tenant_key="tenant-abc"
    )

    # Assert: Job completed, all executions decommissioned
    job_result = await db_session.execute(
        select(AgentJob).where(AgentJob.job_id == "job-complete-test")
    )
    job = job_result.scalar_one()

    executions_result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.job_id == job.job_id)
    )
    executions = executions_result.scalars().all()

    assert job.status == "completed"
    assert job.completed_at is not None

    for execution in executions:
        assert execution.status == "decommissioned"
        assert execution.decommissioned_at is not None


@pytest.mark.asyncio
async def test_cancel_job_decommissions_all_executions(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Cancelling a job decommissions all its executions.

    Similar to complete_job(), but sets status to "cancelled".
    """
    # Setup: Create job with 2 executions
    job = AgentJob(
        job_id="job-cancel-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )
    exec2 = AgentExecution(
        agent_id="agent-002",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=2,
        status="waiting"
    )
    db_session.add_all([exec1, exec2])
    await db_session.commit()

    # Act: Cancel the job
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    await manager.cancel_job(
        job_id="job-cancel-test",
        tenant_key="tenant-abc"
    )

    # Assert: Job cancelled, all executions decommissioned
    job_result = await db_session.execute(
        select(AgentJob).where(AgentJob.job_id == "job-cancel-test")
    )
    job = job_result.scalar_one()

    executions_result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.job_id == job.job_id)
    )
    executions = executions_result.scalars().all()

    assert job.status == "cancelled"
    for execution in executions:
        assert execution.status == "decommissioned"


@pytest.mark.asyncio
async def test_get_active_executions_for_project(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Query active executions for a project (not jobs).

    Scenario: Project has 3 jobs, each with 2 executions (succession).
    get_active_executions() returns 3 active executions (not 6 total, not 3 jobs).
    """
    # Setup: Create project with multiple jobs and executions
    job1 = AgentJob(
        job_id="job-1",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Task 1",
        job_type="analyzer",
        status="active"
    )
    exec1_old = AgentExecution(
        agent_id="exec1-old",
        job_id=job1.job_id,
        tenant_key="tenant-abc",
        agent_type="analyzer",
        instance_number=1,
        status="complete"
    )
    exec1_new = AgentExecution(
        agent_id="exec1-new",
        job_id=job1.job_id,
        tenant_key="tenant-abc",
        agent_type="analyzer",
        instance_number=2,
        status="working"  # Active
    )

    job2 = AgentJob(
        job_id="job-2",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Task 2",
        job_type="implementer",
        status="active"
    )
    exec2_active = AgentExecution(
        agent_id="exec2-active",
        job_id=job2.job_id,
        tenant_key="tenant-abc",
        agent_type="implementer",
        instance_number=1,
        status="working"  # Active
    )

    job3 = AgentJob(
        job_id="job-3",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Task 3",
        job_type="tester",
        status="active"
    )
    exec3_active = AgentExecution(
        agent_id="exec3-active",
        job_id=job3.job_id,
        tenant_key="tenant-abc",
        agent_type="tester",
        instance_number=1,
        status="working"  # Active
    )

    db_session.add_all([job1, job2, job3, exec1_old, exec1_new, exec2_active, exec3_active])
    await db_session.commit()

    # Act: Get active executions for project
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    active_executions = await manager.get_active_executions_for_project(
        project_id="project-123",
        tenant_key="tenant-abc"
    )

    # Assert: Returns 3 active executions (not all 4, not 3 jobs)
    assert len(active_executions) == 3
    agent_ids = {exec.agent_id for exec in active_executions}
    assert agent_ids == {"exec1-new", "exec2-active", "exec3-active"}


@pytest.mark.asyncio
async def test_get_execution_by_agent_id(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Query execution by agent_id (primary lookup method).
    """
    # Setup: Create execution
    job = AgentJob(
        job_id="job-lookup",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id="agent-lookup",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )
    db_session.add(execution)
    await db_session.commit()

    # Act: Get execution by agent_id
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    result = await manager.get_execution_by_agent_id(
        agent_id="agent-lookup",
        tenant_key="tenant-abc"
    )

    # Assert: Returns correct execution
    assert result is not None
    assert result.agent_id == "agent-lookup"
    assert result.job_id == job.job_id


@pytest.mark.asyncio
async def test_get_job_by_job_id(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Query job by job_id (work order lookup).
    """
    # Setup: Create job
    job = AgentJob(
        job_id="job-lookup",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)
    await db_session.commit()

    # Act: Get job by job_id
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    result = await manager.get_job_by_job_id(
        job_id="job-lookup",
        tenant_key="tenant-abc"
    )

    # Assert: Returns correct job
    assert result is not None
    assert result.job_id == "job-lookup"
    assert result.mission == "Build auth"


@pytest.mark.asyncio
async def test_get_all_executions_for_job(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Query all executions for a job (succession history).

    Scenario: Job has 3 executions (succession chain).
    get_all_executions_for_job() returns all 3 (not just active one).
    """
    # Setup: Create job with 3 executions
    job = AgentJob(
        job_id="job-history",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete"
    )
    exec2 = AgentExecution(
        agent_id="agent-002",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=2,
        status="complete"
    )
    exec3 = AgentExecution(
        agent_id="agent-003",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=3,
        status="working"
    )
    db_session.add_all([exec1, exec2, exec3])
    await db_session.commit()

    # Act: Get all executions for job
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    executions = await manager.get_all_executions_for_job(
        job_id="job-history",
        tenant_key="tenant-abc"
    )

    # Assert: Returns all 3 executions (ordered by instance_number)
    assert len(executions) == 3
    assert [e.instance_number for e in executions] == [1, 2, 3]
    assert [e.status for e in executions] == ["complete", "complete", "working"]


@pytest.mark.asyncio
async def test_update_agent_progress(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    Update execution progress (execution-specific, not job-level).
    """
    # Setup: Create execution
    job = AgentJob(
        job_id="job-progress",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id="agent-progress",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working",
        progress=0
    )
    db_session.add(execution)
    await db_session.commit()

    # Act: Update progress
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)
    await manager.update_agent_progress(
        agent_id="agent-progress",
        progress=75,
        current_task="Implementing OAuth2 flow",
        tenant_key="tenant-abc"
    )

    # Assert: Execution progress updated
    execution_result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == "agent-progress")
    )
    execution = execution_result.scalar_one()

    assert execution.progress == 75
    assert execution.current_task == "Implementing OAuth2 flow"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_crud(db_session, db_manager, tenant_manager, test_project_0366b_ajm):
    """
    CRUD operations respect multi-tenant isolation.

    Scenario: Two tenants with similar jobs.
    Queries for tenant-a should NOT return tenant-b data.
    """
    # Create projects for two tenants
    project_a = Project(
        id="project-a",
        tenant_key="tenant-a",
        name="Project A",
        description="Tenant A project",
        mission="Task A",
        status="active"
    )
    project_b = Project(
        id="project-b",
        tenant_key="tenant-b",
        name="Project B",
        description="Tenant B project",
        mission="Task B",
        status="active"
    )
    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Setup: Create jobs for two tenants
    job_a = AgentJob(
        job_id="job-tenant-a",
        tenant_key="tenant-a",
        project_id="project-a",
        mission="Task A",
        job_type="orchestrator",
        status="active"
    )
    exec_a = AgentExecution(
        agent_id="exec-a",
        job_id=job_a.job_id,
        tenant_key="tenant-a",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )

    job_b = AgentJob(
        job_id="job-tenant-b",
        tenant_key="tenant-b",
        project_id="project-b",
        mission="Task B",
        job_type="orchestrator",
        status="active"
    )
    exec_b = AgentExecution(
        agent_id="exec-b",
        job_id=job_b.job_id,
        tenant_key="tenant-b",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )

    db_session.add_all([job_a, job_b, exec_a, exec_b])
    await db_session.commit()

    # Act: Query tenant-a data
    manager = AgentJobManager(db_manager, tenant_manager, test_session=db_session)

    job_result = await manager.get_job_by_job_id(
        job_id="job-tenant-a",
        tenant_key="tenant-a"
    )
    exec_result = await manager.get_execution_by_agent_id(
        agent_id="exec-a",
        tenant_key="tenant-a"
    )

    # Assert: Only tenant-a data returned
    assert job_result.job_id == "job-tenant-a"
    assert exec_result.agent_id == "exec-a"

    # Verify tenant-b data NOT accessible from tenant-a context
    job_b_attempt = await manager.get_job_by_job_id(
        job_id="job-tenant-b",
        tenant_key="tenant-a"  # Wrong tenant
    )
    assert job_b_attempt is None  # Should NOT find tenant-b job
