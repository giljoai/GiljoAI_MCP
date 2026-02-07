"""
Integration test for Handover 0111 - Agent Card Real-Time Updates

Tests that spawn_agent_job broadcasts agent:created event via HTTP bridge,
enabling real-time agent card appearance without page refresh.

PRODUCTION-GRADE: Validates cross-process MCP-to-WebSocket communication
"""

import asyncio
from typing import List
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.orm import Session

from api.dependencies.websocket import WebSocketDependency
from api.websocket import WebSocketManager
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self, client_id: str, tenant_key: str):
        self.client_id = client_id
        self.tenant_key = tenant_key
        self.messages_sent: List[dict] = []
        self.is_connected = True

    async def send_json(self, data: dict):
        """Mock send_json method"""
        if not self.is_connected:
            raise RuntimeError("WebSocket disconnected")
        self.messages_sent.append(data)


@pytest.fixture
def websocket_manager():
    """Create WebSocket manager instance"""
    return WebSocketManager()


@pytest_asyncio.fixture
async def test_user_a(db_session):
    """Create test user A (tenant A)"""
    user = User(
        username=f"user_a_{uuid4().hex[:8]}",
        email=f"usera_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_a_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session, test_user_a: User):
    """Create test product"""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_user_a.tenant_key,
        name="Test Product",
        description="Test product for agent card testing",
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def seed_agent_templates(db_session, test_user_a: User, test_product: Product):
    """Seed minimal active AgentTemplates required by spawn_agent_job validation."""
    from src.giljo_mcp.models.templates import AgentTemplate

    for name in ("implementer", "tester", "analyzer"):
        db_session.add(
            AgentTemplate(
                id=str(uuid4()),
                tenant_key=test_user_a.tenant_key,
                product_id=test_product.id,
                name=name,
                system_instructions=f"Template for {name}",
                user_instructions="",
                is_active=True,
            )
        )

    await db_session.commit()


@pytest_asyncio.fixture
async def test_project_0111(db_session, test_user_a: User, test_product: Product):
    """Create test project for handover 0111 tests"""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_user_a.tenant_key,
        product_id=test_product.id,
        name="Test Project",
        description="Test project for agent card testing",
        mission="Test mission",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
class TestAgentCardRealTimeBroadcasting:
    """
    Test 1: spawn_agent_job emits via in-process WebSocketManager
    Validates loopback elimination (0379e)
    """

    async def test_spawn_agent_job_broadcasts_via_websocket_manager(
        self,
        db_session: Session,
        test_user_a: User,
        test_project_0111: Project,
        seed_agent_templates,
    ):
        """
        Verify spawn_agent_job broadcasts without HTTP loopback.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        mock_ws_manager = AsyncMock()

        with patch("api.app.state") as mock_state:
            mock_state.websocket_manager = mock_ws_manager

            # Act: Spawn agent job
            result = await spawn_agent_job(
                tenant_key=test_user_a.tenant_key,
                project_id=test_project_0111.id,
                agent_display_name="implementer",
                agent_name="implementer",
                mission="Implement authentication module",
                session=db_session,
            )

            # Assert: spawn_agent_job succeeded
            assert result["success"] is True
            assert "job_id" in result

            mock_ws_manager.broadcast_to_tenant.assert_awaited_once()
            call_kwargs = mock_ws_manager.broadcast_to_tenant.await_args.kwargs
            assert call_kwargs["tenant_key"] == test_user_a.tenant_key
            assert call_kwargs["event_type"] == "agent:created"

            payload = call_kwargs["data"]
            assert payload["project_id"] == test_project_0111.id
            assert payload["agent_display_name"] == "implementer"
            assert payload["agent_name"] == "implementer"
            assert payload["thin_client"] is True

    """
    Test 2: agent:created event broadcasts to WebSocket clients
    Validates end-to-end WebSocket event delivery
    """

    async def test_agent_created_event_broadcasts_to_clients(
        self, websocket_manager: WebSocketManager, test_user_a: User, test_project_0111: Project
    ):
        """
        PRODUCTION-GRADE: Validate agent:created event reaches frontend
        """
        # Arrange: Connect 3 WebSocket clients
        clients = []
        for i in range(3):
            client = MockWebSocket(f"client_{i}", test_user_a.tenant_key)
            websocket_manager.active_connections[f"client_{i}"] = client
            websocket_manager.auth_contexts[f"client_{i}"] = {
                "tenant_key": test_user_a.tenant_key,
                "user_id": test_user_a.id,
                "username": test_user_a.username,
            }
            clients.append(client)

        # Act: Broadcast agent:created via WebSocket dependency
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        agent_id = str(uuid4())
        event_data = {
            "project_id": test_project_0111.id,
            "agent_id": agent_id,
            "job_id": agent_id,
            "agent_display_name": "tester",
            "agent_name": "QA Tester",
            "status": "pending",
            "thin_client": True,
            "prompt_tokens": 50,
            "mission_tokens": 2000,
        }

        clients_notified = await ws_dep.broadcast_to_tenant(
            tenant_key=test_user_a.tenant_key,
            event_type="agent:created",
            data=event_data,
        )

        # Assert: All 3 clients received broadcast
        assert clients_notified == 3

        for client in clients:
            assert len(client.messages_sent) == 1
            message = client.messages_sent[0]
            assert message["type"] == "agent:created"
            assert message["data"]["agent_display_name"] == "tester"
            assert message["data"]["agent_name"] == "QA Tester"
            assert message["data"]["project_id"] == test_project_0111.id
            assert message["data"]["thin_client"] is True

    """
    Test 3: HTTP bridge endpoint emits WebSocket events
    Validates the HTTP bridge endpoint functionality
    """

    async def test_http_bridge_endpoint_emits_websocket_event(
        self, websocket_manager: WebSocketManager, test_user_a: User, test_project_0111: Project
    ):
        """
        PRODUCTION-GRADE: Validate HTTP bridge endpoint works correctly
        """
        from api.endpoints.websocket_bridge import WebSocketEventRequest, emit_websocket_event

        # Arrange: Connect WebSocket client
        client = MockWebSocket("test_client", test_user_a.tenant_key)
        websocket_manager.active_connections["test_client"] = client
        websocket_manager.auth_contexts["test_client"] = {
            "tenant_key": test_user_a.tenant_key,
            "user_id": test_user_a.id,
            "username": test_user_a.username,
        }

        # Act: Call HTTP bridge endpoint
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        request = WebSocketEventRequest(
            event_type="agent:created",
            tenant_key=test_user_a.tenant_key,
            data={
                "project_id": test_project_0111.id,
                "agent_id": str(uuid4()),
                "agent_display_name": "architect",
                "agent_name": "System Architect",
                "status": "pending",
            },
        )

        response = await emit_websocket_event(request, ws_dep)

        # Assert: Bridge succeeded
        assert response.success is True
        assert response.clients_notified == 1
        assert response.event_type == "agent:created"

        # Assert: Client received message
        assert len(client.messages_sent) == 1
        message = client.messages_sent[0]
        assert message["type"] == "agent:created"
        assert message["data"]["tenant_key"] == test_user_a.tenant_key

    """
    Test 4: Multi-tenant isolation in agent:created events
    Validates zero cross-tenant leakage
    """

    async def test_agent_created_multi_tenant_isolation(self, websocket_manager: WebSocketManager, db_session: Session):
        """
        PRODUCTION-GRADE: Security validation - zero cross-tenant leakage
        """
        # Arrange: Create two tenants
        tenant_a = f"tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid4().hex[:8]}"

        # Connect clients for both tenants
        client_a = MockWebSocket("client_a", tenant_a)
        client_b = MockWebSocket("client_b", tenant_b)

        websocket_manager.active_connections["client_a"] = client_a
        websocket_manager.auth_contexts["client_a"] = {"tenant_key": tenant_a}

        websocket_manager.active_connections["client_b"] = client_b
        websocket_manager.auth_contexts["client_b"] = {"tenant_key": tenant_b}

        # Act: Broadcast agent:created to tenant A only
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        await ws_dep.broadcast_to_tenant(
            tenant_key=tenant_a,
            event_type="agent:created",
            data={
                "project_id": str(uuid4()),
                "agent_id": str(uuid4()),
                "agent_display_name": "implementer",
                "agent_name": "Backend Implementer",
                "status": "pending",
            },
        )

        # Assert: Only tenant A received event
        assert len(client_a.messages_sent) == 1
        assert len(client_b.messages_sent) == 0  # Tenant B should NOT receive

        # Assert: Message content correct
        assert client_a.messages_sent[0]["type"] == "agent:created"

    """
    Test 5: WebSocket broadcast handles errors gracefully
    Validates loopback elimination resilience (0379e)
    """

    async def test_spawn_agent_job_handles_broadcast_errors_gracefully(
        self,
        db_session: Session,
        test_user_a: User,
        test_project_0111: Project,
        seed_agent_templates,
    ):
        """
        Validate WebSocket broadcast errors don't crash agent spawning.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        mock_ws_manager = AsyncMock()
        mock_ws_manager.broadcast_to_tenant.side_effect = RuntimeError("WebSocket send failed")

        with patch("api.app.state") as mock_state:
            mock_state.websocket_manager = mock_ws_manager

            # Act: Spawn agent job (should succeed despite bridge error)
            result = await spawn_agent_job(
                tenant_key=test_user_a.tenant_key,
                project_id=test_project_0111.id,
                agent_display_name="tester",
                agent_name="tester",
                mission="Run integration tests",
                session=db_session,
            )

            # Assert: spawn_agent_job succeeded (bridge error logged but not fatal)
            assert result["success"] is True
            assert "job_id" in result

            # Assert: Agent job was created in database
            job_id = result["job_id"]
            from sqlalchemy import select

            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            result_query = await db_session.execute(stmt)
            agent_job = result_query.scalar_one_or_none()
            assert agent_job is not None
            assert agent_job.agent_display_name == "tester"
            assert agent_job.status in {"waiting", "working", "complete", "failed", "cancelled", "decommissioned"}

    """
    Test 6: Broadcast errors do not hang
    """

    async def test_spawn_agent_job_does_not_hang_on_broadcast_failure(
        self,
        db_session: Session,
        test_user_a: User,
        test_project_0111: Project,
        seed_agent_templates,
    ):
        """
        Validate the spawn path returns promptly even if broadcasting fails.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        mock_ws_manager = AsyncMock()
        mock_ws_manager.broadcast_to_tenant.side_effect = RuntimeError("WebSocket send failed")

        with patch("api.app.state") as mock_state:
            mock_state.websocket_manager = mock_ws_manager

            start_time = asyncio.get_event_loop().time()

            result = await spawn_agent_job(
                tenant_key=test_user_a.tenant_key,
                project_id=test_project_0111.id,
                agent_display_name="analyzer",
                agent_name="analyzer",
                mission="Analyze codebase",
                session=db_session,
            )

            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            assert duration < 2

            # Assert: spawn_agent_job succeeded despite broadcast failure
            assert result["success"] is True

    """
    Test 7: Agent cards appear without refresh
    Validates the user-facing fix
    """

    async def test_agent_cards_appear_without_refresh(
        self, websocket_manager: WebSocketManager, test_user_a: User, test_project_0111: Project
    ):
        """
        PRODUCTION-GRADE: Simulate user workflow - agent cards appear in real-time
        """
        # Arrange: User has dashboard open (WebSocket connected)
        client = MockWebSocket("user_dashboard", test_user_a.tenant_key)
        websocket_manager.active_connections["user_dashboard"] = client
        websocket_manager.auth_contexts["user_dashboard"] = {
            "tenant_key": test_user_a.tenant_key,
            "user_id": test_user_a.id,
            "username": test_user_a.username,
        }

        # Act: User clicks "Stage Project" - orchestrator spawns agents
        # Simulate orchestrator spawning 3 agents
        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        agents = [
            ("architect", "System Architect"),
            ("implementer", "Backend Implementer"),
            ("tester", "QA Tester"),
        ]

        for agent_display_name, agent_name in agents:
            await ws_dep.broadcast_to_tenant(
                tenant_key=test_user_a.tenant_key,
                event_type="agent:created",
                data={
                    "project_id": test_project_0111.id,
                    "agent_id": str(uuid4()),
                    "agent_display_name": agent_display_name,
                    "agent_name": agent_name,
                    "status": "pending",
                },
            )

        # Assert: User's dashboard received all 3 agent:created events
        assert len(client.messages_sent) == 3

        # Assert: Events are in order
        assert client.messages_sent[0]["data"]["agent_display_name"] == "architect"
        assert client.messages_sent[1]["data"]["agent_display_name"] == "implementer"
        assert client.messages_sent[2]["data"]["agent_display_name"] == "tester"

        # Assert: All events have correct structure
        for message in client.messages_sent:
            assert message["type"] == "agent:created"
            assert "timestamp" in message
            assert message["data"]["project_id"] == test_project_0111.id


@pytest.mark.asyncio
class TestHttpBridgeEdgeCases:
    """Edge cases and error scenarios for HTTP bridge"""

    async def test_http_bridge_missing_websocket_manager(self, test_user_a: User):
        """
        Validate graceful handling when WebSocket manager unavailable
        """
        from api.endpoints.websocket_bridge import WebSocketEventRequest, emit_websocket_event

        # Act: Call bridge with no WebSocket manager
        ws_dep = WebSocketDependency(websocket_manager=None)

        request = WebSocketEventRequest(
            event_type="agent:created",
            tenant_key=test_user_a.tenant_key,
            data={"agent_id": str(uuid4())},
        )

        response = await emit_websocket_event(request, ws_dep)

        # Assert: Returns failure (doesn't crash)
        assert response.success is False
        assert response.clients_notified == 0
        assert "not available" in response.message.lower()

    async def test_http_bridge_invalid_event_type(self, websocket_manager: WebSocketManager, test_user_a: User):
        """
        Validate error handling for invalid event types
        """
        from fastapi import HTTPException

        from api.endpoints.websocket_bridge import WebSocketEventRequest, emit_websocket_event

        ws_dep = WebSocketDependency(websocket_manager=websocket_manager)

        request = WebSocketEventRequest(
            event_type="",  # Empty event type
            tenant_key=test_user_a.tenant_key,
            data={},
        )

        # Act & Assert: Should raise validation error
        with pytest.raises(HTTPException) as exc_info:
            await emit_websocket_event(request, ws_dep)

        assert exc_info.value.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
