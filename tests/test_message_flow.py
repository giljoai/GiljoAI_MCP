"""
Integration tests for inter-agent message flow
Tests the complete message lifecycle from send to complete
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.giljo_mcp.agent_message_queue import AgentMessageQueue
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.tenant import TenantManager


@pytest.mark.asyncio
async def test_send_message_flow(db_manager, db_session, test_project):
    """Test complete message send flow"""
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    # Send message
    result = await service.send_message(
        to_agents=["test-implementer"],
        content="Implement feature X",
        project_id=test_project.id,
        message_type="direct",
        priority="high",
        from_agent="orchestrator",
    )

    # Debug output
    if not result.get("success"):
        print(f"ERROR: {result.get('error')}")

    assert result["success"] is True, f"Failed to send message: {result.get('error')}"
    assert "message_id" in result

    # Verify database
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == result["message_id"])
        msg = (await session.execute(stmt)).scalar_one()

        assert msg.to_agents == ["test-implementer"]
        assert msg.content == "Implement feature X"
        assert msg.priority == "high"
        assert msg.status == "pending"
        assert msg.tenant_key == test_project.tenant_key
        assert msg.project_id == test_project.id


@pytest.mark.asyncio
async def test_send_message_flow_multi_recipient(db_manager, db_session, test_project):
    """Test sending message to multiple recipients"""
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    # Send message to multiple agents
    result = await service.send_message(
        to_agents=["implementer-1", "implementer-2", "analyzer-1"],
        content="Review code changes",
        project_id=test_project.id,
        message_type="direct",
        priority="normal",
        from_agent="orchestrator",
    )

    assert result["success"] is True

    # Verify database
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == result["message_id"])
        msg = (await session.execute(stmt)).scalar_one()

        assert len(msg.to_agents) == 3
        assert "implementer-1" in msg.to_agents
        assert "implementer-2" in msg.to_agents
        assert "analyzer-1" in msg.to_agents


@pytest.mark.asyncio
async def test_receive_messages_flow(db_manager, db_session, test_project, test_agent_jobs):
    """
    Test message retrieval flow.

    Migration Note (0367d): test_agent_jobs now returns list of tuples [(job, execution), ...].
    """
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    # Unpack first job and execution
    first_job, first_execution = test_agent_jobs[0]

    # Create a test message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-implementer"],
        content="Test message content",
        message_type="direct",
        priority="normal",
        status="waiting",
        created_at=datetime.now(timezone.utc),
        meta_data={"_job_id": first_job.job_id},
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Retrieve messages using AgentMessageQueue
    queue = AgentMessageQueue(db_manager)

    async with db_manager.get_session_async() as session:
        result = await queue.get_messages(
            session=session,
            job_id=first_job.job_id,
            tenant_key=test_project.tenant_key,
            to_agent="test-implementer",
            unread_only=True,
        )

    assert result["status"] == "success"
    assert len(result["messages"]) > 0
    assert result["messages"][0]["content"] == "Test message content"


@pytest.mark.asyncio
async def test_acknowledge_message_flow(db_manager, db_session, test_project):
    """Test message acknowledgment flow"""
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    # Create a test message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-implementer"],
        content="Message to acknowledge",
        message_type="direct",
        priority="normal",
        status="waiting",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    service = MessageService(db_manager, tenant_manager)

    result = await service.acknowledge_message(message_id=message.id, agent_name="test-implementer")

    assert result["success"] is True

    # Verify database update
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == message.id)
        msg = (await session.execute(stmt)).scalar_one()

        assert msg.status == "acknowledged"
        assert "test-implementer" in msg.acknowledged_by
        assert msg.acknowledged_at is not None


@pytest.mark.asyncio
async def test_complete_message_flow(db_manager, db_session, test_project):
    """Test message completion flow"""
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    # Create a test message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-implementer"],
        content="Message to complete",
        message_type="direct",
        priority="normal",
        status="acknowledged",
        acknowledged_by=["test-implementer"],
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    service = MessageService(db_manager, tenant_manager)

    result = await service.complete_message(
        message_id=message.id,
        agent_name="test-implementer",
        result_data={"status": "completed", "output": "Feature implemented successfully"},
    )

    assert result["success"] is True

    # Verify database update
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == message.id)
        msg = (await session.execute(stmt)).scalar_one()

        assert msg.status == "completed"
        assert "test-implementer" in msg.completed_by
        assert msg.completed_at is not None
        assert "result_data" in msg.meta_data
        assert msg.meta_data["result_data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_broadcast_message_flow(db_manager, db_session, test_project, test_agent_jobs):
    """Test broadcast message to all agents in project"""
    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(test_project.tenant_key)

    service = MessageService(db_manager, tenant_manager)

    # Send broadcast message (empty to_agents means broadcast)
    result = await service.send_message(
        to_agents=[],  # Empty means broadcast to all
        content="System announcement: Deploy to staging at 3pm",
        project_id=test_project.id,
        message_type="broadcast",
        priority="high",
        from_agent="orchestrator",
    )

    assert result["success"] is True

    # Verify database
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == result["message_id"])
        msg = (await session.execute(stmt)).scalar_one()

        assert msg.message_type == "broadcast"
        assert msg.to_agents == []  # Broadcast has empty recipients
        assert msg.priority == "high"
        assert "System announcement" in msg.content


@pytest.mark.asyncio
async def test_message_multi_tenant_isolation(db_manager, db_session):
    """Test that messages are isolated by tenant"""

    # Create two separate tenants with projects
    tenant1_key = TenantManager.generate_tenant_key()
    tenant2_key = TenantManager.generate_tenant_key()

    # Create projects for each tenant
    project1 = Project(
        id=str(uuid4()),
        name="Tenant 1 Project",
        description="Test project description for tenant 1",
        mission="Test mission 1",
        status="active",
        tenant_key=tenant1_key,
    )
    project2 = Project(
        id=str(uuid4()),
        name="Tenant 2 Project",
        description="Test project description for tenant 2",
        mission="Test mission 2",
        status="active",
        tenant_key=tenant2_key,
    )
    db_session.add(project1)
    db_session.add(project2)
    await db_session.commit()

    # Create messages for each tenant
    message1 = Message(
        id=str(uuid4()),
        tenant_key=tenant1_key,
        project_id=project1.id,
        to_agents=["agent-1"],
        content="Message for tenant 1",
        status="waiting",
    )
    message2 = Message(
        id=str(uuid4()),
        tenant_key=tenant2_key,
        project_id=project2.id,
        to_agents=["agent-2"],
        content="Message for tenant 2",
        status="waiting",
    )
    db_session.add(message1)
    db_session.add(message2)
    await db_session.commit()

    # Query messages for tenant 1
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.tenant_key == tenant1_key)
        tenant1_messages = (await session.execute(stmt)).scalars().all()

        # Tenant 1 should only see their own message
        assert len(tenant1_messages) == 1
        assert tenant1_messages[0].content == "Message for tenant 1"
        assert tenant1_messages[0].id == message1.id

    # Query messages for tenant 2
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.tenant_key == tenant2_key)
        tenant2_messages = (await session.execute(stmt)).scalars().all()

        # Tenant 2 should only see their own message
        assert len(tenant2_messages) == 1
        assert tenant2_messages[0].content == "Message for tenant 2"
        assert tenant2_messages[0].id == message2.id


@pytest.mark.asyncio
async def test_message_priority_ordering(db_manager, db_session, test_project):
    """Test that messages are retrieved in priority order"""

    # Create messages with different priorities
    priorities = ["low", "normal", "high", "critical"]
    messages = []

    for priority in priorities:
        message = Message(
            id=str(uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            to_agents=["test-agent"],
            content=f"Message with {priority} priority",
            priority=priority,
            status="waiting",
        )
        db_session.add(message)
        messages.append(message)

    await db_session.commit()

    # Query messages - should be ordered by priority
    queue = AgentMessageQueue(db_manager)
    async with db_manager.get_session_async() as session:
        # The queue should return highest priority first
        result = await queue.get_messages(
            session=session, job_id=None, tenant_key=test_project.tenant_key, to_agent="test-agent", unread_only=True
        )

    assert result["status"] == "success"
    retrieved_messages = result["messages"]

    # Verify critical priority is first
    assert retrieved_messages[0]["priority"] == "critical"


@pytest.mark.asyncio
async def test_message_retry_count(db_manager, db_session, test_project):
    """Test message retry count functionality"""

    # Create message with retry tracking
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-agent"],
        content="Message with retry tracking",
        status="waiting",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Simulate retry
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == message.id)
        msg = (await session.execute(stmt)).scalar_one()
        msg.retry_count += 1
        await session.commit()
        await session.refresh(msg)

    # Verify retry count incremented
    async with db_manager.get_session_async() as session:
        stmt = select(Message).where(Message.id == message.id)
        msg = (await session.execute(stmt)).scalar_one()
        assert msg.retry_count == 1
        assert msg.max_retries == 3
