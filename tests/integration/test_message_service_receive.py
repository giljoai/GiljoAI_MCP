"""
Integration tests for MessageService.receive_messages and list_messages.

Tests proper database queries without legacy AgentMessageQueue dependency.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.tasks import Message
from giljo_mcp.models.projects import Project, MCPAgentJob
from giljo_mcp.services.message_service import MessageService
from giljo_mcp.tenant import TenantManager


@pytest.fixture
async def setup_test_data(db_manager: DatabaseManager, tenant_key: str):
    """Create test project, agents, and messages."""
    async with db_manager.get_session_async() as session:
        # Create test project
        project = Project(
            id="proj-test-123",
            tenant_key=tenant_key,
            name="Test Project",
            description="Test project for message service",
            status="active"
        )
        session.add(project)

        # Create test agents
        agent1 = MCPAgentJob(
            job_id="agent-1",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="implementer",
            agent_name="Implementer Agent",
            mission="Implement features",
            status="running"
        )
        agent2 = MCPAgentJob(
            job_id="agent-2",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="tester",
            agent_name="Tester Agent",
            mission="Run tests",
            status="running"
        )
        agent3 = MCPAgentJob(
            job_id="agent-3",
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type="analyzer",
            agent_name="Analyzer Agent",
            mission="Analyze code",
            status="running"
        )
        session.add_all([agent1, agent2, agent3])

        # Create test messages
        messages = [
            # Direct message to agent-1
            Message(
                id="msg-1",
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=["agent-1"],
                message_type="direct",
                content="Direct message to agent 1",
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "orchestrator"}
            ),
            # Broadcast message to all
            Message(
                id="msg-2",
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
                id="msg-3",
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=["agent-2"],
                message_type="direct",
                content="Direct message to agent 2",
                priority="normal",
                status="pending",
                meta_data={"_from_agent": "agent-1"}
            ),
            # Acknowledged message to agent-1
            Message(
                id="msg-4",
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=["agent-1"],
                message_type="direct",
                content="Acknowledged message",
                priority="normal",
                status="acknowledged",
                acknowledged_by=["agent-1"],
                acknowledged_at=datetime.now(timezone.utc),
                meta_data={"_from_agent": "orchestrator"}
            ),
            # Multiple recipients (not broadcast)
            Message(
                id="msg-5",
                tenant_key=tenant_key,
                project_id=project.id,
                to_agents=["agent-1", "agent-2"],
                message_type="direct",
                content="Message to multiple agents",
                priority="high",
                status="pending",
                meta_data={"_from_agent": "orchestrator"}
            ),
        ]
        session.add_all(messages)

        await session.commit()

        return {
            "project": project,
            "agents": [agent1, agent2, agent3],
            "messages": messages
        }


@pytest.mark.asyncio
async def test_receive_messages_direct_message(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages returns direct messages to specific agent."""
    service = MessageService(db_manager, tenant_manager)

    # Agent 1 should receive msg-1, msg-2 (broadcast), msg-4, msg-5
    result = await service.receive_messages(agent_id="agent-1", limit=10)

    assert result["success"] is True
    assert result["count"] == 4

    message_ids = {msg["id"] for msg in result["messages"]}
    assert message_ids == {"msg-1", "msg-2", "msg-4", "msg-5"}


@pytest.mark.asyncio
async def test_receive_messages_broadcast(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages includes broadcast messages for all agents."""
    service = MessageService(db_manager, tenant_manager)

    # All agents should receive msg-2 (broadcast)
    result1 = await service.receive_messages(agent_id="agent-1", limit=10)
    result2 = await service.receive_messages(agent_id="agent-2", limit=10)
    result3 = await service.receive_messages(agent_id="agent-3", limit=10)

    # All should have msg-2 in their messages
    msgs1 = {msg["id"] for msg in result1["messages"]}
    msgs2 = {msg["id"] for msg in result2["messages"]}
    msgs3 = {msg["id"] for msg in result3["messages"]}

    assert "msg-2" in msgs1
    assert "msg-2" in msgs2
    assert "msg-2" in msgs3


@pytest.mark.asyncio
async def test_receive_messages_unread_only_default(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages returns only unread (pending) messages by default."""
    service = MessageService(db_manager, tenant_manager)

    # Agent 1 should only get pending messages (not msg-4 which is acknowledged)
    result = await service.receive_messages(agent_id="agent-1", limit=10)

    message_ids = {msg["id"] for msg in result["messages"]}

    # Should NOT include msg-4 (acknowledged)
    assert "msg-4" not in message_ids

    # Should include only pending messages
    for msg in result["messages"]:
        # Note: AgentMessageQueue format uses "acknowledged" boolean field
        # Pending messages should have acknowledged=False
        assert msg.get("acknowledged") is False


@pytest.mark.asyncio
async def test_receive_messages_limit(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages respects limit parameter."""
    service = MessageService(db_manager, tenant_manager)

    # Agent 1 has 4 messages, limit to 2
    result = await service.receive_messages(agent_id="agent-1", limit=2)

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["messages"]) == 2


@pytest.mark.asyncio
async def test_receive_messages_multiple_recipients(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages handles messages with multiple recipients."""
    service = MessageService(db_manager, tenant_manager)

    # Both agent-1 and agent-2 should receive msg-5
    result1 = await service.receive_messages(agent_id="agent-1", limit=10)
    result2 = await service.receive_messages(agent_id="agent-2", limit=10)

    msgs1 = {msg["id"] for msg in result1["messages"]}
    msgs2 = {msg["id"] for msg in result2["messages"]}

    assert "msg-5" in msgs1
    assert "msg-5" in msgs2


@pytest.mark.asyncio
async def test_receive_messages_tenant_isolation(db_manager, tenant_manager):
    """Test receive_messages enforces multi-tenant isolation."""
    service = MessageService(db_manager, tenant_manager)

    tenant_key_1 = "tenant-1"
    tenant_key_2 = "tenant-2"

    async with db_manager.get_session_async() as session:
        # Create two projects for different tenants
        project1 = Project(
            id="proj-tenant-1",
            tenant_key=tenant_key_1,
            name="Tenant 1 Project",
            status="active"
        )
        project2 = Project(
            id="proj-tenant-2",
            tenant_key=tenant_key_2,
            name="Tenant 2 Project",
            status="active"
        )
        session.add_all([project1, project2])

        # Create agents for both tenants
        agent1 = MCPAgentJob(
            job_id="tenant-1-agent",
            tenant_key=tenant_key_1,
            project_id=project1.id,
            agent_type="implementer",
            agent_name="Tenant 1 Agent",
            mission="Work for tenant 1",
            status="running"
        )
        agent2 = MCPAgentJob(
            job_id="tenant-2-agent",
            tenant_key=tenant_key_2,
            project_id=project2.id,
            agent_type="implementer",
            agent_name="Tenant 2 Agent",
            mission="Work for tenant 2",
            status="running"
        )
        session.add_all([agent1, agent2])

        # Create messages for both tenants
        msg1 = Message(
            id="msg-tenant-1",
            tenant_key=tenant_key_1,
            project_id=project1.id,
            to_agents=["tenant-1-agent"],
            content="Message for tenant 1",
            status="pending"
        )
        msg2 = Message(
            id="msg-tenant-2",
            tenant_key=tenant_key_2,
            project_id=project2.id,
            to_agents=["tenant-2-agent"],
            content="Message for tenant 2",
            status="pending"
        )
        session.add_all([msg1, msg2])

        await session.commit()

    # Tenant 1 should only see their messages
    result1 = await service.receive_messages(
        agent_id="tenant-1-agent",
        tenant_key=tenant_key_1
    )

    assert result1["success"] is True
    message_ids = {msg["id"] for msg in result1["messages"]}
    assert "msg-tenant-1" in message_ids
    assert "msg-tenant-2" not in message_ids

    # Tenant 2 should only see their messages
    result2 = await service.receive_messages(
        agent_id="tenant-2-agent",
        tenant_key=tenant_key_2
    )

    assert result2["success"] is True
    message_ids = {msg["id"] for msg in result2["messages"]}
    assert "msg-tenant-2" in message_ids
    assert "msg-tenant-1" not in message_ids


@pytest.mark.asyncio
async def test_receive_messages_nonexistent_agent(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages handles nonexistent agent gracefully."""
    service = MessageService(db_manager, tenant_manager)

    result = await service.receive_messages(agent_id="nonexistent-agent", limit=10)

    # Should fail with appropriate error
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_list_messages_by_agent(db_manager, tenant_manager, setup_test_data):
    """Test list_messages with agent_id filter."""
    service = MessageService(db_manager, tenant_manager)

    # List all messages for agent-1 (including acknowledged)
    result = await service.list_messages(agent_id="agent-1")

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

    # This test should pass if we're using native queries
    # It should fail if we're using AgentMessageQueue.get_messages()
    result = await service.receive_messages(agent_id="agent-1", limit=10)

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
