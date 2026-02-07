"""
Tests for WebSocket Dependency Injection System

Tests the WebSocketDependency class and related dependency injection helpers
for production-grade WebSocket broadcasting with multi-tenant isolation.

Handover 0086B Phase 5.1: Backend Integration Testing
Created: 2025-11-02
Coverage Target: 95%+
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.dependencies.websocket import (
    WebSocketDependency,
    get_websocket_dependency,
    get_websocket_manager,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket_manager():
    """
    Create mock WebSocket manager with connections and auth contexts.

    Simulates a WebSocket manager with multiple clients connected
    across different tenants for testing multi-tenant isolation.
    """
    manager = MagicMock()

    # Mock active connections (client_id -> WebSocket)
    manager.active_connections = {
        "client_1": AsyncMock(),  # Tenant: tenant_abc
        "client_2": AsyncMock(),  # Tenant: tenant_abc
        "client_3": AsyncMock(),  # Tenant: tenant_xyz (different tenant)
    }

    # Mock authentication contexts (client_id -> auth_data)
    manager.auth_contexts = {
        "client_1": {"tenant_key": "tenant_abc", "user_id": "user_1"},
        "client_2": {"tenant_key": "tenant_abc", "user_id": "user_2"},
        "client_3": {"tenant_key": "tenant_xyz", "user_id": "user_3"},
    }

    return manager


@pytest.fixture
def mock_request_with_ws():
    """Create mock FastAPI request with WebSocket manager in app.state."""
    request = MagicMock()
    request.url.path = "/api/test"
    request.method = "POST"

    # Mock app.state with WebSocket manager
    ws_manager = MagicMock()
    request.app.state.websocket_manager = ws_manager

    return request


@pytest.fixture
def mock_request_without_ws():
    """Create mock FastAPI request WITHOUT WebSocket manager (graceful degradation test)."""
    request = MagicMock()
    request.url.path = "/api/test"
    request.method = "POST"

    # Mock app.state WITHOUT websocket_manager attribute
    request.app.state = MagicMock(spec=[])  # Empty spec = no attributes

    return request


# ============================================================================
# Test: get_websocket_manager Dependency
# ============================================================================


@pytest.mark.asyncio
async def test_get_websocket_manager_available(mock_request_with_ws):
    """
    Test get_websocket_manager returns manager when available.

    Validates that the dependency correctly retrieves the WebSocket manager
    from FastAPI app.state when it has been initialized.
    """
    # Act
    manager = await get_websocket_manager(mock_request_with_ws)

    # Assert
    assert manager is not None
    assert manager is mock_request_with_ws.app.state.websocket_manager


@pytest.mark.asyncio
async def test_get_websocket_manager_unavailable(mock_request_without_ws, caplog):
    """
    Test get_websocket_manager returns None when WebSocket not initialized.

    Validates graceful degradation when WebSocket functionality is unavailable.
    This is critical for allowing API endpoints to continue functioning even
    if WebSocket service is temporarily down.
    """
    # Act
    manager = await get_websocket_manager(mock_request_without_ws)

    # Assert
    assert manager is None

    # Verify debug logging
    assert "WebSocket manager not available in app state" in caplog.text
    assert mock_request_without_ws.url.path in caplog.text


# ============================================================================
# Test: WebSocketDependency Initialization
# ============================================================================


def test_websocket_dependency_init_with_manager(mock_websocket_manager):
    """Test WebSocketDependency initializes correctly with manager."""
    # Act
    ws_dep = WebSocketDependency(mock_websocket_manager)

    # Assert
    assert ws_dep.manager is mock_websocket_manager
    assert ws_dep.logger is not None
    assert ws_dep.is_available() is True


def test_websocket_dependency_init_without_manager():
    """Test WebSocketDependency initializes correctly without manager (graceful degradation)."""
    # Act
    ws_dep = WebSocketDependency(None)

    # Assert
    assert ws_dep.manager is None
    assert ws_dep.logger is not None
    assert ws_dep.is_available() is False


# ============================================================================
# Test: broadcast_to_tenant - Success Cases
# ============================================================================


@pytest.mark.asyncio
async def test_broadcast_to_tenant_success(mock_websocket_manager):
    """
    Test successful broadcast to all clients in a tenant.

    Validates that:
    - Only clients with matching tenant_key receive the message
    - Message structure is correct (type, timestamp, schema_version, data)
    - All matching clients receive the exact same message
    - Return value reflects actual sent count
    """
    # Arrange
    ws_dep = WebSocketDependency(mock_websocket_manager)

    # Act
    sent_count = await ws_dep.broadcast_to_tenant(
        tenant_key="tenant_abc", event_type="test:event", data={"message": "Hello tenant_abc"}
    )

    # Assert
    assert sent_count == 2  # client_1 and client_2 (both tenant_abc)

    # Verify client_1 received message
    mock_websocket_manager.active_connections["client_1"].send_json.assert_called_once()
    call_args = mock_websocket_manager.active_connections["client_1"].send_json.call_args[0][0]
    assert call_args["type"] == "test:event"
    assert call_args["data"] == {"message": "Hello tenant_abc"}
    assert "timestamp" in call_args
    assert call_args["schema_version"] == "1.0"

    # Verify client_2 received message
    mock_websocket_manager.active_connections["client_2"].send_json.assert_called_once()

    # Verify client_3 did NOT receive message (different tenant)
    mock_websocket_manager.active_connections["client_3"].send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_to_tenant_multi_tenant_isolation(mock_websocket_manager):
    """
    Test multi-tenant isolation in broadcast.

    CRITICAL SECURITY TEST: Ensures zero cross-tenant leakage.
    Validates that messages for tenant_xyz ONLY reach tenant_xyz clients.
    """
    # Arrange
    ws_dep = WebSocketDependency(mock_websocket_manager)

    # Act
    sent_count = await ws_dep.broadcast_to_tenant(
        tenant_key="tenant_xyz", event_type="sensitive:data", data={"secret": "tenant_xyz_only"}
    )

    # Assert
    assert sent_count == 1  # Only client_3 (tenant_xyz)

    # Verify ONLY client_3 received message
    mock_websocket_manager.active_connections["client_3"].send_json.assert_called_once()

    # CRITICAL: Verify client_1 and client_2 did NOT receive message
    mock_websocket_manager.active_connections["client_1"].send_json.assert_not_called()
    mock_websocket_manager.active_connections["client_2"].send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_to_tenant_exclude_client(mock_websocket_manager):
    """
    Test exclude_client parameter works correctly.

    Validates that specific clients can be excluded from broadcast
    (useful when originating client shouldn't receive echo).
    """
    # Arrange
    ws_dep = WebSocketDependency(mock_websocket_manager)

    # Act
    sent_count = await ws_dep.broadcast_to_tenant(
        tenant_key="tenant_abc", event_type="test:event", data={"message": "Broadcast"}, exclude_client="client_1"
    )

    # Assert
    assert sent_count == 1  # Only client_2 (client_1 excluded)

    # Verify client_1 did NOT receive message
    mock_websocket_manager.active_connections["client_1"].send_json.assert_not_called()

    # Verify client_2 received message
    mock_websocket_manager.active_connections["client_2"].send_json.assert_called_once()


# ============================================================================
# Test: broadcast_to_tenant - Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_broadcast_to_tenant_validation_empty_tenant_key():
    """
    Test broadcast_to_tenant raises ValueError for empty tenant_key.

    Validates input validation - tenant_key is required and cannot be empty.
    """
    # Arrange
    ws_dep = WebSocketDependency(MagicMock())

    # Act & Assert
    with pytest.raises(ValueError, match="tenant_key cannot be empty"):
        await ws_dep.broadcast_to_tenant(tenant_key="", event_type="test:event", data={})


@pytest.mark.asyncio
async def test_broadcast_to_tenant_validation_empty_event_type():
    """
    Test broadcast_to_tenant raises ValueError for empty event_type.

    Validates input validation - event_type is required and cannot be empty.
    """
    # Arrange
    ws_dep = WebSocketDependency(MagicMock())

    # Act & Assert
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        await ws_dep.broadcast_to_tenant(tenant_key="tenant_abc", event_type="", data={})


@pytest.mark.asyncio
async def test_broadcast_to_tenant_graceful_degradation_no_manager(caplog):
    """
    Test graceful degradation when WebSocket manager is unavailable.

    Validates that broadcast_to_tenant returns 0 and logs warning
    when called without an available WebSocket manager.
    This allows API endpoints to continue functioning even if
    WebSocket service is temporarily unavailable.
    """
    # Arrange
    ws_dep = WebSocketDependency(None)  # No manager

    # Act
    sent_count = await ws_dep.broadcast_to_tenant(
        tenant_key="tenant_abc", event_type="test:event", data={"message": "test"}
    )

    # Assert
    assert sent_count == 0
    assert "WebSocket manager not available for broadcast" in caplog.text


@pytest.mark.asyncio
async def test_broadcast_to_tenant_partial_failure(mock_websocket_manager, caplog):
    """
    Test broadcast handles partial failures gracefully.

    Validates that if one client's send fails, the broadcast continues
    to other clients and logs the failure properly.
    """
    # Arrange
    ws_dep = WebSocketDependency(mock_websocket_manager)

    # Make client_1 fail on send
    mock_websocket_manager.active_connections["client_1"].send_json.side_effect = Exception("Connection closed")

    # Act
    sent_count = await ws_dep.broadcast_to_tenant(
        tenant_key="tenant_abc", event_type="test:event", data={"message": "test"}
    )

    # Assert
    assert sent_count == 1  # Only client_2 succeeded

    # Verify failure was logged
    assert "Failed to send WebSocket message to client client_1" in caplog.text
    assert "Connection closed" in caplog.text

    # Verify broadcast completed with summary
    assert "WebSocket broadcast completed: 1 sent, 1 failed" in caplog.text


# ============================================================================
# Test: send_to_project Helper
# ============================================================================


@pytest.mark.asyncio
async def test_send_to_project(mock_websocket_manager):
    """
    Test send_to_project adds project_id to data payload.

    Validates that this specialized helper correctly includes project_id
    for client-side filtering.
    """
    # Arrange
    ws_dep = WebSocketDependency(mock_websocket_manager)

    # Act
    sent_count = await ws_dep.send_to_project(
        tenant_key="tenant_abc",
        project_id="proj_123",
        event_type="agent:created",
        data={"agent_display_name": "orchestrator"},
    )

    # Assert
    assert sent_count == 2

    # Verify project_id was added to data
    call_args = mock_websocket_manager.active_connections["client_1"].send_json.call_args[0][0]
    assert call_args["data"]["project_id"] == "proj_123"
    assert call_args["data"]["agent_display_name"] == "orchestrator"


# ============================================================================
# Test: get_websocket_dependency Factory
# ============================================================================


@pytest.mark.asyncio
async def test_get_websocket_dependency_with_manager(mock_request_with_ws):
    """
    Test get_websocket_dependency factory returns WebSocketDependency with manager.

    Validates the full dependency injection chain:
    Request -> get_websocket_manager -> get_websocket_dependency -> WebSocketDependency
    """
    # Act
    manager = await get_websocket_manager(mock_request_with_ws)
    ws_dep = await get_websocket_dependency(manager)

    # Assert
    assert isinstance(ws_dep, WebSocketDependency)
    assert ws_dep.manager is mock_request_with_ws.app.state.websocket_manager
    assert ws_dep.is_available() is True


@pytest.mark.asyncio
async def test_get_websocket_dependency_without_manager(mock_request_without_ws):
    """
    Test get_websocket_dependency factory returns WebSocketDependency without manager.

    Validates graceful degradation through the full dependency chain.
    """
    # Act
    manager = await get_websocket_manager(mock_request_without_ws)
    ws_dep = await get_websocket_dependency(manager)

    # Assert
    assert isinstance(ws_dep, WebSocketDependency)
    assert ws_dep.manager is None
    assert ws_dep.is_available() is False
