"""
MessageService Counter Tests - Handover 0387f

Tests that MessageService correctly updates counter columns instead of JSONB:
- send_message() increments sent/waiting counters
- acknowledge_message() decrements waiting and increments read counters
- Broadcast messages update sender's sent_count by 1, each recipient's waiting_count by 1
- Counters survive without JSONB persistence

This is the TDD phase for counter-based message persistence.
"""

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
        description="Test product for counter tests",
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
        name="Test Project for Counter Tests",
        description="Test project with agents",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create agent jobs and executions
    agent_display_names = ["orchestrator", "analyzer", "implementer"]
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

        # Create executor instance (AgentExecution) with counter columns initialized
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
) -> MessageService:
    """Create MessageService instance with mocked WebSocket manager and test session."""
    from contextlib import asynccontextmanager

    tenant_manager = TenantManager()

    # Mock db_manager.get_session_async() to return test session
    @asynccontextmanager
    async def mock_get_session_async():
        yield db_session

    db_manager.get_session_async = mock_get_session_async

    # Pass test_session for transaction-aware testing
    service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=mock_websocket_manager,
        test_session=db_session,
    )
    return service


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

    assert result["success"] is True

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

    assert result["success"] is True

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

    assert result["success"] is True

    # Refresh recipients to get updated counts
    for agent in recipients:
        await db_session.refresh(agent)

    # Each recipient should have waiting_count = 1
    for agent in recipients:
        assert agent.messages_waiting_count == 1


@pytest.mark.asyncio
async def test_acknowledge_message_decrements_waiting_increments_read(
    message_service: MessageService,
    test_project_with_agents: tuple[Project, list[AgentExecution]],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """Test that acknowledge_message decrements waiting_count and increments read_count."""
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
    assert result["success"] is True
    message_id = result["data"]["message_id"]

    # Refresh to get updated counts
    await db_session.refresh(analyzer)
    assert analyzer.messages_waiting_count == 1
    assert analyzer.messages_read_count == 0

    # Acknowledge message
    ack_result = await message_service.acknowledge_message(
        message_id=message_id,
        agent_id=analyzer.agent_id,
        tenant_key=test_tenant_key,
    )
    assert ack_result["success"] is True

    # Refresh to get updated counts
    await db_session.refresh(analyzer)

    # Verify waiting_count decremented and read_count incremented
    assert analyzer.messages_waiting_count == 0
    assert analyzer.messages_read_count == 1


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
    assert result["success"] is True

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
        assert result["success"] is True

    # Refresh agents
    await db_session.refresh(orchestrator)
    await db_session.refresh(analyzer)

    # Verify accumulated counts
    assert orchestrator.messages_sent_count == 3
    assert analyzer.messages_waiting_count == 3


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

    assert result["success"] is True

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

    assert result["success"] is True

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

    assert result["success"] is True

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
    assert result["success"] is True
    message_id = result["data"]["message_id"]

    # Reset mock to track only acknowledge call
    mock_websocket_manager.reset_mock()

    # Acknowledge message
    ack_result = await message_service.acknowledge_message(
        message_id=message_id,
        agent_id=analyzer.agent_id,
        tenant_key=test_tenant_key,
    )
    assert ack_result["success"] is True

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

    assert result["success"] is True

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
