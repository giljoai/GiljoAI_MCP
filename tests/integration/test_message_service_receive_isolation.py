"""
Integration tests for MessageService — tenant isolation, list_messages,
and broadcast self-exclusion.
"""

import random
from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.services.message_service import MessageService

pytestmark = pytest.mark.skip(reason="0750c3: schema drift — project_id invalid keyword for AgentExecution")


@pytest.mark.asyncio
async def test_receive_messages_tenant_isolation(db_manager, tenant_manager):
    """Test receive_messages enforces multi-tenant isolation."""
    service = MessageService(db_manager, tenant_manager)

    # Generate unique IDs for this test
    tenant_key_1 = f"tenant-{uuid4().hex[:8]}"
    tenant_key_2 = f"tenant-{uuid4().hex[:8]}"
    project1_id = f"proj-tenant-1-{uuid4().hex[:8]}"
    project2_id = f"proj-tenant-2-{uuid4().hex[:8]}"
    agent1_id = f"agent-tenant-1-{uuid4().hex[:8]}"
    agent2_id = f"agent-tenant-2-{uuid4().hex[:8]}"
    msg1_id = f"msg-tenant-1-{uuid4().hex[:8]}"
    msg2_id = f"msg-tenant-2-{uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        # Create two projects for different tenants
        project1 = Project(
            id=project1_id,
            tenant_key=tenant_key_1,
            name="Tenant 1 Project",
            description="Test project for tenant 1",
            mission="Test mission for tenant 1",
            status="active",
            series_number=random.randint(1, 999999),
        )
        project2 = Project(
            id=project2_id,
            tenant_key=tenant_key_2,
            name="Tenant 2 Project",
            description="Test project for tenant 2",
            mission="Test mission for tenant 2",
            status="active",
            series_number=random.randint(1, 999999),
        )
        session.add_all([project1, project2])

        # Create agents for both tenants (valid status: working)
        agent1 = AgentExecution(
            job_id=agent1_id,
            tenant_key=tenant_key_1,
            project_id=project1.id,
            agent_display_name="implementer",
            agent_name="Tenant 1 Agent",
            mission="Work for tenant 1",
            status="working",
        )
        agent2 = AgentExecution(
            job_id=agent2_id,
            tenant_key=tenant_key_2,
            project_id=project2.id,
            agent_display_name="implementer",
            agent_name="Tenant 2 Agent",
            mission="Work for tenant 2",
            status="working",
        )
        session.add_all([agent1, agent2])

        # Create messages for both tenants
        msg1 = Message(
            id=msg1_id,
            tenant_key=tenant_key_1,
            project_id=project1.id,
            to_agents=[agent1_id],
            content="Message for tenant 1",
            status="pending",
        )
        msg2 = Message(
            id=msg2_id,
            tenant_key=tenant_key_2,
            project_id=project2.id,
            to_agents=[agent2_id],
            content="Message for tenant 2",
            status="pending",
        )
        session.add_all([msg1, msg2])

        await session.commit()

        # Cleanup after test
        try:
            # Tenant 1 should only see their messages
            result1 = await service.receive_messages(agent_id=agent1_id, tenant_key=tenant_key_1)

            assert result1["success"] is True
            message_ids = {msg["id"] for msg in result1["messages"]}
            assert msg1_id in message_ids
            assert msg2_id not in message_ids

            # Tenant 2 should only see their messages
            result2 = await service.receive_messages(agent_id=agent2_id, tenant_key=tenant_key_2)

            assert result2["success"] is True
            message_ids = {msg["id"] for msg in result2["messages"]}
            assert msg2_id in message_ids
            assert msg1_id not in message_ids
        finally:
            # Cleanup
            await session.rollback()


@pytest.mark.asyncio
async def test_list_messages_by_agent(db_manager, tenant_manager, setup_test_data):
    """Test list_messages with agent_id filter."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # List all messages for agent-1 (including acknowledged)
    result = await service.list_messages(agent_id=data["agent1_id"])

    assert result["success"] is True
    assert result["count"] >= 3  # Should include acknowledged messages


@pytest.mark.asyncio
async def test_list_messages_by_project(db_manager, tenant_manager, setup_test_data):
    """Test list_messages with project_id filter."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    result = await service.list_messages(project_id=data["project"].id)

    assert result["success"] is True
    assert result["count"] == 5  # All 5 test messages


@pytest.mark.asyncio
async def test_list_messages_by_status(db_manager, tenant_manager, setup_test_data):
    """Test list_messages with status filter."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # Filter for pending messages only
    result = await service.list_messages(project_id=data["project"].id, status="pending")

    assert result["success"] is True
    assert result["count"] == 4  # 4 pending messages (msg-1, msg-2, msg-3, msg-5)

    # Filter for acknowledged messages
    result = await service.list_messages(project_id=data["project"].id, status="acknowledged")

    assert result["success"] is True
    assert result["count"] == 1  # 1 acknowledged message (msg-4)


@pytest.mark.asyncio
async def test_broadcast_excludes_sender(db_manager, tenant_manager, test_tenant_key):
    """
    TEST FOR ISSUE 0361-3: Verify broadcast messages exclude sender.

    When an agent sends a broadcast message, calling receive_messages()
    should NOT return their own broadcast message.
    """
    service = MessageService(db_manager, tenant_manager)
    tenant_key = test_tenant_key

    # Generate unique IDs for this test
    project_id = f"proj-broadcast-{uuid4().hex[:8]}"
    sender_agent_id = f"sender-{uuid4().hex[:8]}"
    other_agent_id = f"other-{uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        # Create test project
        project = Project(
            id=project_id,
            tenant_key=tenant_key,
            name="Broadcast Test Project",
            description="Test project for broadcast self-exclusion",
            mission="Test mission",
            status="active",
            series_number=random.randint(1, 999999),
        )
        session.add(project)

        # Create sender agent
        sender_agent = AgentExecution(
            job_id=sender_agent_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            agent_name="Orchestrator",
            mission="Coordinate agents",
            status="working",
        )

        # Create other agent
        other_agent = AgentExecution(
            job_id=other_agent_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_display_name="implementer",
            agent_name="Implementer",
            mission="Implement features",
            status="working",
        )
        session.add_all([sender_agent, other_agent])

        # Commit agents
        await session.commit()

    # Sender agent sends broadcast message
    broadcast_result = await service.send_message(
        to_agents=["all"],
        content="Status update: All agents complete staging",
        project_id=project_id,
        from_agent=sender_agent.agent_display_name,
        message_type="broadcast",
    )

    assert broadcast_result["success"] is True

    # CRITICAL TEST: Sender agent receives messages
    # Should NOT get their own broadcast
    sender_messages = await service.receive_messages(agent_id=sender_agent_id, limit=10)

    assert sender_messages["success"] is True
    # Sender should NOT receive own broadcast
    assert sender_messages["count"] == 0, (
        f"Sender should not receive own broadcast, but got {sender_messages['count']} messages"
    )

    # Other agent receives messages
    # SHOULD get the broadcast
    other_messages = await service.receive_messages(agent_id=other_agent_id, limit=10)

    assert other_messages["success"] is True
    # Other agent SHOULD receive the broadcast
    assert other_messages["count"] == 1, (
        f"Other agent should receive broadcast, but got {other_messages['count']} messages"
    )

    # Verify it's the broadcast message
    if other_messages["count"] > 0:
        msg = other_messages["messages"][0]
        assert msg["content"] == "Status update: All agents complete staging"
        assert msg["type"] == "broadcast"
