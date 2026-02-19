"""
Integration Tests for Counter-Based Message System

Tests validate the counter-based messaging architecture (Handover 0700c):
- Message counter columns (messages_sent_count, messages_waiting_count, messages_read_count)
- MessageService.send_message() increments sender sent_count and recipient waiting_count
- MessageService.receive_messages() decrements waiting_count and increments read_count
- Multi-tenant isolation for message counters

Coverage Targets:
- MessageRepository counter increment/decrement operations
- MessageService send_message() counter updates
- MessageService receive_messages() counter updates
- Tenant isolation across counter operations
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
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
    mock.broadcast_job_progress = AsyncMock()
    return mock


@pytest.fixture
async def ws_test_product(
    db_session: AsyncSession,
    test_tenant_key: str,
) -> Product:
    """Create a test product for WebSocket platform tests."""
    product = Product(
        tenant_key=test_tenant_key,
        name="Test Product WS",
        description="Test product for WebSocket platform tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def ws_test_project(
    db_session: AsyncSession,
    test_tenant_key: str,
    ws_test_product: Product,
) -> Project:
    """Create a test project for WebSocket platform tests."""
    project = Project(
        tenant_key=test_tenant_key,
        product_id=ws_test_product.id,
        name="Test Project WS",
        description="Test project for message counter tests",
        mission="Test the counter-based message platform",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_agent_with_execution(
    db_session: AsyncSession,
    test_tenant_key: str,
    ws_test_project: Project,
) -> tuple[AgentJob, AgentExecution]:
    """
    Create an agent with both AgentJob (work order) and AgentExecution (executor).

    Returns tuple of (job, execution) for testing the agent_id/job_id separation.
    """
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=ws_test_project.id,
        job_type="implementer",
        status="active",
        mission="Test agent for message counter tests",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="implementer",
        agent_name="test-implementer",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)

    return job, execution


@pytest.fixture
async def test_sender_agent(
    db_session: AsyncSession,
    test_tenant_key: str,
    ws_test_project: Project,
) -> tuple[AgentJob, AgentExecution]:
    """Create a sender agent (orchestrator) for message tests."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=ws_test_project.id,
        job_type="orchestrator",
        status="active",
        mission="Test sender agent",
    )
    db_session.add(job)
    await db_session.flush()

    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="orchestrator",
        agent_name="test-orchestrator",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)

    return job, execution


@pytest.fixture
async def message_service_factory(
    db_manager,
    db_session,
    mock_websocket_manager,
    tenant_manager,
    test_tenant_key,
):
    """Factory fixture to create MessageService instances with proper dependencies."""

    def _create(tenant_key: str = None):
        key = tenant_key or test_tenant_key
        tenant_manager.set_current_tenant(key)
        return MessageService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=mock_websocket_manager,
            test_session=db_session,
        )

    return _create


# ============================================================================
# Test Classes
# ============================================================================


@pytest.mark.asyncio
class TestMessageCounterUpdates:
    """
    Integration tests for counter-based message system.

    These tests validate that send_message() and receive_messages()
    correctly update the counter columns on AgentExecution.
    """

    async def test_send_message_increments_sender_sent_count(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        send_message() should increment sender's messages_sent_count.
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Verify initial state
        assert sender_execution.messages_sent_count == 0

        # Send a message
        result = await message_service.send_message(
            from_agent=sender_execution.agent_id,
            to_agents=[execution.agent_id],
            content="Test message for counter verification",
            message_type="direct",
            project_id=ws_test_project.id,
        )
        assert result.message_id is not None

        # Verify sender's sent_count was incremented
        await db_session.refresh(sender_execution)
        assert sender_execution.messages_sent_count == 1, (
            f"Sender sent_count should be 1, got {sender_execution.messages_sent_count}"
        )

    async def test_send_message_increments_recipient_waiting_count(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        send_message() should increment recipient's messages_waiting_count.
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Verify initial state
        assert execution.messages_waiting_count == 0

        # Send a message
        result = await message_service.send_message(
            from_agent=sender_execution.agent_id,
            to_agents=[execution.agent_id],
            content="Test message for waiting count",
            message_type="direct",
            project_id=ws_test_project.id,
        )
        assert result.message_id is not None

        # Verify recipient's waiting_count was incremented
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 1, (
            f"Recipient waiting_count should be 1, got {execution.messages_waiting_count}"
        )

    async def test_receive_messages_updates_counters(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        receive_messages() should decrement waiting_count and increment read_count.
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send 3 messages
        for i in range(3):
            await message_service.send_message(
                from_agent=sender_execution.agent_id,
                to_agents=[execution.agent_id],
                content=f"Test message {i + 1}",
                message_type="direct",
                project_id=ws_test_project.id,
            )

        # Verify waiting_count after sends
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 3
        assert execution.messages_read_count == 0

        # Receive messages (auto-acknowledge)
        receive_result = await message_service.receive_messages(
            agent_id=execution.agent_id,
            limit=3,
        )
        assert receive_result.count == 3

        # Verify counters updated after receive
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 0, (
            f"Waiting count should be 0 after reading all, got {execution.messages_waiting_count}"
        )
        assert execution.messages_read_count == 3, (
            f"Read count should be 3 after reading all, got {execution.messages_read_count}"
        )


@pytest.mark.asyncio
class TestCounterPersistenceAcrossRefresh:
    """
    Tests that counter values persist across session refresh (simulating page reload).
    """

    async def test_counters_persist_after_partial_read(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        Send 3 messages, read 2, refresh session, verify counters are accurate.
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send 3 messages
        for i in range(3):
            result = await message_service.send_message(
                from_agent=sender_execution.agent_id,
                to_agents=[execution.agent_id],
                content=f"Persistence test message {i + 1}",
                message_type="direct",
                project_id=ws_test_project.id,
            )
            assert result.message_id is not None

        # Read only 2 of 3 messages
        receive_result = await message_service.receive_messages(
            agent_id=execution.agent_id,
            limit=2,
        )
        assert receive_result.count == 2

        # Simulate page refresh by expiring and refreshing
        db_session.expire_all()
        await db_session.refresh(execution)

        # Verify counters persist correctly
        assert execution.messages_waiting_count == 1, (
            f"Should have 1 waiting after reading 2 of 3, got {execution.messages_waiting_count}"
        )
        assert execution.messages_read_count == 2, (
            f"Should have 2 read after reading 2, got {execution.messages_read_count}"
        )

    async def test_sender_sent_count_persists(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        Sender's sent_count should persist across session refresh.
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send 5 messages
        for i in range(5):
            await message_service.send_message(
                from_agent=sender_execution.agent_id,
                to_agents=[execution.agent_id],
                content=f"Sent count test {i + 1}",
                message_type="direct",
                project_id=ws_test_project.id,
            )

        # Simulate page refresh
        db_session.expire_all()
        await db_session.refresh(sender_execution)

        assert sender_execution.messages_sent_count == 5, (
            f"Sender sent_count should be 5 after refresh, got {sender_execution.messages_sent_count}"
        )


@pytest.mark.asyncio
class TestAgentIdentifierRouting:
    """
    Tests that messages route by agent_id (executor) not job_id (work order).
    """

    async def test_message_counters_keyed_by_agent_id(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        Counter updates should be keyed by agent_id (executor UUID), not job_id.

        This validates the Handover 0381 contract:
        - job_id = "what am I working on" (persists across succession)
        - agent_id = "who am I" (changes on succession)
        - Counters track per-executor, not per-job
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send message to agent_id (executor)
        result = await message_service.send_message(
            from_agent=sender_execution.agent_id,
            to_agents=[execution.agent_id],
            content="Message to executor, not work order",
            message_type="direct",
            project_id=ws_test_project.id,
        )
        assert result.message_id is not None

        # Verify counter is on AgentExecution (by agent_id)
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 1, (
            "Counter should be on AgentExecution keyed by agent_id"
        )

    async def test_receive_messages_returns_message_content(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        ws_test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        receive_messages() should return message content and update counters.
        """
        _job, execution = test_agent_with_execution
        _sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send 5 messages
        for i in range(5):
            await message_service.send_message(
                from_agent=sender_execution.agent_id,
                to_agents=[execution.agent_id],
                content=f"Count test message {i + 1}",
                message_type="direct",
                project_id=ws_test_project.id,
            )

        # Read 3 messages
        result = await message_service.receive_messages(
            agent_id=execution.agent_id,
            limit=3,
        )
        assert result.count == 3
        assert len(result.messages) == 3

        # Verify counter state
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 2, (
            f"Should have 2 waiting, got {execution.messages_waiting_count}"
        )
        assert execution.messages_read_count == 3, (
            f"Should have 3 read, got {execution.messages_read_count}"
        )


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """
    Verify multi-tenant isolation is maintained for message counters.
    """

    async def test_message_counters_respect_tenant_isolation(
        self,
        db_session: AsyncSession,
        db_manager,
        mock_websocket_manager,
    ):
        """
        Messages from one tenant should not affect another tenant's counters.
        """
        tenant_a = TenantManager.generate_tenant_key()
        tenant_b = TenantManager.generate_tenant_key()

        # Create products for each tenant
        product_a = Product(
            tenant_key=tenant_a,
            name="Product A",
            product_memory={},
        )
        product_b = Product(
            tenant_key=tenant_b,
            name="Product B",
            product_memory={},
        )
        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Create projects
        project_a = Project(
            tenant_key=tenant_a,
            product_id=product_a.id,
            name="Project A",
            description="Tenant A isolation test",
            mission="Test tenant isolation A",
            status="active",
        )
        project_b = Project(
            tenant_key=tenant_b,
            product_id=product_b.id,
            name="Project B",
            description="Tenant B isolation test",
            mission="Test tenant isolation B",
            status="active",
        )
        db_session.add_all([project_a, project_b])
        await db_session.flush()

        # Create agents for tenant A
        job_a = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_a,
            project_id=project_a.id,
            job_type="implementer",
            status="active",
            mission="Test agent A",
        )
        db_session.add(job_a)
        await db_session.flush()

        exec_a = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_a.job_id,
            tenant_key=tenant_a,
            agent_display_name="implementer",
            status="working",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )

        # Create sender for tenant A
        sender_job_a = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_a,
            project_id=project_a.id,
            job_type="orchestrator",
            status="active",
            mission="Sender A",
        )
        db_session.add(sender_job_a)
        await db_session.flush()

        sender_exec_a = AgentExecution(
            agent_id=str(uuid4()),
            job_id=sender_job_a.job_id,
            tenant_key=tenant_a,
            agent_display_name="orchestrator",
            status="working",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )

        # Create agent for tenant B
        job_b = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_b,
            project_id=project_b.id,
            job_type="implementer",
            status="active",
            mission="Test agent B",
        )
        db_session.add(job_b)
        await db_session.flush()

        exec_b = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_b.job_id,
            tenant_key=tenant_b,
            agent_display_name="implementer",
            status="working",
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
        )

        db_session.add_all([exec_a, sender_exec_a, exec_b])
        await db_session.commit()

        # Send message in tenant A
        tenant_manager_a = TenantManager()
        tenant_manager_a.set_current_tenant(tenant_a)
        service_a = MessageService(
            db_manager=db_manager,
            tenant_manager=tenant_manager_a,
            websocket_manager=mock_websocket_manager,
            test_session=db_session,
        )
        result = await service_a.send_message(
            from_agent=sender_exec_a.agent_id,
            to_agents=[exec_a.agent_id],
            content="Tenant A message",
            message_type="direct",
            project_id=project_a.id,
        )
        assert result.message_id is not None

        # Verify: Tenant A agent has waiting_count incremented
        await db_session.refresh(exec_a)
        assert exec_a.messages_waiting_count >= 1, (
            "Tenant A agent should have waiting_count incremented"
        )

        # Verify: Tenant B agent counters untouched
        await db_session.refresh(exec_b)
        assert exec_b.messages_waiting_count == 0, (
            "Tenant B agent should NOT be affected by tenant A messages"
        )
        assert exec_b.messages_sent_count == 0, (
            "Tenant B agent sent_count should remain 0"
        )
        assert exec_b.messages_read_count == 0, (
            "Tenant B agent read_count should remain 0"
        )
