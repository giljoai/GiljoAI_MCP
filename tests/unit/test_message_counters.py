"""
TDD tests for message counter columns (Handover 0387e).

Tests the addition of messages_sent_count, messages_waiting_count, and messages_read_count
columns to AgentExecution model, along with atomic increment/decrement operations.

Run with: pytest tests/unit/test_message_counters.py -v
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from tests.fixtures.base_fixtures import TestData


async def create_test_execution(
    session: AsyncSession,
    tenant_key: str,
    agent_display_name: str = "test_worker",
) -> AgentExecution:
    """
    Helper function to create a test AgentExecution with AgentJob and Project.

    Args:
        session: Database session
        tenant_key: Tenant isolation key
        agent_display_name: Agent display name (default: "test_worker")

    Returns:
        AgentExecution instance
    """
    from src.giljo_mcp.models import Project

    # Create Project first (foreign key requirement)
    project_data = TestData.generate_project_data(tenant_key=tenant_key)
    project = Project(**project_data)
    session.add(project)
    await session.flush()  # Ensure project exists before creating job

    # Create AgentJob (work order)
    job_data = TestData.generate_agent_job_data(
        project_id=project.id,
        tenant_key=tenant_key,
        agent_display_name=agent_display_name,
    )
    job = AgentJob(**job_data)
    session.add(job)

    # Create AgentExecution (executor)
    execution_data = TestData.generate_agent_execution_data(
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name=agent_display_name,
    )
    execution = AgentExecution(**execution_data)
    session.add(execution)

    await session.commit()
    await session.refresh(execution)

    return execution


class TestMessageCounterColumns:
    """Tests for message counter columns on AgentExecution (Handover 0387e)."""

    @pytest.mark.asyncio
    async def test_counter_columns_exist(self, db_session: AsyncSession):
        """
        AgentExecution should have messages_sent_count, messages_waiting_count,
        messages_read_count columns with default value 0.

        RED PHASE: This test will FAIL because counter columns don't exist yet.
        """
        # Create a test execution
        execution = await create_test_execution(db_session, tenant_key="test_tenant_001")

        # Assert columns exist with default values
        assert hasattr(execution, "messages_sent_count"), "AgentExecution missing messages_sent_count column"
        assert hasattr(execution, "messages_waiting_count"), "AgentExecution missing messages_waiting_count column"
        assert hasattr(execution, "messages_read_count"), "AgentExecution missing messages_read_count column"

        # Assert default values are 0
        assert execution.messages_sent_count == 0, "messages_sent_count should default to 0"
        assert execution.messages_waiting_count == 0, "messages_waiting_count should default to 0"
        assert execution.messages_read_count == 0, "messages_read_count should default to 0"

    @pytest.mark.asyncio
    async def test_increment_sent_count(self, db_session: AsyncSession):
        """
        increment_sent_count should atomically increase sent counter by 1.

        RED PHASE: This test will FAIL because increment_sent_count method doesn't exist.
        """
        # Create a test execution
        execution = await create_test_execution(db_session, tenant_key="test_tenant_002")

        # Get repository
        repo = AgentJobRepository(None)

        # Increment sent count
        await repo.increment_sent_count(session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_002")

        # Refresh to get updated values
        await db_session.refresh(execution)

        # Assert counter incremented
        assert execution.messages_sent_count == 1, "messages_sent_count should be 1 after increment"
        assert execution.messages_waiting_count == 0, "Other counters should not be affected"
        assert execution.messages_read_count == 0, "Other counters should not be affected"

    @pytest.mark.asyncio
    async def test_increment_waiting_count(self, db_session: AsyncSession):
        """
        increment_waiting_count should atomically increase waiting counter by 1.

        RED PHASE: This test will FAIL because increment_waiting_count method doesn't exist.
        """
        # Create a test execution
        execution = await create_test_execution(db_session, tenant_key="test_tenant_003")

        # Get repository
        repo = AgentJobRepository(None)

        # Increment waiting count
        await repo.increment_waiting_count(
            session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_003"
        )

        # Refresh to get updated values
        await db_session.refresh(execution)

        # Assert counter incremented
        assert execution.messages_waiting_count == 1, "messages_waiting_count should be 1 after increment"
        assert execution.messages_sent_count == 0, "Other counters should not be affected"
        assert execution.messages_read_count == 0, "Other counters should not be affected"

    @pytest.mark.asyncio
    async def test_decrement_waiting_increment_read(self, db_session: AsyncSession):
        """
        Acknowledging a message should decrement waiting and increment read atomically.

        RED PHASE: This test will FAIL because decrement_waiting_increment_read method doesn't exist.
        """
        # Create a test execution
        execution = await create_test_execution(db_session, tenant_key="test_tenant_004")

        # Get repository
        repo = AgentJobRepository(None)

        # First, receive a message (increment waiting)
        await repo.increment_waiting_count(
            session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_004"
        )

        # Refresh to verify waiting count
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 1, "Waiting count should be 1 before ack"

        # Then acknowledge it (decrement waiting, increment read)
        await repo.decrement_waiting_increment_read(
            session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_004"
        )

        # Refresh to get updated values
        await db_session.refresh(execution)

        # Assert dual update occurred atomically
        assert execution.messages_waiting_count == 0, "messages_waiting_count should be 0 after ack"
        assert execution.messages_read_count == 1, "messages_read_count should be 1 after ack"
        assert execution.messages_sent_count == 0, "Sent counter should not be affected"

    @pytest.mark.asyncio
    async def test_counters_are_atomic(self, db_session: AsyncSession):
        """
        Counter operations should be atomic (no race conditions).

        Tests multiple sequential increments to verify atomicity.

        RED PHASE: This test will FAIL because increment methods don't exist.
        """
        # Create a test execution
        execution = await create_test_execution(db_session, tenant_key="test_tenant_005")

        # Get repository
        repo = AgentJobRepository(None)

        # Increment sent 5 times
        for _ in range(5):
            await repo.increment_sent_count(
                session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_005"
            )

        # Refresh to get updated values
        await db_session.refresh(execution)

        # Assert all increments registered
        assert execution.messages_sent_count == 5, "All 5 increments should be registered atomically"

        # Increment waiting 3 times
        for _ in range(3):
            await repo.increment_waiting_count(
                session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_005"
            )

        # Refresh to get updated values
        await db_session.refresh(execution)

        # Assert all increments registered
        assert execution.messages_waiting_count == 3, "All 3 increments should be registered atomically"

    @pytest.mark.asyncio
    async def test_counters_respect_tenant_isolation(self, db_session: AsyncSession):
        """
        Counter updates should only affect executions in the same tenant.

        Verifies multi-tenant isolation for counter operations.

        RED PHASE: This test will FAIL because increment methods don't exist.
        """
        # Create executions in different tenants
        exec_a = await create_test_execution(db_session, tenant_key="tenant_a")
        exec_b = await create_test_execution(db_session, tenant_key="tenant_b")

        # Get repository
        repo = AgentJobRepository(None)

        # Increment only tenant_a
        await repo.increment_sent_count(session=db_session, agent_id=exec_a.agent_id, tenant_key="tenant_a")

        # Refresh both executions
        await db_session.refresh(exec_a)
        await db_session.refresh(exec_b)

        # Assert only tenant_a was affected
        assert exec_a.messages_sent_count == 1, "Tenant A counter should be incremented"
        assert exec_b.messages_sent_count == 0, "Tenant B counter should be unchanged (tenant isolation)"

    @pytest.mark.asyncio
    async def test_waiting_count_cannot_go_negative(self, db_session: AsyncSession):
        """
        decrement_waiting_increment_read should not make waiting_count negative.

        Tests edge case where ack is called when waiting count is already 0.

        RED PHASE: This test will FAIL because decrement_waiting_increment_read doesn't exist.
        """
        # Create a test execution
        execution = await create_test_execution(db_session, tenant_key="test_tenant_007")

        # Get repository
        repo = AgentJobRepository(None)

        # Verify initial state
        await db_session.refresh(execution)
        assert execution.messages_waiting_count == 0, "Initial waiting count should be 0"

        # Try to decrement when count is 0
        await repo.decrement_waiting_increment_read(
            session=db_session, agent_id=execution.agent_id, tenant_key="test_tenant_007"
        )

        # Refresh to get updated values
        await db_session.refresh(execution)

        # Should either stay at 0 or raise an error, not go negative
        assert execution.messages_waiting_count >= 0, "Waiting count should never be negative"
        assert execution.messages_read_count == 1, "Read count should still increment"
