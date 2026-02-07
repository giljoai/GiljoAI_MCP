"""
Tests for ToolAccessor.update_agent_mission() method.

Handover 0380: Enables staging -> implementation flow across terminal sessions.
The orchestrator writes its execution plan during staging via update_agent_mission(),
then retrieves it in a fresh terminal session via get_agent_mission().
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


@pytest_asyncio.fixture
async def tenant_key():
    """Generate test tenant key."""
    return f"tk_test_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def tool_accessor(db_manager, db_session, tenant_key):
    """Create ToolAccessor instance with test session."""
    from src.giljo_mcp.tenant import TenantManager

    tenant_manager = TenantManager()
    tenant_manager.get_current_tenant = lambda: tenant_key

    accessor = ToolAccessor(db_manager, tenant_manager, test_session=db_session)
    return accessor


@pytest_asyncio.fixture
async def orchestrator_job(db_session, tenant_key):
    """Create an orchestrator AgentJob for testing."""
    from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

    job_id = str(uuid4())
    agent_id = str(uuid4())
    project_id = str(uuid4())

    # Create AgentJob (work order)
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        mission="I am ready to create the project mission based on product context and project description.",
        job_type="orchestrator",
        status="active",
    )
    db_session.add(job)

    # Create AgentExecution (executor)
    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        agent_name="Orchestrator",
        status="working",
    )
    db_session.add(execution)
    await db_session.commit()

    return {"job_id": job_id, "agent_id": agent_id, "project_id": project_id}


@pytest.mark.asyncio
async def test_update_agent_mission_success(db_manager, db_session, tenant_key, orchestrator_job):
    """
    Test that update_agent_mission successfully updates AgentJob.mission.

    This is the core functionality for staging -> implementation flow.
    """
    from src.giljo_mcp.tenant import TenantManager

    tenant_manager = TenantManager()
    tenant_manager.get_current_tenant = lambda: tenant_key

    accessor = ToolAccessor(db_manager, tenant_manager, test_session=db_session)

    # The execution plan orchestrator writes during staging
    execution_plan = """
    EXECUTION PLAN:
    - Agent Order: sequential
    - Phase 1: implementer-backend (API endpoints)
    - Phase 2: implementer-frontend (Vue components)
    - Phase 3: tester (integration tests)
    - Checkpoints: After each phase, verify via get_workflow_status()
    """

    # Act: Update the mission
    result = await accessor.update_agent_mission(
        job_id=orchestrator_job["job_id"],
        tenant_key=tenant_key,
        mission=execution_plan,
    )

    # Assert: Success response
    assert result["success"] is True
    assert result["job_id"] == orchestrator_job["job_id"]
    assert result["mission_updated"] is True
    assert result["mission_length"] == len(execution_plan)


@pytest.mark.asyncio
async def test_update_agent_mission_not_found(db_manager, db_session, tenant_key):
    """
    Test that update_agent_mission returns error for non-existent job.
    """
    from src.giljo_mcp.tenant import TenantManager

    tenant_manager = TenantManager()
    tenant_manager.get_current_tenant = lambda: tenant_key

    accessor = ToolAccessor(db_manager, tenant_manager, test_session=db_session)

    # Act: Try to update non-existent job
    result = await accessor.update_agent_mission(
        job_id=str(uuid4()),  # Non-existent
        tenant_key=tenant_key,
        mission="This should fail",
    )

    # Assert: Error response
    assert result["error"] == "NOT_FOUND"
    assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_update_agent_mission_tenant_isolation(db_manager, db_session, tenant_key, orchestrator_job):
    """
    Test that update_agent_mission respects tenant isolation.

    A job created under one tenant cannot be updated by another tenant.
    """
    from src.giljo_mcp.tenant import TenantManager

    wrong_tenant_key = f"tk_wrong_{uuid4().hex[:16]}"

    tenant_manager = TenantManager()
    tenant_manager.get_current_tenant = lambda: wrong_tenant_key

    accessor = ToolAccessor(db_manager, tenant_manager, test_session=db_session)

    # Act: Try to update with wrong tenant
    result = await accessor.update_agent_mission(
        job_id=orchestrator_job["job_id"],
        tenant_key=wrong_tenant_key,  # Wrong tenant
        mission="This should fail due to tenant isolation",
    )

    # Assert: Not found (tenant isolation prevents access)
    assert result["error"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_staging_to_implementation_flow(db_manager, db_session, tenant_key, orchestrator_job):
    """
    Integration test: Write during staging -> Read via get_agent_mission in fresh session.

    This is the key flow that Handover 0380 enables:
    1. Orchestrator writes execution plan during staging
    2. User closes terminal
    3. User opens new terminal, launches implementation
    4. Fresh orchestrator retrieves its persisted plan via get_agent_mission()
    """
    from src.giljo_mcp.services.orchestration_service import OrchestrationService
    from src.giljo_mcp.tenant import TenantManager

    tenant_manager = TenantManager()
    tenant_manager.get_current_tenant = lambda: tenant_key

    # STAGING SESSION: Orchestrator writes its plan
    accessor = ToolAccessor(db_manager, tenant_manager, test_session=db_session)

    execution_plan = """
    ORCHESTRATOR EXECUTION PLAN:
    1. Spawn implementer in parallel with analyzer
    2. Wait for both to complete (via receive_messages polling)
    3. Spawn tester after implementation complete
    4. Final review via reviewer agent
    Dependencies: tester depends on implementer; reviewer depends on all
    """

    write_result = await accessor.update_agent_mission(
        job_id=orchestrator_job["job_id"],
        tenant_key=tenant_key,
        mission=execution_plan,
    )
    assert write_result["success"] is True

    # FRESH SESSION: New orchestrator retrieves the plan
    # Simulate fresh session by creating new service instance
    orchestration_service = OrchestrationService(db_manager, websocket_manager=None)

    read_result = await orchestration_service.get_agent_mission(
        job_id=orchestrator_job["job_id"],
        tenant_key=tenant_key,
    )

    # Assert: The mission was retrieved correctly
    assert read_result["success"] is True
    assert "ORCHESTRATOR EXECUTION PLAN" in read_result["mission"]
    assert "Dependencies: tester depends on implementer" in read_result["mission"]

    # Verify full_protocol is also returned (6-phase lifecycle)
    assert "full_protocol" in read_result
    assert len(read_result["full_protocol"]) > 0
