"""
MessageService 0372 Unification Tests

Tests for Handover 0372: MessageService Unification
- Agent-ID routing (messages route to executor, not work order)
- Smart filtering (exclude_self, exclude_progress, message_types)
- New methods (broadcast_to_project, acknowledge_message)

These tests follow TDD RED phase - they should FAIL until implementation is complete.
"""

import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import models using modular imports
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.database import DatabaseManager
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

        # Assert: Message sent successfully
        assert result["success"] is True
        message_id = result["data"]["message_id"]

        # Assert: Message exists in database
        msg_result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None

        # Assert: Message routes to agent_id (not job_id)
        # The resolved agent should be the agent_id from AgentExecution
        assert recipient.agent_id in db_message.to_agents, \
            f"Expected agent_id {recipient.agent_id} in to_agents, got {db_message.to_agents}"

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
            messages=[],
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

        # Assert: Message sent successfully
        assert result["success"] is True
        message_id = result["data"]["message_id"]

        # Assert: Message routes to NEW orchestrator (agent_id)
        msg_result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert new_orchestrator.agent_id in db_message.to_agents, \
            f"Message should route to NEW orchestrator agent_id {new_orchestrator.agent_id}, got {db_message.to_agents}"


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
        assert send_result["success"] is True

        # Act: Receive messages with exclude_self=True (default)
        result = await message_service.receive_messages(
            agent_id=orchestrator.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
            exclude_self=True,
        )

        # Assert: Result is a dict (not a list)
        assert isinstance(result, dict)
        assert "messages" in result or "success" in result

        # Extract messages from result
        messages = result.get("messages", [])

        # Assert: Orchestrator should NOT see their own broadcast
        for msg in messages:
            from_agent = msg.get("meta_data", {}).get("_from_agent", "")
            assert from_agent != orchestrator.agent_id, \
                f"exclude_self should filter out own messages, but found message from {from_agent}"

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
        assert progress_result["success"] is True

        # Arrange: Send regular message
        direct_result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Direct message",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        assert direct_result["success"] is True

        # Act: Receive messages with exclude_progress=True (default)
        result = await message_service.receive_messages(
            agent_id=recipient.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
            exclude_progress=True,
        )

        # Extract messages from result
        messages = result.get("messages", [])

        # Assert: No progress messages in results
        for msg in messages:
            msg_type = msg.get("message_type", msg.get("type", ""))
            assert msg_type != "progress", \
                f"exclude_progress should filter out progress messages, but found {msg_type}"

    @pytest.mark.asyncio
    async def test_receive_messages_message_types_allowlist_works(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify message_types parameter acts as allowlist.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[1]

        # Arrange: Send messages of different types
        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Direct message",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Broadcast message",
            project_id=project.id,
            message_type="broadcast",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="System message",
            project_id=project.id,
            message_type="system",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        # Act: Receive only "direct" messages
        result = await message_service.receive_messages(
            agent_id=recipient.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
            message_types=["direct"],
        )

        # Extract messages from result
        messages = result.get("messages", [])

        # Assert: Only "direct" messages returned
        assert len(messages) >= 1, "Should have at least one direct message"
        for msg in messages:
            msg_type = msg.get("message_type", msg.get("type", ""))
            assert msg_type == "direct", \
                f"message_types allowlist should only return 'direct', but found {msg_type}"


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

        # Assert: Broadcast succeeded
        assert result["success"] is True
        assert result["count"] == len(agents)

        # Assert: All agents received the message
        for agent in agents:
            await db_session.refresh(agent)
            found = False
            if agent.messages:
                for msg in agent.messages:
                    if "Project-wide announcement" in msg.get("text", ""):
                        found = True
                        break
            assert found, f"{agent.agent_display_name} should receive broadcast"

    @pytest.mark.asyncio
    async def test_acknowledge_message_explicit_works(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        HANDOVER 0372 TEST: Verify explicit acknowledge_message() method works.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[1]

        # Arrange: Send message
        send_result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Message to acknowledge",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        assert send_result["success"] is True
        message_id = send_result["message_id"]

        # Act: Explicitly acknowledge message
        ack_result = await message_service.acknowledge_message(
            message_id=message_id,
            agent_id=recipient.agent_id,
            tenant_key=project.tenant_key,
        )

        # Assert: Acknowledgment succeeded
        assert ack_result["success"] is True
        assert ack_result["acknowledged"] is True
        assert ack_result["message_id"] == message_id

        # Assert: Message status updated
        msg_result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert db_message.status == "acknowledged"
        assert recipient.agent_id in db_message.acknowledged_by
