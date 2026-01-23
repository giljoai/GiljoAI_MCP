"""
End-to-end integration tests for OrchestrationService workflows.

Tests full workflows from MCP tool call to database state verification.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models import Project, Product, AgentTemplate
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution, AgentTodoItem
from src.giljo_mcp.enums import AgentRole


# ============================================================================
# E2E Workflow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_orchestrator_workflow_spawn_execute_complete(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Full orchestrator workflow: spawn -> acknowledge -> report_progress -> complete.

    Verifies:
    1. spawn_agent_job creates AgentJob + AgentExecution
    2. acknowledge_job updates status
    3. report_progress updates job metadata
    4. complete_job finalizes with duration
    """
    service = orchestration_service_with_session

    # Step 1: Spawn agent job
    spawn_result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="backend-implementer",
        mission="Implement user authentication endpoint",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    assert spawn_result["success"] is True
    job_id = spawn_result["job_id"]
    agent_id = spawn_result["agent_id"]

    # Verify AgentJob created
    result = await db_session.execute(
        select(AgentJob).where(AgentJob.job_id == job_id)
    )
    agent_job = result.scalar_one_or_none()
    assert agent_job is not None
    assert agent_job.status == "active"  # Jobs are created as "active"
    assert agent_job.tenant_key == test_tenant_key

    # Verify AgentExecution created
    result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == agent_id)
    )
    agent_execution = result.scalar_one_or_none()
    assert agent_execution is not None
    assert agent_execution.status == "waiting"

    # Step 2: Acknowledge job
    ack_result = await service.acknowledge_job(
        job_id=job_id,
        agent_id=agent_id,
    )

    # Check for success (either "success" key or "status" == "success")
    assert ack_result.get("status") == "success" or ack_result.get("success") is True
    await db_session.refresh(agent_job)
    await db_session.refresh(agent_execution)
    assert agent_job.status == "active"
    assert agent_execution.status == "working"

    # Step 3: Report progress with todo_items
    progress_result = await service.report_progress(
        job_id=job_id,
        tenant_key=test_tenant_key,
        todo_items=[
            {"content": "Setup authentication schema", "status": "completed"},
            {"content": "Implement login endpoint", "status": "in_progress"},
            {"content": "Add JWT token generation", "status": "pending"},
        ]
    )

    # Check for success
    assert progress_result.get("status") == "success" or progress_result.get("success") is True

    # Verify todo items stored in database
    result = await db_session.execute(
        select(AgentTodoItem).where(AgentTodoItem.job_id == job_id)
    )
    todo_items = result.scalars().all()
    assert len(todo_items) == 3
    assert todo_items[0].status == "completed"
    assert todo_items[1].status == "in_progress"
    assert todo_items[2].status == "pending"

    # Verify progress calculated correctly
    await db_session.refresh(agent_execution)
    assert agent_execution.progress == 33  # 1/3 completed = 33%

    # Step 3b: Complete remaining TODO items before completing job
    progress_result_final = await service.report_progress(
        job_id=job_id,
        tenant_key=test_tenant_key,
        todo_items=[
            {"content": "Setup authentication schema", "status": "completed"},
            {"content": "Implement login endpoint", "status": "completed"},
            {"content": "Add JWT token generation", "status": "completed"},
        ]
    )
    assert progress_result_final.get("status") == "success" or progress_result_final.get("success") is True

    # Step 4: Complete job
    complete_result = await service.complete_job(
        job_id=job_id,
        result={"summary": "Authentication endpoint implemented successfully"}
    )

    # Check for success
    assert complete_result.get("status") == "success" or complete_result.get("success") is True
    await db_session.refresh(agent_job)
    await db_session.refresh(agent_execution)
    assert agent_job.status == "completed"
    assert agent_execution.status in ["completed", "complete"]
    # Verify completion time was set
    assert agent_execution.completed_at is not None


@pytest.mark.asyncio
async def test_e2e_succession_workflow(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Full succession workflow: check -> create -> handover.

    Verifies:
    1. check_succession_status returns threshold
    2. create_successor_orchestrator creates new execution
    3. Predecessor marked for succession
    """
    service = orchestration_service_with_session

    # Create orchestrator job with high context usage
    orchestrator_job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=str(test_project.id),
        mission="Orchestrate project delivery",
        job_type="orchestrator",
        status="active",
    )
    db_session.add(orchestrator_job)

    orchestrator_execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=orchestrator_job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        instance_number=1,
        status="working",
        context_used=135000,  # 90% of 150000 default budget
        context_budget=150000,
    )
    db_session.add(orchestrator_execution)
    await db_session.commit()

    # Step 1: Check succession status
    check_result = await service.check_succession_status(
        job_id=orchestrator_job.job_id,
        tenant_key=test_tenant_key,
    )

    assert check_result["should_trigger"] is True
    assert check_result["usage_percentage"] == 90
    assert check_result["threshold_reached"] is True

    # Step 2: Create successor
    successor_result = await service.create_successor_orchestrator(
        current_job_id=orchestrator_job.job_id,
        tenant_key=test_tenant_key,
        reason="context_limit",
    )

    assert successor_result["success"] is True
    successor_agent_id = successor_result["successor_id"]
    assert successor_agent_id != orchestrator_execution.agent_id  # Different executor, same job

    # Verify predecessor marked as decommissioned
    await db_session.refresh(orchestrator_execution)
    assert orchestrator_execution.status == "decommissioned"
    assert orchestrator_execution.succeeded_by == successor_agent_id

    # Verify successor execution created (same job_id, new agent_id)
    result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == successor_agent_id)
    )
    successor_execution = result.scalar_one_or_none()
    assert successor_execution is not None
    assert successor_execution.job_id == orchestrator_job.job_id  # Same work order
    assert successor_execution.instance_number == 2  # Next instance
    assert successor_execution.status == "waiting"


@pytest.mark.asyncio
@pytest.mark.skip(reason="MessageService requires separate db_manager - TODO: fix database injection")
async def test_e2e_agent_communication_workflow(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Agent message flow: spawn -> send_message -> receive_messages.

    Tests message passing between agents.

    NOTE: Skipped because MessageService requires its own db_manager instance.
    This is a known limitation of the current test architecture.
    """
    pass  # Skipped for now


@pytest.mark.asyncio
async def test_e2e_error_propagation(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Error handling: report_error pauses job.

    Verifies errors are properly recorded and job is paused.
    """
    service = orchestration_service_with_session

    # Spawn agent job
    spawn_result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="backend-implementer",
        mission="Implement feature",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    job_id = spawn_result["job_id"]
    agent_id = spawn_result["agent_id"]

    # Acknowledge job to move to active state
    await service.acknowledge_job(job_id=job_id, agent_id=agent_id)

    # Report error
    error_result = await service.report_error(
        job_id=job_id,
        error="Database connection failed during migration"
    )

    # Check for success
    assert error_result.get("status") == "success" or error_result.get("success") is True

    # Verify execution status changed to blocked
    result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == agent_id)
    )
    agent_execution = result.scalar_one_or_none()
    assert agent_execution.status == "blocked"
    assert agent_execution.block_reason == "Database connection failed during migration"

    # Note: AgentJob status remains "active" - only execution is blocked


@pytest.mark.asyncio
async def test_e2e_get_workflow_status(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Test workflow status monitoring across multiple agents.

    Verifies:
    - Active/completed/failed agent counts
    - Progress percent calculation
    - Status aggregation across project
    """
    service = orchestration_service_with_session

    # Spawn multiple agents
    agent1_result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="backend-implementer",
        mission="Implement features",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    agent2_result = await service.spawn_agent_job(
        agent_display_name="tester",
        agent_name="integration-tester",
        mission="Write tests",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    agent3_result = await service.spawn_agent_job(
        agent_display_name="reviewer",
        agent_name="code-reviewer",
        mission="Review code",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    # Complete first agent
    await service.acknowledge_job(
        job_id=agent1_result["job_id"],
        agent_id=agent1_result["agent_id"]
    )
    await service.complete_job(
        job_id=agent1_result["job_id"],
        result={"summary": "Implementation complete"}
    )

    # Start second agent
    await service.acknowledge_job(
        job_id=agent2_result["job_id"],
        agent_id=agent2_result["agent_id"]
    )

    # Third agent remains pending

    # Get workflow status
    status_result = await service.get_workflow_status(
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    # Verify counts
    assert status_result["total_agents"] == 3
    assert status_result["completed_agents"] == 1
    assert status_result["active_agents"] == 1
    assert status_result["pending_agents"] == 1
    assert status_result["failed_agents"] == 0

    # Verify progress percent (1/3 = 33%)
    assert status_result["progress_percent"] == 33.33


@pytest.mark.asyncio
async def test_e2e_get_agent_mission(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Test get_agent_mission returns full protocol and mission.

    Verifies:
    - Mission text is returned
    - Full protocol is included
    - Team awareness context is present
    """
    service = orchestration_service_with_session

    # Spawn agent
    spawn_result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="backend-implementer",
        mission="Implement user authentication with JWT tokens",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    job_id = spawn_result["job_id"]

    # Get agent mission
    mission_result = await service.get_agent_mission(
        job_id=job_id,
        tenant_key=test_tenant_key,
    )

    assert mission_result["success"] is True

    # Verify mission fields
    assert "mission" in mission_result
    assert "Implement user authentication with JWT tokens" in mission_result["mission"]

    # Verify protocol is included
    assert "full_protocol" in mission_result
    assert "Agent Lifecycle Protocol" in mission_result["full_protocol"]
    assert "Phase 1: STARTUP" in mission_result["full_protocol"]
    assert "Phase 2: EXECUTION" in mission_result["full_protocol"]

    # Verify team awareness context
    assert "YOUR IDENTITY" in mission_result["mission"]
    assert "YOUR TEAM" in mission_result["mission"]
    assert "YOUR DEPENDENCIES" in mission_result["mission"]


@pytest.mark.asyncio
async def test_e2e_update_agent_mission(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_project,
    orchestration_service_with_session,
):
    """
    Test update_agent_mission updates mission text.

    Verifies mission can be updated after spawning.
    """
    service = orchestration_service_with_session

    # Spawn agent
    spawn_result = await service.spawn_agent_job(
        agent_display_name="implementer",
        agent_name="backend-implementer",
        mission="Original mission text",
        project_id=str(test_project.id),
        tenant_key=test_tenant_key,
    )

    job_id = spawn_result["job_id"]

    # Update mission
    update_result = await service.update_agent_mission(
        job_id=job_id,
        tenant_key=test_tenant_key,
        mission="Updated mission with new requirements"
    )

    assert update_result["success"] is True

    # Verify mission was updated in database
    result = await db_session.execute(
        select(AgentJob).where(AgentJob.job_id == job_id)
    )
    agent_job = result.scalar_one_or_none()
    assert agent_job.mission == "Updated mission with new requirements"
