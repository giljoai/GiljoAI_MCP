"""
Unit tests for WebSocket Manager class - testing production code paths
Tests all methods without requiring a running server
"""

import json

# Import the production WebSocket manager
import sys
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.websocket import WebSocketManager


class TestWebSocketManager:
    """Test WebSocket manager core functionality"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection"""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    def test_init(self, ws_manager):
        """Test WebSocket manager initialization"""
        assert ws_manager.active_connections == {}
        assert ws_manager.auth_contexts == {}
        assert ws_manager.subscriptions == {}
        assert ws_manager.entity_subscribers == {}

    async def test_connect(self, ws_manager, mock_websocket):
        """Test WebSocket connection handling"""
        client_id = "test_client_001"
        auth_context = {"auth_type": "api_key", "tenant_key": "test_tenant"}

        await ws_manager.connect(mock_websocket, client_id, auth_context)

        assert client_id in ws_manager.active_connections
        assert ws_manager.active_connections[client_id] == mock_websocket
        assert ws_manager.auth_contexts[client_id] == auth_context
        assert client_id in ws_manager.subscriptions
        assert ws_manager.subscriptions[client_id] == set()

    def test_disconnect(self, ws_manager, mock_websocket):
        """Test WebSocket disconnection cleanup"""
        client_id = "test_client_001"
        entity_key = "project:test_project"

        # Setup initial state
        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.auth_contexts[client_id] = {"test": "context"}
        ws_manager.subscriptions[client_id] = {entity_key}
        ws_manager.entity_subscribers[entity_key] = {client_id}

        # Disconnect
        ws_manager.disconnect(client_id)

        # Verify cleanup
        assert client_id not in ws_manager.active_connections
        assert client_id not in ws_manager.auth_contexts
        assert client_id not in ws_manager.subscriptions
        assert entity_key not in ws_manager.entity_subscribers

    @patch("api.websocket.check_subscription_permission")
    async def test_subscribe_authorized(self, mock_check_perm, ws_manager, mock_websocket):
        """Test successful subscription with authorization"""
        client_id = "test_client_001"
        entity_type = "project"
        entity_id = "test_project"
        tenant_key = "test_tenant"

        # Setup
        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.auth_contexts[client_id] = {"tenant_key": tenant_key}
        ws_manager.subscriptions[client_id] = set()
        mock_check_perm.return_value = True

        # Subscribe
        await ws_manager.subscribe(client_id, entity_type, entity_id, tenant_key)

        # Verify
        entity_key = f"{entity_type}:{entity_id}"
        assert entity_key in ws_manager.subscriptions[client_id]
        assert client_id in ws_manager.entity_subscribers[entity_key]
        mock_check_perm.assert_called_once()

    @patch("api.websocket.check_subscription_permission")
    async def test_subscribe_unauthorized(self, mock_check_perm, ws_manager, mock_websocket):
        """Test subscription rejection for unauthorized access"""
        client_id = "test_client_001"
        entity_type = "project"
        entity_id = "test_project"

        # Setup
        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.auth_contexts[client_id] = {"tenant_key": "different_tenant"}
        ws_manager.subscriptions[client_id] = set()
        mock_check_perm.return_value = False

        # Should raise HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await ws_manager.subscribe(client_id, entity_type, entity_id, "test_tenant")

        assert exc_info.value.status_code == 403

    async def test_unsubscribe(self, ws_manager, mock_websocket):
        """Test unsubscription"""
        client_id = "test_client_001"
        entity_type = "project"
        entity_id = "test_project"
        entity_key = f"{entity_type}:{entity_id}"

        # Setup subscription
        ws_manager.active_connections[client_id] = mock_websocket
        ws_manager.subscriptions[client_id] = {entity_key}
        ws_manager.entity_subscribers[entity_key] = {client_id}

        # Unsubscribe
        await ws_manager.unsubscribe(client_id, entity_type, entity_id)

        # Verify
        assert entity_key not in ws_manager.subscriptions[client_id]
        assert entity_key not in ws_manager.entity_subscribers

    async def test_send_personal_message_success(self, ws_manager, mock_websocket):
        """Test sending personal message successfully"""
        client_id = "test_client_001"
        message = "Test message"

        ws_manager.active_connections[client_id] = mock_websocket

        await ws_manager.send_personal_message(message, client_id)

        mock_websocket.send_text.assert_called_once_with(message)

    async def test_send_personal_message_disconnected(self, ws_manager, mock_websocket):
        """Test sending message to disconnected client"""
        client_id = "test_client_001"
        message = "Test message"

        ws_manager.active_connections[client_id] = mock_websocket
        mock_websocket.send_text.side_effect = Exception("Connection lost")

        await ws_manager.send_personal_message(message, client_id)

        # Should remove disconnected client
        assert client_id not in ws_manager.active_connections

    async def test_send_json_success(self, ws_manager, mock_websocket):
        """Test sending JSON data successfully"""
        client_id = "test_client_001"
        data = {"type": "test", "content": "Test content"}

        ws_manager.active_connections[client_id] = mock_websocket

        await ws_manager.send_json(data, client_id)

        mock_websocket.send_json.assert_called_once_with(data)

    async def test_send_json_disconnected(self, ws_manager, mock_websocket):
        """Test sending JSON to disconnected client"""
        client_id = "test_client_001"
        data = {"type": "test", "content": "Test content"}

        ws_manager.active_connections[client_id] = mock_websocket
        mock_websocket.send_json.side_effect = Exception("Connection lost")

        await ws_manager.send_json(data, client_id)

        # Should remove disconnected client
        assert client_id not in ws_manager.active_connections

    async def test_broadcast(self, ws_manager):
        """Test broadcasting to all clients"""
        message = "Broadcast message"

        # Setup multiple clients
        clients = {
            "client_1": AsyncMock(),
            "client_2": AsyncMock(),
            "client_3": AsyncMock()
        }
        ws_manager.active_connections = clients

        await ws_manager.broadcast(message)

        # Verify all clients received the message
        for ws in clients.values():
            ws.send_text.assert_called_once_with(message)

    async def test_broadcast_with_disconnected_client(self, ws_manager):
        """Test broadcasting with one disconnected client"""
        message = "Broadcast message"

        # Setup clients with one that will fail
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        client_2.send_text.side_effect = Exception("Connection lost")
        client_3 = AsyncMock()

        ws_manager.active_connections = {
            "client_1": client_1,
            "client_2": client_2,
            "client_3": client_3
        }

        await ws_manager.broadcast(message)

        # Verify working clients received message
        client_1.send_text.assert_called_once_with(message)
        client_3.send_text.assert_called_once_with(message)

        # Verify disconnected client was removed
        assert "client_2" not in ws_manager.active_connections

    async def test_broadcast_json(self, ws_manager):
        """Test broadcasting JSON data"""
        data = {"type": "broadcast", "content": "Test broadcast"}
        expected_message = json.dumps(data)

        # Setup clients
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        ws_manager.active_connections = {"client_1": client_1, "client_2": client_2}

        await ws_manager.broadcast_json(data)

        # Verify JSON was sent to all clients
        client_1.send_text.assert_called_once_with(expected_message)
        client_2.send_text.assert_called_once_with(expected_message)

    async def test_notify_entity_update(self, ws_manager):
        """Test entity update notifications"""
        entity_type = "project"
        entity_id = "test_project"
        update_data = {"status": "completed"}
        entity_key = f"{entity_type}:{entity_id}"

        # Setup subscribers
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        ws_manager.active_connections = {"client_1": client_1, "client_2": client_2}
        ws_manager.entity_subscribers[entity_key] = {"client_1", "client_2"}

        await ws_manager.notify_entity_update(entity_type, entity_id, update_data)

        # Verify notification was sent
        expected_message = {
            "type": "entity_update",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "data": update_data
        }

        client_1.send_json.assert_called_once_with(expected_message)
        client_2.send_json.assert_called_once_with(expected_message)

    def test_get_connection_count(self, ws_manager):
        """Test connection count tracking"""
        assert ws_manager.get_connection_count() == 0

        # Add connections
        ws_manager.active_connections = {
            "client_1": MagicMock(),
            "client_2": MagicMock(),
            "client_3": MagicMock()
        }

        assert ws_manager.get_connection_count() == 3

    def test_get_subscription_count(self, ws_manager):
        """Test subscription count tracking"""
        entity_key = "project:test_project"

        # No subscriptions
        assert ws_manager.get_subscription_count("project", "test_project") == 0
        assert ws_manager.get_subscription_count() == 0

        # Add subscribers
        ws_manager.entity_subscribers[entity_key] = {"client_1", "client_2"}
        ws_manager.subscriptions = {
            "client_1": {entity_key},
            "client_2": {entity_key, "agent:test_agent"}
        }

        assert ws_manager.get_subscription_count("project", "test_project") == 2
        assert ws_manager.get_subscription_count() == 3  # Total subscriptions

    def test_get_auth_context(self, ws_manager):
        """Test auth context retrieval"""
        client_id = "test_client"
        auth_context = {"auth_type": "jwt", "tenant_key": "test_tenant"}

        assert ws_manager.get_auth_context(client_id) is None

        ws_manager.auth_contexts[client_id] = auth_context
        assert ws_manager.get_auth_context(client_id) == auth_context

    def test_is_authenticated(self, ws_manager):
        """Test authentication status checking"""
        client_id = "test_client"

        # No auth context
        assert ws_manager.is_authenticated(client_id) is False

        # No auth
        ws_manager.auth_contexts[client_id] = {"auth_type": "none"}
        assert ws_manager.is_authenticated(client_id) is False

        # Authenticated
        ws_manager.auth_contexts[client_id] = {"auth_type": "api_key"}
        assert ws_manager.is_authenticated(client_id) is True


class TestWebSocketManagerBroadcasts:
    """Test WebSocket manager broadcast methods"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        return WebSocketManager()

    async def test_broadcast_message_update(self, ws_manager):
        """Test message update broadcasting"""
        message_id = "msg_001"
        project_id = "proj_001"
        update_type = "new"
        message_data = {
            "from_agent": "orchestrator",
            "to_agents": ["agent_1"],
            "content": "Test message",
            "priority": "normal",
            "status": "pending"
        }

        # Mock notify_entity_update
        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_message_update(message_id, project_id, update_type, message_data)

        # Verify project notification
        assert ws_manager.notify_entity_update.call_count == 2  # Project + agent
        calls = ws_manager.notify_entity_update.call_args_list

        # Check project notification
        project_call = calls[0]
        assert project_call[0][0] == "project"
        assert project_call[0][1] == project_id

        # Check agent notification
        agent_call = calls[1]
        assert agent_call[0][0] == "agent"
        assert agent_call[0][1] == f"{project_id}:agent_1"

    async def test_broadcast_progress(self, ws_manager):
        """Test progress update broadcasting"""
        operation_id = "op_001"
        project_id = "proj_001"
        percentage = 75.5
        message = "Processing..."
        details = {"step": "validation"}

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_progress(operation_id, project_id, percentage, message, details)

        # Verify notification
        ws_manager.notify_entity_update.assert_called_once()
        call_args = ws_manager.notify_entity_update.call_args

        assert call_args[0][0] == "project"
        assert call_args[0][1] == project_id

        progress_data = call_args[0][2]
        assert progress_data["type"] == "progress"
        assert progress_data["data"]["percentage"] == 75.5
        assert progress_data["data"]["is_complete"] is False

    async def test_broadcast_progress_complete(self, ws_manager):
        """Test progress broadcasting at 100%"""
        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_progress("op_001", "proj_001", 100.0, "Complete")

        call_args = ws_manager.notify_entity_update.call_args
        progress_data = call_args[0][2]
        assert progress_data["data"]["is_complete"] is True

    async def test_broadcast_notification_to_all(self, ws_manager):
        """Test system notification broadcasting to all clients"""
        ws_manager.broadcast_json = AsyncMock()

        await ws_manager.broadcast_notification(
            "info", "System Update", "System maintenance completed"
        )

        # Should broadcast to all
        ws_manager.broadcast_json.assert_called_once()
        call_args = ws_manager.broadcast_json.call_args[0][0]
        assert call_args["type"] == "notification"
        assert call_args["data"]["notification_type"] == "info"

    async def test_broadcast_notification_to_project(self, ws_manager):
        """Test notification broadcasting to project subscribers"""
        project_id = "proj_001"
        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_notification(
            "warning", "Project Alert", "Resource limit reached", project_id=project_id
        )

        # Should notify project subscribers
        ws_manager.notify_entity_update.assert_called_once_with("project", project_id, ANY)

    async def test_broadcast_notification_to_specific_clients(self, ws_manager):
        """Test notification to specific clients"""
        target_clients = ["client_1", "client_2"]
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        client_3 = AsyncMock()  # Should not receive

        ws_manager.active_connections = {
            "client_1": client_1,
            "client_2": client_2,
            "client_3": client_3
        }

        await ws_manager.broadcast_notification(
            "error", "Error Alert", "Something went wrong", target_clients=target_clients
        )

        # Only targeted clients should receive
        client_1.send_json.assert_called_once()
        client_2.send_json.assert_called_once()
        client_3.send_json.assert_not_called()

    async def test_send_heartbeat(self, ws_manager):
        """Test heartbeat mechanism"""
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        client_3 = AsyncMock()
        client_3.send_json.side_effect = Exception("Connection lost")

        ws_manager.active_connections = {
            "client_1": client_1,
            "client_2": client_2,
            "client_3": client_3
        }

        await ws_manager.send_heartbeat()

        # Working clients should receive heartbeat
        client_1.send_json.assert_called_once()
        client_2.send_json.assert_called_once()

        # Failed client should be removed
        assert "client_3" not in ws_manager.active_connections

    async def test_handle_pong(self, ws_manager):
        """Test pong response handling"""
        client_id = "test_client"

        # Should complete without error
        await ws_manager.handle_pong(client_id)


class TestWebSocketManagerMultiTenant:
    """Test multi-tenant functionality"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        return WebSocketManager()

    async def test_broadcast_agent_update_multi_tenant(self, ws_manager):
        """Test agent update broadcasting respects tenant isolation"""
        agent_id = "agent_001"
        agent_name = "test_agent"
        project_id = "proj_001"
        tenant_key = "tenant_a"

        # Setup clients with different tenants
        client_a1 = AsyncMock()
        client_a2 = AsyncMock()
        client_b = AsyncMock()

        ws_manager.active_connections = {
            "client_a1": client_a1,
            "client_a2": client_a2,
            "client_b": client_b
        }

        ws_manager.auth_contexts = {
            "client_a1": {"tenant_key": "tenant_a"},
            "client_a2": {"tenant_key": "tenant_a"},
            "client_b": {"tenant_key": "tenant_b"}
        }

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_agent_update(
            agent_id, agent_name, project_id, tenant_key, "in_progress", 1000
        )

        # Only tenant_a clients should receive broadcast
        client_a1.send_json.assert_called_once()
        client_a2.send_json.assert_called_once()
        client_b.send_json.assert_not_called()

        # Entity updates should still be called
        assert ws_manager.notify_entity_update.call_count == 2

    async def test_broadcast_template_update_multi_tenant(self, ws_manager):
        """Test template update broadcasting with tenant isolation"""
        template_id = "tmpl_001"
        template_name = "test_template"
        tenant_key = "tenant_a"
        product_id = "prod_001"

        # Setup clients
        client_a = AsyncMock()
        client_b = AsyncMock()

        ws_manager.active_connections = {"client_a": client_a, "client_b": client_b}
        ws_manager.auth_contexts = {
            "client_a": {"tenant_key": "tenant_a"},
            "client_b": {"tenant_key": "tenant_b"}
        }

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_template_update(
            template_id, template_name, "update", tenant_key, product_id, "user_001"
        )

        # Only same tenant should receive
        client_a.send_json.assert_called_once()
        client_b.send_json.assert_not_called()

        # Product notification should be called
        ws_manager.notify_entity_update.assert_called_once_with("product", product_id, ANY)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
