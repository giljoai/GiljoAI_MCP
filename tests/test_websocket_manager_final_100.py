"""
Final WebSocket Manager tests to achieve 100% coverage
Tests the remaining uncovered lines and branches
"""

# Import the production WebSocket manager
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.websocket import WebSocketManager


class TestWebSocketManagerFinal100:
    """Test remaining uncovered lines for 100% coverage"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        return WebSocketManager()

    async def test_notify_entity_update_direct_exception_path(self, ws_manager):
        """Test the direct exception logging path in notify_entity_update"""
        entity_type = "project"
        entity_id = "test_project"
        update_data = {"status": "updated"}
        entity_key = f"{entity_type}:{entity_id}"

        # Setup client that will trigger the exception path in notify_entity_update
        client_id = "test_client"
        mock_websocket = AsyncMock()

        # Client must be in both entity_subscribers AND active_connections
        ws_manager.entity_subscribers[entity_key] = {client_id}
        ws_manager.active_connections[client_id] = mock_websocket

        # Mock send_json to raise an exception (this will trigger the exception logging)
        with patch.object(ws_manager, "send_json", side_effect=Exception("Send failed")) as mock_send:
            with patch("api.websocket.logger") as mock_logger:
                await ws_manager.notify_entity_update(entity_type, entity_id, update_data)

                # Verify send_json was called and failed
                mock_send.assert_called_once()

                # The exception handling and logging should have occurred
                mock_logger.exception.assert_called_once()
                logged_msg = mock_logger.exception.call_args[0][0]
                assert f"Error notifying {client_id}" in logged_msg

    async def test_send_json_method_exception_path(self, ws_manager):
        """Test send_json method's exception handling and disconnect"""
        client_id = "test_client"
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("WebSocket connection lost")

        ws_manager.active_connections[client_id] = mock_websocket

        # This should trigger the exception handling in send_json
        await ws_manager.send_json({"test": "data"}, client_id)

        # Client should be disconnected due to the exception
        assert client_id not in ws_manager.active_connections

    async def test_send_personal_message_exception_path(self, ws_manager):
        """Test send_personal_message method's exception handling"""
        client_id = "test_client"
        mock_websocket = AsyncMock()
        mock_websocket.send_text.side_effect = Exception("WebSocket connection lost")

        ws_manager.active_connections[client_id] = mock_websocket

        # This should trigger the exception handling in send_personal_message
        await ws_manager.send_personal_message("test message", client_id)

        # Client should be disconnected due to the exception
        assert client_id not in ws_manager.active_connections

    async def test_broadcast_exception_cleanup_path(self, ws_manager):
        """Test broadcast method's exception handling and cleanup"""
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        client_2.send_text.side_effect = Exception("Connection failed")

        ws_manager.active_connections = {"client_1": client_1, "client_2": client_2}

        await ws_manager.broadcast("test message")

        # Failed client should be removed
        assert "client_2" not in ws_manager.active_connections
        assert "client_1" in ws_manager.active_connections

    async def test_broadcast_json_exception_cleanup_path(self, ws_manager):
        """Test broadcast_json method calls broadcast with proper JSON"""
        data = {"type": "test", "message": "test data"}

        with patch.object(ws_manager, "broadcast") as mock_broadcast:
            await ws_manager.broadcast_json(data)

            # Should call broadcast with JSON string
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0][0]
            assert '"type": "test"' in call_args
            assert '"message": "test data"' in call_args

    async def test_entity_subscribers_edge_cases(self, ws_manager):
        """Test entity subscribers edge cases"""
        entity_key = "project:test"

        # Test notify with no entity_subscribers entry
        await ws_manager.notify_entity_update("project", "test", {"data": "test"})
        # Should complete without error

        # Test with entity_subscribers but no active_connections
        ws_manager.entity_subscribers[entity_key] = {"nonexistent_client"}
        await ws_manager.notify_entity_update("project", "test", {"data": "test"})
        # Should complete without error

    async def test_subscription_permission_branches(self, ws_manager):
        """Test subscription permission checking branches"""
        client_id = "test_client"
        ws_manager.active_connections[client_id] = AsyncMock()
        ws_manager.auth_contexts[client_id] = {"tenant_key": "test_tenant"}
        ws_manager.subscriptions[client_id] = set()

        # Test with check_subscription_permission returning False
        with patch("api.websocket.check_subscription_permission", return_value=False):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await ws_manager.subscribe(client_id, "project", "test_project", "test_tenant")

            assert exc_info.value.status_code == 403

    async def test_tenant_filtering_branches(self, ws_manager):
        """Test tenant filtering in broadcast methods"""
        # Setup clients with different tenant contexts
        client_a = AsyncMock()
        client_b = AsyncMock()
        client_no_context = AsyncMock()

        ws_manager.active_connections = {
            "client_a": client_a,
            "client_b": client_b,
            "client_no_context": client_no_context
        }

        ws_manager.auth_contexts = {
            "client_a": {"tenant_key": "tenant_1"},
            "client_b": {"tenant_key": "tenant_2"},
            # client_no_context has no auth context
        }

        ws_manager.notify_entity_update = AsyncMock()

        # Test broadcast with tenant filtering
        await ws_manager.broadcast_agent_update(
            "agent_001", "test_agent", "proj_001", "tenant_1", "active", 100
        )

        # Only client_a should receive the message (matching tenant)
        client_a.send_json.assert_called_once()
        client_b.send_json.assert_not_called()
        client_no_context.send_json.assert_not_called()

    async def test_auth_context_edge_cases(self, ws_manager):
        """Test auth context edge cases"""
        client_id = "test_client"

        # Test get_auth_context with None value
        ws_manager.auth_contexts[client_id] = None
        context = ws_manager.get_auth_context(client_id)
        assert context is None

        # Test is_authenticated with various auth_type values
        ws_manager.auth_contexts[client_id] = {"auth_type": "none"}
        assert not ws_manager.is_authenticated(client_id)

        ws_manager.auth_contexts[client_id] = {"auth_type": "api_key"}
        assert ws_manager.is_authenticated(client_id)

        ws_manager.auth_contexts[client_id] = {"auth_type": "jwt"}
        assert ws_manager.is_authenticated(client_id)

    async def test_disconnect_cleanup_edge_cases(self, ws_manager):
        """Test disconnect cleanup with various edge cases"""
        client_id = "test_client"
        entity_key = "project:test"

        # Setup partial state
        ws_manager.active_connections[client_id] = AsyncMock()
        ws_manager.subscriptions[client_id] = {entity_key}
        ws_manager.entity_subscribers[entity_key] = {client_id, "other_client"}

        # Disconnect
        ws_manager.disconnect(client_id)

        # Verify entity_subscribers still has other_client
        assert "other_client" in ws_manager.entity_subscribers[entity_key]
        assert client_id not in ws_manager.entity_subscribers[entity_key]

    async def test_progress_percentage_edge_values(self, ws_manager):
        """Test progress percentage clamping edge values"""
        ws_manager.notify_entity_update = AsyncMock()

        # Test exact boundary values
        await ws_manager.broadcast_progress("op_001", "proj_001", 0.0, "Zero")
        call_args = ws_manager.notify_entity_update.call_args[0][2]
        assert call_args["data"]["percentage"] == 0
        assert call_args["data"]["is_complete"] is False

        await ws_manager.broadcast_progress("op_001", "proj_001", 100.0, "Exactly 100")
        call_args = ws_manager.notify_entity_update.call_args[0][2]
        assert call_args["data"]["percentage"] == 100
        assert call_args["data"]["is_complete"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
