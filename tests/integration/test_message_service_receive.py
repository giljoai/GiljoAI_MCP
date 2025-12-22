"""
Integration tests for MessageService.receive_messages and list_messages.

Tests proper database queries without legacy AgentMessageQueue dependency.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.tasks import Message
from giljo_mcp.models.projects import Project
from giljo_mcp.models.agent_identity import AgentExecution
from giljo_mcp.services.message_service import MessageService
from giljo_mcp.tenant import TenantManager


@pytest.fixture
async def setup_test_data(db_manager: DatabaseManager, test_tenant_key: str):
    """Create test project, agents, and messages with unique IDs."""
    tenant_key = test_tenant_key

    # Generate unique IDs for this test run
    project_id = f"proj-test-{uuid4().hex[:8]}"
    agent1_id = f"agent-{uuid4().hex[:8]}"
    agent2_id = f"agent-{uuid4().hex[:8]}"
    agent3_id = f"agent-{uuid4().hex[:8]}"
    msg1_id = f"msg-{uuid4().hex[:8]}"
    msg2_id = f"msg-{uuid4().hex[:8]}"
    msg3_id = f"msg-{uuid4().hex[:8]}"
    msg4_id = f"msg-{uuid4().hex[:8]}"
    msg5_id = f"msg-{uuid4().hex[:8]}"

    async with db_manager.get_session_async() as session:
        # Create test project
        project = Project(
            id=project_id,
            tenant_key=tenant_key,
            name="Test Project",
            description="Test project for message service",
            mission="Test mission for message service integration tests",
            status="active"
        )
        session.add(project)

        # Create test agents (status must be one of: waiting, working, blocked, complete, failed, cancelled, decommissioned)
        agent1 = AgentExecution(
            job_id=agent1_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="implementer",
            agent_name="Implementer Agent",
            mission="Implement features",
            status="working"
        )
        agent2 = AgentExecution(
            job_id=agent2_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="tester",
            agent_name="Tester Agent",
            mission="Run tests",
            status="working"
        )
        agent3 = AgentExecution(
            job_id=agent3_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="analyzer",
            agent_name="Analyzer Agent",
            mission="Analyze code",
            status="working"
        )
        session.add_all([agent1, agent2, agent3])

        # Create test messages
        messages = [
            # Direct message to agent-1
            Message(
                id=msg1_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent1_id],
                message_type="direct",
                content="Direct message to agent 1",
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "orchestrator"}
            ),
            # Broadcast message to all
            Message(
                id=msg2_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=["all"],
                message_type="broadcast",
                content="Broadcast to all agents",
                priority="high",
                status="pending",
                meta_data={"_from_agent": "orchestrator"}
            ),
            # Direct message to agent-2
            Message(
                id=msg3_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent2_id],
                message_type="direct",
                content="Direct message to agent 2",
                priority="normal",
                status="pending",
                meta_data={"_from_agent": agent1_id}
            ),
            # Acknowledged message to agent-1
            Message(
                id=msg4_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent1_id],
                message_type="direct",
                content="Acknowledged message",
                priority="normal",
                status="acknowledged",
                acknowledged_by=[agent1_id],
                acknowledged_at=datetime.now(timezone.utc),
                meta_data={"_from_agent": "orchestrator"}
            ),
            # Multiple recipients (not broadcast)
            Message(
                id=msg5_id,
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=[agent1_id, agent2_id],
                message_type="direct",
                content="Message to multiple agents",
                priority="high",
                status="pending",
                meta_data={"_from_agent": "orchestrator"}
            ),
        ]
        session.add_all(messages)

        await session.commit()

        # Store IDs for test assertions
        test_data = {
            "project": project,
            "agents": [agent1, agent2, agent3],
            "messages": messages,
            "agent1_id": agent1_id,
            "agent2_id": agent2_id,
            "agent3_id": agent3_id,
            "msg1_id": msg1_id,
            "msg2_id": msg2_id,
            "msg3_id": msg3_id,
            "msg4_id": msg4_id,
            "msg5_id": msg5_id,
        }

        yield test_data

        # Cleanup: Rollback any uncommitted changes
        await session.rollback()


@pytest.mark.asyncio
async def test_receive_messages_direct_message(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages returns direct messages to specific agent."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # Agent 1 should receive msg-1, msg-2 (broadcast), msg-5 (all pending)
    # msg-4 is acknowledged so it's NOT included
    result = await service.receive_messages(agent_id=data["agent1_id"], limit=10)

    assert result["success"] is True
    assert result["count"] == 3

    message_ids = {msg["id"] for msg in result["messages"]}
    assert message_ids == {data["msg1_id"], data["msg2_id"], data["msg5_id"]}


@pytest.mark.asyncio
async def test_receive_messages_broadcast(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages includes broadcast messages for all agents."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # All agents should receive msg-2 (broadcast)
    result1 = await service.receive_messages(agent_id=data["agent1_id"], limit=10)
    result2 = await service.receive_messages(agent_id=data["agent2_id"], limit=10)
    result3 = await service.receive_messages(agent_id=data["agent3_id"], limit=10)

    # All should have msg-2 in their messages
    msgs1 = {msg["id"] for msg in result1["messages"]}
    msgs2 = {msg["id"] for msg in result2["messages"]}
    msgs3 = {msg["id"] for msg in result3["messages"]}

    assert data["msg2_id"] in msgs1
    assert data["msg2_id"] in msgs2
    assert data["msg2_id"] in msgs3


@pytest.mark.asyncio
async def test_receive_messages_unread_only_default(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages returns only unread (pending) messages by default."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # Agent 1 should only get pending messages (not msg-4 which is acknowledged)
    result = await service.receive_messages(agent_id=data["agent1_id"], limit=10)

    message_ids = {msg["id"] for msg in result["messages"]}

    # Should NOT include msg-4 (acknowledged)
    assert data["msg4_id"] not in message_ids

    # Should include only pending messages
    for msg in result["messages"]:
        # Note: AgentMessageQueue format uses acknowledged_at timestamp field
        # Pending messages should have acknowledged_at=None
        assert msg.get("acknowledged_at") is None


@pytest.mark.asyncio
async def test_receive_messages_limit(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages respects limit parameter."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # Agent 1 has 4 messages, limit to 2
    result = await service.receive_messages(agent_id=data["agent1_id"], limit=2)

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["messages"]) == 2


@pytest.mark.asyncio
async def test_receive_messages_multiple_recipients(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages handles messages with multiple recipients."""
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # Both agent-1 and agent-2 should receive msg-5
    result1 = await service.receive_messages(agent_id=data["agent1_id"], limit=10)
    result2 = await service.receive_messages(agent_id=data["agent2_id"], limit=10)

    msgs1 = {msg["id"] for msg in result1["messages"]}
    msgs2 = {msg["id"] for msg in result2["messages"]}

    assert data["msg5_id"] in msgs1
    assert data["msg5_id"] in msgs2


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
            status="active"
        )
        project2 = Project(
            id=project2_id,
            tenant_key=tenant_key_2,
            name="Tenant 2 Project",
            description="Test project for tenant 2",
            mission="Test mission for tenant 2",
            status="active"
        )
        session.add_all([project1, project2])

        # Create agents for both tenants (valid status: working)
        agent1 = AgentExecution(
            job_id=agent1_id,
            tenant_key=tenant_key_1,
            project_id=project1.id,
            agent_type="implementer",
            agent_name="Tenant 1 Agent",
            mission="Work for tenant 1",
            status="working"
        )
        agent2 = AgentExecution(
            job_id=agent2_id,
            tenant_key=tenant_key_2,
            project_id=project2.id,
            agent_type="implementer",
            agent_name="Tenant 2 Agent",
            mission="Work for tenant 2",
            status="working"
        )
        session.add_all([agent1, agent2])

        # Create messages for both tenants
        msg1 = Message(
            id=msg1_id,
            tenant_key=tenant_key_1,
            project_id=project1.id,
            to_agents=[agent1_id],
            content="Message for tenant 1",
            status="pending"
        )
        msg2 = Message(
            id=msg2_id,
            tenant_key=tenant_key_2,
            project_id=project2.id,
            to_agents=[agent2_id],
            content="Message for tenant 2",
            status="pending"
        )
        session.add_all([msg1, msg2])

        await session.commit()

        # Cleanup after test
        try:
            # Tenant 1 should only see their messages
            result1 = await service.receive_messages(
                agent_id=agent1_id,
                tenant_key=tenant_key_1
            )

            assert result1["success"] is True
            message_ids = {msg["id"] for msg in result1["messages"]}
            assert msg1_id in message_ids
            assert msg2_id not in message_ids

            # Tenant 2 should only see their messages
            result2 = await service.receive_messages(
                agent_id=agent2_id,
                tenant_key=tenant_key_2
            )

            assert result2["success"] is True
            message_ids = {msg["id"] for msg in result2["messages"]}
            assert msg2_id in message_ids
            assert msg1_id not in message_ids
        finally:
            # Cleanup
            await session.rollback()


@pytest.mark.asyncio
async def test_receive_messages_nonexistent_agent(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages handles nonexistent agent gracefully."""
    service = MessageService(db_manager, tenant_manager)

    # Use unique ID that definitely doesn't exist
    nonexistent_id = f"nonexistent-{uuid4().hex[:8]}"
    result = await service.receive_messages(agent_id=nonexistent_id, limit=10)

    # Should fail with appropriate error
    assert result["success"] is False
    assert "not found" in result["error"].lower()


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
    result = await service.list_messages(
        project_id=data["project"].id,
        status="pending"
    )

    assert result["success"] is True
    assert result["count"] == 4  # 4 pending messages (msg-1, msg-2, msg-3, msg-5)

    # Filter for acknowledged messages
    result = await service.list_messages(
        project_id=data["project"].id,
        status="acknowledged"
    )

    assert result["success"] is True
    assert result["count"] == 1  # 1 acknowledged message (msg-4)


@pytest.mark.asyncio
async def test_receive_messages_native_queries_no_legacy(db_manager, tenant_manager, setup_test_data):
    """
    CRITICAL TEST: Verify receive_messages uses native Message queries,
    NOT AgentMessageQueue.get_messages() which has broken SQL.
    """
    service = MessageService(db_manager, tenant_manager)
    data = setup_test_data

    # This test should pass if we're using native queries
    # It should fail if we're using AgentMessageQueue.get_messages()
    result = await service.receive_messages(agent_id=data["agent1_id"], limit=10)

    assert result["success"] is True
    assert "error" not in result

    # Verify we got actual messages (not empty due to broken query)
    assert result["count"] > 0
    assert len(result["messages"]) > 0

    # Verify message structure matches expected format
    first_message = result["messages"][0]
    assert "id" in first_message
    assert "from_agent" in first_message
    assert "to_agent" in first_message
    assert "type" in first_message
    assert "content" in first_message
    assert "priority" in first_message
    assert "acknowledged" in first_message


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
            status="active"
        )
        session.add(project)

        # Create sender agent
        sender_agent = AgentExecution(
            job_id=sender_agent_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="orchestrator",
            agent_name="Orchestrator",
            mission="Coordinate agents",
            status="working"
        )

        # Create other agent
        other_agent = AgentExecution(
            job_id=other_agent_id,
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="implementer",
            agent_name="Implementer",
            mission="Implement features",
            status="working"
        )
        session.add_all([sender_agent, other_agent])

        # Commit agents
        await session.commit()

    # Sender agent sends broadcast message
    broadcast_result = await service.send_message(
        to_agents=["all"],
        content="Status update: All agents complete staging",
        project_id=project_id,
        from_agent=sender_agent.agent_type,
        message_type="broadcast"
    )

    assert broadcast_result["success"] is True

    # CRITICAL TEST: Sender agent receives messages
    # Should NOT get their own broadcast
    sender_messages = await service.receive_messages(
        agent_id=sender_agent_id,
        limit=10
    )

    assert sender_messages["success"] is True
    # Sender should NOT receive own broadcast
    assert sender_messages["count"] == 0, \
        f"Sender should not receive own broadcast, but got {sender_messages['count']} messages"

    # Other agent receives messages
    # SHOULD get the broadcast
    other_messages = await service.receive_messages(
        agent_id=other_agent_id,
        limit=10
    )

    assert other_messages["success"] is True
    # Other agent SHOULD receive the broadcast
    assert other_messages["count"] == 1, \
        f"Other agent should receive broadcast, but got {other_messages['count']} messages"

    # Verify it's the broadcast message
    if other_messages["count"] > 0:
        msg = other_messages["messages"][0]
        assert msg["content"] == "Status update: All agents complete staging"
        assert msg["type"] == "broadcast"
