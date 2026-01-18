"""
Integration Tests for Handover 0401: Unified WebSocket Platform

TDD RED PHASE: These tests should FAIL initially until implementation.

Test BEHAVIOR, not implementation:
- Message acknowledgment persists to AgentExecution.messages JSONB
- agent_id resolution works for message handlers
- Both job_id and agent_id included in WebSocket payloads

Coverage Targets:
- _update_jsonb_message_status() queries AgentExecution (not AgentJob)
- receive_messages() correctly updates JSONB message status
- Message read counts persist across page refresh (API reload)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
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
async def test_tenant_key(tenant_manager) -> str:
    """Generate valid tenant key for test isolation using TenantManager."""
    # Use generate_tenant_key() to create properly formatted key
    return tenant_manager.generate_tenant_key(project_name="Test0401")


@pytest.fixture
async def message_service_factory(db_manager, db_session, mock_websocket_manager, tenant_manager, test_tenant_key):
    """Factory fixture to create MessageService instances with proper dependencies."""
    def _create(tenant_key: str = None):
        # Use provided tenant_key or default to test_tenant_key
        key = tenant_key or test_tenant_key
        # Set tenant context before creating service
        tenant_manager.set_current_tenant(key)
        return MessageService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=mock_websocket_manager,
            test_session=db_session,
        )
    return _create


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    """Create a test product."""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Test Product 0401",
        description="Test product for unified WebSocket platform tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
) -> Project:
    """Create a test project."""
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project 0401",
        description="Test project for message persistence tests",  # Required field
        mission="Test the unified WebSocket platform",
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
    test_project: Project,
) -> tuple[AgentJob, AgentExecution]:
    """
    Create an agent with both AgentJob (work order) and AgentExecution (executor).

    Returns tuple of (job, execution) for testing the agent_id/job_id separation.
    """
    # Create work order (AgentJob)
    # Note: AgentJob uses job_type (not agent_display_name), mission is required
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=test_project.id,
        job_type="implementer",  # AgentJob uses job_type, not agent_display_name
        status="active",
        mission="Test agent for message persistence",
    )
    db_session.add(job)
    await db_session.flush()

    # Create executor (AgentExecution) - this holds the messages
    # Note: AgentExecution uses agent_display_name and agent_name
    execution = AgentExecution(
        agent_id=str(uuid4()),  # Different from job_id - this is executor UUID
        job_id=job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="implementer",
        agent_name="test-implementer",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        context_used=0,
        context_budget=100000,
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
    test_project: Project,
) -> tuple[AgentJob, AgentExecution]:
    """Create a sender agent (orchestrator) for message tests."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=test_project.id,
        job_type="orchestrator",  # AgentJob uses job_type
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
        messages=[],
        context_used=0,
        context_budget=100000,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)

    return job, execution


# ============================================================================
# Test Classes
# ============================================================================


@pytest.mark.asyncio
class TestUnifiedWebSocketPlatform:
    """
    Integration tests for Handover 0401: Unified WebSocket Platform.

    These tests validate the JSONB persistence fix and agent_id resolution.
    """

    async def test_jsonb_update_targets_agent_execution_not_agent_job(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        CRITICAL: _update_jsonb_message_status() should query AgentExecution.

        Bug: Previously queried AgentJob.messages which doesn't exist.
        Fix: Query AgentExecution.messages (where messages are actually stored).
        """
        job, execution = test_agent_with_execution
        sender_job, sender_execution = test_sender_agent

        # Create message service using factory
        message_service = message_service_factory(test_tenant_key)

        # Step 1: Send a message to the agent
        send_result = await message_service.send_message(
            from_agent=sender_execution.agent_id,
            to_agents=[execution.agent_id],  # Send to agent_id (executor)
            content="Test message for JSONB persistence",
            message_type="direct",
            project_id=test_project.id,
        )
        assert send_result["success"], f"Failed to send message: {send_result.get('error')}"
        message_id = send_result["data"]["message_id"]

        # Step 2: Verify message is persisted to AgentExecution.messages JSONB
        await db_session.refresh(execution)
        assert execution.messages is not None, "Messages should be persisted to execution"
        assert len(execution.messages) > 0, "Should have at least one message in JSONB"

        # Find the message in JSONB
        jsonb_message = next(
            (m for m in execution.messages if m.get("id") == message_id),
            None
        )
        assert jsonb_message is not None, "Message should exist in JSONB"
        assert jsonb_message.get("status") == "waiting", "Initial status should be 'waiting'"

        # Step 3: Agent reads message (this should update JSONB status)
        receive_result = await message_service.receive_messages(
            agent_id=execution.agent_id,  # Use agent_id, not job_id
            limit=10,
        )
        assert receive_result["success"], f"Failed to receive messages: {receive_result.get('error')}"

        # Step 4: CRITICAL ASSERTION - Verify JSONB status updated
        await db_session.refresh(execution)
        jsonb_message_after = next(
            (m for m in execution.messages if m.get("id") == message_id),
            None
        )
        assert jsonb_message_after is not None, "Message should still exist in JSONB"
        # Status should be 'acknowledged' after receive_messages
        assert jsonb_message_after.get("status") == "acknowledged", (
            f"JSONB status should be 'acknowledged' after read, got: {jsonb_message_after.get('status')}"
        )

    async def test_message_read_count_persists_across_refresh(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        Message read count should persist across page refresh.

        Simulates: Send 3 messages → Agent reads 2 → Refresh page → Counts accurate.
        """
        job, execution = test_agent_with_execution
        sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Step 1: Send 3 messages to the agent
        message_ids = []
        for i in range(3):
            result = await message_service.send_message(
                from_agent=sender_execution.agent_id,
                to_agents=[execution.agent_id],
                content=f"Test message {i+1}",
                message_type="direct",
                project_id=test_project.id,
            )
            assert result["success"]
            message_ids.append(result["data"]["message_id"])

        # Step 2: Verify initial state - 3 waiting, 0 read
        await db_session.refresh(execution)
        waiting_count = sum(
            1 for m in execution.messages
            if m.get("status") == "waiting"
        )
        read_count = sum(
            1 for m in execution.messages
            if m.get("status") in ("acknowledged", "read")
        )
        assert waiting_count == 3, f"Should have 3 waiting messages, got {waiting_count}"
        assert read_count == 0, f"Should have 0 read messages, got {read_count}"

        # Step 3: Agent reads messages (auto-acknowledge)
        receive_result = await message_service.receive_messages(
            agent_id=execution.agent_id,
            limit=2,  # Only read 2 of 3
        )
        assert receive_result["success"]

        # Step 4: CRITICAL - Refresh and verify persistence
        await db_session.refresh(execution)

        waiting_after = sum(
            1 for m in execution.messages
            if m.get("status") == "waiting"
        )
        read_after = sum(
            1 for m in execution.messages
            if m.get("status") in ("acknowledged", "read")
        )

        # Expected: 1 waiting (unread), 2 acknowledged (read)
        assert waiting_after == 1, f"Should have 1 waiting after reading 2, got {waiting_after}"
        assert read_after == 2, f"Should have 2 read after reading 2, got {read_after}"

    async def test_agent_id_used_for_message_persistence(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        Messages should be keyed by agent_id (executor), not job_id (work order).

        This validates the Handover 0381 contract:
        - job_id = "what am I working on" (persists across succession)
        - agent_id = "who am I" (changes on succession)
        - Messaging uses agent_id because messages are between executors
        """
        job, execution = test_agent_with_execution
        sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send message to agent_id
        result = await message_service.send_message(
            from_agent=sender_execution.agent_id,
            to_agents=[execution.agent_id],  # Must use agent_id
            content="Message to executor, not work order",
            message_type="direct",
            project_id=test_project.id,
        )
        assert result["success"]

        # Verify: Message stored on AgentExecution (by agent_id), not AgentJob
        await db_session.refresh(execution)
        assert len(execution.messages) == 1, "Message should be on AgentExecution"

        # AgentJob should NOT have the message (it doesn't have messages column)
        await db_session.refresh(job)
        # AgentJob model may not even have a messages attribute
        assert not hasattr(job, "messages") or job.messages is None, (
            "AgentJob should not have messages - they belong on AgentExecution"
        )


@pytest.mark.asyncio
class TestWebSocketPayloadIntegrity:
    """
    Tests that WebSocket event payloads include both job_id and agent_id.
    """

    async def test_message_send_includes_both_identifiers(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        WebSocket message:sent event should include both job_id and agent_id.

        This allows frontend to resolve by either identifier.
        """
        job, execution = test_agent_with_execution
        sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send message - capture the result which should have both IDs
        result = await message_service.send_message(
            from_agent=sender_execution.agent_id,
            to_agents=[execution.agent_id],
            content="Test for payload structure",
            message_type="direct",
            project_id=test_project.id,
        )
        assert result["success"]

        # The send_message result should contain message data
        message_data = result.get("data", {})

        # For complete verification, we'd need to intercept WebSocket events
        # Here we verify the service returns proper data structure
        assert message_data.get("message_id"), "Should have message_id"
        # Note: Full WebSocket payload testing requires E2E test with actual WebSocket

    async def test_receive_messages_returns_correct_counts(
        self,
        db_session: AsyncSession,
        test_tenant_key: str,
        test_project: Project,
        test_agent_with_execution: tuple[AgentJob, AgentExecution],
        test_sender_agent: tuple[AgentJob, AgentExecution],
        message_service_factory,
    ):
        """
        receive_messages() should return accurate waiting/read counts.
        """
        job, execution = test_agent_with_execution
        sender_job, sender_execution = test_sender_agent

        message_service = message_service_factory(test_tenant_key)

        # Send 5 messages
        for i in range(5):
            await message_service.send_message(
                from_agent=sender_execution.agent_id,
                to_agents=[execution.agent_id],
                content=f"Count test message {i+1}",
                message_type="direct",
                project_id=test_project.id,
            )

        # Read 3 messages
        result = await message_service.receive_messages(
            agent_id=execution.agent_id,
            limit=3,
        )
        assert result["success"]

        # Result should include count information
        messages = result.get("data", {}).get("messages", [])
        assert len(messages) == 3, f"Should receive 3 messages, got {len(messages)}"

        # Verify JSONB persistence
        await db_session.refresh(execution)
        waiting = sum(1 for m in execution.messages if m.get("status") == "waiting")
        acknowledged = sum(1 for m in execution.messages if m.get("status") == "acknowledged")

        assert waiting == 2, f"Should have 2 waiting, got {waiting}"
        assert acknowledged == 3, f"Should have 3 acknowledged, got {acknowledged}"


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """
    Verify multi-tenant isolation is maintained in the unified platform.
    """

    async def test_message_persistence_respects_tenant_isolation(
        self,
        db_session: AsyncSession,
        db_manager,
        mock_websocket_manager,
        tenant_manager,
    ):
        """
        Messages from one tenant should not affect another tenant's data.
        """
        # Generate valid tenant keys using TenantManager
        tenant_a = tenant_manager.generate_tenant_key(project_name="IsolationA")
        tenant_b = tenant_manager.generate_tenant_key(project_name="IsolationB")

        # Create products for each tenant
        product_a = Product(
            id=str(uuid4()),
            tenant_key=tenant_a,
            name="Product A",
            product_memory={},
        )
        product_b = Product(
            id=str(uuid4()),
            tenant_key=tenant_b,
            name="Product B",
            product_memory={},
        )
        db_session.add_all([product_a, product_b])
        await db_session.flush()

        # Create projects (mission is required)
        project_a = Project(
            id=str(uuid4()),
            tenant_key=tenant_a,
            product_id=product_a.id,
            name="Project A",
            description="Test project A for tenant isolation",
            mission="Test tenant isolation A",
            status="active",
        )
        project_b = Project(
            id=str(uuid4()),
            tenant_key=tenant_b,
            product_id=product_b.id,
            name="Project B",
            description="Test project B for tenant isolation",
            mission="Test tenant isolation B",
            status="active",
        )
        db_session.add_all([project_a, project_b])
        await db_session.flush()

        # Create agents for each tenant
        job_a = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_a,
            project_id=project_a.id,
            job_type="implementer",  # AgentJob uses job_type
            status="active",
            mission="Test agent A",
        )
        exec_a = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_a.job_id,
            tenant_key=tenant_a,
            agent_display_name="implementer",
            status="working",
            messages=[],
        )

        job_b = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_b,
            project_id=project_b.id,
            job_type="implementer",  # AgentJob uses job_type
            status="active",
            mission="Test agent B",
        )
        exec_b = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_b.job_id,
            tenant_key=tenant_b,
            agent_display_name="implementer",
            status="working",
            messages=[],
        )

        db_session.add_all([job_a, exec_a, job_b, exec_b])
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
        await service_a.send_message(
            from_agent=exec_a.agent_id,
            to_agents=[exec_a.agent_id],  # Self-message for test
            content="Tenant A message",
            message_type="direct",
            project_id=project_a.id,
        )

        # Verify: Tenant B's agent should NOT have tenant A's message
        await db_session.refresh(exec_a)
        await db_session.refresh(exec_b)

        assert len(exec_a.messages) >= 1, "Tenant A should have message"
        assert len(exec_b.messages) == 0, "Tenant B should NOT have tenant A's message"
