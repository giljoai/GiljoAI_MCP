"""
Integration Test: Message WebSocket Recipient Counters (Handover 0294)

Tests that message:received events properly update recipient agent counters.

TDD Workflow:
1. Write test (this file) - EXPECT IT TO FAIL
2. Run test and observe failure
3. Fix the bug
4. Verify test passes
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from api.websocket import WebSocketManager
from src.giljo_mcp.services.message_service import MessageService


class TestMessageWebSocketRecipientCounters:
    """Test suite for message:received WebSocket events"""

    @pytest.fixture
    def tenant_key(self):
        """Generate a unique tenant key for test isolation"""
        return str(uuid4())

    @pytest.fixture
    def project_id(self):
        """Generate a unique project ID"""
        return str(uuid4())

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocket manager"""
        manager = MagicMock(spec=WebSocketManager)
        manager.broadcast_message_sent = AsyncMock()
        manager.broadcast_message_received = AsyncMock()
        return manager

    @pytest.fixture
    async def message_service(self, db_manager, mock_websocket_manager):
        """Create MessageService with mocked WebSocket manager"""
        from src.giljo_mcp.tenant import TenantManager

        tenant_manager = TenantManager()
        service = MessageService(
            db_manager=db_manager, tenant_manager=tenant_manager, websocket_manager=mock_websocket_manager
        )

        return service

    @pytest.mark.asyncio
    async def test_broadcast_message_received_sends_to_all_recipients(
        self, message_service, mock_websocket_manager, test_project
    ):
        """
        Test: broadcast_message_received() is called with correct recipient job_ids

        EXPECTED BEHAVIOR:
        - When sending a broadcast message (to_agents=['all'])
        - Backend fetches ALL agent job_ids from database
        - Backend calls broadcast_message_received() with recipient_job_ids
        - WebSocket manager broadcasts to all connected clients

        ASSERTION:
        - broadcast_message_received() called with list of job_ids
        - to_agent_ids parameter contains expected job_ids
        """
        # Setup: Create test agents in database
        from src.giljo_mcp import models

        project_id = test_project.id
        tenant_key = test_project.tenant_key

        async with message_service.db_manager.get_session_async() as session:
            # Create 3 recipient agents
            recipient_job_ids = [str(uuid4()) for _ in range(3)]
            for i, job_id in enumerate(recipient_job_ids):
                agent = models.AgentExecution(
                    tenant_key=tenant_key,
                    project_id=project_id,
                    job_id=job_id,
                    agent_display_name="implementer",
                    agent_name=f"implementer-{i + 1}",
                    mission=f"Test mission {i + 1}",
                    status="waiting",
                    progress=0,
                    tool_type="claude-code",
                )
                session.add(agent)

            await session.commit()

        # Action: Send broadcast message
        result = await message_service.send_message(
            to_agents=["all"],
            content="Test broadcast message",
            project_id=project_id,
            message_type="broadcast",
            priority="normal",
            from_agent="orchestrator",
        )

        # Assert: Message sent successfully
        assert result["success"] is True
        assert "message_id" in result

        # Assert: broadcast_message_received() was called
        mock_websocket_manager.broadcast_message_received.assert_called_once()

        # Assert: Called with correct recipient job_ids
        call_kwargs = mock_websocket_manager.broadcast_message_received.call_args.kwargs
        assert "to_agent_ids" in call_kwargs

        actual_recipients = call_kwargs["to_agent_ids"]
        assert len(actual_recipients) == 3, f"Expected 3 recipients, got {len(actual_recipients)}"

        # Assert: All recipient job_ids present
        for job_id in recipient_job_ids:
            assert job_id in actual_recipients, f"job_id {job_id} not in recipients"

        print(f"[PASS] Test passed: broadcast_message_received called with {len(actual_recipients)} recipients")

    @pytest.mark.asyncio
    async def test_websocket_manager_broadcasts_to_all_clients(self, tenant_key):
        """
        Test: WebSocket manager actually broadcasts to all connected clients

        EXPECTED BEHAVIOR:
        - broadcast_message_received() sends message to ALL clients in tenant
        - Multi-tenant isolation prevents cross-tenant leakage

        ASSERTION:
        - All clients in same tenant receive the event
        - Clients in different tenants do NOT receive the event
        """
        # Setup: Create WebSocket manager with mock clients
        ws_manager = WebSocketManager()

        # Mock 3 clients in same tenant
        mock_clients = {}
        for i in range(3):
            client_id = f"client-{i}"
            mock_ws = AsyncMock()
            mock_ws.send_json = AsyncMock()

            ws_manager.active_connections[client_id] = mock_ws
            ws_manager.auth_contexts[client_id] = {"tenant_key": tenant_key}
            mock_clients[client_id] = mock_ws

        # Mock 1 client in different tenant (should NOT receive)
        other_tenant_client = "client-other"
        other_ws = AsyncMock()
        other_ws.send_json = AsyncMock()
        ws_manager.active_connections[other_tenant_client] = other_ws
        ws_manager.auth_contexts[other_tenant_client] = {"tenant_key": "other-tenant"}

        # Action: Broadcast message
        await ws_manager.broadcast_message_received(
            message_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=["agent-1", "agent-2", "agent-3"],
            message_type="broadcast",
            content_preview="Test message",
            priority=1,
            project_id=str(uuid4()),
        )

        # Assert: All same-tenant clients received the event
        for client_id, mock_ws in mock_clients.items():
            mock_ws.send_json.assert_called_once()
            call_args = mock_ws.send_json.call_args[0][0]

            assert call_args["type"] == "message:received"
            assert call_args["data"]["to_agent_ids"] == ["agent-1", "agent-2", "agent-3"]
            print(f"[PASS] Client {client_id} received message:received event")

        # Assert: Other tenant client did NOT receive the event
        other_ws.send_json.assert_not_called()
        print("[PASS] Multi-tenant isolation verified")

    @pytest.mark.asyncio
    async def test_direct_message_sends_to_single_recipient(
        self, message_service, mock_websocket_manager, test_project
    ):
        """
        Test: Direct messages send to single recipient, not all agents

        EXPECTED BEHAVIOR:
        - When sending direct message (to_agents=['specific-agent'])
        - Backend sends to_agent_ids with single job_id
        - Only that recipient's counter increments

        ASSERTION:
        - to_agent_ids contains only the specified recipient
        """
        # Setup: Create test agents
        from src.giljo_mcp import models

        project_id = test_project.id
        tenant_key = test_project.tenant_key

        async with message_service.db_manager.get_session_async() as session:
            # Create 2 agents
            agent1_job_id = str(uuid4())
            agent2_job_id = str(uuid4())

            for i, (job_id, name) in enumerate([(agent1_job_id, "agent-1"), (agent2_job_id, "agent-2")]):
                agent = models.AgentExecution(
                    tenant_key=tenant_key,
                    project_id=project_id,
                    job_id=job_id,
                    agent_display_name="implementer",
                    agent_name=name,
                    mission="Test mission",
                    status="waiting",
                    progress=0,
                    tool_type="claude-code",
                )
                session.add(agent)

            await session.commit()

        # Action: Send direct message to agent-1 only
        result = await message_service.send_message(
            to_agents=["agent-1"],
            content="Direct message to agent-1",
            project_id=project_id,
            message_type="direct",
            priority="normal",
            from_agent="orchestrator",
        )

        # Assert: Message sent successfully
        assert result["success"] is True

        # Assert: broadcast_message_received() called with single recipient
        call_kwargs = mock_websocket_manager.broadcast_message_received.call_args.kwargs
        actual_recipients = call_kwargs["to_agent_ids"]

        assert len(actual_recipients) == 1, f"Expected 1 recipient, got {len(actual_recipients)}"
        assert actual_recipients[0] == "agent-1"

        print("[PASS] Direct message sent to single recipient only")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
