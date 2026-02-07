"""
Integration tests for WebSocket event naming and payload structure.

These tests verify that backend WebSocket events match frontend expectations.
Tests follow TDD RED phase - they SHOULD FAIL against current implementation.

Handover 0286 - Jobs Dashboard WebSocket Wiring

CRITICAL: These tests are BEHAVIORAL tests, not implementation tests.
- We test the event TYPE that gets emitted (e.g., 'agent:status_changed')
- We test payload field names (e.g., 'status' not 'new_status')
- We test that tenant_key is included in all payloads
- We DO NOT test internal implementation details

Expected to FAIL until backend is updated to match frontend expectations.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from api.websocket import WebSocketManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def websocket_manager():
    """Create WebSocketManager instance for testing"""
    manager = WebSocketManager()
    yield manager
    # Cleanup any connections
    manager.active_connections.clear()
    manager.auth_contexts.clear()


@pytest_asyncio.fixture
async def mock_websocket_connection(websocket_manager):
    """Create a mock WebSocket connection with tenant authentication"""
    tenant_key = str(uuid.uuid4())
    client_id = str(uuid.uuid4())

    # Create mock WebSocket
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()

    # Add connection with authentication
    websocket_manager.active_connections[client_id] = mock_ws
    websocket_manager.auth_contexts[client_id] = {"tenant_key": tenant_key, "user_id": str(uuid.uuid4())}

    return {"manager": websocket_manager, "client_id": client_id, "tenant_key": tenant_key, "mock_ws": mock_ws}


@pytest_asyncio.fixture
async def test_agent_job_data(db_session, test_project):
    """Create test agent job and execution in database"""

    # Create AgentJob first (contains project_id)
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        job_type="implementer",
        mission="Test mission for implementer agent",
        status="active",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Create AgentExecution for this job
    execution = AgentExecution(
        job_id=job.job_id,
        tenant_key=test_project.tenant_key,
        agent_display_name="implementer",
        status="waiting",  # Valid status: 'waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)

    # Return both job and execution for testing
    return {"job": job, "execution": execution}


@pytest_asyncio.fixture
async def test_message_data(test_agent_job_data, test_project):
    """Create test message data (no database - just for WebSocket testing)"""
    # We don't need a real Message model instance for WebSocket testing
    # Just return the data that would be broadcast
    return {
        "id": str(uuid.uuid4()),
        "from_agent": "orchestrator",
        "to_agent": test_agent_job_data["job"].job_id,
        "content": "Test message content for integration testing",
        "project_id": test_project.id,
        "tenant_key": test_project.tenant_key,
    }


# ============================================================================
# EVENT TYPE TESTS - Verify correct event names are emitted
# ============================================================================


@pytest.mark.asyncio
async def test_status_change_emits_agent_status_changed_event(mock_websocket_connection, test_agent_job_data):
    """
    Test that status changes emit 'agent:status_changed' event.

    Frontend expects: 'agent:status_changed'
    Backend currently emits: 'agent_job:status_update', 'agent_job:acknowledged', etc.

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 874: on('agent:status_changed', handleStatusUpdate)
    - Backend: websocket.py line 815: event_type = "agent_job:status_update"
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast status update (use same tenant as mock connection)
    # Valid statuses: 'waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
    )

    # Verify WebSocket was called
    assert mock_ws.send_json.called, "WebSocket send_json should be called"

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: Frontend expects 'agent:status_changed', not 'agent_job:*'
    assert sent_message["type"] == "agent:status_changed", (
        f"Expected event type 'agent:status_changed', "
        f"got '{sent_message['type']}'. "
        "Frontend handler: on('agent:status_changed', handleStatusUpdate)"
    )


@pytest.mark.asyncio
async def test_message_sent_emits_message_sent_event(mock_websocket_connection, test_message_data):
    """
    Test that sending messages emits 'message:sent' event.

    Frontend expects: 'message:sent'
    Backend currently emits: 'agent_communication:message_sent'

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 875: on('message:sent', handleMessageSent)
    - Backend: websocket.py line 985: "type": "agent_communication:message_sent"
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast message sent
    await manager.broadcast_message_sent(
        message_id=test_message_data["id"],
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        from_agent="developer",
        to_agent=test_message_data["to_agent"],
        message_type="task",
        content_preview="Test message",
        priority=1,
    )

    # Verify WebSocket was called
    assert mock_ws.send_json.called, "WebSocket send_json should be called"

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: Frontend expects 'message:sent', not 'agent_communication:message_sent'
    assert sent_message["type"] == "message:sent", (
        f"Expected event type 'message:sent', "
        f"got '{sent_message['type']}'. "
        "Frontend handler: on('message:sent', handleMessageSent)"
    )


@pytest.mark.asyncio
async def test_message_acknowledged_emits_message_acknowledged_event(mock_websocket_connection, test_message_data):
    """
    Test that message acknowledgment emits 'message:acknowledged' event.

    Frontend expects: 'message:acknowledged'
    Backend currently emits: 'agent_communication:message_acknowledged'

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 876: on('message:acknowledged', handleMessageAcknowledged)
    - Backend: websocket.py line 1048: "type": "agent_communication:message_acknowledged"
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast message acknowledged
    await manager.broadcast_message_acknowledged(
        message_id=test_message_data["id"],
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        agent_id=test_message_data["to_agent"],
    )

    # Verify WebSocket was called
    assert mock_ws.send_json.called, "WebSocket send_json should be called"

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: Frontend expects 'message:acknowledged', not 'agent_communication:message_acknowledged'
    assert sent_message["type"] == "message:acknowledged", (
        f"Expected event type 'message:acknowledged', "
        f"got '{sent_message['type']}'. "
        "Frontend handler: on('message:acknowledged', handleMessageAcknowledged)"
    )


@pytest.mark.asyncio
async def test_new_message_emits_message_new_event(mock_websocket_connection, test_message_data):
    """
    Test that new messages emit 'message:new' event.

    Frontend expects: 'message:new'
    Backend currently emits: 'agent_job:message'

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 877: on('message:new', handleNewMessage)
    - Backend: websocket.py line 878: "type": "agent_job:message"
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast new job message
    await manager.broadcast_job_message(
        job_id=str(uuid.uuid4()),
        message_id=test_message_data["id"],
        from_agent=test_message_data["from_agent"],
        tenant_key=tenant_key,
        to_agent=test_message_data["to_agent"],
        message_type="status",
        content_preview="New message from agent",
    )

    # Verify WebSocket was called
    assert mock_ws.send_json.called, "WebSocket send_json should be called"

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: Frontend expects 'message:new', not 'agent_job:message'
    assert sent_message["type"] == "message:new", (
        f"Expected event type 'message:new', "
        f"got '{sent_message['type']}'. "
        "Frontend handler: on('message:new', handleNewMessage)"
    )


# ============================================================================
# PAYLOAD FIELD TESTS - Verify correct field names in event data
# ============================================================================


@pytest.mark.asyncio
async def test_status_payload_includes_status_field_not_new_status(mock_websocket_connection, test_agent_job_data):
    """
    Test that status change payload uses 'status' field, not 'new_status'.

    Frontend expects: data.status
    Backend currently provides: data.new_status

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 864: agent.status = data.status
    - Backend: websocket.py line 821: "new_status": new_status
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast status update
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
    )

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # Frontend handler: agent.status = data.status
    assert "status" in sent_message["data"], (
        "Payload must include 'status' field for frontend compatibility. Frontend expects: data.status"
    )
    assert sent_message["data"]["status"] == "working", "status field should contain the new status value"

    # Backend should NOT use 'new_status' as primary field
    # (Can keep for backwards compatibility but 'status' is required)


@pytest.mark.asyncio
async def test_message_payload_includes_message_field_not_content_preview(mock_websocket_connection, test_message_data):
    """
    Test that message payload uses 'message' field, not 'content_preview'.

    Frontend expects: data.message
    Backend currently provides: data.content_preview

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 785: text: data.message
    - Backend: websocket.py line 992: "content_preview": content_preview[:200]
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    test_message_text = "Important message from developer"

    # Broadcast message sent
    await manager.broadcast_message_sent(
        message_id=test_message_data["id"],
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        from_agent="developer",
        to_agent=test_message_data["to_agent"],
        message_type="task",
        content_preview=test_message_text,
        priority=1,
    )

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # Frontend handler: text: data.message
    assert "message" in sent_message["data"], (
        "Payload must include 'message' field for frontend compatibility. Frontend expects: data.message"
    )
    # Backend should rename 'content_preview' to 'message'


@pytest.mark.asyncio
async def test_all_events_include_tenant_key_in_payload(
    mock_websocket_connection, test_agent_job_data, test_message_data
):
    """
    Test that all event payloads include tenant_key for frontend validation.

    Frontend performs: data.tenant_key !== currentTenantKey.value check
    Backend currently: Does not include tenant_key in payload data

    This test SHOULD FAIL until backend is updated.

    References:
    - Frontend: JobsTab.vue line 768: if (data.tenant_key !== currentTenantKey.value)
    - Frontend: JobsTab.vue line 798: if (data.tenant_key !== currentTenantKey.value)
    - Backend: websocket.py - tenant_key not in message["data"]
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Test 1: Status update event
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="active",
    )

    sent_message = mock_ws.send_json.call_args[0][0]
    assert "tenant_key" in sent_message["data"], (
        "Status update payload must include tenant_key. "
        "Frontend checks: if (data.tenant_key !== currentTenantKey.value)"
    )
    assert sent_message["data"]["tenant_key"] == tenant_key, "tenant_key must match the broadcast value"

    # Test 2: Message sent event
    await manager.broadcast_message_sent(
        message_id=test_message_data["id"],
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        from_agent="developer",
        to_agent=test_message_data["to_agent"],
        message_type="task",
        content_preview="Test",
        priority=1,
    )

    sent_message = mock_ws.send_json.call_args[0][0]
    assert "tenant_key" in sent_message["data"], "Message sent payload must include tenant_key"

    # Test 3: Message acknowledged event
    await manager.broadcast_message_acknowledged(
        message_id=test_message_data["id"],
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        agent_id=test_message_data["to_agent"],
    )

    sent_message = mock_ws.send_json.call_args[0][0]
    assert "tenant_key" in sent_message["data"], "Message acknowledged payload must include tenant_key"

    # Test 4: New message event
    await manager.broadcast_job_message(
        job_id=str(uuid.uuid4()),
        message_id=test_message_data["id"],
        from_agent=test_message_data["from_agent"],
        tenant_key=tenant_key,
        to_agent=test_message_data["to_agent"],
        message_type="status",
        content_preview="Test",
    )

    sent_message = mock_ws.send_json.call_args[0][0]
    assert "tenant_key" in sent_message["data"], "New message payload must include tenant_key"


# ============================================================================
# MULTI-TENANT ISOLATION TESTS - Verify events don't leak across tenants
# ============================================================================


@pytest.mark.asyncio
async def test_events_only_broadcast_to_matching_tenant():
    """
    Test that WebSocket events are only sent to clients with matching tenant_key.

    This verifies multi-tenant isolation at the WebSocket broadcast level.
    """
    manager = WebSocketManager()

    # Create two tenants
    tenant1_key = str(uuid.uuid4())
    tenant2_key = str(uuid.uuid4())

    # Create WebSocket connections for each tenant
    client1_id = str(uuid.uuid4())
    client2_id = str(uuid.uuid4())

    mock_ws1 = MagicMock()
    mock_ws1.send_json = AsyncMock()
    mock_ws2 = MagicMock()
    mock_ws2.send_json = AsyncMock()

    # Add connections
    manager.active_connections[client1_id] = mock_ws1
    manager.auth_contexts[client1_id] = {"tenant_key": tenant1_key}

    manager.active_connections[client2_id] = mock_ws2
    manager.auth_contexts[client2_id] = {"tenant_key": tenant2_key}

    # Broadcast to tenant1 only
    await manager.broadcast_job_status_update(
        job_id=str(uuid.uuid4()),
        agent_display_name="worker",
        tenant_key=tenant1_key,
        old_status="waiting",
        new_status="working",
    )

    # Verify only tenant1 client received the message
    assert mock_ws1.send_json.called, "Tenant1 client should receive message"
    assert not mock_ws2.send_json.called, "Tenant2 client should NOT receive message"


# ============================================================================
# COMPREHENSIVE EVENT STRUCTURE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_status_change_event_complete_structure(mock_websocket_connection, test_agent_job_data):
    """
    Test the complete expected structure of agent:status_changed event.

    Expected structure based on frontend handler in JobsTab.vue:
    {
      "type": "agent:status_changed",
      "data": {
        "job_id": "...",
        "status": "active",
        "tenant_key": "...",
        "agent_display_name": "implementer"
      },
      "timestamp": "2025-01-15T10:00:00Z"
    }
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
    )

    sent_message = mock_ws.send_json.call_args[0][0]

    # Verify top-level structure
    assert "type" in sent_message
    assert "data" in sent_message
    assert "timestamp" in sent_message

    # Verify event type
    assert sent_message["type"] == "agent:status_changed"

    # Verify required data fields
    data = sent_message["data"]
    assert "job_id" in data
    assert "status" in data
    assert "tenant_key" in data
    assert "agent_display_name" in data

    # Verify data values
    assert data["job_id"] == test_agent_job_data["job"].job_id
    assert data["status"] == "working"
    assert data["tenant_key"] == tenant_key
    assert data["agent_display_name"] == test_agent_job_data["execution"].agent_display_name


@pytest.mark.asyncio
async def test_message_sent_event_complete_structure(mock_websocket_connection, test_message_data):
    """
    Test the complete expected structure of message:sent event.

    Expected structure based on frontend handler in JobsTab.vue:
    {
      "type": "message:sent",
      "data": {
        "message_id": "...",
        "to_agent": "...",
        "message": "...",
        "priority": "medium",
        "timestamp": "...",
        "tenant_key": "..."
      },
      "timestamp": "2025-01-15T10:00:00Z"
    }
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    test_message = "Important task for agent"

    await manager.broadcast_message_sent(
        message_id=test_message_data["id"],
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        from_agent="developer",
        to_agent=test_message_data["to_agent"],
        message_type="task",
        content_preview=test_message,
        priority=1,
    )

    sent_message = mock_ws.send_json.call_args[0][0]

    # Verify event type
    assert sent_message["type"] == "message:sent"

    # Verify required data fields
    data = sent_message["data"]
    assert "message_id" in data
    assert "to_agent" in data
    assert "message" in data  # NOT content_preview
    assert "priority" in data
    assert "timestamp" in data
    assert "tenant_key" in data

    # Verify data values
    assert data["message_id"] == test_message_data["id"]
    assert data["to_agent"] == test_message_data["to_agent"]
    assert data["tenant_key"] == tenant_key


# ============================================================================
# HANDOVER 0463: Project-Aware Event Filtering Tests
# ============================================================================


@pytest.mark.asyncio
async def test_status_update_includes_project_id_when_provided(mock_websocket_connection, test_agent_job_data):
    """
    Test that project_id is included in agent:status_changed payload when provided.

    Handover 0463: Ghost Agents Cross-Project Event Leak Fix

    When project_id is provided to broadcast_job_status_update(), it MUST be
    included in the WebSocket event payload to enable frontend project-aware
    filtering.

    Frontend can then filter: if (data.project_id !== activeProjectId) return;

    References:
    - Backend: websocket.py line 834: project_id parameter added
    - Backend: websocket.py lines 852-854: project_id conditionally added to payload
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Create a project_id for testing
    project_id = str(uuid.uuid4())

    # Broadcast status update WITH project_id
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
        project_id=project_id,  # CRITICAL: Handover 0463 addition
    )

    # Verify WebSocket was called
    assert mock_ws.send_json.called, "WebSocket send_json should be called"

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: project_id MUST be in payload when provided
    assert "project_id" in sent_message["data"], (
        "Payload must include 'project_id' field when provided to "
        "broadcast_job_status_update(). This enables frontend project-aware "
        "filtering to prevent cross-project ghost agent rows."
    )

    # Verify project_id value matches
    assert sent_message["data"]["project_id"] == project_id, (
        f"Expected project_id '{project_id}', got '{sent_message['data']['project_id']}'"
    )


@pytest.mark.asyncio
async def test_status_update_excludes_project_id_when_not_provided(mock_websocket_connection, test_agent_job_data):
    """
    Test backward compatibility - project_id NOT in payload when not provided.

    Handover 0463: Ghost Agents Cross-Project Event Leak Fix

    When project_id is NOT provided (None), the field should be excluded from
    the payload to maintain backward compatibility with callers that don't
    provide project_id.

    This ensures existing code paths (that don't know about project_id) continue
    to work without breaking changes.

    References:
    - Backend: websocket.py lines 852-854: if project_id is not None check
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast status update WITHOUT project_id (backward compatibility)
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
        # project_id intentionally NOT provided (None by default)
    )

    # Verify WebSocket was called
    assert mock_ws.send_json.called, "WebSocket send_json should be called"

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: project_id should NOT be in payload when not provided
    assert "project_id" not in sent_message["data"], (
        "Payload should NOT include 'project_id' field when not provided to "
        "broadcast_job_status_update(). This maintains backward compatibility "
        "with existing callers that don't provide project_id."
    )

    # Verify other required fields are still present (sanity check)
    assert "job_id" in sent_message["data"]
    assert "status" in sent_message["data"]
    assert "tenant_key" in sent_message["data"]


@pytest.mark.asyncio
async def test_status_update_with_explicit_none_project_id(mock_websocket_connection, test_agent_job_data):
    """
    Test explicit None project_id excludes field from payload.

    Edge case: Caller explicitly passes project_id=None (vs not providing it).
    Should behave identically to not providing project_id.

    Handover 0463: Ghost Agents Cross-Project Event Leak Fix
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Broadcast with explicit project_id=None
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name=test_agent_job_data["execution"].agent_display_name,
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
        project_id=None,  # Explicit None
    )

    # Get the message that was sent
    sent_message = mock_ws.send_json.call_args[0][0]

    # CRITICAL: Explicit None should exclude field from payload
    assert "project_id" not in sent_message["data"], (
        "Explicit project_id=None should exclude field from payload, maintaining backward compatibility."
    )


@pytest.mark.asyncio
async def test_project_id_enables_cross_project_filtering(mock_websocket_connection, test_agent_job_data):
    """
    Integration test: project_id enables frontend to filter cross-project events.

    Scenario:
    1. User has two projects open in different browser tabs
    2. Agent status change happens in Project A
    3. Both tabs receive the WebSocket event (same tenant_key)
    4. Tab viewing Project B should ignore the event using project_id filter

    Handover 0463: This is the core use case - preventing ghost agent rows
    when users have multiple project tabs open simultaneously.
    """
    manager = mock_websocket_connection["manager"]
    mock_ws = mock_websocket_connection["mock_ws"]
    tenant_key = mock_websocket_connection["tenant_key"]

    # Simulate two different projects
    project_a_id = str(uuid.uuid4())
    project_b_id = str(uuid.uuid4())

    # Broadcast event for Project A
    await manager.broadcast_job_status_update(
        job_id=test_agent_job_data["job"].job_id,
        agent_display_name="implementer",
        tenant_key=tenant_key,
        old_status="waiting",
        new_status="working",
        project_id=project_a_id,  # Event belongs to Project A
    )

    sent_message = mock_ws.send_json.call_args[0][0]

    # Frontend logic (simulated):
    # Tab viewing Project B should reject this event
    active_project_in_tab = project_b_id
    event_project_id = sent_message["data"].get("project_id")

    # CRITICAL: Frontend can now filter cross-project events
    should_process_event = (
        event_project_id is None  # Backward compat: process if no project_id
        or event_project_id == active_project_in_tab  # Match active project
    )

    assert not should_process_event, (
        "Frontend should reject event when project_id doesn't match active project. "
        f"Event project: {event_project_id}, Active project: {active_project_in_tab}"
    )

    # Verify event structure is correct for filtering
    assert event_project_id == project_a_id
    assert event_project_id != project_b_id
