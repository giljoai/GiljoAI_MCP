"""
Display Name in Messages Tests - Handover 0827a

Tests that MessageService correctly:
1. Stores _from_display_name in metadata at send time
2. Returns display name in from_agent at receive time (new messages)
3. Falls back to batch-resolving display names for old messages
4. Resolves completed agents by display name
5. Includes from_agent_id in receive_messages output
"""

import random
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message, MessageRecipient
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
    mock.broadcast_job_status_change = AsyncMock()
    mock.broadcast_job_status_update = AsyncMock()
    return mock


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create a test product."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Display Name Test Product",
        description="Product for 0827a display name tests",
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
    """Create a test project with agents that have display names."""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Display Name Test Project",
        description="Test project for 0827a",
        mission="Test display name feature",
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    agent_configs = [
        ("Orchestrator Agent", "orchestrator", "working"),
        ("Code Analyzer", "analyzer", "waiting"),
        ("TDD Implementor", "implementer", "waiting"),
    ]
    agents = []
    for display_name, role, status in agent_configs:
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=project.id,
            job_type=role,
            mission=f"Test mission for {role}",
            status="active",
        )
        db_session.add(job)

        agent = AgentExecution(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name=display_name,
            status=status,
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
# Test Cases
# ============================================================================


class TestDisplayNameAtSendTime:
    """Test that _from_display_name is stored in message metadata at send time."""

    @pytest.mark.asyncio
    async def test_send_message_stores_display_name_in_metadata(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        test_tenant_key: str,
    ):
        """
        Verify that when an agent sends a message, its display name is stored
        in meta_data['_from_display_name'] on the Message row.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]  # "Orchestrator Agent"
        analyzer = agents[1]  # "Code Analyzer"

        result = await message_service.send_message(
            to_agents=[analyzer.agent_id],
            content="Please analyze this code",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_id,
            tenant_key=test_tenant_key,
        )

        assert result.message_id is not None

        # Verify the stored message has from_display_name column (Handover 0840b)
        from sqlalchemy import select

        msg_result = await db_session.execute(
            select(Message).where(Message.id == result.message_id)
        )
        msg = msg_result.scalar_one()
        assert msg.from_display_name == "Orchestrator Agent"
        assert msg.from_agent_id == orchestrator.agent_id

    @pytest.mark.asyncio
    async def test_send_message_from_orchestrator_string_stores_display_name(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        test_tenant_key: str,
    ):
        """
        When from_agent is None (defaulting to 'orchestrator'), _from_display_name
        should be 'orchestrator' since there is no agent to look up.
        """
        project, agents = test_project_with_agents
        analyzer = agents[1]

        result = await message_service.send_message(
            to_agents=[analyzer.agent_id],
            content="Hello from orchestrator",
            project_id=project.id,
            message_type="direct",
            from_agent=None,
            tenant_key=test_tenant_key,
        )

        from sqlalchemy import select

        msg_result = await db_session.execute(
            select(Message).where(Message.id == result.message_id)
        )
        msg = msg_result.scalar_one()
        # Handover 0840b: from_display_name is now a column
        assert msg.from_display_name == "orchestrator"


class TestDisplayNameAtReceiveTime:
    """Test that receive_messages returns display names correctly."""

    @pytest.mark.asyncio
    async def test_receive_messages_returns_display_name_for_new_messages(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        test_tenant_key: str,
    ):
        """
        Messages sent after 0827a should have _from_display_name in metadata.
        receive_messages should return the display name in 'from_agent'.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]  # "Orchestrator Agent"
        analyzer = agents[1]  # "Code Analyzer"

        # Send a message (will store _from_display_name)
        await message_service.send_message(
            to_agents=[analyzer.agent_id],
            content="Analyze the codebase",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_id,
            tenant_key=test_tenant_key,
        )

        # Receive messages as the analyzer
        result = await message_service.receive_messages(
            agent_id=analyzer.agent_id,
            tenant_key=test_tenant_key,
        )

        assert result.count >= 1
        msg = result.messages[0]
        assert msg["from_agent"] == "Orchestrator Agent"

    @pytest.mark.asyncio
    async def test_receive_messages_returns_display_name_for_old_messages_fallback(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        test_tenant_key: str,
    ):
        """
        Old messages (pre-0827a) that don't have _from_display_name in metadata
        should still resolve the sender's display name via fallback batch lookup.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]  # "Orchestrator Agent"
        analyzer = agents[1]  # "Code Analyzer"

        # Manually create a "legacy" message without from_display_name
        # Handover 0840b: Use new columns and MessageRecipient junction table
        legacy_msg = Message(
            project_id=project.id,
            tenant_key=test_tenant_key,
            content="Legacy message without display name",
            message_type="direct",
            priority="normal",
            status="pending",
            from_agent_id=orchestrator.agent_id,
        )
        db_session.add(legacy_msg)
        await db_session.flush()
        db_session.add(MessageRecipient(
            message_id=legacy_msg.id,
            agent_id=analyzer.agent_id,
            tenant_key=test_tenant_key,
        ))
        await db_session.commit()

        # Receive messages as the analyzer
        result = await message_service.receive_messages(
            agent_id=analyzer.agent_id,
            tenant_key=test_tenant_key,
        )

        assert result.count >= 1
        msg = result.messages[0]
        # Should resolve display name via fallback even though metadata lacks it
        assert msg["from_agent"] == "Orchestrator Agent"
        # from_agent_id should contain the raw UUID
        assert msg["from_agent_id"] == orchestrator.agent_id

    @pytest.mark.asyncio
    async def test_receive_messages_includes_from_agent_id(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        test_tenant_key: str,
    ):
        """
        Verify that receive_messages output includes 'from_agent_id' field
        containing the raw agent UUID.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        analyzer = agents[1]

        await message_service.send_message(
            to_agents=[analyzer.agent_id],
            content="Check from_agent_id field",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_id,
            tenant_key=test_tenant_key,
        )

        result = await message_service.receive_messages(
            agent_id=analyzer.agent_id,
            tenant_key=test_tenant_key,
        )

        assert result.count >= 1
        msg = result.messages[0]
        assert "from_agent_id" in msg
        assert msg["from_agent_id"] == orchestrator.agent_id
        # from_agent should be the display name, not the UUID
        assert msg["from_agent"] == "Orchestrator Agent"


class TestCompletedAgentResolution:
    """Test that completed agents can be resolved by display name."""

    @pytest.mark.asyncio
    async def test_send_message_resolves_completed_agent_by_name(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        test_tenant_key: str,
    ):
        """
        An agent in 'complete' status should still be resolvable by display name
        when used as a recipient in send_message.
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        implementer = agents[2]  # "TDD Implementor"

        # Set implementer to 'complete' status
        implementer.status = "complete"
        await db_session.commit()
        await db_session.refresh(implementer)

        # Send message to the completed agent using its display name
        result = await message_service.send_message(
            to_agents=["TDD Implementor"],
            content="Follow-up on completed work",
            project_id=project.id,
            message_type="direct",
            from_agent=orchestrator.agent_id,
            tenant_key=test_tenant_key,
        )

        assert result.message_id is not None
        # Verify the message was routed to the correct agent_id
        assert implementer.agent_id in result.to_agents
