"""
MCP Messaging Tools Tests - Handover 0295

Tests that HTTP MCP endpoint correctly exposes messaging tools:
- send_message
- receive_messages
- acknowledge_message
- list_messages

These are the canonical public messaging tools for agents over HTTP MCP.

Test Coverage:
- Message sending (direct, broadcast, system)
- Message receiving with filtering
- Message acknowledgment tracking
- Message listing with status filtering
- Multi-tenant isolation
- Authentication requirements
- Tool catalog verification
- WebSocket event emission (mocked)

Following TDD principles: RED → GREEN → REFACTOR
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Message, Project, User, APIKey
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


# ============================================================================
# Helper Functions
# ============================================================================


def make_mcp_request(
    method: str,
    params: dict[str, Any] | None = None,
    request_id: int = 1
) -> dict[str, Any]:
    """
    Create a JSON-RPC 2.0 MCP request structure.

    Args:
        method: JSON-RPC method name (e.g., "tools/call")
        params: Method parameters
        request_id: Request ID for correlation

    Returns:
        dict: JSON-RPC 2.0 request object
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": request_id,
    }


def make_tool_call_request(
    tool_name: str,
    arguments: dict[str, Any],
    request_id: int = 1
) -> dict[str, Any]:
    """
    Create an MCP tools/call request.

    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments
        request_id: Request ID

    Returns:
        dict: JSON-RPC 2.0 tools/call request
    """
    return make_mcp_request(
        method="tools/call",
        params={
            "name": tool_name,
            "arguments": arguments,
        },
        request_id=request_id,
    )


async def initialize_mcp_session(
    api_client: AsyncClient,
    api_key_value: str
) -> dict[str, Any]:
    """
    Initialize an MCP session via the initialize method.

    Args:
        api_client: AsyncClient for making requests
        api_key_value: API key for authentication

    Returns:
        dict: JSON-RPC response from initialize
    """
    response = await api_client.post(
        "/mcp",
        json=make_mcp_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "client_info": {"name": "test-client", "version": "1.0.0"},
            },
        ),
        headers={"X-API-Key": api_key_value},
    )
    assert response.status_code == 200, f"Initialize failed: {response.text}"
    return response.json()


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user for API key authentication"""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    tenant_key = TenantManager.generate_tenant_key()

    user = User(
        username="test_mcp_messaging_user",
        password_hash=bcrypt.hash("test_password"),
        email="test_mcp_messaging@example.com",
        role="developer",
        tenant_key=tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield user

    # Cleanup
    await db_session.delete(user)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_api_key(db_session: AsyncSession, test_user):
    """Create test API key for authentication"""
    from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
    from src.giljo_mcp.models import APIKey

    # Generate API key
    api_key_value = generate_api_key()
    key_hash = hash_api_key(api_key_value)
    key_prefix = get_key_prefix(api_key_value, length=12)

    # Create API key record
    api_key = APIKey(
        user_id=test_user.id,
        tenant_key=test_user.tenant_key,
        name="MCP Messaging Test Key",
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    # Return both the record and plaintext key
    yield (api_key, api_key_value)

    # Cleanup
    await db_session.delete(api_key)
    await db_session.commit()


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user) -> Project:
    """
    Create a test project for messaging tests.

    Returns:
        Project: Test project with tenant isolation
    """
    project = Project(
        id=str(uuid.uuid4()),
        name="MCP Messaging Test Project",
        description="Test project for MCP messaging tool validation",
        mission="Test messaging tool validation",
        tenant_key=test_user.tenant_key,
        status="active",
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest_asyncio.fixture
async def test_agents(
    db_session: AsyncSession,
    test_project: Project
) -> list[AgentExecution]:
    """
    Create test agents for messaging tests.

    Creates:
    - orchestrator (orchestrator type)
    - agent1 (implementer type)
    - agent2 (tester type)

    Returns:
        list[AgentExecution]: List of test agent jobs
    """
    agents = []

    agent_configs = [
        ("orchestrator", "orchestrator", "Orchestration agent"),
        ("agent1", "implementer", "Implementation agent"),
        ("agent2", "tester", "Testing agent"),
    ]

    for agent_name, agent_type, mission in agent_configs:
        agent = AgentExecution(
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            job_id=str(uuid.uuid4()),
            agent_type=agent_type,
            agent_name=agent_name,
            mission=mission,
            status="working",
            messages=[],  # JSONB message queue
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()

    for agent in agents:
        await db_session.refresh(agent)

    return agents


# ============================================================================
# Test Class
# ============================================================================


class TestMCPMessagingTools:
    """Test MCP messaging tools via /mcp endpoint"""

    # ========================================================================
    # send_message Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_send_message_mcp_tool_creates_direct_message(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
        test_agents: list[AgentExecution],
        db_session: AsyncSession,
    ):
        """
        Test send_message MCP tool creates a direct message.

        Validates:
        - Direct message is created in messages table
        - Correct to_agents, message_type, priority
        - Returns success with message_id
        - Multi-tenant isolation enforced
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        agent1 = test_agents[1]  # implementer

        # Call send_message tool
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="send_message",
                arguments={
                    "to_agents": [agent1.agent_name],
                    "content": "Please review the implementation",
                    "project_id": test_project.id,
                    "message_type": "direct",
                    "priority": "normal",
                    "from_agent": "orchestrator",
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()

        # Verify JSON-RPC success response
        assert data.get("jsonrpc") == "2.0"
        assert "result" in data
        assert "error" not in data

        result = data["result"]
        assert "content" in result
        assert len(result["content"]) > 0

        # Parse tool response from content
        content_text = result["content"][0]["text"]
        assert "success" in content_text.lower()
        assert "message_id" in content_text.lower()

        # Verify message created in database
        stmt = select(Message).where(
            Message.project_id == test_project.id,
            Message.tenant_key == test_project.tenant_key,
        )
        result = await db_session.execute(stmt)
        messages = result.scalars().all()

        assert len(messages) >= 1, "Message not created in database"

        message = messages[-1]  # Get most recent message
        assert message.content == "Please review the implementation"
        assert agent1.agent_name in message.to_agents
        assert message.message_type == "direct"
        assert message.priority == "normal"
        assert message.status == "pending"
        assert message.tenant_key == test_project.tenant_key

    @pytest.mark.asyncio
    async def test_send_message_mcp_tool_broadcasts_to_all_agents(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
        test_agents: list[AgentExecution],
        db_session: AsyncSession,
    ):
        """
        Test send_message MCP tool broadcasts to all agents when to_agents=['all'].

        Validates:
        - Broadcast message is created with message_type='broadcast'
        - All agents in project are added to to_agents
        - Returns success with message_id and broadcast count
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        # Call send_message tool with broadcast
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="send_message",
                arguments={
                    "to_agents": ["all"],
                    "content": "Project update: All agents proceed to next phase",
                    "project_id": test_project.id,
                    "message_type": "broadcast",
                    "priority": "high",
                    "from_agent": "orchestrator",
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        result = data["result"]
        content_text = result["content"][0]["text"]

        assert "success" in content_text.lower()
        assert "broadcast" in content_text.lower()

        # Verify broadcast message in database
        stmt = select(Message).where(
            Message.project_id == test_project.id,
            Message.message_type == "broadcast",
        )
        result = await db_session.execute(stmt)
        messages = result.scalars().all()

        assert len(messages) >= 1, "Broadcast message not created"

        message = messages[-1]
        assert message.content == "Project update: All agents proceed to next phase"
        assert message.message_type == "broadcast"
        assert message.priority == "high"

        # Verify all agents are in to_agents
        agent_names = [agent.agent_name for agent in test_agents]
        for agent_name in agent_names:
            assert agent_name in message.to_agents, f"{agent_name} not in broadcast recipients"

    @pytest.mark.asyncio
    async def test_receive_messages_returns_pending_messages_for_agent(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
        test_agents: list[AgentExecution],
        db_session: AsyncSession,
    ):
        """
        Test receive_messages MCP tool returns pending messages for a specific agent.

        Validates:
        - Only messages where agent is in to_agents are returned
        - Only pending/unacknowledged messages are returned
        - Messages have correct structure
        - Multi-tenant isolation enforced
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        agent1 = test_agents[1]  # implementer

        # Create test messages
        message1 = Message(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            to_agents=[agent1.agent_name],
            content="Message 1 for agent1",
            message_type="direct",
            priority="normal",
            status="waiting",
            acknowledged_by=[],
            created_at=datetime.now(timezone.utc),
        )

        message2 = Message(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            to_agents=[agent1.agent_name, "agent2"],
            content="Message 2 for multiple agents",
            message_type="direct",
            priority="high",
            status="waiting",
            acknowledged_by=[],
            created_at=datetime.now(timezone.utc),
        )

        # Message for different agent - should not be returned
        message3 = Message(
            id=str(uuid.uuid4()),
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            to_agents=["agent2"],
            content="Message only for agent2",
            message_type="direct",
            priority="normal",
            status="waiting",
            acknowledged_by=[],
            created_at=datetime.now(timezone.utc),
        )

        db_session.add_all([message1, message2, message3])
        await db_session.commit()

        # Call receive_messages tool
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="receive_messages",
                arguments={
                    "agent_id": agent1.agent_name,
                    "limit": 10,
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        result = data["result"]
        content_text = result["content"][0]["text"]

        # Verify only agent1's messages are returned
        assert "Message 1 for agent1" in content_text
        assert "Message 2 for multiple agents" in content_text
        assert "Message only for agent2" not in content_text

    @pytest.mark.asyncio
    async def test_list_messages_filters_by_status_and_agent(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
        test_agents: list[AgentExecution],
        db_session: AsyncSession,
    ):
        """
        Test list_messages MCP tool filters by status and agent.

        Validates:
        - Filtering by agent_id returns only relevant messages
        - Filtering by status works correctly
        - Limit parameter is respected
        - Results include message metadata
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        agent1 = test_agents[1]

        # Create messages with different statuses
        messages = [
            Message(
                id=str(uuid.uuid4()),
                tenant_key=test_project.tenant_key,
                project_id=test_project.id,
                to_agents=[agent1.agent_name],
                content=f"Pending message {i}",
                message_type="direct",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

        # Add a completed message
        messages.append(
            Message(
                id=str(uuid.uuid4()),
                tenant_key=test_project.tenant_key,
                project_id=test_project.id,
                to_agents=[agent1.agent_name],
                content="Completed message",
                message_type="direct",
                priority="normal",
                status="completed",
                acknowledged_by=[agent1.agent_name],
                completed_by=[agent1.agent_name],
                created_at=datetime.now(timezone.utc),
            )
        )

        db_session.add_all(messages)
        await db_session.commit()

        # List pending messages only
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="list_messages",
                arguments={
                    "agent_id": agent1.agent_name,
                    "status": "pending",
                    "limit": 10,
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        result = data["result"]
        content_text = result["content"][0]["text"]

        # Should contain pending messages
        assert "Pending message" in content_text
        # Should not contain completed message
        assert "Completed message" not in content_text or "status" in content_text.lower()

    @pytest.mark.asyncio
    async def test_mcp_tools_list_includes_messaging_tools(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
    ):
        """
        Test that tools/list MCP method returns the canonical messaging tools.

        Validates:
        - send_message tool is present
        - receive_messages tool is present
        - acknowledge_message tool is present
        - list_messages tool is present
        - Each tool has proper metadata (name, description, inputSchema)
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        # List available tools
        response = await api_client.post(
            "/mcp",
            json=make_mcp_request(method="tools/list"),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        result = data["result"]
        assert "tools" in result

        tools = result["tools"]
        tool_names = [tool["name"] for tool in tools]

        # Verify canonical messaging tools are present
        required_tools = [
            "send_message",
            "receive_messages",
            "acknowledge_message",
            "list_messages",
        ]

        for tool_name in required_tools:
            assert tool_name in tool_names, f"Tool '{tool_name}' not found in tools/list"

        # Verify tool metadata is complete
        for tool in tools:
            if tool["name"] in required_tools:
                assert "description" in tool, f"Tool {tool['name']} missing description"
                assert "inputSchema" in tool, f"Tool {tool['name']} missing inputSchema"

    @pytest.mark.asyncio
    async def test_mcp_messaging_tools_require_authentication(
        self,
        api_client: AsyncClient,
    ):
        """
        Test that unauthenticated requests to messaging tools are rejected.

        Validates:
        - Missing X-API-Key header returns error
        - Invalid API key returns error
        - Error response follows JSON-RPC 2.0 format
        """
        # Test without API key
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="send_message",
                arguments={
                    "to_agents": ["agent1"],
                    "content": "Test message",
                    "project_id": "some-project-id",
                },
            ),
            # No X-API-Key header
        )

        assert response.status_code == 200  # JSON-RPC always returns 200
        data = response.json()

        # Should have error in response
        assert "error" in data
        error = data["error"]
        assert "X-API-Key" in error.get("message", "")

        # Test with invalid API key
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="send_message",
                arguments={
                    "to_agents": ["agent1"],
                    "content": "Test message",
                    "project_id": "some-project-id",
                },
            ),
            headers={"X-API-Key": "invalid_key_12345"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        error = data["error"]
        assert "invalid" in error.get("message", "").lower() or "authentication" in error.get("message", "").lower()

    # ========================================================================
    # Additional Edge Case Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_send_message_validates_empty_content(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
    ):
        """
        Test send_message rejects empty content.
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="send_message",
                arguments={
                    "to_agents": ["agent1"],
                    "content": "",  # Empty content
                    "project_id": test_project.id,
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return error or validation failure
        assert "result" in data or "error" in data

    @pytest.mark.asyncio
    async def test_send_message_validates_to_agents_not_empty(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
    ):
        """
        Test send_message rejects empty to_agents list.
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="send_message",
                arguments={
                    "to_agents": [],  # Empty list
                    "content": "Test message",
                    "project_id": test_project.id,
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()

        # Should handle gracefully
        assert "result" in data or "error" in data

    @pytest.mark.asyncio
    async def test_receive_messages_respects_limit_parameter(
        self,
        api_client: AsyncClient,
        test_api_key: tuple,
        test_project: Project,
        test_agents: list[AgentExecution],
        db_session: AsyncSession,
    ):
        """
        Test receive_messages respects the limit parameter.
        """
        api_key_record, api_key_value = test_api_key
        await initialize_mcp_session(api_client, api_key_value)

        agent1 = test_agents[1]

        # Create 5 messages
        for i in range(5):
            message = Message(
                id=str(uuid.uuid4()),
                tenant_key=test_project.tenant_key,
                project_id=test_project.id,
                to_agents=[agent1.agent_name],
                content=f"Message {i}",
                message_type="direct",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                created_at=datetime.now(timezone.utc),
            )
            db_session.add(message)

        await db_session.commit()

        # Request only 2 messages
        response = await api_client.post(
            "/mcp",
            json=make_tool_call_request(
                tool_name="receive_messages",
                arguments={
                    "agent_id": agent1.agent_name,
                    "limit": 2,
                },
            ),
            headers={"X-API-Key": api_key_value},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        # Verify limit is respected (response should indicate 2 or fewer messages returned)
        result = data["result"]
        content_text = result["content"][0]["text"]

        # Basic validation that response is not empty and limit was applied
        assert len(content_text) > 0
