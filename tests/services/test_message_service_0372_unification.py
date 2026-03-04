"""
MessageService 0372 Unification Tests

Tests for Handover 0372: MessageService Unification
- Agent-ID routing (messages route to executor, not work order)
- Smart filtering (exclude_self, exclude_progress, message_types)
- New methods (broadcast_to_project)

Updated for Handover 0730: Exception-based patterns (no success wrapper)
Updated for Handover 0731c: Typed returns (SendMessageResult, BroadcastResult, etc.)
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project

# Import models using modular imports
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.schemas.service_responses import (
    BroadcastResult,
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
        name="Test Product 0372",
        description="Test product for MessageService 0372 unification tests",
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
    Returns tuple of (project, [agent_executions]).
    """
    # Create project
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project 0372",
        description="Test project for 0372 unification",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create agent jobs and executions
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
        agent = AgentExecution(
            job_id=job.job_id,
            agent_id=str(uuid4()),  # Explicit agent_id for executor identity
            tenant_key=test_tenant_key,
            agent_display_name=agent_display_name,
            status="waiting",  # Must be >= 1 per check constraint
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
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
    from contextlib import asynccontextmanager

    tenant_manager = TenantManager()

    # Mock db_manager.get_session_async() to return test session
    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,
    )
    return service


# ============================================================================
# Handover 0372 Tests - Agent-ID Routing
# ============================================================================


class TestMessageService0372AgentIDRouting:
    """Test agent-ID routing for succession support (Handover 0372)."""

    @pytest.mark.asyncio
    async def test_send_message_routes_by_agent_id_not_job_id(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify send_message() routes by agent_id (executor)
        instead of job_id (work order). This enables succession support.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[1]  # analyzer

        # Act: Send message using agent_display_name (should resolve to agent_id)
        result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Test message for agent-ID routing",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        # Handover 0731c: send_message returns SendMessageResult typed model
        assert isinstance(result, SendMessageResult)
        assert result.message_id is not None
        message_id = result.message_id

        # Assert: Message exists in database
        msg_result = await db_session.execute(select(Message).where(Message.id == message_id))
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None

        # Assert: Message routes to agent_id (not job_id)
        # The resolved agent should be the agent_id from AgentExecution
        assert recipient.agent_id in db_message.to_agents, (
            f"Expected agent_id {recipient.agent_id} in to_agents, got {db_message.to_agents}"
        )

    @pytest.mark.asyncio
    async def test_succession_routing_delivers_to_new_executor(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify messages route to NEW orchestrator after succession.

        Scenario:
        1. Original orchestrator exists
        2. Succession creates new orchestrator
        3. Send message to "orchestrator" type
        4. Verify message routes to NEW orchestrator (latest instance)
        """
        project, agents = test_project_with_agents
        old_orchestrator = agents[0]

        # Create new orchestrator instance (simulating succession)
        new_orchestrator = AgentExecution(
            job_id=old_orchestrator.job_id,  # Same work order
            agent_id=str(uuid4()),  # Different executor
            tenant_key=project.tenant_key,
            agent_display_name="orchestrator",
            status="working",  # Higher instance number (old was 1)
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(new_orchestrator)

        # Deactivate old orchestrator
        old_orchestrator.status = "complete"  # Must be valid status per check constraint
        await db_session.commit()
        await db_session.refresh(new_orchestrator)

        # Act: Send message to "orchestrator" agent type
        result = await message_service.send_message(
            to_agents=["orchestrator"],
            content="Message for successor orchestrator",
            project_id=project.id,
            from_agent="analyzer",
            tenant_key=project.tenant_key,
        )

        # Handover 0731c: send_message returns SendMessageResult typed model
        assert isinstance(result, SendMessageResult)
        assert result.message_id is not None
        message_id = result.message_id

        # Assert: Message routes to NEW orchestrator (agent_id)
        msg_result = await db_session.execute(select(Message).where(Message.id == message_id))
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert new_orchestrator.agent_id in db_message.to_agents, (
            f"Message should route to NEW orchestrator agent_id {new_orchestrator.agent_id}, got {db_message.to_agents}"
        )


# ============================================================================
# Handover 0372 Tests - Filtering Parameters
# ============================================================================


class TestMessageService0372Filtering:
    """Test filtering parameters in receive_messages() (Handover 0372)."""

    @pytest.mark.asyncio
    async def test_receive_messages_exclude_self_filters_own_messages(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify exclude_self parameter filters out
        messages from the same agent_id.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]

        # Act: Orchestrator sends broadcast (will include self)
        send_result = await message_service.send_message(
            to_agents=["all"],
            content="Broadcast from orchestrator",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        # Handover 0731c: send_message returns SendMessageResult typed model
        assert isinstance(send_result, SendMessageResult)
        assert send_result.message_id is not None

        # Act: Receive messages with exclude_self=True (default)
        result = await message_service.receive_messages(
            agent_id=orchestrator.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
            exclude_self=True,
        )

        # Handover 0731c: receive_messages returns MessageListResult typed model
        assert isinstance(result, MessageListResult)

        # Extract messages from result
        messages = result.messages

        # Assert: Orchestrator should NOT see their own broadcast
        for msg in messages:
            from_agent = msg.get("metadata", {}).get("_from_agent", "")
            assert from_agent != orchestrator.agent_id, (
                f"exclude_self should filter out own messages, but found message from {from_agent}"
            )

    @pytest.mark.asyncio
    async def test_receive_messages_exclude_progress_filters_progress_type(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify exclude_progress parameter filters out
        progress-type messages.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[1]

        # Arrange: Send progress message
        progress_result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Progress: 50% complete",
            project_id=project.id,
            message_type="progress",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        # Handover 0731c: send_message returns SendMessageResult typed model
        assert isinstance(progress_result, SendMessageResult)
        assert progress_result.message_id is not None

        # Arrange: Send regular message
        direct_result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Direct message",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        assert isinstance(direct_result, SendMessageResult)
        assert direct_result.message_id is not None

        # Act: Receive messages with exclude_progress=True (default)
        result = await message_service.receive_messages(
            agent_id=recipient.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
            exclude_progress=True,
        )

        # Extract messages from result
        messages = result.messages

        # Assert: No progress messages in results
        for msg in messages:
            msg_type = msg.get("type", "")
            assert msg_type != "progress", f"exclude_progress should filter out progress messages, but found {msg_type}"


# ============================================================================
# Handover 0372 Tests - New Methods
# ============================================================================


class TestMessageService0372NewMethods:
    """Test new methods from 0366b (Handover 0372)."""

    @pytest.mark.asyncio
    async def test_broadcast_to_project_sends_to_all_active_executions(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify broadcast_to_project() sends to all
        active executions in project.
        """
        project, agents = test_project_with_agents

        # Act: Broadcast to project
        result = await message_service.broadcast_to_project(
            project_id=project.id,
            content="Project-wide announcement",
            from_agent="orchestrator",
            tenant_key=project.tenant_key,
        )

        # Handover 0731c: broadcast_to_project returns BroadcastResult typed model
        assert isinstance(result, BroadcastResult)
        assert result.message_id is not None
        assert result.recipients_count == len(agents)
