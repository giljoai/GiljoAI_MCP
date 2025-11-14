"""
Tests for POST /api/v1/orchestration/launch-project endpoint (Handover 0109).

This endpoint transitions projects from staging to execution phase.

TDD Principles:
1. Write comprehensive tests first (this file)
2. Run tests (expect failures - endpoint doesn't exist yet)
3. Implement endpoint in api/endpoints/orchestration.py
4. Run tests again (expect all pass)

Test Coverage:
- Success case: Valid project with mission and spawned agents
- Error case: Project not found (404)
- Error case: Project missing mission (400)
- Error case: No agents spawned (400)
- Error case: Multi-tenant isolation (404)
- WebSocket broadcasting verification
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import status
from sqlalchemy import select


@pytest.fixture
async def test_user(test_db):
    """Create a test user with tenant_key."""
    from src.giljo_mcp.models import User

    unique_suffix = uuid4().hex[:8]
    user = User(
        id=str(uuid4()),
        tenant_key=f"test_tenant_{unique_suffix}",
        username=f"test_user_{unique_suffix}",
        email=f"test_{unique_suffix}@example.com",
        password_hash="hashed_password",
        is_active=True,
    )

    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    return user


@pytest.fixture
async def test_product(test_db, test_user):
    """Create a test product."""
    from src.giljo_mcp.models import Product

    product = Product(
        id=str(uuid4()),
        tenant_key=test_user.tenant_key,
        name="Test Product",
        description="Test product description",
        is_active=True,
    )

    test_db.add(product)
    await test_db.commit()
    await test_db.refresh(product)

    return product


@pytest.fixture
async def test_project_with_mission(test_db, test_user, test_product):
    """Create a test project with mission ready for launch."""
    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid4()),
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        name="Test Project",
        description="User requirements for the project",
        mission="Detailed mission plan created by orchestrator during staging",
        status="active",
        staging_status="staged",  # Staged = ready to launch
    )

    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)

    return project


@pytest.fixture
async def test_project_no_mission(test_db, test_user, test_product):
    """Create a test project WITHOUT mission (invalid state)."""
    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid4()),
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        name="Project Without Mission",
        description="User requirements",
        mission="",  # Empty mission - not ready
        status="active",
        staging_status=None,
    )

    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)

    return project


@pytest.fixture
async def spawned_agents(test_db, test_user, test_project_with_mission):
    """Create MCPAgentJob records (spawned agents in waiting state)."""
    from src.giljo_mcp.models import MCPAgentJob

    agents = []

    agent_types = [
        ("orchestrator", "Orchestrator", "Coordinate team during execution phase"),
        ("analyzer", "Requirements Analyst", "Analyze technical requirements"),
        ("implementer", "Backend Developer", "Implement REST API endpoints"),
        ("tester", "QA Engineer", "Write and execute test cases"),
    ]

    for agent_type, agent_name, mission in agent_types:
        agent = MCPAgentJob(
            tenant_key=test_user.tenant_key,
            project_id=test_project_with_mission.id,
            job_id=str(uuid4()),
            agent_type=agent_type,
            agent_name=agent_name,
            mission=mission,
            status="waiting",  # Ready to be launched
            tool_type="universal",
            progress=0,
            acknowledged=False,
        )

        test_db.add(agent)
        agents.append(agent)

    await test_db.commit()

    for agent in agents:
        await test_db.refresh(agent)

    return agents


class TestLaunchProjectEndpoint:
    """Tests for POST /api/v1/orchestration/launch-project endpoint."""

    @pytest.mark.asyncio
    async def test_launch_project_success(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_with_mission,
        spawned_agents,
    ):
        """Test successful project launch with all prerequisites met."""
        project_id = str(test_project_with_mission.id)

        # Make request
        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": project_id},
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert data["success"] is True
        assert data["project_id"] == project_id
        assert data["staging_status"] in ["launching", "active"]
        assert data["agent_count"] == 4
        assert len(data["agents"]) == 4

        # Verify agent data structure
        for agent in data["agents"]:
            assert "agent_id" in agent
            assert "agent_type" in agent
            assert "agent_name" in agent
            assert "status" in agent
            assert "mission" in agent

        # Verify database was updated
        from src.giljo_mcp.models import Project

        stmt = select(Project).where(Project.id == project_id)
        result = await test_db.execute(stmt)
        updated_project = result.scalar_one_or_none()

        assert updated_project is not None
        assert updated_project.staging_status == "launching"

    @pytest.mark.asyncio
    async def test_launch_project_not_found(
        self,
        authenticated_client,
        test_db,
        test_user,
    ):
        """Test 404 error when project doesn't exist."""
        non_existent_id = str(uuid4())

        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": non_existent_id},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_launch_project_missing_mission(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_no_mission,
    ):
        """Test 400 error when project has no mission."""
        project_id = str(test_project_no_mission.id)

        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": project_id},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "mission" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_launch_project_no_agents(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_with_mission,
    ):
        """Test 400 error when no agents are spawned."""
        project_id = str(test_project_with_mission.id)

        # Project has mission but NO agents spawned
        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": project_id},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "agent" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_launch_project_tenant_isolation(
        self,
        test_db,
        test_user,
        test_project_with_mission,
        spawned_agents,
    ):
        """Test multi-tenant isolation (different tenant can't launch)."""
        from src.giljo_mcp.models import User
        from fastapi.testclient import TestClient
        from api.app import app

        # Create user in DIFFERENT tenant
        other_user = User(
            id=str(uuid4()),
            tenant_key="other-tenant-999",  # Different tenant
            username="other_user",
            email="other@example.com",
            password_hash="hashed",
            is_active=True,
        )

        test_db.add(other_user)
        await test_db.commit()

        # Mock authentication for other user
        with patch("api.dependencies.auth.get_current_active_user", return_value=other_user):
            client = TestClient(app)

            response = client.post(
                "/api/v1/orchestration/launch-project",
                json={"project_id": str(test_project_with_mission.id)},
            )

            # Should return 404 (not 403) to prevent tenant enumeration
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_launch_project_websocket_broadcast(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_with_mission,
        spawned_agents,
    ):
        """Test that WebSocket event is broadcasted on successful launch."""
        from unittest.mock import MagicMock

        # Mock WebSocket manager
        mock_ws_manager = MagicMock()
        mock_ws_manager.broadcast_to_tenant = AsyncMock(return_value=1)

        # Inject mock WebSocket manager
        with patch("api.dependencies.websocket.get_websocket_manager", return_value=mock_ws_manager):
            response = await authenticated_client.post(
                "/api/v1/orchestration/launch-project",
                json={"project_id": str(test_project_with_mission.id)},
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify WebSocket broadcast was called
            mock_ws_manager.broadcast_to_tenant.assert_called_once()
            call_args = mock_ws_manager.broadcast_to_tenant.call_args

            # Verify broadcast parameters
            assert call_args.kwargs["tenant_key"] == test_user.tenant_key
            assert call_args.kwargs["event_type"] == "project:launched"
            assert "project_id" in call_args.kwargs["data"]

    @pytest.mark.asyncio
    async def test_launch_project_validation_request_format(
        self,
        authenticated_client,
        test_db,
    ):
        """Test validation of request format."""
        # Missing project_id
        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid project_id format
        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": "not-a-uuid"},
        )

        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_launch_project_idempotency(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_with_mission,
        spawned_agents,
    ):
        """Test that launching same project twice is handled gracefully."""
        project_id = str(test_project_with_mission.id)

        # First launch
        response1 = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": project_id},
        )

        assert response1.status_code == status.HTTP_200_OK

        # Second launch (should also succeed or return 409 Conflict)
        response2 = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": project_id},
        )

        # Either 200 (idempotent) or 409 (already launched)
        assert response2.status_code in [status.HTTP_200_OK, status.HTTP_409_CONFLICT]


class TestLaunchProjectAgentStatusUpdates:
    """Tests for optional agent status updates during launch."""

    @pytest.mark.asyncio
    async def test_agent_status_transitions(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_with_mission,
        spawned_agents,
    ):
        """Test that agent statuses can be updated during launch."""
        project_id = str(test_project_with_mission.id)

        # Verify agents start in "waiting" state
        from src.giljo_mcp.models import MCPAgentJob

        stmt = select(MCPAgentJob).where(MCPAgentJob.project_id == project_id)
        result = await test_db.execute(stmt)
        agents_before = result.scalars().all()

        assert all(agent.status == "waiting" for agent in agents_before)

        # Launch project
        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": project_id},
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify agents are still in valid state (waiting or preparing)
        result = await test_db.execute(stmt)
        agents_after = result.scalars().all()

        for agent in agents_after:
            assert agent.status in ["waiting", "preparing", "active"]


class TestLaunchProjectEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_launch_project_deleted_project(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_product,
    ):
        """Test that soft-deleted projects cannot be launched."""
        from src.giljo_mcp.models import Project

        # Create soft-deleted project
        deleted_project = Project(
            id=str(uuid4()),
            tenant_key=test_user.tenant_key,
            product_id=test_product.id,
            name="Deleted Project",
            description="Test",
            mission="Mission exists but project is deleted",
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )

        test_db.add(deleted_project)
        await test_db.commit()

        response = await authenticated_client.post(
            "/api/v1/orchestration/launch-project",
            json={"project_id": str(deleted_project.id)},
        )

        # Should return 404 (project not found when deleted)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_launch_project_concurrent_requests(
        self,
        authenticated_client,
        test_db,
        test_user,
        test_project_with_mission,
        spawned_agents,
    ):
        """Test handling of concurrent launch requests (race condition)."""
        import asyncio

        project_id = str(test_project_with_mission.id)

        # Simulate concurrent requests
        responses = await asyncio.gather(
            authenticated_client.post(
                "/api/v1/orchestration/launch-project",
                json={"project_id": project_id},
            ),
            authenticated_client.post(
                "/api/v1/orchestration/launch-project",
                json={"project_id": project_id},
            ),
            return_exceptions=True,
        )

        # At least one should succeed
        success_count = sum(1 for r in responses if r.status_code == status.HTTP_200_OK)
        assert success_count >= 1


# Pytest configuration
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]
