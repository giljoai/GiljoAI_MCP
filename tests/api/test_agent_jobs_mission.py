"""
Tests for Agent Job Mission Update Endpoint - Handover 0244b

Tests the PATCH /api/agent-jobs/{job_id}/mission endpoint for updating agent missions.
Covers:
- Successful mission updates
- Multi-tenant isolation
- Validation rules (required, max length)
- WebSocket event emission
- Error handling (404, 400, 422)

Following TDD principles: Tests written first (RED phase).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from src.giljo_mcp.models.agents import MCPAgentJob


@pytest.mark.asyncio
async def test_update_agent_mission_success(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test successful mission update with valid data."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-001",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Implementor",
        mission="Original mission text",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()
    await async_session.refresh(agent_job)

    # New mission text
    new_mission = "Updated mission with more detailed instructions for the agent"

    # Mock WebSocket manager to verify event emission
    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock) as mock_ws:
        # Call endpoint
        response = await async_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": new_mission},
            headers=test_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["job_id"] == agent_job.job_id
        assert data["mission"] == new_mission

        # Verify WebSocket event emitted
        mock_ws.assert_called_once()
        call_args = mock_ws.call_args
        assert call_args[0][0] == test_user.tenant_key
        assert call_args[0][1] == "agent:mission_updated"
        event_data = call_args[0][2]
        assert event_data["job_id"] == agent_job.job_id
        assert event_data["agent_type"] == "implementor"
        assert event_data["agent_name"] == "Test Implementor"
        assert event_data["mission"] == new_mission
        assert event_data["project_id"] == "test-project-001"

    # Verify database updated
    await async_session.refresh(agent_job)
    assert agent_job.mission == new_mission
    assert agent_job.updated_at is not None


@pytest.mark.asyncio
async def test_update_mission_tenant_isolation(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test that users cannot update jobs from other tenants."""
    # Create agent job for different tenant
    other_tenant_job = MCPAgentJob(
        job_id="other-tenant-job",
        tenant_key="other-tenant-key",
        project_id="other-project",
        agent_type="implementor",
        agent_name="Other Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(other_tenant_job)
    await async_session.commit()

    # Try to update job from different tenant
    response = await async_client.patch(
        f"/api/agent-jobs/{other_tenant_job.job_id}/mission",
        json={"mission": "Hacker trying to update another tenant's mission"},
        headers=test_headers,
    )

    # Should return 404 (not exposing that job exists)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_mission_validation_empty_mission(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test validation rejects empty mission."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-002",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()

    # Try to update with empty mission
    response = await async_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={"mission": ""},
        headers=test_headers,
    )

    # Should return 422 validation error
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("mission" in str(err).lower() for err in error_detail)


@pytest.mark.asyncio
async def test_update_mission_validation_too_long(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test validation rejects mission exceeding 50,000 characters."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-003",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()

    # Create mission that's too long (>50K characters)
    too_long_mission = "x" * 50001

    # Try to update with too-long mission
    response = await async_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={"mission": too_long_mission},
        headers=test_headers,
    )

    # Should return 422 validation error
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("mission" in str(err).lower() for err in error_detail)


@pytest.mark.asyncio
async def test_update_mission_validation_max_length_boundary(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test validation accepts mission at exactly 50,000 characters."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-004",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()

    # Create mission at exactly 50K characters (boundary test)
    boundary_mission = "x" * 50000

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        # Try to update with exactly 50K characters
        response = await async_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": boundary_mission},
            headers=test_headers,
        )

        # Should succeed
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["mission"]) == 50000


@pytest.mark.asyncio
async def test_update_mission_not_found(
    async_client: AsyncClient,
    test_headers,
):
    """Test updating non-existent job returns 404."""
    response = await async_client.patch(
        "/api/agent-jobs/nonexistent-job-id/mission",
        json={"mission": "New mission"},
        headers=test_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_mission_missing_field(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test request without mission field returns 422."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-005",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()

    # Try to update without mission field
    response = await async_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={},
        headers=test_headers,
    )

    # Should return 422 validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_mission_unauthorized(
    async_client: AsyncClient,
    test_user,
    async_session: AsyncSession,
):
    """Test updating mission without authentication returns 401."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-006",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()

    # Try to update without authentication headers
    response = await async_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={"mission": "Unauthorized update"},
    )

    # Should return 401 unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_mission_preserves_other_fields(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test that updating mission doesn't affect other job fields."""
    # Create test agent job with specific values
    agent_job = MCPAgentJob(
        job_id="test-job-007",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="active",
        progress=50,
        acknowledged=True,
    )
    async_session.add(agent_job)
    await async_session.commit()
    await async_session.refresh(agent_job)

    # Store original values
    original_status = agent_job.status
    original_progress = agent_job.progress
    original_acknowledged = agent_job.acknowledged
    original_created_at = agent_job.created_at

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        # Update mission
        response = await async_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": "Updated mission"},
            headers=test_headers,
        )

        assert response.status_code == 200

    # Verify other fields unchanged
    await async_session.refresh(agent_job)
    assert agent_job.status == original_status
    assert agent_job.progress == original_progress
    assert agent_job.acknowledged == original_acknowledged
    assert agent_job.created_at == original_created_at
    assert agent_job.mission == "Updated mission"


@pytest.mark.asyncio
async def test_update_mission_updates_timestamp(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test that updating mission updates the updated_at timestamp."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-008",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()
    await async_session.refresh(agent_job)

    original_updated_at = agent_job.updated_at

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        # Update mission
        response = await async_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": "Updated mission"},
            headers=test_headers,
        )

        assert response.status_code == 200

    # Verify updated_at changed
    await async_session.refresh(agent_job)
    assert agent_job.updated_at is not None
    if original_updated_at:
        assert agent_job.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_update_mission_with_special_characters(
    async_client: AsyncClient,
    test_user,
    test_headers,
    async_session: AsyncSession,
):
    """Test updating mission with special characters and unicode."""
    # Create test agent job
    agent_job = MCPAgentJob(
        job_id="test-job-009",
        tenant_key=test_user.tenant_key,
        project_id="test-project-001",
        agent_type="implementor",
        agent_name="Test Agent",
        mission="Original mission",
        status="pending",
    )
    async_session.add(agent_job)
    await async_session.commit()

    # Mission with special characters, newlines, and unicode
    special_mission = """Mission with:
    - Special chars: !@#$%^&*()
    - Unicode: 你好世界 🚀 ✅
    - Newlines and tabs:\t\t
    - Quotes: "double" and 'single'
    """

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        response = await async_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": special_mission},
            headers=test_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mission"] == special_mission

    # Verify stored correctly in database
    await async_session.refresh(agent_job)
    assert agent_job.mission == special_mission
