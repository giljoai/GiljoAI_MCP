"""
Agent Jobs Messages API Integration Tests - Handover 0387g

Tests the /api/agent-jobs/{job_id}/messages endpoint for MessageAuditModal.

Test Coverage:
- Happy path: Retrieve messages for valid job
- Multi-tenant isolation: No cross-tenant message leakage
- Authentication enforcement: 401 Unauthorized
- Not found scenarios: 404 for invalid job_id
- Message direction: Correctly identifies inbound/outbound
- Limit parameter: Respects query parameter limits
- Empty results: Returns empty array when no messages exist

Technical Validation:
- PostgreSQL array containment for to_agents filtering
- Tenant_key filtering on both AgentExecution and Message
- Message truncation (500 chars) for preview
- Descending timestamp ordering (newest first)
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone


# ============================================================================
# FIXTURES - Test Users
# ============================================================================

@pytest.fixture
async def tenant_a_admin(db_manager):
    """Create Tenant A admin user."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_a_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "password_a"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_admin(db_manager):
    """Create Tenant B admin user for cross-tenant testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_b_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "password_b"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def auth_headers_a(api_client: AsyncClient, tenant_a_admin):
    """Get authentication headers for Tenant A."""
    response = await api_client.post(
        "/api/auth/token",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def auth_headers_b(api_client: AsyncClient, tenant_b_admin):
    """Get authentication headers for Tenant B."""
    response = await api_client.post(
        "/api/auth/token",
        json={
            "username": tenant_b_admin._test_username,
            "password": tenant_b_admin._test_password,
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# FIXTURES - Test Data
# ============================================================================

@pytest.fixture
async def agent_job_with_messages(db_manager, tenant_a_admin):
    """Create an agent job with test messages."""
    from src.giljo_mcp.models import AgentJob, Message
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = f"job_{uuid4()}"
    agent_id = str(uuid4())
    other_agent_id = str(uuid4())
    project_id = str(uuid4())

    async with db_manager.get_session_async() as session:
        # Create agent job
        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Test Agent",
            agent_name="test-agent",
            mission="Test mission",
            status="active",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(agent_job)

        # Create agent execution
        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Test Agent",
            agent_name="test-agent",
            mission="Test mission",
            status="active",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(execution)

        # Create outbound message (agent is sender)
        msg_outbound = Message(
            from_agent=agent_id,
            to_agents=[other_agent_id],
            content="Outbound message from test agent",
            status="sent",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(msg_outbound)

        # Create inbound message (agent is recipient)
        msg_inbound = Message(
            from_agent=other_agent_id,
            to_agents=[agent_id],
            content="Inbound message to test agent",
            status="delivered",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(msg_inbound)

        # Create broadcast message (agent is one of many recipients)
        msg_broadcast = Message(
            from_agent=other_agent_id,
            to_agents=[agent_id, str(uuid4()), str(uuid4())],
            content="Broadcast message to multiple agents",
            status="delivered",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(msg_broadcast)

        await session.commit()

    return {
        "job_id": job_id,
        "agent_id": agent_id,
        "tenant_key": tenant_a_admin.tenant_key,
        "message_count": 3,
    }


@pytest.fixture
async def agent_job_cross_tenant(db_manager, tenant_b_admin):
    """Create an agent job in Tenant B for cross-tenant testing."""
    from src.giljo_mcp.models import AgentJob, Message
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = f"job_{uuid4()}"
    agent_id = str(uuid4())
    project_id = str(uuid4())

    async with db_manager.get_session_async() as session:
        # Create agent job for Tenant B
        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Tenant B Agent",
            agent_name="tenant-b-agent",
            mission="Tenant B mission",
            status="active",
            tenant_key=tenant_b_admin.tenant_key,
        )
        session.add(agent_job)

        # Create agent execution for Tenant B
        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Tenant B Agent",
            agent_name="tenant-b-agent",
            mission="Tenant B mission",
            status="active",
            tenant_key=tenant_b_admin.tenant_key,
        )
        session.add(execution)

        # Create message for Tenant B
        msg = Message(
            from_agent=agent_id,
            to_agents=[str(uuid4())],
            content="Tenant B message - should not be visible to Tenant A",
            status="sent",
            tenant_key=tenant_b_admin.tenant_key,
        )
        session.add(msg)

        await session.commit()

    return {
        "job_id": job_id,
        "agent_id": agent_id,
        "tenant_key": tenant_b_admin.tenant_key,
    }


# ============================================================================
# TESTS - Happy Path
# ============================================================================

@pytest.mark.asyncio
async def test_get_job_messages_success(
    api_client: AsyncClient,
    auth_headers_a,
    agent_job_with_messages,
):
    """Test successful retrieval of messages for a job."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_with_messages['job_id']}/messages",
        headers=auth_headers_a,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "job_id" in data
    assert "agent_id" in data
    assert "messages" in data

    # Verify job_id and agent_id
    assert data["job_id"] == agent_job_with_messages["job_id"]
    assert data["agent_id"] == agent_job_with_messages["agent_id"]

    # Verify message count (should have 3 messages)
    assert len(data["messages"]) == agent_job_with_messages["message_count"]

    # Verify message structure
    for msg in data["messages"]:
        assert "id" in msg
        assert "from_agent" in msg
        assert "to_agents" in msg
        assert "content" in msg
        assert "status" in msg
        assert "created_at" in msg
        assert "direction" in msg
        assert msg["direction"] in ["inbound", "outbound"]


@pytest.mark.asyncio
async def test_get_job_messages_direction_identification(
    api_client: AsyncClient,
    auth_headers_a,
    agent_job_with_messages,
):
    """Test that message direction is correctly identified."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_with_messages['job_id']}/messages",
        headers=auth_headers_a,
    )

    assert response.status_code == 200
    data = response.json()
    messages = data["messages"]

    # Count inbound and outbound messages
    outbound_count = sum(1 for m in messages if m["direction"] == "outbound")
    inbound_count = sum(1 for m in messages if m["direction"] == "inbound")

    # Should have 1 outbound (agent is sender) and 2 inbound (agent is recipient)
    assert outbound_count == 1
    assert inbound_count == 2


@pytest.mark.asyncio
async def test_get_job_messages_with_limit(
    api_client: AsyncClient,
    auth_headers_a,
    agent_job_with_messages,
):
    """Test that limit parameter is respected."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_with_messages['job_id']}/messages?limit=2",
        headers=auth_headers_a,
    )

    assert response.status_code == 200
    data = response.json()

    # Should only return 2 messages
    assert len(data["messages"]) == 2


@pytest.mark.asyncio
async def test_get_job_messages_empty_result(
    api_client: AsyncClient,
    auth_headers_a,
    db_manager,
    tenant_a_admin,
):
    """Test retrieving messages for a job with no messages."""
    from src.giljo_mcp.models import AgentJob
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = f"job_{uuid4()}"
    agent_id = str(uuid4())
    project_id = str(uuid4())

    # Create job without messages
    async with db_manager.get_session_async() as session:
        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Empty Agent",
            agent_name="empty-agent",
            mission="Empty mission",
            status="active",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(agent_job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Empty Agent",
            agent_name="empty-agent",
            mission="Empty mission",
            status="active",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(execution)
        await session.commit()

    response = await api_client.get(
        f"/api/agent-jobs/{job_id}/messages",
        headers=auth_headers_a,
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty messages array
    assert len(data["messages"]) == 0
    assert data["job_id"] == job_id


# ============================================================================
# TESTS - Multi-Tenant Isolation
# ============================================================================

@pytest.mark.asyncio
async def test_get_job_messages_cross_tenant_isolation(
    api_client: AsyncClient,
    auth_headers_a,
    agent_job_cross_tenant,
):
    """Test that Tenant A cannot access Tenant B's job messages."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_cross_tenant['job_id']}/messages",
        headers=auth_headers_a,
    )

    # Should return 404 (job not found for this tenant)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# TESTS - Authentication & Authorization
# ============================================================================

@pytest.mark.asyncio
async def test_get_job_messages_unauthenticated(
    api_client: AsyncClient,
    agent_job_with_messages,
):
    """Test that unauthenticated requests are rejected."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_with_messages['job_id']}/messages",
    )

    # Should return 401 Unauthorized
    assert response.status_code == 401


# ============================================================================
# TESTS - Error Conditions
# ============================================================================

@pytest.mark.asyncio
async def test_get_job_messages_not_found(
    api_client: AsyncClient,
    auth_headers_a,
):
    """Test retrieving messages for non-existent job."""
    fake_job_id = f"job_{uuid4()}"

    response = await api_client.get(
        f"/api/agent-jobs/{fake_job_id}/messages",
        headers=auth_headers_a,
    )

    # Should return 404
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_job_messages_invalid_limit(
    api_client: AsyncClient,
    auth_headers_a,
    agent_job_with_messages,
):
    """Test that invalid limit parameter is rejected."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_with_messages['job_id']}/messages?limit=0",
        headers=auth_headers_a,
    )

    # Should return 422 Validation Error (limit must be >= 1)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_job_messages_limit_exceeds_max(
    api_client: AsyncClient,
    auth_headers_a,
    agent_job_with_messages,
):
    """Test that limit parameter exceeding max is rejected."""
    response = await api_client.get(
        f"/api/agent-jobs/{agent_job_with_messages['job_id']}/messages?limit=300",
        headers=auth_headers_a,
    )

    # Should return 422 Validation Error (limit max is 200)
    assert response.status_code == 422


# ============================================================================
# TESTS - Message Content Truncation
# ============================================================================

@pytest.mark.asyncio
async def test_get_job_messages_truncation(
    api_client: AsyncClient,
    auth_headers_a,
    db_manager,
    tenant_a_admin,
):
    """Test that message content is truncated to 500 characters."""
    from src.giljo_mcp.models import AgentJob, Message
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = f"job_{uuid4()}"
    agent_id = str(uuid4())
    project_id = str(uuid4())

    # Create job with long message
    long_content = "A" * 1000  # 1000 character message

    async with db_manager.get_session_async() as session:
        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Test Agent",
            agent_name="test-agent",
            mission="Test mission",
            status="active",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(agent_job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            project_id=project_id,
            agent_display_name="Test Agent",
            agent_name="test-agent",
            mission="Test mission",
            status="active",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(execution)

        msg = Message(
            from_agent=agent_id,
            to_agents=[str(uuid4())],
            content=long_content,
            status="sent",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(msg)
        await session.commit()

    response = await api_client.get(
        f"/api/agent-jobs/{job_id}/messages",
        headers=auth_headers_a,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify message content is truncated to 500 chars
    assert len(data["messages"]) == 1
    assert len(data["messages"][0]["content"]) == 500
