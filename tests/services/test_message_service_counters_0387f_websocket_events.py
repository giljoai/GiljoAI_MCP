"""
MessageService WebSocket Event Counter Tests - Handover 0387g

Tests that WebSocket events include correct counter values:
- message:sent event includes sender_sent_count and recipient_waiting_count
- message:received event includes waiting_count
- message:acknowledged event includes waiting_count and read_count
- Broadcast message events include correct counters for all recipients

Split from test_message_service_counters_0387f.py during test reorganization.
Updated for Handover 0731c: Typed returns (SendMessageResult, AcknowledgeMessageResult, etc.)
"""

from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import (
    AcknowledgeMessageResult,
    SendMessageResult,
)
from src.giljo_mcp.services.message_service import MessageService


# ============================================================================
# WebSocket Event Counter Tests - Handover 0387g
# ============================================================================


@pytest.mark.asyncio
async def test_message_sent_event_includes_sender_counter(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
    mock_websocket_manager: MagicMock,
):
    """Test that message:sent event includes sender's messages_sent_count."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    analyzer = agents[1]  # recipient

    # Send message
    result = await message_service.send_message(
        to_agents=[analyzer.agent_id],
        content="Test message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)

    # Verify WebSocket broadcast_message_sent was called
    assert mock_websocket_manager.broadcast_message_sent.called

    # Get the call arguments
    call_args = mock_websocket_manager.broadcast_message_sent.call_args

    # Verify sender_sent_count is included in the call
    # This will fail until we add the parameter to the broadcast call
    assert "sender_sent_count" in call_args.kwargs
    assert call_args.kwargs["sender_sent_count"] == 1


@pytest.mark.asyncio
async def test_message_sent_event_includes_recipient_counter(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
    mock_websocket_manager: MagicMock,
):
    """Test that message:sent event includes recipient's messages_waiting_count."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    analyzer = agents[1]  # recipient

    # Send message
    result = await message_service.send_message(
        to_agents=[analyzer.agent_id],
        content="Test message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)

    # Verify WebSocket broadcast_message_sent was called
    assert mock_websocket_manager.broadcast_message_sent.called

    # Get the call arguments
    call_args = mock_websocket_manager.broadcast_message_sent.call_args

    # Verify recipient_waiting_count is included in the call
    # This will fail until we add the parameter to the broadcast call
    assert "recipient_waiting_count" in call_args.kwargs
    assert call_args.kwargs["recipient_waiting_count"] == 1


@pytest.mark.asyncio
async def test_message_received_event_includes_waiting_counter(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
    mock_websocket_manager: MagicMock,
):
    """Test that message:received event includes recipient's messages_waiting_count."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    analyzer = agents[1]  # recipient

    # Send message
    result = await message_service.send_message(
        to_agents=[analyzer.agent_id],
        content="Test message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)

    # Verify WebSocket broadcast_message_received was called
    assert mock_websocket_manager.broadcast_message_received.called

    # Get the call arguments
    call_args = mock_websocket_manager.broadcast_message_received.call_args

    # Verify waiting_count is included in the call
    # This will fail until we add the parameter to the broadcast call
    assert "waiting_count" in call_args.kwargs
    assert call_args.kwargs["waiting_count"] == 1


@pytest.mark.asyncio
async def test_message_acknowledged_event_includes_counters(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
    mock_websocket_manager: MagicMock,
):
    """Test that message:acknowledged event includes waiting_count and read_count."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    analyzer = agents[1]  # recipient

    # Send message first
    result = await message_service.send_message(
        to_agents=[analyzer.agent_id],
        content="Test message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )
    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)
    message_id = result.message_id

    # Reset mock to track only acknowledge call
    mock_websocket_manager.reset_mock()

    # Acknowledge message
    ack_result = await message_service.acknowledge_message(
        message_id=message_id,
        agent_id=analyzer.agent_id,
        tenant_key=test_tenant_key,
    )
    # Handover 0731c: acknowledge_message returns AcknowledgeMessageResult typed model
    assert isinstance(ack_result, AcknowledgeMessageResult)
    assert ack_result.acknowledged is True

    # Verify WebSocket broadcast_message_acknowledged was called
    assert mock_websocket_manager.broadcast_message_acknowledged.called

    # Get the call arguments
    call_args = mock_websocket_manager.broadcast_message_acknowledged.call_args

    # Verify waiting_count and read_count are included in the call
    # This will fail until we add the parameters to the broadcast call
    assert "waiting_count" in call_args.kwargs
    assert "read_count" in call_args.kwargs
    assert call_args.kwargs["waiting_count"] == 0  # decremented from 1
    assert call_args.kwargs["read_count"] == 1  # incremented from 0


@pytest.mark.skip(reason="0750c3: broadcast counter format changed")
@pytest.mark.asyncio
async def test_broadcast_message_includes_counters_for_multiple_recipients(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
    mock_websocket_manager: MagicMock,
):
    """Test that broadcast message events include correct counter values for all recipients."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    recipients = agents[1:]  # 2 recipients

    # Send broadcast message
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)

    # Verify broadcast_message_sent was called
    assert mock_websocket_manager.broadcast_message_sent.called
    sent_call_args = mock_websocket_manager.broadcast_message_sent.call_args

    # Sender should have sent_count = 1 (not number of recipients)
    assert "sender_sent_count" in sent_call_args.kwargs
    assert sent_call_args.kwargs["sender_sent_count"] == 1

    # Verify broadcast_message_received was called
    assert mock_websocket_manager.broadcast_message_received.called
    received_call_args = mock_websocket_manager.broadcast_message_received.call_args

    # Each recipient should have waiting_count = 1
    # Note: The broadcast creates individual messages for each recipient
    # so the waiting_count shown should be for the recipients collectively
    assert "waiting_count" in received_call_args.kwargs
    # The waiting_count parameter should reflect that recipients now have 1 waiting message
    assert received_call_args.kwargs["waiting_count"] == 1
