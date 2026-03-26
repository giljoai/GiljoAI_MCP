"""
MessageService Contract Tests - Handover 0295

Tests that MessageService correctly implements the messaging contract:
- Messages create database rows
- Counters are updated on AgentExecution (Handover 0700c: JSONB messages removed)
- Acknowledgments update counter columns
- Completions preserve acknowledgment state
- Multi-tenant isolation is enforced

Updated for Handover 0730: Exception-based patterns (no success wrapper)
Updated for Handover 0700c: AgentExecution.messages JSONB removed, using counter columns
Updated for Handover 0731c: Typed returns (SendMessageResult, CompleteMessageResult, etc.)
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project

# Import models using modular imports (Post-Handover 0128a)
from src.giljo_mcp.models.tasks import Message, MessageAcknowledgment, MessageRecipient
from src.giljo_mcp.schemas.service_responses import (
    CompleteMessageResult,
    MessageListResult,
    SendMessageResult,
)
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for testing without real WebSocket connections."""
    mock = MagicMock()
    mock.broadcast_message_sent = AsyncMock()
    mock.broadcast_message_received = AsyncMock()
    mock.broadcast_message_acknowledged = AsyncMock()
    mock.broadcast_job_message = AsyncMock()
    return mock


@pytest.fixture
async def test_tenant_key() -> str:
    """Generate unique tenant key for test isolation."""
    return f"test-tenant-{uuid4().hex[:8]}"


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create a test product for tests."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Test product for MessageService contract tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project_with_agents(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> tuple[Project, list[AgentExecution]]:
    """
    Create a test project with multiple agents.
    Returns tuple of (project, [agent_jobs]).
    """
    # Create project
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project for Message Contract",
        description="Test project with agents",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create agent jobs and executions (Handover 0372: Separate work order from executor)
    agent_display_names = ["orchestrator", "analyzer", "implementer", "tester"]
    agents = []
    for agent_display_name in agent_display_names:
        # Create work order (AgentJob)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=project.id,
            job_type=agent_display_name,
            mission=f"Test mission for {agent_display_name}",
            status="active",
        )
        db_session.add(job)

        # Create executor instance (AgentExecution)
        # Handover 0700c: No messages JSONB - using counter columns only
        agent = AgentExecution(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name=agent_display_name,
            status="waiting",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)

    return project, agents


@pytest.fixture
async def message_service(
    db_manager: DatabaseManager,
    db_session: AsyncSession,
    mock_websocket_manager: MagicMock,
    test_tenant_key: str,
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
    from contextlib import asynccontextmanager

    tenant_manager = MagicMock(spec=TenantManager)
    tenant_manager.get_current_tenant.return_value = test_tenant_key

    # Mock db_manager.get_session_async() to return test session
    # This ensures MessageService uses the transactional test session
    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    # Patch the db_manager's method
    db_manager.get_session_async = mock_get_session_async

    # Handover 0372: Pass test_session for transaction-aware testing
    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,  # Share test transaction
    )
    return service


# ============================================================================
# Test Cases
# ============================================================================


class TestMessageCreationAndCounterUpdates:
    """Test that messages create database rows and update counters."""

    @pytest.mark.asyncio
    async def test_send_message_creates_message_and_updates_counters(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        mock_websocket_manager: MagicMock,
    ):
        """
        CRITICAL CONTRACT TEST: Verify that send_message():
        1. Creates a Message row in the database
        2. Increments sender's messages_sent_count
        3. Increments recipient's messages_waiting_count
        4. Emits WebSocket events correctly

        Handover 0700c: JSONB messages removed - using counter columns only
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]  # orchestrator
        recipient = agents[1]  # analyzer

        # Verify initial counts
        assert orchestrator.messages_sent_count == 0
        assert recipient.messages_waiting_count == 0

        # Act: Send message from orchestrator to analyzer
        # Handover 0731c: Returns SendMessageResult typed model
        result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Analyze the codebase for patterns",
            project_id=project.id,
            message_type="direct",
            priority="high",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        # Assert: Message sending succeeded - typed return
        assert isinstance(result, SendMessageResult)
        assert result.message_id is not None
        message_id = result.message_id

        # Assert: Message row exists in database
        msg_result = await db_session.execute(select(Message).where(Message.id == message_id))
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None, "Message should exist in database"
        assert db_message.project_id == project.id
        assert db_message.tenant_key == project.tenant_key
        # Handover 0840b: Recipients stored in MessageRecipient junction table
        recip_result = await db_session.execute(
            select(MessageRecipient).where(MessageRecipient.message_id == message_id)
        )
        recipients = recip_result.scalars().all()
        assert len(recipients) == 1
        assert recipients[0].agent_id == recipient.agent_id
        assert db_message.content == "Analyze the codebase for patterns"
        assert db_message.message_type == "direct"
        assert db_message.priority == "high"
        assert db_message.status == "pending"

        # Refresh agents to get updated counters (Handover 0700c: Counter-based)
        await db_session.refresh(orchestrator)
        await db_session.refresh(recipient)

        # Assert: Sender's sent_count incremented
        assert orchestrator.messages_sent_count == 1

        # Assert: Recipient's waiting_count incremented
        assert recipient.messages_waiting_count == 1

        # Assert: WebSocket events were emitted
        mock_websocket_manager.broadcast_message_sent.assert_awaited_once()
        mock_websocket_manager.broadcast_message_received.assert_awaited_once()


class TestMessageCompletion:
    """Test that completions preserve acknowledgment state."""

    @pytest.mark.asyncio
    async def test_complete_message_marks_completed_and_preserves_ack(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        CRITICAL CONTRACT TEST: Verify that complete_message():
        1. Sets Message.status = "completed"
        2. Sets Message.result with completion result
        3. Preserves MessageAcknowledgment rows (0840b: junction table)
        4. Creates MessageCompletion row (0840b: junction table)
        5. Sets Message.completed_at timestamp
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[2]  # implementer

        # Arrange: Send a message
        send_result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Implement feature X",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        message_id = send_result.message_id

        # Auto-acknowledge via receive_messages (Handover 0326)
        receive_result = await message_service.receive_messages(
            agent_id=recipient.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
        )
        assert isinstance(receive_result, MessageListResult)
        assert len(receive_result.messages) >= 1, (
            f"Expected messages but got {receive_result.count}"
        )

        # Act: Complete the message
        complete_result = await message_service.complete_message(
            message_id=message_id,
            agent_name=recipient.agent_display_name,
            result="Feature X implemented successfully with 95% test coverage",
        )

        # Assert: Completion succeeded - typed return
        assert isinstance(complete_result, CompleteMessageResult)
        assert complete_result.message_id == message_id
        assert complete_result.completed_by == recipient.agent_display_name

        # Assert: Message status is "completed"
        msg_result = await db_session.execute(select(Message).where(Message.id == message_id))
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert db_message.status == "completed"
        assert db_message.result == "Feature X implemented successfully with 95% test coverage"
        assert db_message.completed_at is not None

        # Handover 0840b: Check completions via MessageCompletion junction table
        from src.giljo_mcp.models.tasks import MessageCompletion
        comp_result = await db_session.execute(
            select(MessageCompletion).where(MessageCompletion.message_id == message_id)
        )
        completions = comp_result.scalars().all()
        assert any(c.agent_id == recipient.agent_display_name for c in completions), (
            f"Expected completion by {recipient.agent_display_name} in completions"
        )

        # Handover 0840b: Verify acknowledgments preserved via MessageAcknowledgment junction table
        ack_result = await db_session.execute(
            select(MessageAcknowledgment).where(MessageAcknowledgment.message_id == message_id)
        )
        acks = ack_result.scalars().all()
        assert any(a.agent_id == recipient.agent_id for a in acks), (
            f"Acknowledgment should be preserved after completion. Expected {recipient.agent_id} in acknowledgments"
        )


class TestBroadcastMessaging:
    """Test broadcast message resolution to all agents."""

    @pytest.mark.asyncio
    async def test_broadcast_updates_all_recipient_counters(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        CRITICAL CONTRACT TEST: Verify that send_message(to_agents=['all']):
        1. Resolves to all active agents in the project
        2. Increments waiting_count for each recipient
        3. Sender's sent_count is incremented by 1 (not N)
        4. Emits WebSocket events to all recipients

        Handover 0700c: JSONB messages removed - using counter columns only
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        other_agents = agents[1:]  # All non-orchestrator agents

        # Verify initial counts
        assert orchestrator.messages_sent_count == 0
        for agent in other_agents:
            assert agent.messages_waiting_count == 0

        # Act: Broadcast message to all agents
        result = await message_service.send_message(
            to_agents=["all"],
            content="Project status: All systems operational",
            project_id=project.id,
            message_type="broadcast",
            priority="normal",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        # Assert: Broadcast succeeded - typed return
        assert isinstance(result, SendMessageResult)
        message_id = result.message_id

        # Assert: Message row exists
        msg_result = await db_session.execute(select(Message).where(Message.id == message_id))
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert db_message.message_type == "broadcast"

        # Refresh agents
        await db_session.refresh(orchestrator)
        for agent in other_agents:
            await db_session.refresh(agent)

        # Assert: Sender's sent_count is 1 (not len(other_agents))
        assert orchestrator.messages_sent_count == 1

        # Assert: Each recipient has waiting_count = 1
        for agent in other_agents:
            assert agent.messages_waiting_count == 1, (
                f"{agent.agent_display_name} should have waiting_count=1"
            )


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestMessageServiceErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_project_fails(
        self,
        message_service: MessageService,
    ):
        """Test that sending to nonexistent project raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await message_service.send_message(
                to_agents=["analyzer"],
                content="Test message",
                project_id="nonexistent-project-id",
                from_agent="orchestrator",
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_complete_nonexistent_message_fails(
        self,
        message_service: MessageService,
    ):
        """Test that completing nonexistent message raises ResourceNotFoundError."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await message_service.complete_message(
                message_id="nonexistent-message-id",
                agent_name="analyzer",
                result="Test result",
            )

        assert "not found" in str(exc_info.value).lower()
