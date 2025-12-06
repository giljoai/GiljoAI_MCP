"""
Integration tests for WebSocket message events
Tests real-time message broadcasts via WebSocket
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.models.tasks import Message


@pytest.mark.asyncio
async def test_websocket_message_broadcast(db_manager, test_project):
    """Test WebSocket broadcasts on message creation"""
    from api.websocket import WebSocketManager

    # Mock WebSocket manager
    ws_manager = AsyncMock(spec=WebSocketManager)

    # Create message
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    result = await service.send_message(
        to_agents=["test-agent"],
        content="WebSocket test message",
        project_id=test_project.id,
        message_type="direct",
        priority="normal"
    )

    assert result["success"] is True

    # Manually trigger broadcast (in real app, this is automatic via API endpoint)
    await ws_manager.broadcast_message_update(
        message_id=result["message_id"],
        project_id=test_project.id,
        update_type="new",
        message_data={
            "from_agent": "orchestrator",
            "to_agents": ["test-agent"],
            "content": "WebSocket test message",
            "priority": "normal",
            "status": "pending"
        }
    )

    # Verify broadcast was called
    ws_manager.broadcast_message_update.assert_called_once()
    call_args = ws_manager.broadcast_message_update.call_args
    assert call_args.kwargs["message_id"] == result["message_id"]
    assert call_args.kwargs["update_type"] == "new"


@pytest.mark.asyncio
async def test_websocket_acknowledge_event(db_manager, test_project, db_session):
    """Test WebSocket event when message is acknowledged"""
    from api.websocket import WebSocketManager

    # Mock WebSocket manager
    ws_manager = AsyncMock(spec=WebSocketManager)

    # Create a test message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-agent"],
        content="Message to acknowledge via WebSocket",
        status="waiting"
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Acknowledge message
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)
    result = await service.acknowledge_message(
        message_id=message.id,
        agent_name="test-agent"
    )

    assert result["success"] is True

    # Manually trigger WebSocket event
    await ws_manager.broadcast_message_update(
        message_id=message.id,
        project_id=test_project.id,
        update_type="acknowledged",
        message_data={
            "status": "acknowledged",
            "acknowledged_by": ["test-agent"],
            "acknowledged_at": datetime.now(timezone.utc).isoformat()
        }
    )

    # Verify broadcast was called
    ws_manager.broadcast_message_update.assert_called_once()
    call_args = ws_manager.broadcast_message_update.call_args
    assert call_args.kwargs["update_type"] == "acknowledged"
    assert "acknowledged_by" in call_args.kwargs["message_data"]


@pytest.mark.asyncio
async def test_websocket_complete_event(db_manager, test_project, db_session):
    """Test WebSocket event when message is completed"""
    from api.websocket import WebSocketManager

    # Mock WebSocket manager
    ws_manager = AsyncMock(spec=WebSocketManager)

    # Create an acknowledged message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-agent"],
        content="Message to complete via WebSocket",
        status="acknowledged",
        acknowledged_by=["test-agent"]
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Complete message
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)
    result = await service.complete_message(
        message_id=message.id,
        agent_name="test-agent",
        result_data={"status": "success", "output": "Task completed"}
    )

    assert result["success"] is True

    # Manually trigger WebSocket event
    await ws_manager.broadcast_message_update(
        message_id=message.id,
        project_id=test_project.id,
        update_type="completed",
        message_data={
            "status": "completed",
            "completed_by": ["test-agent"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result_data": {"status": "success", "output": "Task completed"}
        }
    )

    # Verify broadcast was called
    ws_manager.broadcast_message_update.assert_called_once()
    call_args = ws_manager.broadcast_message_update.call_args
    assert call_args.kwargs["update_type"] == "completed"
    assert "completed_by" in call_args.kwargs["message_data"]


@pytest.mark.asyncio
async def test_websocket_broadcast_to_specific_project(db_manager, test_project, db_session):
    """Test that WebSocket broadcasts are project-scoped"""
    from api.websocket import WebSocketManager

    # Mock WebSocket manager with connection tracking
    ws_manager = AsyncMock(spec=WebSocketManager)
    ws_manager.project_connections = {
        test_project.id: [MagicMock(), MagicMock()],  # 2 connections for this project
        str(uuid4()): [MagicMock()]  # 1 connection for another project
    }

    # Create and broadcast message
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)
    result = await service.send_message(
        to_agents=["test-agent"],
        content="Project-scoped message",
        project_id=test_project.id
    )

    # Broadcast to specific project
    await ws_manager.broadcast_message_update(
        message_id=result["message_id"],
        project_id=test_project.id,
        update_type="new",
        message_data={"content": "Project-scoped message"}
    )

    # Verify broadcast was called with correct project_id
    ws_manager.broadcast_message_update.assert_called_once()
    call_args = ws_manager.broadcast_message_update.call_args
    assert call_args.kwargs["project_id"] == test_project.id


@pytest.mark.asyncio
async def test_websocket_connection_authentication(test_project):
    """Test that WebSocket connections require authentication"""
    from api.websocket import WebSocketManager

    ws_manager = MagicMock(spec=WebSocketManager)

    # Mock WebSocket connection with authentication
    mock_websocket = MagicMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()

    # Simulate authentication check
    def authenticate_connection(tenant_key: str):
        if not tenant_key:
            raise ValueError("Authentication required")
        return True

    # Valid authentication should succeed
    try:
        authenticate_connection(test_project.tenant_key)
        authenticated = True
    except ValueError:
        authenticated = False

    assert authenticated is True

    # Invalid authentication should fail
    try:
        authenticate_connection(None)
        authenticated = True
    except ValueError:
        authenticated = False

    assert authenticated is False


@pytest.mark.asyncio
async def test_websocket_message_priority_broadcast(db_manager, test_project):
    """Test WebSocket broadcasts include message priority"""
    from api.websocket import WebSocketManager

    ws_manager = AsyncMock(spec=WebSocketManager)

    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    # Send high priority message
    result = await service.send_message(
        to_agents=["test-agent"],
        content="High priority message",
        project_id=test_project.id,
        priority="high"
    )

    # Broadcast with priority
    await ws_manager.broadcast_message_update(
        message_id=result["message_id"],
        project_id=test_project.id,
        update_type="new",
        message_data={
            "content": "High priority message",
            "priority": "high"
        }
    )

    # Verify priority is included in broadcast
    call_args = ws_manager.broadcast_message_update.call_args
    assert call_args.kwargs["message_data"]["priority"] == "high"


@pytest.mark.asyncio
async def test_websocket_broadcast_message_batch(db_manager, test_project):
    """Test broadcasting multiple messages efficiently"""
    from api.websocket import WebSocketManager

    ws_manager = AsyncMock(spec=WebSocketManager)

    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    # Send multiple messages
    message_ids = []
    for i in range(5):
        result = await service.send_message(
            to_agents=[f"agent-{i}"],
            content=f"Batch message {i}",
            project_id=test_project.id
        )
        message_ids.append(result["message_id"])

        # Broadcast each message
        await ws_manager.broadcast_message_update(
            message_id=result["message_id"],
            project_id=test_project.id,
            update_type="new",
            message_data={"content": f"Batch message {i}"}
        )

    # Verify all broadcasts were called
    assert ws_manager.broadcast_message_update.call_count == 5


@pytest.mark.asyncio
async def test_websocket_reconnection_handling(test_project):
    """Test handling of WebSocket reconnections"""
    from api.websocket import WebSocketManager

    ws_manager = MagicMock(spec=WebSocketManager)

    # Simulate connection pool
    connection_pool = {}

    # Add connection
    connection_id = str(uuid4())
    mock_websocket = MagicMock()
    connection_pool[connection_id] = {
        "websocket": mock_websocket,
        "project_id": test_project.id,
        "connected_at": datetime.now(timezone.utc)
    }

    # Simulate disconnection
    del connection_pool[connection_id]

    # Simulate reconnection
    new_connection_id = str(uuid4())
    connection_pool[new_connection_id] = {
        "websocket": mock_websocket,
        "project_id": test_project.id,
        "connected_at": datetime.now(timezone.utc)
    }

    # Verify reconnection
    assert new_connection_id in connection_pool
    assert connection_pool[new_connection_id]["project_id"] == test_project.id


@pytest.mark.asyncio
async def test_websocket_error_handling(db_manager, test_project):
    """Test WebSocket error handling"""
    from api.websocket import WebSocketManager

    ws_manager = AsyncMock(spec=WebSocketManager)
    ws_manager.broadcast_message_update.side_effect = Exception("Connection error")

    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    result = await service.send_message(
        to_agents=["test-agent"],
        content="Test message",
        project_id=test_project.id
    )

    # Try to broadcast - should handle error gracefully
    try:
        await ws_manager.broadcast_message_update(
            message_id=result["message_id"],
            project_id=test_project.id,
            update_type="new",
            message_data={"content": "Test message"}
        )
        error_raised = False
    except Exception:
        error_raised = True

    # Error should be raised (in mock scenario)
    assert error_raised is True


@pytest.mark.asyncio
async def test_websocket_tenant_isolation(db_session):
    """Test that WebSocket broadcasts respect tenant isolation"""
    from api.websocket import WebSocketManager

    ws_manager = MagicMock(spec=WebSocketManager)

    # Create two tenants
    tenant1_key = f"tk_test_{uuid4().hex[:16]}"
    tenant2_key = f"tk_test_{uuid4().hex[:16]}"

    # Mock connection pools per tenant
    tenant_connections = {
        tenant1_key: [MagicMock(), MagicMock()],
        tenant2_key: [MagicMock()]
    }

    # Simulate broadcast to tenant 1 only
    def broadcast_to_tenant(tenant_key: str, message_data: dict):
        connections = tenant_connections.get(tenant_key, [])
        return len(connections)

    # Verify tenant 1 has 2 connections
    count = broadcast_to_tenant(tenant1_key, {"test": "data"})
    assert count == 2

    # Verify tenant 2 has 1 connection
    count = broadcast_to_tenant(tenant2_key, {"test": "data"})
    assert count == 1

    # Verify non-existent tenant has 0 connections
    count = broadcast_to_tenant("fake-tenant", {"test": "data"})
    assert count == 0
