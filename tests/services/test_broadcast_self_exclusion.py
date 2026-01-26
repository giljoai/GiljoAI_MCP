"""
Broadcast Self-Exclusion Test

Tests that broadcast messages (to_agents=['all']) exclude the sender.

This test verifies:
1. Agent A sends broadcast to ['all']
2. Agent A does NOT receive the message (self-exclusion)
3. Agents B and C DO receive the message
4. Message counters are updated correctly (sender +1 sent, recipients +1 waiting each)
"""

import pytest
from datetime import datetime, timezone
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
        name="Test Product",
        description="Test product for broadcast self-exclusion tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project_with_three_agents(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> tuple[Project, AgentExecution, AgentExecution, AgentExecution]:
    """
    Create a test project with three agents (A, B, C).
    Returns tuple of (project, agent_a, agent_b, agent_c).
    """
    # Create project
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project for Broadcast Self-Exclusion",
        description="Test project with 3 agents",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create agent jobs and executions for Agent A, B, C
    agent_display_names = ["agent-a", "agent-b", "agent-c"]
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
            instance_number=1,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()
    for agent in agents:
        await db_session.refresh(agent)

    return project, agents[0], agents[1], agents[2]


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
# Broadcast Self-Exclusion Tests
# ============================================================================

@pytest.mark.asyncio
async def test_broadcast_excludes_sender(
    message_service: MessageService,
    test_project_with_three_agents: tuple[Project, AgentExecution, AgentExecution, AgentExecution],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """
    Test that broadcast messages (to_agents=['all']) exclude the sender.

    Scenario:
    1. Agent A sends broadcast to ['all']
    2. Agent A should NOT receive the message (self-exclusion)
    3. Agents B and C should receive the message
    """
    project, agent_a, agent_b, agent_c = test_project_with_three_agents

    # Verify initial state
    assert agent_a.messages_sent_count == 0
    assert agent_a.messages_waiting_count == 0
    assert agent_b.messages_waiting_count == 0
    assert agent_c.messages_waiting_count == 0

    # Agent A sends broadcast to ['all']
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast message from Agent A",
        project_id=project.id,
        from_agent=agent_a.agent_display_name,
        tenant_key=test_tenant_key,
    )

    assert result["success"] is True

    # Refresh all agents to get updated counts
    await db_session.refresh(agent_a)
    await db_session.refresh(agent_b)
    await db_session.refresh(agent_c)

    # CRITICAL ASSERTION 1: Agent A's sent_count incremented by 1
    assert agent_a.messages_sent_count == 1, \
        f"Expected sender's sent_count to be 1, got {agent_a.messages_sent_count}"

    # CRITICAL ASSERTION 2: Agent A did NOT receive the message (waiting_count = 0)
    assert agent_a.messages_waiting_count == 0, \
        f"Expected sender's waiting_count to be 0 (self-exclusion), got {agent_a.messages_waiting_count}"

    # CRITICAL ASSERTION 3: Agent B received the message (waiting_count = 1)
    assert agent_b.messages_waiting_count == 1, \
        f"Expected Agent B's waiting_count to be 1, got {agent_b.messages_waiting_count}"

    # CRITICAL ASSERTION 4: Agent C received the message (waiting_count = 1)
    assert agent_c.messages_waiting_count == 1, \
        f"Expected Agent C's waiting_count to be 1, got {agent_c.messages_waiting_count}"

    # Verify message records in database (should be 2 messages, not 3)
    result = await db_session.execute(
        select(Message).where(Message.project_id == project.id)
    )
    messages = result.scalars().all()

    assert len(messages) == 2, \
        f"Expected 2 messages (Agent A excluded), got {len(messages)}"

    # Verify message recipients are Agent B and Agent C (not Agent A)
    recipient_ids = {msg.to_agents[0] for msg in messages if msg.to_agents}
    assert agent_a.agent_id not in recipient_ids, \
        f"Agent A should not be in recipient list"
    assert agent_b.agent_id in recipient_ids, \
        f"Agent B should be in recipient list"
    assert agent_c.agent_id in recipient_ids, \
        f"Agent C should be in recipient list"


@pytest.mark.asyncio
async def test_broadcast_excludes_sender_by_agent_id(
    message_service: MessageService,
    test_project_with_three_agents: tuple[Project, AgentExecution, AgentExecution, AgentExecution],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """
    Test that broadcast exclusion works when sender is specified by agent_id (UUID).

    This tests the alternate code path where sender is identified by agent_id instead of
    agent_display_name (see message_service.py lines 176-177).
    """
    project, agent_a, agent_b, agent_c = test_project_with_three_agents

    # Agent A sends broadcast using agent_id instead of agent_display_name
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast message from Agent A (by agent_id)",
        project_id=project.id,
        from_agent=agent_a.agent_id,  # Use agent_id instead of display name
        tenant_key=test_tenant_key,
    )

    assert result["success"] is True

    # Refresh all agents
    await db_session.refresh(agent_a)
    await db_session.refresh(agent_b)
    await db_session.refresh(agent_c)

    # Verify Agent A excluded (waiting_count = 0)
    assert agent_a.messages_waiting_count == 0, \
        f"Expected sender (by agent_id) to be excluded, got waiting_count={agent_a.messages_waiting_count}"

    # Verify Agents B and C received the message
    assert agent_b.messages_waiting_count == 1
    assert agent_c.messages_waiting_count == 1


@pytest.mark.asyncio
async def test_broadcast_with_multiple_messages_accumulates_correctly(
    message_service: MessageService,
    test_project_with_three_agents: tuple[Project, AgentExecution, AgentExecution, AgentExecution],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """
    Test that sending multiple broadcasts accumulates counters correctly.

    Scenario:
    1. Agent A sends 3 broadcasts
    2. Agent A's sent_count should be 3
    3. Agent A's waiting_count should remain 0 (never receives own broadcasts)
    4. Agents B and C should each have waiting_count = 3
    """
    project, agent_a, agent_b, agent_c = test_project_with_three_agents

    # Send 3 broadcasts from Agent A
    for i in range(3):
        result = await message_service.send_message(
            to_agents=["all"],
            content=f"Broadcast message {i+1}",
            project_id=project.id,
            from_agent=agent_a.agent_display_name,
            tenant_key=test_tenant_key,
        )
        assert result["success"] is True

    # Refresh all agents
    await db_session.refresh(agent_a)
    await db_session.refresh(agent_b)
    await db_session.refresh(agent_c)

    # Verify Agent A's counters
    assert agent_a.messages_sent_count == 3, \
        f"Expected sender's sent_count to be 3, got {agent_a.messages_sent_count}"
    assert agent_a.messages_waiting_count == 0, \
        f"Expected sender's waiting_count to remain 0, got {agent_a.messages_waiting_count}"

    # Verify Agents B and C accumulated messages
    assert agent_b.messages_waiting_count == 3, \
        f"Expected Agent B's waiting_count to be 3, got {agent_b.messages_waiting_count}"
    assert agent_c.messages_waiting_count == 3, \
        f"Expected Agent C's waiting_count to be 3, got {agent_c.messages_waiting_count}"


@pytest.mark.asyncio
async def test_broadcast_from_different_agents(
    message_service: MessageService,
    test_project_with_three_agents: tuple[Project, AgentExecution, AgentExecution, AgentExecution],
    db_session: AsyncSession,
    test_tenant_key: str,
):
    """
    Test that each agent is excluded from their own broadcasts.

    Scenario:
    1. Agent A broadcasts -> B and C receive, A does not
    2. Agent B broadcasts -> A and C receive, B does not
    3. Agent C broadcasts -> A and B receive, C does not
    """
    project, agent_a, agent_b, agent_c = test_project_with_three_agents

    # Agent A broadcasts
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast from A",
        project_id=project.id,
        from_agent=agent_a.agent_display_name,
        tenant_key=test_tenant_key,
    )
    assert result["success"] is True

    # Agent B broadcasts
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast from B",
        project_id=project.id,
        from_agent=agent_b.agent_display_name,
        tenant_key=test_tenant_key,
    )
    assert result["success"] is True

    # Agent C broadcasts
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast from C",
        project_id=project.id,
        from_agent=agent_c.agent_display_name,
        tenant_key=test_tenant_key,
    )
    assert result["success"] is True

    # Refresh all agents
    await db_session.refresh(agent_a)
    await db_session.refresh(agent_b)
    await db_session.refresh(agent_c)

    # Verify each agent sent 1 message
    assert agent_a.messages_sent_count == 1
    assert agent_b.messages_sent_count == 1
    assert agent_c.messages_sent_count == 1

    # Verify each agent received 2 messages (from the other two agents)
    assert agent_a.messages_waiting_count == 2, \
        f"Agent A should receive 2 messages (from B and C), got {agent_a.messages_waiting_count}"
    assert agent_b.messages_waiting_count == 2, \
        f"Agent B should receive 2 messages (from A and C), got {agent_b.messages_waiting_count}"
    assert agent_c.messages_waiting_count == 2, \
        f"Agent C should receive 2 messages (from A and B), got {agent_c.messages_waiting_count}"


@pytest.mark.asyncio
async def test_broadcast_to_empty_project_no_crash(
    message_service: MessageService,
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """
    Test that broadcasting to a project with no agents doesn't crash.

    Edge case: ['all'] expansion results in empty recipient list.
    """
    # Create project with NO agents
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Empty Project",
        description="Project with no agents",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Attempt to send broadcast (should not crash)
    result = await message_service.send_message(
        to_agents=["all"],
        content="Broadcast to empty project",
        project_id=project.id,
        from_agent="ghost-agent",
        tenant_key=test_tenant_key,
    )

    # Should succeed but create no messages
    assert result["success"] is True
    assert result["data"]["message_id"] is None  # No messages created

    # Verify no messages were created
    result = await db_session.execute(
        select(Message).where(Message.project_id == project.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 0
