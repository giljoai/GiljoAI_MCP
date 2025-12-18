"""
Tests for WebSocket message counter events (Handover 0297).

Verifies that WebSocket events provide sufficient data for counter updates.

These tests validate the three critical WebSocket events:
1. message:sent - Increments "Messages Sent" counter on sender's agent card
2. message:received - Increments "Messages Waiting" counter on recipient's agent card
3. message:acknowledged - Decrements "Waiting", increments "Read" counter

Event Structure Verified (Based on Existing Implementation):

message:sent event:
{
    "type": "message:sent",
    "data": {
        "message_id": str,
        "job_id": str,              # Sender's job_id
        "project_id": str,
        "from_agent": str,
        "to_agent": str | None,     # None for broadcasts
        "message_type": str,
        "content": str,
        "content_preview": str,
        "tenant_key": str,
        "priority": int,
        "timestamp": str (ISO)
    },
    "timestamp": str (ISO)
}

message:received event:
{
    "type": "message:received",
    "data": {
        "message_id": str,
        "job_id": str,              # Sender's job_id
        "project_id": str,
        "from_agent": str,
        "to_agent_ids": list[str],  # List of recipient job_ids
        "message_type": str,
        "content": str,
        "content_preview": str,
        "tenant_key": str,
        "priority": int,
        "timestamp": str (ISO)
    },
    "timestamp": str (ISO)
}

message:acknowledged event:
{
    "type": "message:acknowledged",
    "data": {
        "message_id": str,
        "job_id": str,              # Acknowledger's job_id
        "agent_id": str,
        "tenant_key": str,
        "acknowledged_at": str (ISO),
        "response_data": dict (optional)
    },
    "timestamp": str (ISO)
}
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import uuid

pytestmark = pytest.mark.asyncio


class TestMessageSentEvent:
    """Tests for message:sent WebSocket event."""

    async def test_message_sent_event_structure(self):
        """message:sent event should have correct structure with all required fields."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()

        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        client_id = "test-client-1"
        tenant_key = "tenant-123"

        # Simulate authenticated connection
        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.auth_contexts[client_id] = {"tenant_key": tenant_key}

        # Broadcast message:sent event
        message_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())

        await ws_manager.broadcast_message_sent(
            message_id=message_id,
            job_id=job_id,
            project_id=project_id,
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="direct",
            content_preview="Test message content",
            priority=1,
        )

        # Verify WebSocket send was called
        assert mock_websocket.send_json.called
        sent_message = mock_websocket.send_json.call_args[0][0]

        # Verify event structure
        assert sent_message["type"] == "message:sent"
        assert "data" in sent_message
        assert "timestamp" in sent_message

        # Verify required data fields for counter updates
        data = sent_message["data"]
        assert data["message_id"] == message_id
        assert data["job_id"] == job_id  # Critical for sender counter update
        assert data["project_id"] == project_id
        assert data["from_agent"] == "orchestrator"
        assert data["to_agent"] == "implementer"
        assert data["message_type"] == "direct"
        assert data["tenant_key"] == tenant_key
        assert data["priority"] == 1
        assert "timestamp" in data

        # Verify content fields (multiple aliases for compatibility)
        assert "content" in data
        assert "content_preview" in data
        assert "message" in data

    async def test_message_sent_broadcast_has_no_to_agent(self):
        """message:sent event for broadcast should have to_agent=None."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_websocket = AsyncMock()
        client_id = "test-client-1"
        tenant_key = "tenant-123"

        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.auth_contexts[client_id] = {"tenant_key": tenant_key}

        await ws_manager.broadcast_message_sent(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent=None,  # Broadcast
            message_type="broadcast",
            content_preview="Broadcast message",
            priority=1,
        )

        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["data"]["to_agent"] is None

    async def test_message_sent_only_broadcasts_to_same_tenant(self):
        """message:sent event should only be sent to clients in the same tenant."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()

        # Create two clients with different tenants
        mock_ws_tenant1 = AsyncMock()
        mock_ws_tenant2 = AsyncMock()

        ws_manager.active_connections["client-1"] = mock_ws_tenant1
        ws_manager.active_connections["client-2"] = mock_ws_tenant2
        ws_manager.auth_contexts["client-1"] = {"tenant_key": "tenant-1"}
        ws_manager.auth_contexts["client-2"] = {"tenant_key": "tenant-2"}

        # Broadcast to tenant-1 only
        await ws_manager.broadcast_message_sent(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key="tenant-1",
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="direct",
            content_preview="Test",
            priority=1,
        )

        # Only client-1 should receive the event
        assert mock_ws_tenant1.send_json.called
        assert not mock_ws_tenant2.send_json.called


class TestMessageReceivedEvent:
    """Tests for message:received WebSocket event."""

    async def test_message_received_event_structure(self):
        """message:received event should have correct structure with recipient job_ids."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_websocket = AsyncMock()
        client_id = "test-client-1"
        tenant_key = "tenant-123"

        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.auth_contexts[client_id] = {"tenant_key": tenant_key}

        message_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        recipient_job_id = str(uuid.uuid4())

        await ws_manager.broadcast_message_received(
            message_id=message_id,
            job_id=job_id,  # Sender's job_id
            project_id=project_id,
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=[recipient_job_id],  # List of recipients
            message_type="direct",
            content_preview="Task assignment",
            priority=2,
        )

        sent_message = mock_websocket.send_json.call_args[0][0]

        # Verify event type
        assert sent_message["type"] == "message:received"

        # Verify critical data for recipient counter updates
        data = sent_message["data"]
        assert data["message_id"] == message_id
        assert data["job_id"] == job_id  # Sender's job_id
        assert data["project_id"] == project_id
        assert data["from_agent"] == "orchestrator"
        assert data["to_agent_ids"] == [recipient_job_id]  # Critical for recipient counter
        assert data["message_type"] == "direct"
        assert data["tenant_key"] == tenant_key
        assert data["priority"] == 2

    async def test_message_received_broadcast_includes_all_recipients(self):
        """message:received event for broadcast should include all recipient job_ids."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_websocket = AsyncMock()
        tenant_key = "tenant-123"

        ws_manager.active_connections["client-1"] = mock_websocket
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        # Simulate broadcast to multiple agents
        recipient_job_ids = [str(uuid.uuid4()) for _ in range(5)]

        await ws_manager.broadcast_message_received(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=recipient_job_ids,  # All 5 recipients
            message_type="broadcast",
            content_preview="Broadcast to all",
            priority=1,
        )

        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["data"]["to_agent_ids"] == recipient_job_ids
        assert len(sent_message["data"]["to_agent_ids"]) == 5

    async def test_message_received_multi_tenant_isolation(self):
        """message:received event should respect tenant boundaries."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()

        mock_ws_1 = AsyncMock()
        mock_ws_2 = AsyncMock()

        ws_manager.active_connections["client-1"] = mock_ws_1
        ws_manager.active_connections["client-2"] = mock_ws_2
        ws_manager.auth_contexts["client-1"] = {"tenant_key": "tenant-A"}
        ws_manager.auth_contexts["client-2"] = {"tenant_key": "tenant-B"}

        await ws_manager.broadcast_message_received(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key="tenant-A",
            from_agent="orchestrator",
            to_agent_ids=[str(uuid.uuid4())],
            message_type="direct",
            content_preview="Test",
            priority=1,
        )

        # Only tenant-A client should receive
        assert mock_ws_1.send_json.called
        assert not mock_ws_2.send_json.called


class TestMessageAcknowledgedEvent:
    """Tests for message:acknowledged WebSocket event."""

    async def test_message_acknowledged_event_structure(self):
        """message:acknowledged event should have correct structure."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_websocket = AsyncMock()
        tenant_key = "tenant-123"

        ws_manager.active_connections["client-1"] = mock_websocket
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        message_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())  # Agent job_id who acknowledged
        message_ids = [message_id, str(uuid.uuid4())]

        await ws_manager.broadcast_message_acknowledged(
            message_id=message_id,
            agent_id=agent_id,
            tenant_key=tenant_key,
            project_id=project_id,
            message_ids=message_ids,
        )

        sent_message = mock_websocket.send_json.call_args[0][0]

        # Verify event type
        assert sent_message["type"] == "message:acknowledged"

        # Verify critical data for counter updates
        data = sent_message["data"]
        assert data["message_id"] == message_id
        assert data["message_ids"] == message_ids
        assert data["agent_id"] == agent_id
        assert data["project_id"] == project_id
        assert data["tenant_key"] == tenant_key
        assert "timestamp" in data

    async def test_message_acknowledged_with_multiple_messages(self):
        """message:acknowledged event should handle multiple message IDs."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_websocket = AsyncMock()
        tenant_key = "tenant-123"

        ws_manager.active_connections["client-1"] = mock_websocket
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        message_ids = [str(uuid.uuid4()) for _ in range(5)]

        await ws_manager.broadcast_message_acknowledged(
            message_id=message_ids[0],
            agent_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=str(uuid.uuid4()),
            message_ids=message_ids,
        )

        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["data"]["message_ids"] == message_ids
        assert len(sent_message["data"]["message_ids"]) == 5

    async def test_message_acknowledged_tenant_isolation(self):
        """message:acknowledged event should respect tenant boundaries."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()

        mock_ws_1 = AsyncMock()
        mock_ws_2 = AsyncMock()

        ws_manager.active_connections["client-1"] = mock_ws_1
        ws_manager.active_connections["client-2"] = mock_ws_2
        ws_manager.auth_contexts["client-1"] = {"tenant_key": "tenant-X"}
        ws_manager.auth_contexts["client-2"] = {"tenant_key": "tenant-Y"}

        message_id = str(uuid.uuid4())
        await ws_manager.broadcast_message_acknowledged(
            message_id=message_id,
            agent_id=str(uuid.uuid4()),
            tenant_key="tenant-X",
            project_id=str(uuid.uuid4()),
            message_ids=[message_id],
        )

        # Only tenant-X client receives
        assert mock_ws_1.send_json.called
        assert not mock_ws_2.send_json.called


class TestMessageServiceIntegration:
    """Integration tests for MessageService emitting WebSocket events."""

    async def test_send_message_emits_message_sent_event(self):
        """MessageService.send_message should emit message:sent event."""
        from src.giljo_mcp.services.message_service import MessageService
        from src.giljo_mcp.database import DatabaseManager
        from src.giljo_mcp.tenant import TenantManager
        from api.websocket import WebSocketManager

        # Mock database and WebSocket manager
        db_manager = MagicMock(spec=DatabaseManager)
        tenant_manager = MagicMock(spec=TenantManager)
        ws_manager = AsyncMock(spec=WebSocketManager)

        # Create service with mocked dependencies
        service = MessageService(db_manager=db_manager, tenant_manager=tenant_manager, websocket_manager=ws_manager)

        # Mock database session and project lookup
        mock_session = AsyncMock()
        mock_project = MagicMock()
        mock_project.id = str(uuid.uuid4())
        mock_project.tenant_key = "tenant-123"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_project)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        # Mock async context manager properly
        async_context_manager = AsyncMock()
        async_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        async_context_manager.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = MagicMock(return_value=async_context_manager)

        # Send message
        result = await service.send_message(
            to_agents=["implementer"],
            content="Test message",
            project_id=mock_project.id,
            message_type="direct",
            priority="normal",
            from_agent="orchestrator",
        )

        # Verify WebSocket broadcast was called
        assert ws_manager.broadcast_message_sent.called
        call_kwargs = ws_manager.broadcast_message_sent.call_args[1]
        assert call_kwargs["from_agent"] == "orchestrator"
        assert call_kwargs["tenant_key"] == "tenant-123"

    @pytest.mark.skip(reason="MessageService.acknowledge_message method was removed - acknowledgment happens via receive_messages")
    async def test_acknowledge_message_emits_acknowledged_event(self):
        """MessageService.acknowledge_message should emit message:acknowledged event.

        NOTE: This test is skipped because the acknowledge_message method was removed.
        Message acknowledgment is now handled via receive_messages() which calls
        broadcast_message_acknowledged. See Handover 0326 for details.
        """
        pass


class TestEventDataSufficiencyForCounters:
    """Tests verifying that events have all data needed for counter updates."""

    async def test_all_events_include_job_id(self):
        """All three events must include job_id for counter association."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_ws = AsyncMock()
        tenant_key = "tenant-123"

        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        job_id = str(uuid.uuid4())

        # Test message:sent
        await ws_manager.broadcast_message_sent(
            message_id=str(uuid.uuid4()),
            job_id=job_id,
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="direct",
            content_preview="Test",
            priority=1,
        )
        sent_event = mock_ws.send_json.call_args_list[0][0][0]
        assert sent_event["data"]["job_id"] == job_id

        # Test message:received
        await ws_manager.broadcast_message_received(
            message_id=str(uuid.uuid4()),
            job_id=job_id,
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=[str(uuid.uuid4())],
            message_type="direct",
            content_preview="Test",
            priority=1,
        )
        received_event = mock_ws.send_json.call_args_list[1][0][0]
        assert received_event["data"]["job_id"] == job_id

        # Test message:acknowledged
        ack_message_id = str(uuid.uuid4())
        await ws_manager.broadcast_message_acknowledged(
            message_id=ack_message_id,
            agent_id=job_id,  # agent_id is the job_id of acknowledging agent
            tenant_key=tenant_key,
            project_id=str(uuid.uuid4()),
            message_ids=[ack_message_id],
        )
        ack_event = mock_ws.send_json.call_args_list[2][0][0]
        assert ack_event["data"]["agent_id"] == job_id

    async def test_all_events_include_tenant_key(self):
        """All events must include tenant_key for multi-tenant isolation."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_ws = AsyncMock()
        tenant_key = "tenant-secure-123"

        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        # Test all three events include tenant_key in data payload
        await ws_manager.broadcast_message_sent(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="direct",
            content_preview="Test",
            priority=1,
        )
        assert mock_ws.send_json.call_args_list[0][0][0]["data"]["tenant_key"] == tenant_key

        await ws_manager.broadcast_message_received(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=[str(uuid.uuid4())],
            message_type="direct",
            content_preview="Test",
            priority=1,
        )
        assert mock_ws.send_json.call_args_list[1][0][0]["data"]["tenant_key"] == tenant_key

        ack_message_id = str(uuid.uuid4())
        await ws_manager.broadcast_message_acknowledged(
            message_id=ack_message_id,
            agent_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=str(uuid.uuid4()),
            message_ids=[ack_message_id],
        )
        assert mock_ws.send_json.call_args_list[2][0][0]["data"]["tenant_key"] == tenant_key

    async def test_message_received_includes_recipient_list(self):
        """message:received must include to_agent_ids list for recipient counter updates."""
        from api.websocket import WebSocketManager

        ws_manager = WebSocketManager()
        mock_ws = AsyncMock()
        tenant_key = "tenant-123"

        ws_manager.active_connections["client-1"] = mock_ws
        ws_manager.auth_contexts["client-1"] = {"tenant_key": tenant_key}

        recipient_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]

        await ws_manager.broadcast_message_received(
            message_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            project_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            from_agent="orchestrator",
            to_agent_ids=recipient_ids,
            message_type="broadcast",
            content_preview="Test",
            priority=1,
        )

        event = mock_ws.send_json.call_args[0][0]
        assert event["data"]["to_agent_ids"] == recipient_ids
        assert isinstance(event["data"]["to_agent_ids"], list)
        assert len(event["data"]["to_agent_ids"]) == 3
