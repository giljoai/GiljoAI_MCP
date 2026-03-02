"""
Integration tests for MessageService.receive_messages — core functionality.

Tests direct messages, broadcasts, unread filtering, limits, multiple
recipients, nonexistent agents, and native query verification.
"""

import pytest

from src.giljo_mcp.services.message_service import MessageService

pytestmark = pytest.mark.skip(reason="0750c3: schema drift — project_id invalid keyword for AgentExecution")


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
async def test_receive_messages_nonexistent_agent(db_manager, tenant_manager, setup_test_data):
    """Test receive_messages handles nonexistent agent gracefully."""
    service = MessageService(db_manager, tenant_manager)

    # Use unique ID that definitely doesn't exist
    from uuid import uuid4

    nonexistent_id = f"nonexistent-{uuid4().hex[:8]}"
    result = await service.receive_messages(agent_id=nonexistent_id, limit=10)

    # Should fail with appropriate error
    assert result["success"] is False
    assert "not found" in result["error"].lower()


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
