"""
WebSocket Event Tests for Mission Tracking - Updated for simplified job signaling

Tests verify that WebSocket events are emitted when:
1. mission_acknowledged_at is set (orchestrator/agent fetches mission)

Multi-tenant isolation is CRITICAL - events must only broadcast to the correct tenant.

Note: This file has been updated to reflect the removal of mission_read_at and
the acknowledged boolean. Only mission_acknowledged_at remains.

Backend Integration Tester Agent - GiljoAI MCP
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.websocket import WebSocketManager
from src.giljo_mcp.models import AgentExecution, Product, Project
from src.giljo_mcp.services.agent_job_manager import AgentJobManager


@pytest.fixture
def tenant_key() -> str:
    """Provide test tenant key"""
    return "test-tenant-mission-tracking"


@pytest.fixture
async def mock_websocket_manager():
    """Mock WebSocketManager for testing broadcasts"""
    manager = MagicMock(spec=WebSocketManager)
    manager.broadcast_to_tenant = AsyncMock(return_value=1)  # Returns sent_count
    return manager


@pytest.fixture
async def test_project(db_session: AsyncSession, tenant_key: str):
    """Create test project"""
    product = Product(
        id="test-product-123",
        name="Test Product",
        tenant_key=tenant_key,
        description="Test product for mission tracking",
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        id="test-project-123",
        name="Test Project",
        tenant_key=tenant_key,
        product_id=product.id,
        description="Test project for mission tracking",
        mission="Test mission for mission tracking tests",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest.fixture
async def test_orchestrator(db_session: AsyncSession, test_project: Project, tenant_key: str):
    """Create test orchestrator job"""
    orchestrator = AgentExecution(
        job_id="orch-test-123",
        tenant_key=tenant_key,
        project_id=test_project.id,
        agent_display_name="orchestrator",
        mission="Test mission",
        agent_name="Test Orchestrator",
        status="waiting",
        mission_acknowledged_at=None,  # Not yet acknowledged
    )
    db_session.add(orchestrator)
    await db_session.commit()
    return orchestrator


# ==============================================================================
# TEST: mission_acknowledged_at Auto-Setting
# ==============================================================================


@pytest.mark.asyncio
async def test_mission_acknowledged_at_set_by_get_orchestrator_instructions(
    db_session: AsyncSession, test_orchestrator: AgentExecution, tenant_key: str, db_manager
):
    """
    Test that get_orchestrator_instructions() auto-sets mission_acknowledged_at.

    Expected behavior:
    - When orchestrator first fetches mission, mission_acknowledged_at should be set to current UTC time
    - Subsequent fetches should NOT update the timestamp (idempotent)

    Note: WebSocket events are tested separately - this focuses on the field update.
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Setup: Ensure mission not yet acknowledged
    assert test_orchestrator.mission_acknowledged_at is None

    # Action: Fetch orchestrator instructions (should set mission_acknowledged_at)
    result = await get_orchestrator_instructions(
        orchestrator_id=test_orchestrator.job_id, tenant_key=tenant_key, db_manager=db_manager
    )

    # Verify: Result is valid
    assert "error" not in result
    assert result["orchestrator_id"] == test_orchestrator.job_id

    # Refresh job from database
    await db_session.refresh(test_orchestrator)

    # Assert: mission_acknowledged_at should now be set
    assert test_orchestrator.mission_acknowledged_at is not None, (
        "mission_acknowledged_at should be set after first fetch"
    )
    assert isinstance(test_orchestrator.mission_acknowledged_at, datetime)

    first_ack_time = test_orchestrator.mission_acknowledged_at

    # Second fetch should NOT update timestamp
    result2 = await get_orchestrator_instructions(
        orchestrator_id=test_orchestrator.job_id, tenant_key=tenant_key, db_manager=db_manager
    )

    assert "error" not in result2
    await db_session.refresh(test_orchestrator)

    # Assert: mission_acknowledged_at should NOT change (idempotent)
    assert test_orchestrator.mission_acknowledged_at == first_ack_time, (
        "mission_acknowledged_at should not update on subsequent fetches"
    )


# ==============================================================================
# TEST: mission_acknowledged_at WebSocket Event Emission
# ==============================================================================


@pytest.mark.asyncio
async def test_mission_acknowledged_event_emitted_when_status_becomes_working(
    db_session: AsyncSession, test_project: Project, tenant_key: str, mock_websocket_manager: MagicMock, db_manager
):
    """
    RED TEST: Verify WebSocket event is emitted when job transitions to 'working'.

    This test FAILS initially because:
    - AgentJobManager.update_status() doesn't set mission_acknowledged_at yet
    - No WebSocket broadcast_to_tenant() call for 'job:mission_acknowledged'

    Expected behavior:
    - When job status changes from 'pending' -> 'working', set mission_acknowledged_at
    - WebSocket event 'job:mission_acknowledged' should be broadcasted to tenant
    - Event payload should include job_id, mission_acknowledged_at, timestamp

    Multi-tenant isolation:
    - Event must use broadcast_to_tenant (NOT broadcast)
    - Only clients with matching tenant_key should receive event
    """
    # Create pending agent job
    agent_job = AgentExecution(
        job_id="agent-test-456",
        tenant_key=tenant_key,
        project_id=test_project.id,
        agent_display_name="implementer",
        mission="Test mission",
        agent_name="Test Implementer",
        status="waiting",
        mission_acknowledged_at=None,
    )
    db_session.add(agent_job)
    await db_session.commit()

    # Setup AgentJobManager
    job_manager = AgentJobManager(db_manager)

    # Patch WebSocket manager
    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_websocket_manager

        # Action: Update status to 'working' (simulating agent acknowledging mission)
        await job_manager.update_status(job_id=agent_job.job_id, new_status="working", tenant_key=tenant_key)

        # Refresh job from database
        await db_session.refresh(agent_job)

        # Assert: mission_acknowledged_at should be set
        assert agent_job.mission_acknowledged_at is not None, (
            "mission_acknowledged_at should be set when status becomes 'working'"
        )
        assert isinstance(agent_job.mission_acknowledged_at, datetime)

        # Assert: WebSocket broadcast_to_tenant was called
        mock_websocket_manager.broadcast_to_tenant.assert_called()

        # Verify broadcast call for mission_acknowledged event
        calls = mock_websocket_manager.broadcast_to_tenant.call_args_list
        mission_ack_call = None
        for call in calls:
            kwargs = call.kwargs
            if kwargs.get("event_type") == "job:mission_acknowledged":
                mission_ack_call = kwargs
                break

        assert mission_ack_call is not None, "job:mission_acknowledged event should be emitted"

        # Verify event structure
        assert mission_ack_call["tenant_key"] == tenant_key
        event_data = mission_ack_call["data"]
        assert event_data["job_id"] == agent_job.job_id
        assert "mission_acknowledged_at" in event_data
        assert "timestamp" in event_data


@pytest.mark.asyncio
async def test_mission_acknowledged_event_not_emitted_for_other_status_transitions(
    db_session: AsyncSession, test_project: Project, tenant_key: str, mock_websocket_manager: MagicMock, db_manager
):
    """
    RED TEST: Verify mission_acknowledged event is ONLY emitted for 'working' status.

    Other status transitions (pending->failed, working->completed, etc.) should NOT
    emit job:mission_acknowledged events.
    """
    # Create pending agent job
    agent_job = AgentExecution(
        job_id="agent-test-789",
        tenant_key=tenant_key,
        project_id=test_project.id,
        agent_display_name="tester",
        mission="Test mission",
        agent_name="Test Tester",
        status="waiting",
        mission_acknowledged_at=None,
    )
    db_session.add(agent_job)
    await db_session.commit()

    # Setup AgentJobManager
    job_manager = AgentJobManager(db_manager)

    # Patch WebSocket manager
    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_websocket_manager

        # Action: Update status to 'failed' (NOT 'working')
        await job_manager.update_status(job_id=agent_job.job_id, new_status="failed", tenant_key=tenant_key)

        # Refresh job from database
        await db_session.refresh(agent_job)

        # Assert: mission_acknowledged_at should NOT be set
        assert agent_job.mission_acknowledged_at is None, (
            "mission_acknowledged_at should only be set for 'working' status"
        )

        # Assert: job:mission_acknowledged event should NOT be emitted
        if mock_websocket_manager.broadcast_to_tenant.called:
            for call in mock_websocket_manager.broadcast_to_tenant.call_args_list:
                kwargs = call.kwargs
                assert kwargs.get("event_type") != "job:mission_acknowledged", (
                    "job:mission_acknowledged should not be emitted for non-working status"
                )


# ==============================================================================
# TEST: Multi-Tenant Isolation
# ==============================================================================


@pytest.mark.asyncio
async def test_mission_tracking_events_scoped_to_tenant(
    db_session: AsyncSession, mock_websocket_manager: MagicMock, db_manager
):
    """
    RED TEST: Verify WebSocket events are tenant-scoped (CRITICAL for security).

    Two tenants with separate projects:
    - Tenant A: orch-tenant-a-123
    - Tenant B: orch-tenant-b-456

    When Tenant A fetches mission:
    - WebSocket event should ONLY be sent to Tenant A (tenant_key='tenant-a')
    - Tenant B should NOT receive any events

    This prevents data leakage across tenants.
    """
    # Create two separate tenants with orchestrators
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    # Tenant A: Product + Project + Orchestrator
    product_a = Product(id="product-a", name="Product A", tenant_key=tenant_a)
    project_a = Project(
        id="project-a",
        name="Project A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        mission="Tenant A mission",
        status="active",
    )
    orch_a = AgentExecution(
        job_id="orch-a",
        tenant_key=tenant_a,
        project_id=project_a.id,
        agent_display_name="orchestrator",
        agent_name="Orch A",
        mission="Tenant A orch mission",
        status="waiting",
    )

    # Tenant B: Product + Project + Orchestrator
    product_b = Product(id="product-b", name="Product B", tenant_key=tenant_b)
    project_b = Project(
        id="project-b",
        name="Project B",
        tenant_key=tenant_b,
        product_id=product_b.id,
        mission="Tenant B mission",
        status="active",
    )
    orch_b = AgentExecution(
        job_id="orch-b",
        tenant_key=tenant_b,
        project_id=project_b.id,
        agent_display_name="orchestrator",
        agent_name="Orch B",
        mission="Tenant B orch mission",
        status="waiting",
    )

    db_session.add_all([product_a, project_a, orch_a, product_b, project_b, orch_b])
    await db_session.commit()

    # Patch WebSocket manager
    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_websocket_manager

        # Action: Tenant A fetches mission
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        result = await get_orchestrator_instructions(
            orchestrator_id=orch_a.job_id, tenant_key=tenant_a, db_manager=db_manager
        )

        # Verify: Result is valid
        assert "error" not in result

        # Assert: WebSocket broadcast was called
        mock_websocket_manager.broadcast_to_tenant.assert_called()

        # Verify: ALL broadcast calls used tenant_a (NOT tenant_b)
        for call in mock_websocket_manager.broadcast_to_tenant.call_args_list:
            kwargs = call.kwargs
            assert kwargs["tenant_key"] == tenant_a, f"Event should be scoped to {tenant_a}, got {kwargs['tenant_key']}"

            # Additional check: Verify tenant_b is NEVER used
            assert kwargs["tenant_key"] != tenant_b, f"Event MUST NOT be sent to {tenant_b}"


# ==============================================================================
# TEST: Event Payload Structure
# ==============================================================================


@pytest.mark.asyncio
async def test_mission_acknowledged_event_has_correct_payload_structure(
    db_session: AsyncSession, test_project: Project, tenant_key: str, mock_websocket_manager: MagicMock, db_manager
):
    """
    RED TEST: Verify job:mission_acknowledged event has correct payload structure.

    Required fields:
    - job_id: str (UUID)
    - mission_acknowledged_at: str (ISO-formatted timestamp)
    - timestamp: str (ISO-formatted current time)
    """
    # Create agent job
    agent_job = AgentExecution(
        job_id="agent-payload-test",
        tenant_key=tenant_key,
        project_id=test_project.id,
        agent_display_name="implementer",
        mission="Test mission",
        agent_name="Test Agent",
        status="waiting",
        mission_acknowledged_at=None,
    )
    db_session.add(agent_job)
    await db_session.commit()

    from giljo_mcp.database import DatabaseManager

    db_manager = DatabaseManager()
    job_manager = AgentJobManager(db_manager)

    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_websocket_manager

        # Update status to working
        await job_manager.update_status(job_id=agent_job.job_id, new_status="working", tenant_key=tenant_key)

        # Find job:mission_acknowledged call
        mission_ack_call = None
        for call in mock_websocket_manager.broadcast_to_tenant.call_args_list:
            kwargs = call.kwargs
            if kwargs.get("event_type") == "job:mission_acknowledged":
                mission_ack_call = kwargs
                break

        assert mission_ack_call is not None
        event_data = mission_ack_call["data"]

        # Assert: Required fields exist
        assert "job_id" in event_data
        assert "mission_acknowledged_at" in event_data
        assert "timestamp" in event_data

        # Assert: job_id is correct
        assert event_data["job_id"] == agent_job.job_id

        # Assert: Timestamps are ISO-formatted strings
        from datetime import datetime

        try:
            datetime.fromisoformat(event_data["mission_acknowledged_at"])
            datetime.fromisoformat(event_data["timestamp"])
        except (ValueError, TypeError):
            pytest.fail("Timestamps must be ISO-8601 formatted strings")
