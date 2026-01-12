"""
MessageService Contract Tests - Handover 0295

Tests that MessageService correctly implements the messaging contract:
- Messages create database rows AND JSONB mirrors
- Acknowledgments update both table and JSONB
- Completions preserve acknowledgment state
- Multi-tenant isolation is enforced

This is the RED phase of TDD - these tests validate the contract and may initially fail.
"""

import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import models using modular imports (Post-Handover 0128a)
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
        agent = AgentExecution(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name=agent_display_name,
            status="waiting",
            instance_number=1,
            messages=[],  # Initialize empty JSONB array
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
    from unittest.mock import AsyncMock, patch

    tenant_manager = TenantManager()

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

class TestMessageCreationAndJSONBMirroring:
    """Test that messages create both database rows and JSONB mirrors."""

    @pytest.mark.asyncio
    async def test_send_message_creates_message_and_updates_jsonb_counters(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
        mock_websocket_manager: MagicMock,
    ):
        """
        CRITICAL CONTRACT TEST: Verify that send_message():
        1. Creates a Message row in the database
        2. Mirrors message to recipient's AgentExecution.messages JSONB column
        3. Sets status="waiting" in JSONB for inbound messages
        4. Emits WebSocket events correctly
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]  # orchestrator
        recipient = agents[1]  # analyzer

        # Act: Send message from orchestrator to analyzer
        # Handover 0372: Must pass tenant_key for agent-ID resolution
        result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Analyze the codebase for patterns",
            project_id=project.id,
            message_type="direct",
            priority="high",
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )

        # Assert: Message sending succeeded
        if not result["success"]:
            pytest.fail(f"Message sending failed: {result.get('error', 'Unknown error')}")
        assert result["success"] is True
        assert "message_id" in result
        message_id = result["message_id"]

        # Assert: Message row exists in database
        msg_result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None, "Message should exist in database"
        assert db_message.project_id == project.id
        assert db_message.tenant_key == project.tenant_key
        # Handover 0372: Message stores resolved agent_ids (executor), not job_ids (work order)
        # This enables succession: messages route to NEW executor after handover
        assert db_message.to_agents == [recipient.agent_id]
        assert db_message.content == "Analyze the codebase for patterns"
        assert db_message.message_type == "direct"
        assert db_message.priority == "high"
        assert db_message.status == "pending"

        # Assert: Recipient's JSONB has inbound message with status="waiting"
        await db_session.refresh(recipient)
        assert recipient.messages is not None, "Recipient should have messages JSONB array"
        assert len(recipient.messages) > 0, "Recipient should have at least one message"

        # Find the message in JSONB array
        inbound_msg = None
        for msg in recipient.messages:
            if msg.get("id") == message_id:
                inbound_msg = msg
                break

        assert inbound_msg is not None, f"Message {message_id} should be in recipient's JSONB"
        assert inbound_msg["from"] == orchestrator.agent_display_name
        assert inbound_msg["direction"] == "inbound"
        assert inbound_msg["status"] == "waiting", "Inbound message should have status='waiting'"
        assert inbound_msg["text"] == "Analyze the codebase for patterns"
        assert inbound_msg["priority"] == "high"

        # Assert: Sender's JSONB has outbound message with status="sent"
        await db_session.refresh(orchestrator)
        assert orchestrator.messages is not None, "Sender should have messages JSONB array"

        outbound_msg = None
        for msg in orchestrator.messages:
            if msg.get("id") == message_id:
                outbound_msg = msg
                break

        assert outbound_msg is not None, f"Message {message_id} should be in sender's JSONB"
        assert outbound_msg["from"] == orchestrator.agent_display_name
        assert outbound_msg["direction"] == "outbound"
        assert outbound_msg["status"] == "sent"
        # Handover 0372: to_agents contains agent_ids (executor) after resolution
        assert outbound_msg["to_agents"] == [recipient.agent_id]

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
        3. Preserves Message.acknowledged_by array
        4. Sets Message.completed_by
        5. Sets Message.completed_at timestamp
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[2]  # implementer

        # Arrange: Send a message
        # Handover 0372: Must pass tenant_key for agent-ID resolution
        send_result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Implement feature X",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
            tenant_key=project.tenant_key,
        )
        assert send_result["success"] is True
        message_id = send_result["message_id"]

        # Auto-acknowledge via receive_messages (Handover 0326)
        # Handover 0372: Now uses agent_id (executor), not job_id (work order)
        receive_result = await message_service.receive_messages(
            agent_id=recipient.agent_id,
            limit=10,
            tenant_key=project.tenant_key,
        )
        assert receive_result["success"] is True, f"receive_messages failed: {receive_result.get('error', 'unknown')}"
        assert len(receive_result["messages"]) >= 1, f"Expected messages but got {receive_result['count']}"

        # Act: Complete the message
        complete_result = await message_service.complete_message(
            message_id=message_id,
            agent_name=recipient.agent_display_name,
            result="Feature X implemented successfully with 95% test coverage",
        )

        # Assert: Completion succeeded
        assert complete_result["success"] is True
        assert complete_result["message_id"] == message_id
        assert complete_result["completed_by"] == recipient.agent_display_name

        # Assert: Message status is "completed"
        msg_result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert db_message.status == "completed"
        assert db_message.result == "Feature X implemented successfully with 95% test coverage"
        assert db_message.completed_by == recipient.agent_display_name
        assert db_message.completed_at is not None

        # Assert: acknowledged_by is PRESERVED (not overwritten)
        # Handover 0372: acknowledged_by now contains agent_id (executor), not job_id
        assert recipient.agent_id in db_message.acknowledged_by, \
            f"Acknowledgment should be preserved after completion. Expected {recipient.agent_id} in {db_message.acknowledged_by}"


class TestBroadcastMessaging:
    """Test broadcast message resolution to all agents."""

    @pytest.mark.asyncio
    async def test_broadcast_resolves_all_agents_in_project(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        CRITICAL CONTRACT TEST: Verify that send_message(to_agents=['all']):
        1. Resolves to all active agents in the project
        2. Creates JSONB mirrors in ALL agent JSONB columns
        3. Each agent receives inbound message with status="waiting"
        4. Emits WebSocket events to all recipients
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        other_agents = agents[1:]  # All non-orchestrator agents

        # Act: Broadcast message to all agents
        result = await message_service.send_message(
            to_agents=["all"],
            content="Project status: All systems operational",
            project_id=project.id,
            message_type="broadcast",
            priority="normal",
            from_agent=orchestrator.agent_display_name,
        )

        # Assert: Broadcast succeeded
        assert result["success"] is True
        message_id = result["message_id"]

        # Assert: Message row exists
        msg_result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        db_message = msg_result.scalar_one_or_none()
        assert db_message is not None
        assert db_message.message_type == "broadcast"

        # Assert: EVERY agent (except possibly sender) has the message in JSONB
        for agent in other_agents:
            await db_session.refresh(agent)
            assert agent.messages is not None, f"{agent.agent_display_name} should have messages"

            # Find broadcast message in agent's JSONB
            found_msg = None
            for msg in agent.messages:
                if msg.get("id") == message_id:
                    found_msg = msg
                    break

            assert found_msg is not None, \
                f"Broadcast message should be in {agent.agent_display_name}'s JSONB"
            assert found_msg["from"] == orchestrator.agent_display_name
            assert found_msg["direction"] == "inbound"
            assert found_msg["status"] == "waiting"
            assert "Project status" in found_msg["text"]


class TestMultiTenantIsolation:
    """Test that multi-tenant isolation is enforced."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires integration test with real database sessions - covered in tests/api/test_messages_api.py")
    async def test_multi_tenant_message_isolation(
        self,
        db_session: AsyncSession,
        db_manager: DatabaseManager,
        mock_websocket_manager: MagicMock,
        test_product: Product,
    ):
        """
        CRITICAL CONTRACT TEST: Verify multi-tenant isolation:
        1. Messages from tenant A are not visible to tenant B
        2. MessageService properly filters by tenant_key
        3. JSONB mirrors respect tenant boundaries
        """
        # Arrange: Create two separate tenants with their own products and projects
        # Use TenantManager.generate_tenant_key() to get properly formatted keys
        tenant_a_key = TenantManager.generate_tenant_key(f"tenant-a-{uuid4().hex[:8]}")
        tenant_b_key = TenantManager.generate_tenant_key(f"tenant-b-{uuid4().hex[:8]}")

        # Create separate products for each tenant (required due to unique constraint)
        product_a = Product(
            id=str(uuid4()),
            tenant_key=tenant_a_key,
            name=f"Product A {uuid4().hex[:8]}",
            description="Product for tenant A",
            is_active=True,
        )
        product_b = Product(
            id=str(uuid4()),
            tenant_key=tenant_b_key,
            name=f"Product B {uuid4().hex[:8]}",
            description="Product for tenant B",
            is_active=True,
        )
        db_session.add_all([product_a, product_b])
        await db_session.commit()

        # Create projects for both tenants (each uses their own product)
        project_a = Project(
            id=str(uuid4()),
            tenant_key=tenant_a_key,
            product_id=product_a.id,
            name="Tenant A Project",
            description="Project for tenant A",
            mission="Tenant A mission",
            status="active",
        )
        project_b = Project(
            id=str(uuid4()),
            tenant_key=tenant_b_key,
            product_id=product_b.id,
            name="Tenant B Project",
            description="Project for tenant B",
            mission="Tenant B mission",
            status="active",
        )
        db_session.add_all([project_a, project_b])
        await db_session.commit()

        # Create agents for both tenants
        agent_a = AgentExecution(
            job_id=str(uuid4()),
            tenant_key=tenant_a_key,
            project_id=project_a.id,
            agent_display_name="analyzer",
            mission="Analyze for tenant A",
            status="waiting",
            messages=[],
        )
        agent_b = AgentExecution(
            job_id=str(uuid4()),
            tenant_key=tenant_b_key,
            project_id=project_b.id,
            agent_display_name="analyzer",
            mission="Analyze for tenant B",
            status="waiting",
            messages=[],
        )
        db_session.add_all([agent_a, agent_b])
        await db_session.commit()

        # Create message services for both tenants
        tenant_a_manager = TenantManager()
        tenant_a_manager.set_current_tenant(tenant_a_key)
        service_a = MessageService(db_manager, tenant_a_manager, mock_websocket_manager)

        tenant_b_manager = TenantManager()
        tenant_b_manager.set_current_tenant(tenant_b_key)
        service_b = MessageService(db_manager, tenant_b_manager, mock_websocket_manager)

        # Act: Tenant A sends a message
        result_a = await service_a.send_message(
            to_agents=[agent_a.agent_display_name],
            content="Tenant A confidential data",
            project_id=project_a.id,
            from_agent="orchestrator",
        )
        assert result_a["success"] is True
        message_a_id = result_a["message_id"]

        # Act: Tenant B sends a message
        result_b = await service_b.send_message(
            to_agents=[agent_b.agent_display_name],
            content="Tenant B confidential data",
            project_id=project_b.id,
            from_agent="orchestrator",
        )
        assert result_b["success"] is True
        message_b_id = result_b["message_id"]

        # Assert: Tenant A's message is NOT visible to Tenant B's agent
        await db_session.refresh(agent_b)
        assert agent_b.messages is not None
        for msg in agent_b.messages:
            assert msg.get("id") != message_a_id, \
                "Tenant A's message should NOT be in Tenant B's JSONB"
            assert "Tenant A confidential" not in msg.get("text", ""), \
                "Tenant A's content should NOT leak to Tenant B"

        # Assert: Tenant B's message is NOT visible to Tenant A's agent
        await db_session.refresh(agent_a)
        assert agent_a.messages is not None
        for msg in agent_a.messages:
            assert msg.get("id") != message_b_id, \
                "Tenant B's message should NOT be in Tenant A's JSONB"
            assert "Tenant B confidential" not in msg.get("text", ""), \
                "Tenant B's content should NOT leak to Tenant A"

        # Assert: Database messages have correct tenant isolation
        msg_a_result = await db_session.execute(
            select(Message).where(Message.id == message_a_id)
        )
        db_message_a = msg_a_result.scalar_one_or_none()
        assert db_message_a is not None
        assert db_message_a.tenant_key == tenant_a_key

        msg_b_result = await db_session.execute(
            select(Message).where(Message.id == message_b_id)
        )
        db_message_b = msg_b_result.scalar_one_or_none()
        assert db_message_b is not None
        assert db_message_b.tenant_key == tenant_b_key


class TestMessagePersistenceContract:
    """Test message persistence guarantees."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Session isolation issues - expires don't work as expected in async context")
    async def test_message_survives_page_refresh(
        self,
        db_session: AsyncSession,
        message_service: MessageService,
        test_project_with_agents: tuple[Project, list[AgentExecution]],
    ):
        """
        CRITICAL CONTRACT TEST: Verify message persistence for counter survival:
        1. Messages persist to AgentExecution.messages JSONB
        2. Messages survive database session close/reopen (page refresh simulation)
        3. Counters can be recalculated from JSONB on load
        """
        project, agents = test_project_with_agents
        orchestrator = agents[0]
        recipient = agents[1]

        # Act: Send message
        result = await message_service.send_message(
            to_agents=[recipient.agent_display_name],
            content="Message that should persist",
            project_id=project.id,
            from_agent=orchestrator.agent_display_name,
        )
        assert result["success"] is True
        message_id = result["message_id"]

        # Commit and detach (simulate session close)
        await db_session.commit()
        db_session.expire_all()  # expire_all is sync, not async

        # Simulate page refresh: Re-fetch agent from database
        recipient_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == recipient.job_id)
        )
        refreshed_agent = recipient_result.scalar_one_or_none()
        assert refreshed_agent is not None

        # Assert: Message still exists in JSONB
        assert refreshed_agent.messages is not None
        found_msg = None
        for msg in refreshed_agent.messages:
            if msg.get("id") == message_id:
                found_msg = msg
                break

        assert found_msg is not None, "Message should survive session refresh"
        assert found_msg["text"] == "Message that should persist"
        assert found_msg["status"] == "waiting"

        # Assert: Counter can be recalculated
        waiting_count = sum(
            1 for msg in refreshed_agent.messages
            if msg.get("status") == "waiting" and msg.get("direction") == "inbound"
        )
        assert waiting_count >= 1, "Should be able to count waiting messages from JSONB"


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
        """Test that sending to nonexistent project fails gracefully."""
        result = await message_service.send_message(
            to_agents=["analyzer"],
            content="Test message",
            project_id="nonexistent-project-id",
            from_agent="orchestrator",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_complete_nonexistent_message_fails(
        self,
        message_service: MessageService,
    ):
        """Test that completing nonexistent message fails gracefully."""
        result = await message_service.complete_message(
            message_id="nonexistent-message-id",
            agent_name="analyzer",
            result="Test result",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
