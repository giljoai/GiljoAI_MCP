"""
Additional WebSocket Manager tests to reach 80%+ coverage
Tests the specific methods and branches that were missing in the unit tests
"""

import asyncio

# Import the production WebSocket manager
import sys
from pathlib import Path
from unittest.mock import ANY, AsyncMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.websocket import WebSocketManager


class TestWebSocketManagerCoverage:
    """Test uncovered methods in WebSocket manager"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        return WebSocketManager()

    async def test_broadcast_project_update(self, ws_manager):
        """Test project update broadcasting - covers lines 267-282"""
        project_id = "proj_001"
        update_type = "status_changed"
        project_data = {
            "name": "Test Project",
            "status": "active",
            "mission": "Test mission",
            "context_used": 1500,
            "context_budget": 5000
        }

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_project_update(project_id, update_type, project_data)

        # Verify notification was called
        ws_manager.notify_entity_update.assert_called_once()
        call_args = ws_manager.notify_entity_update.call_args

        assert call_args[0][0] == "project"
        assert call_args[0][1] == project_id

        message_data = call_args[0][2]
        assert message_data["type"] == "project_update"
        assert message_data["data"]["project_id"] == project_id
        assert message_data["data"]["update_type"] == update_type
        assert message_data["data"]["name"] == "Test Project"
        assert message_data["data"]["status"] == "active"

    async def test_start_heartbeat(self, ws_manager):
        """Test heartbeat mechanism start - covers lines 288-290"""
        ws_manager.send_heartbeat = AsyncMock()

        # Mock asyncio.sleep to prevent infinite loop
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]  # First sleep succeeds, second cancels

            with pytest.raises(asyncio.CancelledError):
                await ws_manager.start_heartbeat(interval=1)

            # Verify sleep was called with correct interval
            mock_sleep.assert_called_with(1)
            # Verify heartbeat was sent
            ws_manager.send_heartbeat.assert_called_once()

    async def test_broadcast_sub_agent_spawned(self, ws_manager):
        """Test sub-agent spawn broadcasting - covers lines 327-348"""
        interaction_id = "int_001"
        parent_agent_name = "parent_agent"
        sub_agent_name = "sub_agent"
        project_id = "proj_001"
        mission = "Test sub-agent mission"
        start_time = "2025-01-01T00:00:00Z"
        meta_data = {"test": "data"}

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_sub_agent_spawned(
            interaction_id, parent_agent_name, sub_agent_name,
            project_id, mission, start_time, meta_data
        )

        # Should call notify_entity_update twice (project + parent agent)
        assert ws_manager.notify_entity_update.call_count == 2

        # Check project notification
        project_call = ws_manager.notify_entity_update.call_args_list[0]
        assert project_call[0][0] == "project"
        assert project_call[0][1] == project_id

        # Check parent agent notification
        agent_call = ws_manager.notify_entity_update.call_args_list[1]
        assert agent_call[0][0] == "agent"
        assert agent_call[0][1] == f"{project_id}:{parent_agent_name}"

        # Verify message content
        message_data = project_call[0][2]
        assert message_data["type"] == "agent.sub_agent.spawned"
        assert message_data["data"]["interaction_id"] == interaction_id
        assert message_data["data"]["sub_agent_name"] == sub_agent_name
        assert message_data["data"]["mission"] == mission

    async def test_broadcast_sub_agent_completed(self, ws_manager):
        """Test sub-agent completion broadcasting - covers lines 364-390"""
        interaction_id = "int_001"
        sub_agent_name = "sub_agent"
        parent_agent_name = "parent_agent"
        project_id = "proj_001"
        status = "completed"
        duration_seconds = 120
        tokens_used = 5000
        result = "Task completed successfully"
        meta_data = {"performance": "good"}

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_sub_agent_completed(
            interaction_id, sub_agent_name, parent_agent_name,
            project_id, status, duration_seconds, tokens_used,
            result, None, meta_data
        )

        # Should call notify_entity_update twice
        assert ws_manager.notify_entity_update.call_count == 2

        # Verify message content
        project_call = ws_manager.notify_entity_update.call_args_list[0]
        message_data = project_call[0][2]
        assert message_data["type"] == "agent.sub_agent.completed"
        assert message_data["data"]["status"] == "completed"
        assert message_data["data"]["duration_seconds"] == 120
        assert message_data["data"]["result"] == result
        assert message_data["data"]["error_message"] is None

    async def test_broadcast_sub_agent_error(self, ws_manager):
        """Test sub-agent error broadcasting"""
        interaction_id = "int_001"
        sub_agent_name = "sub_agent"
        parent_agent_name = "parent_agent"
        project_id = "proj_001"
        status = "error"
        duration_seconds = 60
        error_message = "Task failed due to timeout"

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_sub_agent_completed(
            interaction_id, sub_agent_name, parent_agent_name,
            project_id, status, duration_seconds, None,
            None, error_message, None
        )

        # Verify error event type
        project_call = ws_manager.notify_entity_update.call_args_list[0]
        message_data = project_call[0][2]
        assert message_data["type"] == "agent.sub_agent.error"
        assert message_data["data"]["error_message"] == error_message
        assert message_data["data"]["result"] is None

    async def test_broadcast_agent_spawn(self, ws_manager):
        """Test agent spawn broadcasting - covers lines 408-439"""
        agent_id = "agent_001"
        agent_name = "test_agent"
        parent_agent_id = "parent_001"
        project_id = "proj_001"
        tenant_key = "tenant_a"
        role = "worker"
        mission = "Test agent mission"
        initial_status = "active"
        meta_data = {"priority": "high"}

        # Setup clients with matching tenant
        client_a = AsyncMock()
        client_b = AsyncMock()
        client_other = AsyncMock()

        ws_manager.active_connections = {
            "client_a": client_a,
            "client_b": client_b,
            "client_other": client_other
        }

        ws_manager.auth_contexts = {
            "client_a": {"tenant_key": "tenant_a"},
            "client_b": {"tenant_key": "tenant_a"},
            "client_other": {"tenant_key": "tenant_b"}  # Different tenant
        }

        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_agent_spawn(
            agent_id, agent_name, parent_agent_id, project_id,
            tenant_key, role, mission, initial_status, meta_data
        )

        # Only clients with matching tenant should receive broadcast
        client_a.send_json.assert_called_once()
        client_b.send_json.assert_called_once()
        client_other.send_json.assert_not_called()

        # Should also notify entity subscribers
        assert ws_manager.notify_entity_update.call_count == 2  # Project + parent agent

        # Verify message content
        sent_message = client_a.send_json.call_args[0][0]
        assert sent_message["type"] == "agent:spawn"
        assert sent_message["data"]["agent_name"] == agent_name
        assert sent_message["data"]["parent_agent_id"] == parent_agent_id
        assert sent_message["data"]["role"] == role

    async def test_broadcast_agent_complete(self, ws_manager):
        """Test agent completion broadcasting - covers lines 457-487"""
        agent_id = "agent_001"
        agent_name = "test_agent"
        project_id = "proj_001"
        tenant_key = "tenant_a"
        duration_seconds = 300.5
        final_status = "completed"
        context_usage = 2500
        completion_reason = "Mission accomplished"
        meta_data = {"efficiency": "high"}

        # Setup client with matching tenant
        client = AsyncMock()
        ws_manager.active_connections = {"client": client}
        ws_manager.auth_contexts = {"client": {"tenant_key": "tenant_a"}}
        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_agent_complete(
            agent_id, agent_name, project_id, tenant_key,
            duration_seconds, final_status, context_usage,
            completion_reason, meta_data
        )

        # Verify broadcast to matching tenant
        client.send_json.assert_called_once()
        sent_message = client.send_json.call_args[0][0]
        assert sent_message["type"] == "agent:complete"
        assert sent_message["data"]["duration_seconds"] == 300.5
        assert sent_message["data"]["final_status"] == "completed"
        assert sent_message["data"]["context_usage"] == 2500

        # Verify entity notifications
        assert ws_manager.notify_entity_update.call_count == 2

    async def test_broadcast_agent_spawn_no_parent(self, ws_manager):
        """Test agent spawn without parent agent"""
        agent_id = "agent_001"
        agent_name = "root_agent"
        project_id = "proj_001"
        tenant_key = "tenant_a"
        role = "orchestrator"

        client = AsyncMock()
        ws_manager.active_connections = {"client": client}
        ws_manager.auth_contexts = {"client": {"tenant_key": "tenant_a"}}
        ws_manager.notify_entity_update = AsyncMock()

        await ws_manager.broadcast_agent_spawn(
            agent_id, agent_name, None, project_id, tenant_key, role
        )

        # Should only notify project (no parent agent)
        ws_manager.notify_entity_update.assert_called_once_with("project", project_id, ANY)

    async def test_websocket_connection_failure_handling(self, ws_manager):
        """Test WebSocket connection failure handling in broadcasts"""
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        client_2.send_json.side_effect = Exception("Connection failed")

        ws_manager.active_connections = {"client_1": client_1, "client_2": client_2}
        ws_manager.auth_contexts = {
            "client_1": {"tenant_key": "tenant_a"},
            "client_2": {"tenant_key": "tenant_a"}
        }

        await ws_manager.broadcast_agent_spawn(
            "agent_001", "test_agent", None, "proj_001", "tenant_a", "worker"
        )

        # Working client should receive message
        client_1.send_json.assert_called_once()
        # Failed client should be handled gracefully (no exception raised)

    async def test_broadcast_with_empty_connections(self, ws_manager):
        """Test broadcasting with no active connections"""
        ws_manager.notify_entity_update = AsyncMock()

        # Should not raise exception with empty connections
        await ws_manager.broadcast_agent_spawn(
            "agent_001", "test_agent", None, "proj_001", "tenant_a", "worker"
        )

        # Entity notifications should still work
        ws_manager.notify_entity_update.assert_called_once()

    async def test_subscription_cleanup_on_disconnect(self, ws_manager):
        """Test subscription cleanup when client disconnects"""
        client_id = "test_client"
        entity_key_1 = "project:proj_001"
        entity_key_2 = "agent:agent_001"

        # Setup client with multiple subscriptions
        ws_manager.active_connections[client_id] = AsyncMock()
        ws_manager.auth_contexts[client_id] = {"tenant_key": "test"}
        ws_manager.subscriptions[client_id] = {entity_key_1, entity_key_2}
        ws_manager.entity_subscribers[entity_key_1] = {client_id, "other_client"}
        ws_manager.entity_subscribers[entity_key_2] = {client_id}

        # Disconnect client
        ws_manager.disconnect(client_id)

        # Verify cleanup
        assert client_id not in ws_manager.subscriptions
        assert client_id not in ws_manager.entity_subscribers[entity_key_1]
        assert entity_key_2 not in ws_manager.entity_subscribers  # Removed when empty

    async def test_heartbeat_with_connection_errors(self, ws_manager):
        """Test heartbeat with some connection failures"""
        client_1 = AsyncMock()
        client_2 = AsyncMock()
        client_2.send_json.side_effect = Exception("Connection lost")

        ws_manager.active_connections = {"client_1": client_1, "client_2": client_2}

        await ws_manager.send_heartbeat()

        # Working client should receive heartbeat
        client_1.send_json.assert_called_once()

        # Failed client should be removed
        assert "client_2" not in ws_manager.active_connections
        assert "client_1" in ws_manager.active_connections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
