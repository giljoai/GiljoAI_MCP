"""
Integration tests for Broadcast Messaging API (Handover 0073).

Tests:
- POST /api/agent-jobs/broadcast - Broadcast message to all agents
- Multi-tenant isolation
- Message validation
- WebSocket event broadcasting
- Error handling
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution


@pytest.mark.asyncio
async def test_broadcast_message_success(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test successful message broadcast to multiple agents."""
    # Create test project
    project = Project(
        id="broadcast-proj-001",
        tenant_key=test_user.tenant_key,
        name="Broadcast Project",
        mission="Test broadcast",
        description="Testing broadcast messaging",
        status="active",
    )
    db_session.add(project)

    # Create multiple agents
    agent_count = 5
    for i in range(agent_count):
        agent = AgentExecution(
            job_id=f"agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name=f"developer-{i}",
            mission=f"Develop feature {i}",
            status="working",
        )
        db_session.add(agent)

    await db_session.commit()

    # Broadcast message
    broadcast_data = {
        "project_id": project.id,
        "content": "All agents: Please commit your changes and prepare status report",
    }

    response = await client.post("/api/agent-jobs/broadcast", json=broadcast_data, headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert "broadcast_id" in data
    assert "message_ids" in data
    assert "agent_count" in data
    assert "timestamp" in data

    # Validate counts
    assert data["agent_count"] == agent_count
    assert len(data["message_ids"]) == agent_count

    # Verify broadcast_id is UUID format
    assert len(data["broadcast_id"]) == 36  # UUID format

    # Verify messages were added to agents
    for i in range(agent_count):
        agent_result = await db_session.get(AgentExecution, i + 1)
        assert agent_result is not None
        assert len(agent_result.messages) == 1

        message = agent_result.messages[0]
        assert message["broadcast_id"] == data["broadcast_id"]
        assert message["from"] == "developer"
        assert message["content"] == broadcast_data["content"]
        assert message["status"] == "pending"
        assert message["is_broadcast"] is True


@pytest.mark.asyncio
async def test_broadcast_message_empty_content(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test broadcast with empty message content."""
    project = Project(
        id="test-proj-empty",
        tenant_key=test_user.tenant_key,
        name="Test Project",
        mission="Test",
        description="Test",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # Try broadcasting empty message
    response = await client.post(
        "/api/agent-jobs/broadcast", json={"project_id": project.id, "content": "   "}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_broadcast_message_max_length_exceeded(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test broadcast with content exceeding max length."""
    project = Project(
        id="test-proj-long",
        tenant_key=test_user.tenant_key,
        name="Test Project",
        mission="Test",
        description="Test",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # Try broadcasting message longer than 10000 chars
    long_content = "A" * 10001
    response = await client.post(
        "/api/agent-jobs/broadcast", json={"project_id": project.id, "content": long_content}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "maximum length" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_broadcast_message_project_not_found(client: AsyncClient, auth_headers: dict):
    """Test broadcast to non-existent project."""
    response = await client.post(
        "/api/agent-jobs/broadcast",
        json={"project_id": "nonexistent-project", "content": "Test message"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_broadcast_message_no_agents(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test broadcast to project with no agents."""
    # Create project without agents
    project = Project(
        id="empty-proj-001",
        tenant_key=test_user.tenant_key,
        name="Empty Project",
        mission="No agents",
        description="Project without agents",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()

    # Try broadcasting
    response = await client.post(
        "/api/agent-jobs/broadcast", json={"project_id": project.id, "content": "Test message"}, headers=auth_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "no agents" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_broadcast_message_unauthorized(client: AsyncClient):
    """Test broadcast without authentication."""
    response = await client.post("/api/agent-jobs/broadcast", json={"project_id": "test-proj", "content": "Test"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_broadcast_multi_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user_2: User,
    auth_headers: dict,
    auth_headers_user_2: dict,
):
    """Test multi-tenant isolation in broadcast messaging."""
    # Create project for user 1
    project = Project(
        id="tenant1-broadcast",
        tenant_key=test_user.tenant_key,
        name="Tenant 1 Project",
        mission="Build feature",
        description="Feature development",
        status="active",
    )
    db_session.add(project)

    # Create agents for user 1
    for i in range(3):
        agent = AgentExecution(
            job_id=f"tenant1-agent-{i}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="developer",
            mission="Develop",
            status="working",
        )
        db_session.add(agent)

    await db_session.commit()

    # User 2 tries to broadcast to user 1's project
    response = await client.post(
        "/api/agent-jobs/broadcast",
        json={"project_id": project.id, "content": "Unauthorized broadcast"},
        headers=auth_headers_user_2,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Verify no messages were added to user 1's agents
    for i in range(3):
        agent_id = i + 1
        agent = await db_session.get(AgentExecution, agent_id)
        assert len(agent.messages) == 0


@pytest.mark.asyncio
async def test_broadcast_preserves_existing_messages(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test that broadcast preserves existing messages in agent queues."""
    # Create project and agent with existing message
    project = Project(
        id="preserve-proj",
        tenant_key=test_user.tenant_key,
        name="Preserve Project",
        mission="Test",
        description="Test",
        status="active",
    )
    db_session.add(project)

    agent = AgentExecution(
        job_id="agent-with-msgs",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_display_name="developer",
        mission="Develop",
        status="working",
        messages=[
            {
                "id": "existing-msg-1",
                "from": "developer",
                "content": "Existing message",
                "timestamp": "2025-01-01T00:00:00Z",
                "status": "acknowledged",
            }
        ],
    )
    db_session.add(agent)
    await db_session.commit()

    # Broadcast new message
    response = await client.post(
        "/api/agent-jobs/broadcast",
        json={"project_id": project.id, "content": "New broadcast message"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    # Verify both messages exist
    await db_session.refresh(agent)
    assert len(agent.messages) == 2
    assert agent.messages[0]["content"] == "Existing message"
    assert agent.messages[1]["content"] == "New broadcast message"


@pytest.mark.asyncio
async def test_broadcast_multiple_broadcasts_same_project(
    client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test multiple sequential broadcasts to same project."""
    # Create project with agents
    project = Project(
        id="multi-broadcast-proj",
        tenant_key=test_user.tenant_key,
        name="Multi Broadcast",
        mission="Test",
        description="Test",
        status="active",
    )
    db_session.add(project)

    agent = AgentExecution(
        job_id="multi-agent",
        tenant_key=test_user.tenant_key,
        project_id=project.id,
        agent_display_name="developer",
        mission="Develop",
        status="working",
    )
    db_session.add(agent)
    await db_session.commit()

    # Send first broadcast
    response1 = await client.post(
        "/api/agent-jobs/broadcast", json={"project_id": project.id, "content": "First broadcast"}, headers=auth_headers
    )
    assert response1.status_code == status.HTTP_200_OK
    broadcast_id_1 = response1.json()["broadcast_id"]

    # Send second broadcast
    response2 = await client.post(
        "/api/agent-jobs/broadcast",
        json={"project_id": project.id, "content": "Second broadcast"},
        headers=auth_headers,
    )
    assert response2.status_code == status.HTTP_200_OK
    broadcast_id_2 = response2.json()["broadcast_id"]

    # Verify different broadcast IDs
    assert broadcast_id_1 != broadcast_id_2

    # Verify agent has both messages
    await db_session.refresh(agent)
    assert len(agent.messages) == 2
    assert agent.messages[0]["broadcast_id"] == broadcast_id_1
    assert agent.messages[1]["broadcast_id"] == broadcast_id_2
