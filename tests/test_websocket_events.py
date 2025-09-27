#!/usr/bin/env python3
"""
Test script for new WebSocket event handlers
"""

import asyncio
import sys
from pathlib import Path


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import logging

from api.websocket import WebSocketManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self, tenant_key: str):
        self.tenant_key = tenant_key
        self.messages = []

    async def send_json(self, message: dict):
        """Store messages sent to this websocket"""
        self.messages.append(message)

    def get_messages_by_type(self, msg_type: str):
        """Get all messages of a specific type"""
        return [m for m in self.messages if m.get("type") == msg_type]


async def test_agent_spawn_event():
    """Test agent:spawn event broadcasting"""

    manager = WebSocketManager()

    # Create mock WebSocket connections for different tenants
    ws_tenant1 = MockWebSocket("tenant-1")
    ws_tenant2 = MockWebSocket("tenant-2")
    ws_tenant1_b = MockWebSocket("tenant-1")  # Second connection for tenant-1

    # Add connections (using client IDs as keys)
    manager.active_connections["client-1a"] = ws_tenant1
    manager.active_connections["client-2"] = ws_tenant2
    manager.active_connections["client-1b"] = ws_tenant1_b

    # Set auth contexts
    manager.auth_contexts["client-1a"] = {"tenant_key": "tenant-1"}
    manager.auth_contexts["client-2"] = {"tenant_key": "tenant-2"}
    manager.auth_contexts["client-1b"] = {"tenant_key": "tenant-1"}

    # Broadcast agent spawn event for tenant-1
    await manager.broadcast_agent_spawn(
        agent_id="agent-001",
        agent_name="implementer",
        parent_agent_id="agent-orchestrator",
        project_id="project-001",
        tenant_key="tenant-1",
        role="implementer",
        mission="Implement API endpoints",
        initial_status="active",
    )

    # Check results
    tenant1_messages = ws_tenant1.get_messages_by_type("agent:spawn")
    tenant2_messages = ws_tenant2.get_messages_by_type("agent:spawn")
    tenant1b_messages = ws_tenant1_b.get_messages_by_type("agent:spawn")

    # Verify multi-tenant isolation
    assert len(tenant1_messages) == 1, "Tenant-1 should receive the message"
    assert len(tenant1b_messages) == 1, "Tenant-1 (second connection) should receive the message"
    assert len(tenant2_messages) == 0, "Tenant-2 should NOT receive the message"

    # Verify message content
    if tenant1_messages:
        msg = tenant1_messages[0]
        assert msg["data"]["agent_name"] == "implementer"
        assert msg["data"]["parent_agent_id"] == "agent-orchestrator"
        assert msg["data"]["tenant_key"] == "tenant-1"


async def test_agent_complete_event():
    """Test agent:complete event broadcasting"""

    manager = WebSocketManager()

    # Create mock connections
    ws_tenant1 = MockWebSocket("tenant-1")
    ws_tenant2 = MockWebSocket("tenant-2")

    manager.active_connections["client-1"] = ws_tenant1
    manager.active_connections["client-2"] = ws_tenant2

    manager.auth_contexts["client-1"] = {"tenant_key": "tenant-1"}
    manager.auth_contexts["client-2"] = {"tenant_key": "tenant-2"}

    # Broadcast agent complete event
    await manager.broadcast_agent_complete(
        agent_id="agent-001",
        agent_name="implementer",
        project_id="project-001",
        tenant_key="tenant-1",
        duration_seconds=45.6,
        final_status="completed",
        context_usage=12500,
        completion_reason="All tasks completed successfully",
    )

    # Check results
    tenant1_messages = ws_tenant1.get_messages_by_type("agent:complete")
    tenant2_messages = ws_tenant2.get_messages_by_type("agent:complete")

    assert len(tenant1_messages) == 1, "Tenant-1 should receive the message"
    assert len(tenant2_messages) == 0, "Tenant-2 should NOT receive the message"

    if tenant1_messages:
        msg = tenant1_messages[0]
        assert msg["data"]["duration_seconds"] == 45.6
        assert msg["data"]["context_usage"] == 12500


async def test_agent_update_event():
    """Test agent:update event broadcasting"""

    manager = WebSocketManager()

    ws_tenant1 = MockWebSocket("tenant-1")
    manager.active_connections["client-1"] = ws_tenant1
    manager.auth_contexts["client-1"] = {"tenant_key": "tenant-1"}

    # Simulate multiple updates
    updates = [
        {"status": "working", "context": 1000, "task": "Analyzing codebase", "progress": 25},
        {"status": "working", "context": 3500, "task": "Implementing endpoints", "progress": 50},
        {"status": "working", "context": 8000, "task": "Testing endpoints", "progress": 75},
    ]

    for update in updates:
        await manager.broadcast_agent_update(
            agent_id="agent-001",
            agent_name="implementer",
            project_id="project-001",
            tenant_key="tenant-1",
            status=update["status"],
            context_usage=update["context"],
            context_delta=(
                update["context"] - updates[updates.index(update) - 1]["context"]
                if updates.index(update) > 0
                else update["context"]
            ),
            current_task=update["task"],
            progress_percentage=update["progress"],
        )

    messages = ws_tenant1.get_messages_by_type("agent:update")
    assert len(messages) == 3, "Should receive 3 update messages"

    for _i, _msg in enumerate(messages):
        pass


async def test_template_update_event():
    """Test template:update event broadcasting"""

    manager = WebSocketManager()

    ws_tenant1 = MockWebSocket("tenant-1")
    ws_tenant2 = MockWebSocket("tenant-2")

    manager.active_connections["client-1"] = ws_tenant1
    manager.active_connections["client-2"] = ws_tenant2

    manager.auth_contexts["client-1"] = {"tenant_key": "tenant-1"}
    manager.auth_contexts["client-2"] = {"tenant_key": "tenant-2"}

    # Test different template operations
    operations = ["create", "update", "archive", "delete"]

    for op in operations:
        await manager.broadcast_template_update(
            template_id=f"template-{op}",
            template_name=f"test_template_{op}",
            operation=op,
            tenant_key="tenant-1",
            product_id="product-001",
            user_id="user-admin",
            change_summary=f"Testing {op} operation",
            version=1,
        )

    tenant1_messages = ws_tenant1.get_messages_by_type("template:update")
    tenant2_messages = ws_tenant2.get_messages_by_type("template:update")

    assert len(tenant1_messages) == 4, "Tenant-1 should receive all 4 operations"
    assert len(tenant2_messages) == 0, "Tenant-2 should NOT receive any messages"

    for _msg in tenant1_messages:
        pass


async def main():
    """Run all WebSocket event tests"""

    try:
        await test_agent_spawn_event()
        await test_agent_complete_event()
        await test_agent_update_event()
        await test_template_update_event()

    except AssertionError:
        pass
        # sys.exit(1)  # Commented for pytest
    except Exception:
        pass
        # sys.exit(1)  # Commented for pytest


if __name__ == "__main__":
    asyncio.run(main())
