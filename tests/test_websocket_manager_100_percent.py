"""
WebSocket Manager tests to achieve 100% coverage
Tests the remaining exception handling paths and edge cases
"""

# Import the production WebSocket manager
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.websocket import WebSocketManager


class TestWebSocketManager100Percent:
    """Test remaining uncovered lines for 100% coverage"""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance"""
        return WebSocketManager()

    async def test_all_remaining_branch_conditions(self, ws_manager):
        """Test remaining branch conditions for 100% branch coverage"""

        # Test subscription with empty entity_subscribers
        client_id = "test_client"
        ws_manager.active_connections[client_id] = AsyncMock()
        ws_manager.subscriptions[client_id] = set()

        # Test notify_entity_update with no subscribers
        await ws_manager.notify_entity_update("project", "nonexistent", {"data": "test"})
        # Should complete without error

        # Test unsubscribe with empty entity_subscribers
        await ws_manager.unsubscribe(client_id, "project", "nonexistent")
        # Should complete without error

        # Test get_subscription_count with None entity
        count = ws_manager.get_subscription_count(None, None)
        assert count == 0

        # Test is_authenticated with missing auth_type
        ws_manager.auth_contexts[client_id] = {}
        assert not ws_manager.is_authenticated(client_id)

        # Test broadcast methods with no matching tenants
        await ws_manager.broadcast_agent_update(
            "agent_001", "test_agent", "proj_001", "nonexistent_tenant", "active", 50
        )

        await ws_manager.broadcast_template_update(
            "tmpl_001", "test_template", "create", "nonexistent_tenant", "prod_001"
        )

    async def test_edge_cases_for_complete_coverage(self, ws_manager):
        """Test edge cases to ensure 100% coverage"""

        # Test broadcast_progress with percentage clamping
        ws_manager.notify_entity_update = AsyncMock()

        # Test percentage > 100 (should clamp to 100)
        await ws_manager.broadcast_progress("op_001", "proj_001", 150.0, "Over 100%")
        call_args = ws_manager.notify_entity_update.call_args[0][2]
        assert call_args["data"]["percentage"] == 100

        # Test percentage < 0 (should clamp to 0)
        await ws_manager.broadcast_progress("op_001", "proj_001", -10.0, "Negative")
        call_args = ws_manager.notify_entity_update.call_args[0][2]
        assert call_args["data"]["percentage"] == 0

        # Test broadcast_sub_agent_completed without optional parameters
        await ws_manager.broadcast_sub_agent_completed(
            "int_001", "sub_agent", "parent_agent", "proj_001", "completed", 60
        )

        # Test broadcast_agent_update without optional parameters
        await ws_manager.broadcast_agent_update("agent_001", "test_agent", "proj_001", "tenant_a", "active", 500)

        # Test broadcast_template_update without optional parameters
        await ws_manager.broadcast_template_update("tmpl_001", "test_template", "delete", "tenant_a", "prod_001")

    async def test_subscription_edge_cases(self, ws_manager):
        """Test subscription edge cases"""
        client_id = "test_client"
        ws_manager.active_connections[client_id] = AsyncMock()
        ws_manager.auth_contexts[client_id] = {"tenant_key": "test_tenant"}

        # Initialize empty subscriptions
        ws_manager.subscriptions[client_id] = set()

        # Test subscribe to create new entity_subscribers entry
        with patch("api.websocket.check_subscription_permission", return_value=True):
            await ws_manager.subscribe(client_id, "project", "new_project", "test_tenant")

        entity_key = "project:new_project"
        assert entity_key in ws_manager.subscriptions[client_id]
        assert client_id in ws_manager.entity_subscribers[entity_key]

        # Test unsubscribe from entity with multiple subscribers
        other_client = "other_client"
        ws_manager.entity_subscribers[entity_key].add(other_client)

        await ws_manager.unsubscribe(client_id, "project", "new_project")

        # Should remove client but keep entity_subscribers entry (has other_client)
        assert entity_key not in ws_manager.subscriptions[client_id]
        assert client_id not in ws_manager.entity_subscribers[entity_key]
        assert other_client in ws_manager.entity_subscribers[entity_key]

    async def test_connection_management_edge_cases(self, ws_manager):
        """Test connection management edge cases"""

        # Test sending to non-existent client
        await ws_manager.send_personal_message("test", "nonexistent_client")
        await ws_manager.send_json({"test": "data"}, "nonexistent_client")
        # Should complete without error

        # Test disconnect of non-existent client
        ws_manager.disconnect("nonexistent_client")
        # Should complete without error

        # Test get_auth_context for non-existent client
        context = ws_manager.get_auth_context("nonexistent_client")
        assert context is None

        # Test is_authenticated for non-existent client
        assert not ws_manager.is_authenticated("nonexistent_client")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
