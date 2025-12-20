"""
Tests for OrchestrationService with new agent identity model (Handover 0366b).

These tests are written FIRST (TDD RED phase) to define expected behavior:
1. Succession creates new AgentExecution on SAME job (not new job)
2. Mission is stored ONCE in AgentJob (no duplication)
3. Handover summary stored in execution (execution-specific state)
4. Job status vs execution status are independent

Test Coverage:
- Succession creates new execution, preserves job_id
- Mission stored in job, accessed via relationship
- Handover summary generation and storage
- Job status remains active when execution completes
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager


@pytest_asyncio.fixture
async def test_project_0366b(db_session):
    """Create test project for 0366b tests."""
    project = Project(
        id="project-123",
        tenant_key="tenant-abc",
        name="Test Project 0366b",
        description="Test project for agent identity refactor",
        mission="Build authentication system",  # Required field
        status="active"
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest.mark.asyncio
async def test_succession_creates_new_execution_same_job(db_session, test_project_0366b):
    """
    Succession creates new execution on SAME job (not new job).

    This is the CORE semantic change:
    - OLD: Succession created new MCPAgentJob (new job_id)
    - NEW: Succession creates new AgentExecution (SAME job_id, new agent_id)
    """
    # Setup: Create job and first execution (project created by fixture)
    job = AgentJob(
        job_id="job-persistent",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build authentication system",
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
        status="complete",
        context_used=135000,  # 90% of 150K budget - triggers succession
        context_budget=150000
    )
    db_session.add(exec1)
    await db_session.commit()

    # Act: Trigger succession
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    exec2 = await manager.create_successor(exec1, "context_limit")

    # Assert: New execution, SAME job
    assert exec2.agent_id != exec1.agent_id  # Different executor
    assert exec2.job_id == exec1.job_id  # SAME work order
    assert exec2.instance_number == 2  # Incremented
    assert exec2.spawned_by == exec1.agent_id  # Lineage preserved

    # Verify succession chain is bidirectional
    await db_session.refresh(exec1)
    assert exec1.succeeded_by == exec2.agent_id  # Succession chain


@pytest.mark.asyncio
async def test_succession_preserves_mission(db_session, test_project_0366b):
    """
    Mission is NOT duplicated - stored in job, shared by executions.

    This validates the data normalization:
    - Mission stored ONCE in AgentJob
    - All executions access via relationship (no duplication)
    """
    # Setup
    job = AgentJob(
        job_id="job-mission-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Original mission: Build auth system with OAuth2 support",
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
    db_session.add(exec1)
    await db_session.commit()

    # Act: Create successor
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    exec2 = await manager.create_successor(exec1, "manual")

    # Refresh to load relationships
    await db_session.refresh(exec2, ["job"])

    # Assert: Mission stored ONCE in job (not duplicated in executions)
    assert job.mission == "Original mission: Build auth system with OAuth2 support"
    assert exec2.job.mission == job.mission  # Accessed via relationship

    # Verify executions do NOT have mission field (data normalization)
    assert not hasattr(exec2, 'mission')  # AgentExecution has no mission field


@pytest.mark.asyncio
async def test_handover_summary_stored_in_execution(db_session, test_project_0366b):
    """
    Handover summary stored in execution, NOT job.

    Rationale: Handover summary is execution-specific state
    (what THIS executor did), not job-level metadata.
    """
    # Setup
    job = AgentJob(
        job_id="job-handover-test",
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
        status="working",
        messages=[
            {"id": "msg-1", "type": "status", "content": "75% complete"},
            {"id": "msg-2", "type": "blocker", "content": "Database schema issue"}
        ]
    )
    db_session.add(exec1)
    await db_session.commit()

    # Act: Generate handover summary
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    summary = manager.generate_handover_summary(exec1)

    # Assert: Summary contains execution-specific state
    assert "project_status" in summary
    assert summary["project_status"] == "75% complete"
    assert len(summary.get("unresolved_blockers", [])) > 0

    # Summary should be stored in execution, not job
    exec1.handover_summary = summary
    await db_session.commit()

    await db_session.refresh(exec1)
    assert exec1.handover_summary is not None
    assert exec1.handover_summary["project_status"] == "75% complete"


@pytest.mark.asyncio
async def test_job_status_independent_from_execution_status(db_session, test_project_0366b):
    """
    Job status and execution status are independent.

    Scenario: Execution completes, but job remains active (awaiting next execution).
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

    # Act: Mark execution complete (simulate agent finishing work)
    execution.status = "complete"
    execution.completed_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Assert: Execution complete, job STILL active (awaiting next execution or completion)
    await db_session.refresh(job)
    await db_session.refresh(execution)

    assert execution.status == "complete"
    assert job.status == "active"  # Job persists until explicitly completed


@pytest.mark.asyncio
async def test_succession_chain_preserves_lineage(db_session, test_project_0366b):
    """
    Succession chain preserves full lineage across multiple handovers.

    Scenario: exec1 → exec2 → exec3 (all on SAME job)
    """
    # Setup: Create job
    job = AgentJob(
        job_id="job-lineage",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Long-running project",
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
    db_session.add(exec1)
    await db_session.commit()

    # Act: Create succession chain
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")

    exec2 = await manager.create_successor(exec1, "context_limit")
    exec2.status = "complete"  # Simulate completion
    await db_session.commit()

    exec3 = await manager.create_successor(exec2, "context_limit")
    await db_session.commit()

    # Assert: Full lineage preserved
    await db_session.refresh(exec1)
    await db_session.refresh(exec2)
    await db_session.refresh(exec3)

    # Verify chain: exec1 → exec2 → exec3
    assert exec1.succeeded_by == exec2.agent_id
    assert exec2.spawned_by == exec1.agent_id
    assert exec2.succeeded_by == exec3.agent_id
    assert exec3.spawned_by == exec2.agent_id

    # All on SAME job
    assert exec1.job_id == exec2.job_id == exec3.job_id == job.job_id

    # Instance numbers increment
    assert exec1.instance_number == 1
    assert exec2.instance_number == 2
    assert exec3.instance_number == 3


@pytest.mark.asyncio
async def test_succession_reason_captured(db_session, test_project_0366b):
    """
    Succession reason is captured in execution metadata.
    """
    # Setup
    job = AgentJob(
        job_id="job-reason-test",
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
    db_session.add(exec1)
    await db_session.commit()

    # Act: Create successor with specific reason
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    exec2 = await manager.create_successor(exec1, "phase_transition")

    # Assert: Reason captured
    await db_session.refresh(exec1)
    assert exec1.succession_reason == "phase_transition"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_succession(db_session, test_project_0366b):
    """
    Succession respects multi-tenant isolation.

    Scenario: Two tenants with same job_type - succession must not cross tenants.
    """
    # Create projects for two tenants
    project_a = Project(
        id="project-a",
        tenant_key="tenant-a",
        name="Project A",
        description="Tenant A project",
        mission="Build auth for tenant A",
        status="active"
    )
    project_b = Project(
        id="project-b",
        tenant_key="tenant-b",
        name="Project B",
        description="Tenant B project",
        mission="Build auth for tenant B",
        status="active"
    )
    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Setup: Create jobs for two tenants
    job_tenant_a = AgentJob(
        job_id="job-tenant-a",
        tenant_key="tenant-a",
        project_id="project-a",
        mission="Build auth for tenant A",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job_tenant_a)

    exec_tenant_a = AgentExecution(
        agent_id="agent-a",
        job_id=job_tenant_a.job_id,
        tenant_key="tenant-a",
        agent_type="orchestrator",
        instance_number=1,
        status="complete"
    )
    db_session.add(exec_tenant_a)

    job_tenant_b = AgentJob(
        job_id="job-tenant-b",
        tenant_key="tenant-b",
        project_id="project-b",
        mission="Build auth for tenant B",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job_tenant_b)

    exec_tenant_b = AgentExecution(
        agent_id="agent-b",
        job_id=job_tenant_b.job_id,
        tenant_key="tenant-b",
        agent_type="orchestrator",
        instance_number=1,
        status="complete"
    )
    db_session.add(exec_tenant_b)
    await db_session.commit()

    # Act: Create successors for each tenant
    manager_a = OrchestratorSuccessionManager(db_session, "tenant-a")
    exec2_tenant_a = await manager_a.create_successor(exec_tenant_a, "context_limit")

    manager_b = OrchestratorSuccessionManager(db_session, "tenant-b")
    exec2_tenant_b = await manager_b.create_successor(exec_tenant_b, "context_limit")

    # Assert: Tenant isolation maintained
    assert exec2_tenant_a.tenant_key == "tenant-a"
    assert exec2_tenant_a.job_id == job_tenant_a.job_id

    assert exec2_tenant_b.tenant_key == "tenant-b"
    assert exec2_tenant_b.job_id == job_tenant_b.job_id

    # Verify no cross-tenant references
    assert exec2_tenant_a.job_id != exec2_tenant_b.job_id
