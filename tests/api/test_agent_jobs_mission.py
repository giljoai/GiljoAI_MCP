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
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from passlib.hash import bcrypt

from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models import User


@pytest.mark.asyncio
async def test_update_agent_mission_success(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test successful mission update with valid data."""
    # Get tenant_key from auth headers (extract from user in database)
    async with db_manager.get_session_async() as session:
        # Extract username from cookie to find user
        from sqlalchemy import select

        # We need to get the user from the auth_headers fixture context
        # For simplicity, create a test user and agent job with known tenant_key
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        # Create agent job with known tenant
        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Implementor",
            mission="Original mission text",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()
        await session.refresh(agent_job)

    # New mission text
    new_mission = "Updated mission with more detailed instructions for the agent"

    # Mock WebSocket manager to verify event emission
    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock) as mock_ws:
        # Call endpoint
        response = await api_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": new_mission},
            headers=auth_headers,
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
        # Note: tenant_key from auth_headers may differ, so we check structure
        assert call_args[0][1] == "agent:mission_updated"
        event_data = call_args[0][2]
        assert event_data["job_id"] == agent_job.job_id
        assert event_data["agent_display_name"] == "implementor"
        assert event_data["agent_name"] == "Test Implementor"
        assert event_data["mission"] == new_mission
        assert event_data["project_id"] == "test-project-001"


@pytest.mark.asyncio
async def test_update_mission_tenant_isolation(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test that users cannot update jobs from other tenants."""
    async with db_manager.get_session_async() as session:
        # Create agent job for different tenant
        other_tenant_job = AgentExecution(
            job_id="other-tenant-job",
            tenant_key="other-tenant-key-999",
            project_id="other-project",
            agent_display_name="implementor",
            agent_name="Other Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(other_tenant_job)
        await session.commit()

    # Try to update job from different tenant
    response = await api_client.patch(
        f"/api/agent-jobs/{other_tenant_job.job_id}/mission",
        json={"mission": "Hacker trying to update another tenant's mission"},
        headers=auth_headers,
    )

    # Should return 404 (not exposing that job exists)
    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_update_mission_validation_empty_mission(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test validation rejects empty mission."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()

    # Try to update with empty mission
    response = await api_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={"mission": ""},
        headers=auth_headers,
    )

    # Should return 422 validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_mission_validation_too_long(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test validation rejects mission exceeding 50,000 characters."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()

    # Create mission that's too long (>50K characters)
    too_long_mission = "x" * 50001

    # Try to update with too-long mission
    response = await api_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={"mission": too_long_mission},
        headers=auth_headers,
    )

    # Should return 422 validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_mission_validation_max_length_boundary(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test validation accepts mission at exactly 50,000 characters."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()

    # Create mission at exactly 50K characters (boundary test)
    boundary_mission = "x" * 50000

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        # Try to update with exactly 50K characters
        response = await api_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": boundary_mission},
            headers=auth_headers,
        )

        # Should succeed
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["mission"]) == 50000


@pytest.mark.asyncio
async def test_update_mission_not_found(
    api_client: AsyncClient,
    auth_headers: dict,
):
    """Test updating non-existent job returns 404."""
    response = await api_client.patch(
        "/api/agent-jobs/nonexistent-job-id/mission",
        json={"mission": "New mission"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_update_mission_missing_field(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test request without mission field returns 422."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()

    # Try to update without mission field
    response = await api_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={},
        headers=auth_headers,
    )

    # Should return 422 validation error
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_mission_unauthorized(
    api_client: AsyncClient,
    db_manager,
):
    """Test updating mission without authentication returns 401."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=f"test_tenant_{unique_id}",
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()

    # Try to update without authentication headers
    response = await api_client.patch(
        f"/api/agent-jobs/{agent_job.job_id}/mission",
        json={"mission": "Unauthorized update"},
    )

    # Should return 401 unauthorized
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_mission_preserves_other_fields(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test that updating mission doesn't affect other job fields."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        # Create test agent job with specific values
        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="working",
            progress=50,
        )
        session.add(agent_job)
        await session.commit()
        await session.refresh(agent_job)

        # Store original values
        original_status = agent_job.status
        original_progress = agent_job.progress
        original_mission_acknowledged_at = agent_job.mission_acknowledged_at
        original_created_at = agent_job.created_at

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        # Update mission
        response = await api_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": "Updated mission"},
            headers=auth_headers,
        )

        assert response.status_code == 200

    # Verify other fields unchanged
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        stmt = select(AgentExecution).where(AgentExecution.job_id == agent_job.job_id)
        result = await session.execute(stmt)
        updated_job = result.scalar_one()

        assert updated_job.status == original_status
        assert updated_job.progress == original_progress
        assert updated_job.mission_acknowledged_at == original_mission_acknowledged_at
        assert updated_job.created_at == original_created_at
        assert updated_job.mission == "Updated mission"


@pytest.mark.asyncio
async def test_update_mission_updates_timestamp(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test that updating mission updates the updated_at timestamp."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()
        await session.refresh(agent_job)

        original_updated_at = agent_job.updated_at

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        # Update mission
        response = await api_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": "Updated mission"},
            headers=auth_headers,
        )

        assert response.status_code == 200

    # Verify updated_at changed
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        stmt = select(AgentExecution).where(AgentExecution.job_id == agent_job.job_id)
        result = await session.execute(stmt)
        updated_job = result.scalar_one()

        assert updated_job.updated_at is not None
        if original_updated_at:
            assert updated_job.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_update_mission_with_special_characters(
    api_client: AsyncClient,
    auth_headers: dict,
    db_manager,
):
    """Test updating mission with special characters and unicode."""
    async with db_manager.get_session_async() as session:
        unique_id = uuid4().hex[:8]
        tenant_key = f"test_tenant_{unique_id}"

        agent_job = AgentExecution(
            job_id=f"test-job-{unique_id}",
            tenant_key=tenant_key,
            project_id="test-project-001",
            agent_display_name="implementor",
            agent_name="Test Agent",
            mission="Original mission",
            status="waiting",
        )
        session.add(agent_job)
        await session.commit()

    # Mission with special characters, newlines, and unicode
    special_mission = """Mission with:
    - Special chars: !@#$%^&*()
    - Unicode: 你好世界 🚀 ✅
    - Newlines and tabs:\t\t
    - Quotes: "double" and 'single'
    """

    with patch("api.websocket_manager.manager.emit_to_tenant", new_callable=AsyncMock):
        response = await api_client.patch(
            f"/api/agent-jobs/{agent_job.job_id}/mission",
            json={"mission": special_mission},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mission"] == special_mission

    # Verify stored correctly in database
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        stmt = select(AgentExecution).where(AgentExecution.job_id == agent_job.job_id)
        result = await session.execute(stmt)
        updated_job = result.scalar_one()
        assert updated_job.mission == special_mission
