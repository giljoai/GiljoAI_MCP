"""
MessageService Counter Update Tests - Handover 0387f

Tests that MessageService correctly updates counter columns instead of JSONB:
- send_message() increments sent/waiting counters
- Broadcast messages update sender's sent_count by 1, each recipient's waiting_count by 1
- Counters survive without JSONB persistence
- Multiple messages accumulate counters

Split from test_message_service_counters_0387f.py during test reorganization.
Updated for Handover 0731c: Typed returns (SendMessageResult, etc.)
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import (
    SendMessageResult,
)
from src.giljo_mcp.services.message_service import MessageService


# ============================================================================
# Counter Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_send_message_increments_sender_sent_count(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """Test that send_message increments sender's messages_sent_count by 1."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    analyzer = agents[1]  # recipient

    # Verify initial counts
    assert orchestrator.messages_sent_count == 0
    assert analyzer.messages_waiting_count == 0

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

    # Refresh agents to get updated counts
    await db_session.refresh(orchestrator)
    await db_session.refresh(analyzer)

    # Verify sender's sent_count incremented by 1
    assert orchestrator.messages_sent_count == 1

    # Verify recipient's waiting_count incremented by 1
    assert analyzer.messages_waiting_count == 1


@pytest.mark.asyncio
async def test_send_broadcast_increments_sender_sent_count_once(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """Test that broadcast increments sender's sent_count by 1, not N."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    recipients = agents[1:]  # 2 recipients

    # Verify initial counts
    assert orchestrator.messages_sent_count == 0

    # Send broadcast to multiple recipients
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)

    # Refresh agents to get updated counts
    await db_session.refresh(orchestrator)

    # CRITICAL: sender's sent_count should be 1, not len(recipients)
    assert orchestrator.messages_sent_count == 1


@pytest.mark.asyncio
async def test_send_broadcast_increments_each_recipient_waiting_count(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """Test that broadcast increments each recipient's waiting_count by 1."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]  # sender
    recipients = agents[1:]  # 2 recipients

    # Verify initial counts
    for agent in recipients:
        assert agent.messages_waiting_count == 0

    # Send broadcast
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast message",
        project_id=project.id,
        from_agent=orchestrator.agent_display_name,
        tenant_key=test_tenant_key,
    )

    # Handover 0731c: send_message returns SendMessageResult typed model
    assert isinstance(result, SendMessageResult)

    # Refresh recipients to get updated counts
    for agent in recipients:
        await db_session.refresh(agent)

    # Each recipient should have waiting_count = 1
    for agent in recipients:
        assert agent.messages_waiting_count == 1


@pytest.mark.asyncio
async def test_counters_survive_without_jsonb_persistence(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """Test that counters are persisted independently of JSONB field."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]
    analyzer = agents[1]

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

    # Store IDs before expiring objects
    orchestrator_id = orchestrator.agent_id
    analyzer_id = analyzer.agent_id

    # Commit transaction and clear session to simulate page reload
    await db_session.commit()
    db_session.expire_all()  # Not async

    # Re-fetch agents from database
    orchestrator_result = await db_session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == orchestrator_id)
    )
    refreshed_orchestrator = orchestrator_result.scalar_one()

    analyzer_result = await db_session.execute(select(AgentExecution).where(AgentExecution.agent_id == analyzer_id))
    refreshed_analyzer = analyzer_result.scalar_one()

    # Verify counters persisted correctly
    assert refreshed_orchestrator.messages_sent_count == 1
    assert refreshed_analyzer.messages_waiting_count == 1


@pytest.mark.asyncio
async def test_multiple_messages_accumulate_counters(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """Test that sending multiple messages accumulates counter values."""
    project, agents = test_project_with_agents
    orchestrator = agents[0]
    analyzer = agents[1]

    # Send 3 messages
    for i in range(3):
        result = await message_service.send_message(
            to_agents=[analyzer.agent_id],
            content=f"Test message {i}",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
            tenant_key=test_tenant_key,
        )
        # Handover 0731c: send_message returns SendMessageResult typed model
        assert isinstance(result, SendMessageResult)

    # Refresh agents
    await db_session.refresh(orchestrator)
    await db_session.refresh(analyzer)

    # Verify accumulated counts
    assert orchestrator.messages_sent_count == 3
    assert analyzer.messages_waiting_count == 3
