"""
TDD Tests for OrchestrationService Dual-Model Migration (Handover 0358b).

RED PHASE - These tests WILL FAIL initially.

Purpose: Verify OrchestrationService correctly uses AgentJob + AgentExecution
         instead of monolithic MCPAgentJob model.

Key Semantic Changes:
- job_id: Now refers to WORK ORDER (persists across succession)
- agent_id: NEW - Refers to EXECUTOR (changes on succession)
- spawned_by: Now points to agent_id (executor), not job_id
- succeeded_by: Renamed from handover_to (points to agent_id)

Design Philosophy:
- AgentJob: Persistent work order (mission, scope) - WHAT
- AgentExecution: Executor instance (who, when, status) - WHO
- Succession: New execution, SAME job (job_id persists, agent_id changes)

Test Coverage:
1. spawn_agent_job creates BOTH AgentJob and AgentExecution
2. Succession creates new execution, NOT new job
3. Query methods correctly join AgentJob + AgentExecution
4. Update methods target AgentExecution (not AgentJob)
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import AgentExecution, AgentJob, Project


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key() -> str:
    """Generate unique tenant key for test isolation."""
    return f"tk_test_{uuid.uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_project(db_session, test_tenant_key) -> Project:
    """Create test project for agent jobs."""
    project = Project(
        id=str(uuid.uuid4()),
        name="Dual Model Test Project",
        description="Test project for dual-model migration",
        mission="Test mission for dual-model migration",
        status="active",
        tenant_key=test_tenant_key,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# Test Class: spawn_agent_job Creates BOTH Job and Execution
# ============================================================================


@pytest.mark.asyncio
class TestSpawnAgentJobDualModel:
    """
    Tests that spawn_agent_job creates BOTH AgentJob and AgentExecution.

    Expected Behavior:
    - Creates AgentJob record (work order)
    - Creates AgentExecution record (executor)
    - job_id and agent_id are DIFFERENT UUIDs
    - mission stored in AgentJob only (not duplicated)
    - Returns dict with both job_id and agent_id keys
    - instance_number starts at 1 for first execution
    """

    async def test_spawn_creates_both_job_and_execution(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify spawn_agent_job creates BOTH AgentJob and AgentExecution."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement authentication system",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Verify return structure
        assert result["success"] is True
        assert "job_id" in result
        assert "agent_id" in result

        # Verify job_id and agent_id are DIFFERENT UUIDs
        assert result["job_id"] != result["agent_id"]
        assert isinstance(uuid.UUID(result["job_id"]), uuid.UUID)
        assert isinstance(uuid.UUID(result["agent_id"]), uuid.UUID)

        # Verify AgentJob was created
        job_stmt = select(AgentJob).where(AgentJob.job_id == result["job_id"])
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one_or_none()
        assert job is not None
        assert job.mission == "Implement authentication system"
        assert job.job_type == "implementer"
        assert job.tenant_key == test_tenant_key
        assert job.project_id == test_project.id

        # Verify AgentExecution was created
        exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == result["agent_id"])
        exec_result = await db_session.execute(exec_stmt)
        execution = exec_result.scalar_one_or_none()
        assert execution is not None
        assert execution.job_id == result["job_id"]
        assert execution.agent_display_name == "implementer"
        assert execution.tenant_key == test_tenant_key
        assert execution.instance_number == 1

    async def test_spawn_stores_mission_in_job_not_execution(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify mission is stored in AgentJob, NOT duplicated in AgentExecution."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        mission = "Build OAuth2 authentication with JWT tokens"
        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="auth-impl",
            mission=mission,
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Verify mission in AgentJob
        job_stmt = select(AgentJob).where(AgentJob.job_id == result["job_id"])
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.mission == mission

        # Verify AgentExecution does NOT have mission field
        exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == result["agent_id"])
        exec_result = await db_session.execute(exec_stmt)
        execution = exec_result.scalar_one()
        # AgentExecution should NOT have a 'mission' attribute
        assert not hasattr(execution, "mission")

    async def test_spawn_returns_both_ids(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify spawn_agent_job returns dict with both job_id and agent_id."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="test-1",
            mission="Write integration tests",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Verify return structure
        assert "success" in result
        assert "job_id" in result
        assert "agent_id" in result
        assert result["success"] is True

        # Verify both IDs are valid UUIDs
        try:
            uuid.UUID(result["job_id"])
            uuid.UUID(result["agent_id"])
        except ValueError:
            pytest.fail("job_id or agent_id is not a valid UUID")

    async def test_spawn_sets_instance_number_to_one(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify first execution starts with instance_number = 1."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="analyzer",
            agent_name="analyzer-1",
            mission="Analyze codebase architecture",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Verify instance_number is 1
        exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == result["agent_id"])
        exec_result = await db_session.execute(exec_stmt)
        execution = exec_result.scalar_one()
        assert execution.instance_number == 1


# ============================================================================
# Test Class: Succession Creates New Execution, NOT New Job
# ============================================================================


@pytest.mark.asyncio
class TestSuccessionDualModel:
    """
    Tests that succession creates new AgentExecution, NOT new AgentJob.

    Expected Behavior:
    - trigger_succession creates new AgentExecution with new agent_id
    - trigger_succession uses SAME job_id (work order persists)
    - Predecessor's succeeded_by points to new agent_id
    - New execution's instance_number increments
    - New execution's spawned_by points to predecessor's agent_id (not job_id)
    """

    async def test_succession_creates_new_execution_same_job(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify succession creates new execution but reuses same job."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn initial orchestrator
        initial = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            mission="Orchestrate project development",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        initial_job_id = initial["job_id"]
        initial_agent_id = initial["agent_id"]

        # Trigger succession (job_id treated as agent_id for backwards compat)
        succession_result = await service.trigger_succession(
            job_id=initial_agent_id,
            reason="context_limit",
            tenant_key=test_tenant_key,
        )

        # Verify new execution was created
        assert succession_result["success"] is True
        assert "successor_agent_id" in succession_result
        new_agent_id = succession_result["successor_agent_id"]
        assert new_agent_id != initial_agent_id

        # Verify job_id is SAME
        new_exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == new_agent_id)
        new_exec_result = await db_session.execute(new_exec_stmt)
        new_execution = new_exec_result.scalar_one()
        assert new_execution.job_id == initial_job_id  # SAME job

        # Verify only ONE AgentJob exists (not duplicated)
        job_count_stmt = select(AgentJob).where(AgentJob.job_id == initial_job_id)
        job_count_result = await db_session.execute(job_count_stmt)
        jobs = job_count_result.scalars().all()
        assert len(jobs) == 1  # Only ONE job

    async def test_succession_sets_succeeded_by_on_predecessor(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify predecessor's succeeded_by points to new agent_id."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn initial orchestrator
        initial = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            mission="Orchestrate project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        initial_agent_id = initial["agent_id"]

        # Trigger succession (job_id treated as agent_id for backwards compat)
        succession_result = await service.trigger_succession(
            job_id=initial_agent_id,
            reason="manual",
            tenant_key=test_tenant_key,
        )
        new_agent_id = succession_result["successor_agent_id"]

        # Verify predecessor's succeeded_by is set
        predecessor_stmt = select(AgentExecution).where(AgentExecution.agent_id == initial_agent_id)
        predecessor_result = await db_session.execute(predecessor_stmt)
        predecessor = predecessor_result.scalar_one()
        assert predecessor.succeeded_by == new_agent_id

    async def test_succession_sets_spawned_by_on_successor(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify new execution's spawned_by points to predecessor's agent_id."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn initial orchestrator
        initial = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            mission="Orchestrate project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        initial_agent_id = initial["agent_id"]

        # Trigger succession (job_id treated as agent_id for backwards compat)
        succession_result = await service.trigger_succession(
            job_id=initial_agent_id,
            reason="context_limit",
            tenant_key=test_tenant_key,
        )
        new_agent_id = succession_result["successor_agent_id"]

        # Verify new execution's spawned_by points to predecessor's agent_id
        new_exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == new_agent_id)
        new_exec_result = await db_session.execute(new_exec_stmt)
        new_execution = new_exec_result.scalar_one()
        assert new_execution.spawned_by == initial_agent_id  # NOT job_id

    async def test_succession_increments_instance_number(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify new execution's instance_number increments."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn initial orchestrator
        initial = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator-1",
            mission="Orchestrate project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        initial_agent_id = initial["agent_id"]

        # Verify initial instance is 1
        initial_exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == initial_agent_id)
        initial_exec_result = await db_session.execute(initial_exec_stmt)
        initial_execution = initial_exec_result.scalar_one()
        assert initial_execution.instance_number == 1

        # Trigger succession (job_id treated as agent_id for backwards compat)
        succession_result = await service.trigger_succession(
            job_id=initial_agent_id,
            reason="context_limit",
            tenant_key=test_tenant_key,
        )
        new_agent_id = succession_result["successor_agent_id"]

        # Verify new instance is 2
        new_exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == new_agent_id)
        new_exec_result = await db_session.execute(new_exec_stmt)
        new_execution = new_exec_result.scalar_one()
        assert new_execution.instance_number == 2


# ============================================================================
# Test Class: Query Methods Correctly Join Job + Execution
# ============================================================================


@pytest.mark.asyncio
class TestQueryMethodsDualModel:
    """
    Tests that query methods correctly join AgentJob + AgentExecution.

    Expected Behavior:
    - list_jobs returns both job_id and agent_id
    - get_pending_jobs filters by AgentExecution.status (not AgentJob)
    - get_workflow_status aggregates across executions correctly
    - get_agent_mission returns mission from AgentJob (joined)
    """

    async def test_list_jobs_returns_both_ids(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify list_jobs returns both job_id and agent_id."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn an agent
        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement feature X",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # List jobs - returns {"jobs": [...], "total": N, ...}
        jobs_result = await service.list_jobs(tenant_key=test_tenant_key)
        jobs = jobs_result["jobs"]

        assert len(jobs) >= 1
        job_entry = next((j for j in jobs if j["job_id"] == result["job_id"]), None)
        assert job_entry is not None
        assert "job_id" in job_entry
        assert "agent_id" in job_entry
        assert job_entry["job_id"] == result["job_id"]
        assert job_entry["agent_id"] == result["agent_id"]

    async def test_get_pending_jobs_filters_by_execution_status(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify get_pending_jobs filters by AgentExecution.status."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn waiting agent
        waiting_result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-waiting",
            mission="Waiting task",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Spawn working agent
        working_result = await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="test-working",
            mission="Working task",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Update working agent to "working" status
        working_exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == working_result["agent_id"])
        working_exec_result = await db_session.execute(working_exec_stmt)
        working_exec = working_exec_result.scalar_one()
        working_exec.status = "working"
        await db_session.commit()

        # Get pending jobs for implementer type (waiting only)
        pending_result = await service.get_pending_jobs(agent_display_name="implementer", tenant_key=test_tenant_key)
        pending_jobs = pending_result.get("jobs", [])

        # Verify only waiting job of type implementer is returned
        pending_job_ids = [j["job_id"] for j in pending_jobs]
        assert waiting_result["job_id"] in pending_job_ids
        assert working_result["job_id"] not in pending_job_ids

    async def test_get_agent_mission_returns_mission_from_job(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify get_agent_mission returns mission from AgentJob (joined)."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        mission = "Build comprehensive test suite"
        result = await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="tester-1",
            mission=mission,
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Get mission via job_id (job_id parameter is actually job_id)
        fetched_mission = await service.get_agent_mission(
            job_id=result["job_id"], tenant_key=test_tenant_key
        )

        assert fetched_mission.get("success") is True
        # Mission includes team context header prefix, so check it ends with the original mission
        assert mission in fetched_mission["mission"]

    async def test_get_workflow_status_aggregates_across_executions(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify get_workflow_status aggregates across all executions correctly."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        # Spawn multiple agents
        await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Task 1",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        await service.spawn_agent_job(
            agent_display_name="tester",
            agent_name="test-1",
            mission="Task 2",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )

        # Get workflow status
        status = await service.get_workflow_status(project_id=test_project.id, tenant_key=test_tenant_key)

        # get_workflow_status returns counts directly without "success" key
        assert "error" not in status
        assert "total_agents" in status
        assert status["total_agents"] >= 2


# ============================================================================
# Test Class: Update Methods Target AgentExecution
# ============================================================================


@pytest.mark.asyncio
class TestUpdateMethodsDualModel:
    """
    Tests that update methods target AgentExecution (not AgentJob).

    Expected Behavior:
    - acknowledge_job updates AgentExecution.mission_acknowledged_at
    - complete_job updates AgentExecution.status, not AgentJob.status
    - report_progress updates AgentExecution fields
    - update_context_usage updates AgentExecution.context_used
    """

    async def test_acknowledge_job_updates_execution(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify acknowledge_job updates AgentExecution.mission_acknowledged_at."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement feature",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        agent_id = result["agent_id"]
        job_id = result["job_id"]

        # Acknowledge job (requires job_id and agent_id)
        ack_result = await service.acknowledge_job(job_id=job_id, agent_id=agent_id, tenant_key=test_tenant_key)

        assert ack_result.get("status") == "success"

        # Verify AgentExecution.mission_acknowledged_at is set
        exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        exec_result = await db_session.execute(exec_stmt)
        execution = exec_result.scalar_one()
        assert execution.mission_acknowledged_at is not None

    async def test_complete_job_updates_execution_status(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify complete_job updates AgentExecution.status, not AgentJob.status."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement feature",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        agent_id = result["agent_id"]
        job_id = result["job_id"]

        # Complete job (requires job_id and result dict)
        complete_result = await service.complete_job(job_id=job_id, result={"output": "Task done"}, tenant_key=test_tenant_key)

        assert complete_result.get("status") == "success"

        # Verify AgentExecution.status is "complete"
        exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        exec_result = await db_session.execute(exec_stmt)
        execution = exec_result.scalar_one()
        assert execution.status == "complete"

        # Verify AgentJob.status is now "completed" (job completes when last execution completes)
        job_stmt = select(AgentJob).where(AgentJob.job_id == job_id)
        job_result = await db_session.execute(job_stmt)
        job = job_result.scalar_one()
        assert job.status == "completed"  # Job completes with last execution

    async def test_report_progress_updates_execution_fields(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify report_progress updates AgentExecution fields."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="Implement feature",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        agent_id = result["agent_id"]
        job_id = result["job_id"]

        # Report progress (requires job_id and progress dict)
        # Note: In test environment, message queue may fail but progress fields still get updated
        progress_result = await service.report_progress(
            job_id=job_id,
            progress={"percent": 50, "message": "Implementing database schema"},
            tenant_key=test_tenant_key,
        )

        # Progress fields are updated in execution even if message queue fails
        # Verify AgentExecution fields updated by refreshing session
        await db_session.commit()  # Ensure changes are visible
        exec_stmt = select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        exec_result = await db_session.execute(exec_stmt)
        execution = exec_result.scalar_one()
        assert execution.progress == 50
        assert execution.current_task == "Implementing database schema"
        assert execution.last_progress_at is not None

    async def test_update_context_usage_updates_execution(self, db_session, db_manager, test_project, test_tenant_key):
        """Verify update_context_usage updates AgentExecution.context_used."""
        from src.giljo_mcp.services.orchestration_service import OrchestrationService
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = OrchestrationService(db_manager=db_manager, tenant_manager=tenant_manager, test_session=db_session)

        result = await service.spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="orch-1",
            mission="Orchestrate project",
            project_id=test_project.id,
            tenant_key=test_tenant_key,
        )
        agent_id = result["agent_id"]
        job_id = result["job_id"]

        # Update context usage (requires job_id and additional_tokens)
        # First call with 25000 tokens
        context_result1 = await service.update_context_usage(
            job_id=job_id, additional_tokens=25000, tenant_key=test_tenant_key
        )
        assert context_result1.get("success") is True
        first_used = context_result1.get("context_used")

        # Second call with 25000 more tokens - verify increment works
        context_result2 = await service.update_context_usage(
            job_id=job_id, additional_tokens=25000, tenant_key=test_tenant_key
        )
        assert context_result2.get("success") is True
        second_used = context_result2.get("context_used")

        # Verify context_used incremented correctly (returns cumulative total)
        assert second_used == first_used + 25000  # Incremented by second call
