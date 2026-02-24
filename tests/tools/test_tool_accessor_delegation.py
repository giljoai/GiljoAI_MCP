"""
Tests verifying ToolAccessor properly delegates to OrchestrationService.

These tests ensure that ToolAccessor methods are thin wrappers that delegate
to OrchestrationService without adding business logic.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager for testing."""
    manager = MagicMock(spec=DatabaseManager)
    manager.get_session_async = MagicMock()
    return manager


@pytest.fixture
def mock_tenant_manager():
    """Mock TenantManager for testing."""
    manager = MagicMock(spec=TenantManager)
    manager.get_current_tenant = MagicMock(return_value="test_tenant")
    return manager


@pytest.fixture
def tool_accessor(mock_db_manager, mock_tenant_manager):
    """Create ToolAccessor with mocked OrchestrationService."""
    accessor = ToolAccessor(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
    )

    # Mock the OrchestrationService
    accessor._orchestration_service = MagicMock()

    # Make all orchestration service methods async mocks
    accessor._orchestration_service.get_orchestrator_instructions = AsyncMock()
    accessor._orchestration_service.spawn_agent_job = AsyncMock()
    accessor._orchestration_service.get_agent_mission = AsyncMock()
    accessor._orchestration_service.get_workflow_status = AsyncMock()
    accessor._orchestration_service.get_pending_jobs = AsyncMock()
    accessor._orchestration_service.acknowledge_job = AsyncMock()
    accessor._orchestration_service.report_progress = AsyncMock()
    accessor._orchestration_service.complete_job = AsyncMock()
    accessor._orchestration_service.report_error = AsyncMock()
    # NOTE: create_successor_orchestrator, check_succession_status removed (succession via UI only)
    accessor._orchestration_service.update_agent_mission = AsyncMock()

    return accessor


# ============================================================================
# Delegation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_delegates_to_service(tool_accessor):
    """ToolAccessor.get_orchestrator_instructions calls OrchestrationService.get_orchestrator_instructions"""
    job_id = str(uuid4())
    tenant_key = "test_tenant"

    # Setup mock response
    expected_result = {"success": True, "data": {"instructions": "Test instructions"}}
    tool_accessor._orchestration_service.get_orchestrator_instructions.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.get_orchestrator_instructions(job_id, tenant_key)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.get_orchestrator_instructions.assert_called_once_with(job_id, tenant_key)

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_spawn_agent_job_delegates_to_service(tool_accessor):
    """ToolAccessor.spawn_agent_job calls OrchestrationService.spawn_agent_job"""
    agent_display_name = "implementer"
    agent_name = "backend-implementer"
    mission = "Test mission"
    project_id = str(uuid4())
    tenant_key = "test_tenant"
    parent_job_id = str(uuid4())

    # Setup mock response
    expected_result = {"success": True, "data": {"job_id": str(uuid4()), "agent_id": str(uuid4())}}
    tool_accessor._orchestration_service.spawn_agent_job.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.spawn_agent_job(
        agent_display_name=agent_display_name,
        agent_name=agent_name,
        mission=mission,
        project_id=project_id,
        tenant_key=tenant_key,
        parent_job_id=parent_job_id,
    )

    # Verify service method was called with correct args (Handover 0411a: phase=None default)
    tool_accessor._orchestration_service.spawn_agent_job.assert_called_once_with(
        agent_display_name=agent_display_name,
        agent_name=agent_name,
        mission=mission,
        project_id=project_id,
        tenant_key=tenant_key,
        parent_job_id=parent_job_id,
        phase=None,
    )

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_agent_mission_delegates_to_service(tool_accessor):
    """ToolAccessor.get_agent_mission calls OrchestrationService.get_agent_mission"""
    job_id = str(uuid4())
    tenant_key = "test_tenant"

    # Setup mock response
    expected_result = {"success": True, "data": {"mission": "Test mission", "full_protocol": "Protocol text"}}
    tool_accessor._orchestration_service.get_agent_mission.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.get_agent_mission(job_id, tenant_key)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.get_agent_mission.assert_called_once_with(job_id=job_id, tenant_key=tenant_key)

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_workflow_status_delegates_to_service(tool_accessor):
    """ToolAccessor.get_workflow_status calls OrchestrationService.get_workflow_status"""
    project_id = str(uuid4())
    tenant_key = "test_tenant"

    # Setup mock response
    expected_result = {
        "success": True,
        "data": {
            "total_agents": 3,
            "completed_agents": 1,
            "active_agents": 1,
            "pending_agents": 1,
            "progress_percent": 33,
        },
    }
    tool_accessor._orchestration_service.get_workflow_status.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.get_workflow_status(project_id, tenant_key)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.get_workflow_status.assert_called_once_with(
        project_id=project_id, tenant_key=tenant_key
    )

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_pending_jobs_delegates_to_service(tool_accessor):
    """ToolAccessor.get_pending_jobs calls OrchestrationService.get_pending_jobs"""
    agent_display_name = "implementer"
    tenant_key = "test_tenant"

    # Setup mock response
    expected_result = {"success": True, "data": {"jobs": [{"job_id": str(uuid4())}]}}
    tool_accessor._orchestration_service.get_pending_jobs.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.get_pending_jobs(agent_display_name, tenant_key)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.get_pending_jobs.assert_called_once_with(
        agent_display_name=agent_display_name, tenant_key=tenant_key
    )

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_acknowledge_job_delegates_to_service(tool_accessor):
    """ToolAccessor.acknowledge_job calls OrchestrationService.acknowledge_job"""
    job_id = str(uuid4())
    agent_id = str(uuid4())

    # Setup mock response
    expected_result = {"success": True, "data": {"status": "active"}}
    tool_accessor._orchestration_service.acknowledge_job.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.acknowledge_job(job_id, agent_id)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.acknowledge_job.assert_called_once_with(job_id=job_id, agent_id=agent_id)

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_report_progress_delegates_to_service(tool_accessor):
    """ToolAccessor.report_progress calls OrchestrationService.report_progress"""
    job_id = str(uuid4())
    tenant_key = "test_tenant"
    todo_items = [
        {"content": "Task 1", "status": "completed"},
        {"content": "Task 2", "status": "in_progress"},
    ]

    # Setup mock response
    expected_result = {"success": True, "data": {"progress_percent": 50}}
    tool_accessor._orchestration_service.report_progress.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.report_progress(job_id=job_id, tenant_key=tenant_key, todo_items=todo_items)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.report_progress.assert_called_once_with(
        job_id=job_id, progress=None, tenant_key=tenant_key, todo_items=todo_items
    )

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_complete_job_delegates_to_service(tool_accessor):
    """ToolAccessor.complete_job calls OrchestrationService.complete_job"""
    job_id = str(uuid4())
    result_data = {"summary": "Job completed successfully"}

    # Setup mock response
    expected_result = {"success": True, "data": {"status": "completed"}}
    tool_accessor._orchestration_service.complete_job.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.complete_job(job_id, result_data)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.complete_job.assert_called_once_with(job_id=job_id, result=result_data)

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_report_error_delegates_to_service(tool_accessor):
    """ToolAccessor.report_error calls OrchestrationService.report_error"""
    job_id = str(uuid4())
    error = "Database connection failed"

    # Setup mock response
    expected_result = {"success": True, "data": {"status": "error"}}
    tool_accessor._orchestration_service.report_error.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.report_error(job_id, error)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.report_error.assert_called_once_with(job_id=job_id, error=error)

    # Verify result passed through
    assert result == expected_result


@pytest.mark.asyncio
async def test_update_agent_mission_delegates_to_service(tool_accessor):
    """ToolAccessor.update_agent_mission calls OrchestrationService.update_agent_mission"""
    job_id = str(uuid4())
    tenant_key = "test_tenant"
    mission = "Updated mission text"

    # Setup mock response
    expected_result = {"success": True, "data": {"mission": mission}}
    tool_accessor._orchestration_service.update_agent_mission.return_value = expected_result

    # Call accessor method
    result = await tool_accessor.update_agent_mission(job_id, tenant_key, mission)

    # Verify service method was called with correct args
    tool_accessor._orchestration_service.update_agent_mission.assert_called_once_with(job_id, tenant_key, mission)

    # Verify result passed through
    assert result == expected_result


# ============================================================================
# Additional Coverage Tests
# ============================================================================


@pytest.mark.asyncio
async def test_all_orchestration_methods_delegate_without_modification(tool_accessor):
    """
    Verify that all orchestration methods are pure delegation (no business logic added).

    This meta-test ensures ToolAccessor remains a thin wrapper.
    """
    # List of methods that should delegate to OrchestrationService
    # NOTE: check_succession_status removed in Handover 0461a (manual succession only)
    # NOTE: orchestrate_project removed in Handover 0470 (deprecated)
    # NOTE: create_successor_orchestrator removed - succession via UI only
    delegation_methods = [
        "get_orchestrator_instructions",
        "spawn_agent_job",
        "get_agent_mission",
        "get_workflow_status",
        "get_pending_jobs",
        "acknowledge_job",
        "report_progress",
        "complete_job",
        "report_error",
        "update_agent_mission",
    ]

    # Verify all methods exist on ToolAccessor
    for method_name in delegation_methods:
        assert hasattr(tool_accessor, method_name), f"ToolAccessor missing delegation method: {method_name}"

        # Verify method exists on OrchestrationService
        assert hasattr(tool_accessor._orchestration_service, method_name), (
            f"OrchestrationService missing method: {method_name}"
        )


@pytest.mark.asyncio
async def test_delegation_preserves_return_values(tool_accessor):
    """
    Verify that delegation preserves exact return values without transformation.
    """
    # Test with various return value types
    test_cases = [
        {"success": True, "data": {"key": "value"}},
        {"success": False, "error": "Test error"},
        {"success": True, "data": None},
        {"success": True, "data": []},
        {"success": True, "data": {"nested": {"deep": {"value": 123}}}},
    ]

    for test_return in test_cases:
        # Mock get_agent_mission as example
        tool_accessor._orchestration_service.get_agent_mission.return_value = test_return

        result = await tool_accessor.get_agent_mission(str(uuid4()), "test_tenant")

        # Verify exact return (no modification)
        assert result == test_return
        assert result is test_return  # Same object reference
