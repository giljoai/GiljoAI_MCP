"""
Integration tests for message API endpoints
Tests REST API endpoints for inter-agent messaging
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from httpx import AsyncClient

from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.models.projects import Project


@pytest.mark.asyncio
async def test_send_message_endpoint(async_client: AsyncClient, test_project):
    """Test POST /api/messages/"""
    response = await async_client.post(
        "/api/messages/",
        json={
            "to_agents": ["test-implementer"],
            "content": "Test message from API",
            "project_id": test_project.id,
            "message_type": "direct",
            "priority": "normal"
        },
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["content"] == "Test message from API"
    assert data["priority"] == "normal"
    assert data["status"] == "pending"
    assert "test-implementer" in data["to_agents"]


@pytest.mark.asyncio
async def test_send_message_endpoint_with_priority(async_client: AsyncClient, test_project):
    """Test sending message with high priority"""
    response = await async_client.post(
        "/api/messages/",
        json={
            "to_agents": ["analyzer-1"],
            "content": "Urgent code review needed",
            "project_id": test_project.id,
            "message_type": "direct",
            "priority": "high",
            "from_agent": "orchestrator"
        },
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "high"
    assert data["from"] == "orchestrator"


@pytest.mark.asyncio
async def test_send_message_endpoint_broadcast(async_client: AsyncClient, test_project):
    """Test broadcast message endpoint"""
    response = await async_client.post(
        "/api/messages/",
        json={
            "to_agents": [],  # Empty for broadcast
            "content": "System announcement",
            "project_id": test_project.id,
            "message_type": "broadcast",
            "priority": "high"
        },
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "broadcast"
    assert data["to_agents"] == []


@pytest.mark.asyncio
async def test_send_message_endpoint_validation_error(async_client: AsyncClient, test_project):
    """Test validation error for missing required fields"""
    response = await async_client.post(
        "/api/messages/",
        json={
            "to_agents": ["test-agent"],
            # Missing content field
            "project_id": test_project.id
        },
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_messages_endpoint(async_client: AsyncClient, test_project, db_session):
    """Test GET /api/messages/"""
    # Create test messages
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-implementer"],
        content="Test message for listing",
        message_type="direct",
        priority="normal",
        status="waiting",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    response = await async_client.get(
        "/api/messages/",
        params={"project_id": test_project.id},
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    messages = response.json()
    assert len(messages) > 0
    assert any(msg["id"] == str(message.id) for msg in messages)


@pytest.mark.asyncio
async def test_list_messages_endpoint_filter_by_status(async_client: AsyncClient, test_project, db_session):
    """Test filtering messages by status"""
    # Create messages with different statuses
    message_pending = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["agent-1"],
        content="Pending message",
        status="waiting"
    )
    message_completed = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["agent-1"],
        content="Completed message",
        status="completed"
    )
    db_session.add(message_pending)
    db_session.add(message_completed)
    await db_session.commit()

    # Filter by pending status
    response = await async_client.get(
        "/api/messages/",
        params={"project_id": test_project.id, "status": "pending"},
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    messages = response.json()
    # All returned messages should have pending status
    for msg in messages:
        assert msg["status"] == "pending"


@pytest.mark.asyncio
async def test_list_messages_endpoint_filter_by_agent(async_client: AsyncClient, test_project, db_session):
    """Test filtering messages by agent name"""
    # Create messages for different agents
    message1 = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["target-agent"],
        content="Message for target agent",
        status="waiting"
    )
    message2 = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["other-agent"],
        content="Message for other agent",
        status="waiting"
    )
    db_session.add(message1)
    db_session.add(message2)
    await db_session.commit()

    # Filter by agent name
    response = await async_client.get(
        "/api/messages/",
        params={"project_id": test_project.id, "agent_name": "target-agent"},
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    messages = response.json()
    # All returned messages should be for target-agent
    for msg in messages:
        assert "target-agent" in msg["to_agents"]


@pytest.mark.asyncio
async def test_get_message_endpoint(async_client: AsyncClient, test_project, db_session):
    """Test GET /api/messages/{id}"""
    # Create a test message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-agent"],
        content="Message to retrieve",
        message_type="direct",
        priority="normal",
        status="waiting"
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    response = await async_client.get(
        f"/api/messages/{message.id}",
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(message.id)
    assert data["content"] == "Message to retrieve"


@pytest.mark.asyncio
async def test_get_message_endpoint_not_found(async_client: AsyncClient, test_project):
    """Test 404 for non-existent message"""
    fake_id = str(uuid4())
    response = await async_client.get(
        f"/api/messages/{fake_id}",
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_complete_message_endpoint(async_client: AsyncClient, test_project, db_session):
    """Test POST /api/messages/{id}/complete"""
    # Create an acknowledged message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-implementer"],
        content="Message to complete",
        status="acknowledged",
        acknowledged_by=["test-implementer"]
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    response = await async_client.post(
        f"/api/messages/{message.id}/complete",
        json={
            "agent_name": "test-implementer",
            "result_data": {"status": "success", "output": "Task completed"}
        },
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify the message was completed
    get_response = await async_client.get(
        f"/api/messages/{message.id}",
        headers={"X-Tenant-Key": test_project.tenant_key}
    )
    message_data = get_response.json()
    assert message_data["status"] == "completed"
    assert "test-implementer" in message_data.get("completed_by", [])


@pytest.mark.asyncio
async def test_delete_message_endpoint(async_client: AsyncClient, test_project, db_session):
    """Test DELETE /api/messages/{id}"""
    # Create a test message
    message = Message(
        id=str(uuid4()),
        tenant_key=test_project.tenant_key,
        project_id=test_project.id,
        to_agents=["test-agent"],
        content="Message to delete",
        status="waiting"
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    response = await async_client.delete(
        f"/api/messages/{message.id}",
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify the message is deleted
    get_response = await async_client.get(
        f"/api/messages/{message.id}",
        headers={"X-Tenant-Key": test_project.tenant_key}
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_message_endpoint_tenant_isolation(async_client: AsyncClient, db_session):
    """Test that API endpoints respect tenant isolation"""
    # Create two tenants with projects
    from src.giljo_mcp.tenant import TenantManager
    tenant1_key = TenantManager.generate_tenant_key()
    tenant2_key = TenantManager.generate_tenant_key()

    project1 = Project(
        id=str(uuid4()),
        name="Tenant 1 Project",
        description="Test project description for tenant 1",
        mission="Mission 1",
        status="active",
        tenant_key=tenant1_key
    )
    project2 = Project(
        id=str(uuid4()),
        name="Tenant 2 Project",
        description="Test project description for tenant 2",
        mission="Mission 2",
        status="active",
        tenant_key=tenant2_key
    )
    db_session.add(project1)
    db_session.add(project2)
    await db_session.commit()

    # Create message for tenant 1
    message = Message(
        id=str(uuid4()),
        tenant_key=tenant1_key,
        project_id=project1.id,
        to_agents=["agent-1"],
        content="Tenant 1 message",
        status="waiting"
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    # Try to access tenant 1 message with tenant 2 credentials
    response = await async_client.get(
        f"/api/messages/{message.id}",
        headers={"X-Tenant-Key": tenant2_key}
    )

    # Should not be able to access (404 or 403)
    assert response.status_code in [404, 403]


@pytest.mark.asyncio
async def test_message_count_endpoint(async_client: AsyncClient, test_project, db_session):
    """Test GET /api/messages/count endpoint for message statistics"""
    # Create messages with different statuses
    statuses = ["pending", "acknowledged", "completed"]
    for status in statuses:
        for i in range(3):  # Create 3 messages per status
            message = Message(
                id=str(uuid4()),
                tenant_key=test_project.tenant_key,
                project_id=test_project.id,
                to_agents=["test-agent"],
                content=f"Message {i} with status {status}",
                status=status
            )
            db_session.add(message)
    await db_session.commit()

    response = await async_client.get(
        "/api/messages/count",
        params={"project_id": test_project.id},
        headers={"X-Tenant-Key": test_project.tenant_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 9  # At least 9 messages
    assert "by_status" in data
    assert data["by_status"]["pending"] >= 3
    assert data["by_status"]["acknowledged"] >= 3
    assert data["by_status"]["completed"] >= 3
