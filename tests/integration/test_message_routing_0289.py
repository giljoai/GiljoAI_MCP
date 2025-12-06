#!/usr/bin/env python
"""
Integration tests for Message Routing WebSocket Emissions (Handover 0289 - RED Phase)

Tests WebSocket event emissions when messages are sent, acknowledged, and broadcast.
These tests are written in TDD RED phase - they SHOULD FAIL initially because
MessageService does NOT yet emit WebSocket events.

CRITICAL: These tests validate that MessageService correctly emits WebSocket events
for real-time agent communication monitoring.

Test Coverage:
1. Direct message sends emit 'message:sent' event
2. Broadcast messages emit 'message:new' event to all agents except sender
3. Message acknowledgment emits 'message:acknowledged' event
4. Multi-tenant isolation (messages don't leak across tenants)

Handover 0289: Message Routing Architecture Fix
Phase: RED (Failing Tests)
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.services.message_service import MessageService


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def test_tenant_a():
    """Create test tenant A identifier"""
    return f"tenant_a_{uuid4().hex[:8]}"


@pytest.fixture
def test_tenant_b():
    """Create test tenant B identifier"""
    return f"tenant_b_{uuid4().hex[:8]}"


@pytest.fixture
async def test_project_a(db_session, test_tenant_a):
    """Create test project for tenant A"""
    project = Project(
        id=str(uuid4()),
        name="Test Project A",
        description="Test project for tenant A",
        mission="Test mission for tenant A",
        status="active",
        tenant_key=test_tenant_a,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_project_b(db_session, test_tenant_b):
    """Create test project for tenant B"""
    project = Project(
        id=str(uuid4()),
        name="Test Project B",
        description="Test project for tenant B",
        mission="Test mission for tenant B",
        status="active",
        tenant_key=test_tenant_b,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager to verify event emissions"""
    mock_manager = MagicMock()

    # Mock the broadcast methods with AsyncMock
    mock_manager.broadcast_message_sent = AsyncMock(return_value=None)
    mock_manager.broadcast_job_message = AsyncMock(return_value=None)
    mock_manager.broadcast_message_acknowledged = AsyncMock(return_value=None)

    return mock_manager


@pytest_asyncio.fixture
async def message_service(db_manager, db_session, tenant_manager, mock_websocket_manager):
    """Create MessageService instance for testing with WebSocket manager injected"""
    # Configure db_manager to return the test's db_session
    # This ensures MessageService operations see test data
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def get_test_session():
        yield db_session

    # Override get_session_async to return test session
    db_manager.get_session_async = get_test_session

    # MessageService now accepts websocket_manager parameter (GREEN phase implemented)
    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager
    )
    return service


# ============================================================================
# Test 1: Direct Message Emits WebSocket Event
# ============================================================================


@pytest.mark.asyncio
async def test_direct_message_emits_websocket_event(
    message_service,
    test_project_a,
    test_tenant_a,
    mock_websocket_manager
):
    """
    RED PHASE TEST: Direct message should emit WebSocket 'message:sent' event

    Expected behavior:
    1. MessageService.send_message() is called with direct message
    2. Message is created in database
    3. WebSocket manager's broadcast_message_sent() is called
    4. Event contains correct message metadata

    EXPECTED TO FAIL: MessageService currently does NOT emit WebSocket events
    """
    # Act: Send direct message
    result = await message_service.send_message(
        to_agents=["implementer-1"],
        content="Implement feature X",
        project_id=str(test_project_a.id),
        message_type="direct",
        priority="high",
        from_agent="orchestrator",
    )

    # Assert: Message created successfully
    assert result["success"] is True, f"Message send failed: {result.get('error', 'Unknown error')}"
    assert "message_id" in result

    # Assert: WebSocket broadcast_message_sent was called
    # THIS WILL FAIL - MessageService does NOT have websocket_manager attribute yet
    assert hasattr(message_service, '_websocket_manager'), \
        "MessageService should have _websocket_manager attribute"

    # If websocket_manager exists, verify it was called
    if hasattr(message_service, '_websocket_manager') and message_service._websocket_manager:
        mock_websocket_manager.broadcast_message_sent.assert_called_once()

        # Assert: WebSocket call had correct parameters
        call_args = mock_websocket_manager.broadcast_message_sent.call_args
        assert call_args is not None

        # Verify event payload structure
        kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else {}
        assert kwargs.get("from_agent") == "orchestrator"
        assert "implementer-1" in (kwargs.get("to_agent") or kwargs.get("to_agents") or [])
        assert kwargs.get("message_type") == "direct"
        assert kwargs.get("tenant_key") == test_tenant_a


# ============================================================================
# Test 2: Broadcast Message Emits WebSocket Event
# ============================================================================


@pytest.mark.asyncio
async def test_broadcast_message_emits_websocket_event(
    message_service,
    test_project_a,
    test_tenant_a,
    mock_websocket_manager,
    db_session
):
    """
    RED PHASE TEST: Broadcast message should emit WebSocket 'message:new' event

    Expected behavior:
    1. MessageService.broadcast() is called
    2. Message is sent to all agents in project
    3. WebSocket manager's broadcast_job_message() is called for each agent
    4. Event is NOT sent to the sender agent (no echo)

    EXPECTED TO FAIL: MessageService currently does NOT emit WebSocket events
    """
    # Arrange: Create agent jobs in project (simulating active agents)
    from src.giljo_mcp.models import MCPAgentJob

    agent_jobs = [
        MCPAgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_a,
            project_id=str(test_project_a.id),
            agent_type=agent_type,
            mission=f"Test mission for {agent_type}",
            status="working",  # Valid status: waiting, working, blocked, complete, failed, cancelled, decommissioned
            created_at=datetime.now(timezone.utc),
        )
        for agent_type in ["implementer", "tester", "analyzer"]
    ]

    for job in agent_jobs:
        db_session.add(job)
    await db_session.commit()

    # Act: Broadcast message to all agents
    result = await message_service.broadcast(
        content="Project status update: All tests passing",
        project_id=str(test_project_a.id),
        priority="normal",
        from_agent="orchestrator"
    )

    # Assert: Broadcast successful
    assert result["success"] is True
    assert result["type"] == "broadcast"

    # Assert: WebSocket manager attribute exists
    # THIS WILL FAIL - MessageService does NOT have websocket_manager attribute yet
    assert hasattr(message_service, '_websocket_manager'), \
        "MessageService should have _websocket_manager attribute for WebSocket emissions"

    # If websocket_manager exists, verify it was called
    if hasattr(message_service, '_websocket_manager') and message_service._websocket_manager:
        # Assert: WebSocket broadcast_job_message was called for each recipient
        assert mock_websocket_manager.broadcast_job_message.call_count >= 1, \
            "WebSocket broadcast_job_message should be called for broadcast messages"


# ============================================================================
# Test 3: Message Acknowledgment Emits WebSocket Event
# ============================================================================


@pytest.mark.asyncio
async def test_message_acknowledgment_emits_websocket_event(
    message_service,
    test_project_a,
    test_tenant_a,
    mock_websocket_manager,
    db_session
):
    """
    RED PHASE TEST: Message acknowledgment should emit WebSocket event

    Expected behavior:
    1. Message is created and sent
    2. Agent acknowledges the message
    3. WebSocket manager's broadcast_message_acknowledged() is called
    4. Event contains acknowledgment metadata

    EXPECTED TO FAIL: MessageService currently does NOT emit WebSocket events
    """
    # Arrange: Create a message in the database
    message = Message(
        id=str(uuid4()),
        tenant_key=test_tenant_a,
        project_id=str(test_project_a.id),
        to_agents=["implementer-1"],
        message_type="direct",
        content="Review PR #42",
        priority="high",
        status="waiting",
        acknowledged_by=[],
        meta_data={"_from_agent": "orchestrator"},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Act: Acknowledge the message
    result = await message_service.acknowledge_message(
        message_id=str(message.id),
        agent_name="implementer-1"
    )

    # Assert: Acknowledgment successful
    assert result["success"] is True
    assert result["acknowledged_by"] == "implementer-1"

    # Assert: WebSocket manager attribute exists
    # THIS WILL FAIL - MessageService does NOT have websocket_manager attribute yet
    assert hasattr(message_service, '_websocket_manager'), \
        "MessageService should have _websocket_manager attribute for WebSocket emissions"

    # If websocket_manager exists, verify it was called
    if hasattr(message_service, '_websocket_manager') and message_service._websocket_manager:
        mock_websocket_manager.broadcast_message_acknowledged.assert_called_once()

        # Assert: WebSocket call had correct parameters
        call_args = mock_websocket_manager.broadcast_message_acknowledged.call_args
        assert call_args is not None

        # Verify event payload structure
        kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else {}
        assert kwargs.get("message_id") == str(message.id)
        assert kwargs.get("tenant_key") == test_tenant_a


# ============================================================================
# Test 4: Multi-Tenant Message Isolation
# ============================================================================


@pytest.mark.asyncio
async def test_multi_tenant_message_isolation(
    message_service,
    test_project_a,
    test_project_b,
    test_tenant_a,
    test_tenant_b,
    mock_websocket_manager,
    db_session
):
    """
    RED PHASE TEST: Messages in tenant A should NOT be visible to tenant B

    Expected behavior:
    1. Messages sent in tenant A are isolated from tenant B
    2. WebSocket events are only broadcast to the correct tenant
    3. No cross-tenant message leakage

    EXPECTED TO FAIL: MessageService currently does NOT emit WebSocket events
    (but tenant isolation should still work at database level)
    """
    # Arrange: Create messages in both tenants
    message_a = Message(
        id=str(uuid4()),
        tenant_key=test_tenant_a,
        project_id=str(test_project_a.id),
        to_agents=["implementer-a"],
        message_type="direct",
        content="Tenant A message",
        priority="normal",
        status="waiting",
        acknowledged_by=[],
        meta_data={"_from_agent": "orchestrator"},
        created_at=datetime.now(timezone.utc),
    )

    message_b = Message(
        id=str(uuid4()),
        tenant_key=test_tenant_b,
        project_id=str(test_project_b.id),
        to_agents=["implementer-b"],
        message_type="direct",
        content="Tenant B message",
        priority="normal",
        status="waiting",
        acknowledged_by=[],
        meta_data={"_from_agent": "orchestrator"},
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(message_a)
    db_session.add(message_b)
    await db_session.commit()

    # Act: Query messages for each tenant
    query_a = select(Message).where(
        Message.tenant_key == test_tenant_a,
        Message.project_id == str(test_project_a.id)
    )
    result_a = await db_session.execute(query_a)
    messages_a = result_a.scalars().all()

    query_b = select(Message).where(
        Message.tenant_key == test_tenant_b,
        Message.project_id == str(test_project_b.id)
    )
    result_b = await db_session.execute(query_b)
    messages_b = result_b.scalars().all()

    # Assert: Each tenant only sees their own messages
    assert len(messages_a) == 1
    assert len(messages_b) == 1
    assert messages_a[0].id == message_a.id
    assert messages_b[0].id == message_b.id
    assert messages_a[0].content == "Tenant A message"
    assert messages_b[0].content == "Tenant B message"

    # Assert: Messages don't leak across tenants
    assert message_a.id != message_b.id
    assert message_a.tenant_key != message_b.tenant_key

    # Assert: WebSocket manager attribute exists (needed for real-time isolation verification)
    # THIS WILL FAIL - MessageService does NOT have websocket_manager attribute yet
    assert hasattr(message_service, '_websocket_manager'), \
        "MessageService should have _websocket_manager attribute for tenant-isolated broadcasts"


# ============================================================================
# Test 5: Message Completion with WebSocket Emission
# ============================================================================


@pytest.mark.asyncio
async def test_message_completion_emits_websocket_event(
    message_service,
    test_project_a,
    test_tenant_a,
    mock_websocket_manager,
    db_session
):
    """
    RED PHASE TEST: Message completion should trigger appropriate WebSocket events

    Expected behavior:
    1. Message is completed with result
    2. Status changes to 'completed'
    3. WebSocket event is emitted for completion

    EXPECTED TO FAIL: MessageService currently does NOT emit WebSocket events
    """
    # Arrange: Create a message that's already acknowledged
    message = Message(
        id=str(uuid4()),
        tenant_key=test_tenant_a,
        project_id=str(test_project_a.id),
        to_agents=["implementer-1"],
        message_type="direct",
        content="Deploy to staging",
        priority="high",
        status="acknowledged",
        acknowledged_by=["implementer-1"],
        meta_data={"_from_agent": "orchestrator"},
        created_at=datetime.now(timezone.utc),
        acknowledged_at=datetime.now(timezone.utc),
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Act: Complete the message
    result = await message_service.complete_message(
        message_id=str(message.id),
        agent_name="implementer-1",
        result="Successfully deployed to staging environment"
    )

    # Assert: Completion successful
    assert result["success"] is True
    assert result["completed_by"] == "implementer-1"

    # Verify message status in database
    # Use string ID to avoid lazy loading issues after expire_all
    message_id_str = str(message.id)
    db_session.expire_all()
    query = select(Message).where(Message.id == message_id_str)
    db_result = await db_session.execute(query)
    updated_message = db_result.scalar_one()

    assert updated_message.status == "completed"
    assert updated_message.completed_by == "implementer-1"

    # Assert: WebSocket manager attribute exists
    # THIS WILL FAIL - MessageService does NOT have websocket_manager attribute yet
    assert hasattr(message_service, '_websocket_manager'), \
        "MessageService should have _websocket_manager attribute for completion event emissions"
