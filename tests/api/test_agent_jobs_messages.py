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

from uuid import uuid4

import pytest
from httpx import AsyncClient


# ============================================================================
# FIXTURES - Test Users
# ============================================================================


@pytest.fixture
async def tenant_a_admin(db_manager):
    """Create Tenant A admin user."""
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_a_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id required)
        org = Organization(
            name=f"Tenant A Org {unique_id}",
            slug=f"tenant-a-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # 0424j: Required for User.org_id NOT NULL
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
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_b_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id required)
        org = Organization(
            name=f"Tenant B Org {unique_id}",
            slug=f"tenant-b-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # 0424j: Required for User.org_id NOT NULL
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
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def auth_headers_b(api_client: AsyncClient, tenant_b_admin):
    """Get authentication headers for Tenant B."""
    response = await api_client.post(
        "/api/auth/login",
        json={
            "username": tenant_b_admin._test_username,
            "password": tenant_b_admin._test_password,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return {"Authorization": f"Bearer {access_token}"}


# ============================================================================
# FIXTURES - Test Data
# ============================================================================


@pytest.fixture
async def agent_job_with_messages(db_manager, tenant_a_admin):
    """Create an agent job with test messages."""
    from src.giljo_mcp.models import AgentJob, Message, Product, Project
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = str(uuid4())  # Just use UUID, not "job_" prefix (DB varchar(36) limit)
    agent_id = str(uuid4())
    other_agent_id = str(uuid4())
    project_id = str(uuid4())
    product_id = str(uuid4())

    async with db_manager.get_session_async() as session:
        # Create product first (required for project FK)
        product = Product(
            id=product_id,
            name=f"Test Product {uuid4().hex[:8]}",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(product)

        # Create project (required for agent_job FK)
        project = Project(
            id=project_id,
            product_id=product_id,
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for agent job with messages",
            mission="Test mission for message testing",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(project)

        # Create agent job (work order - minimal fields)
        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            mission="Test mission",
            job_type="test-agent",  # Required field
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(agent_job)

        # Create agent execution (execution details with agent info)
        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            agent_display_name="Test Agent",
            tenant_key=tenant_a_admin.tenant_key,
            status="working",
        )
        session.add(execution)

        # Create outbound message (sent by agent)
        msg_outbound = Message(
            project_id=project_id,
            to_agents=[other_agent_id],
            content="Outbound message from test agent",
            status="pending",
            tenant_key=tenant_a_admin.tenant_key,
            meta_data={"_from_agent": agent_id},  # Track sender in metadata (underscore prefix)
        )
        session.add(msg_outbound)

        # Create inbound message (received by agent)
        msg_inbound = Message(
            project_id=project_id,
            to_agents=[agent_id],
            content="Inbound message to test agent",
            status="pending",
            tenant_key=tenant_a_admin.tenant_key,
            meta_data={"_from_agent": other_agent_id},
        )
        session.add(msg_inbound)

        # Create broadcast message (agent is one of many recipients)
        msg_broadcast = Message(
            project_id=project_id,
            to_agents=[agent_id, str(uuid4()), str(uuid4())],
            content="Broadcast message to multiple agents",
            status="pending",
            tenant_key=tenant_a_admin.tenant_key,
            meta_data={"_from_agent": other_agent_id},
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
    from src.giljo_mcp.models import AgentJob, Message, Product, Project
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = str(uuid4())  # Just use UUID, not "job_" prefix (DB varchar(36) limit)
    agent_id = str(uuid4())
    project_id = str(uuid4())
    product_id = str(uuid4())

    async with db_manager.get_session_async() as session:
        # Create product first (required for project FK)
        product = Product(
            id=product_id,
            name=f"Test Product B {uuid4().hex[:8]}",
            tenant_key=tenant_b_admin.tenant_key,
        )
        session.add(product)

        # Create project (required for agent_job FK)
        project = Project(
            id=project_id,
            product_id=product_id,
            name=f"Test Project B {uuid4().hex[:8]}",
            description="Test project for Tenant B agent job",
            mission="Test mission for Tenant B",
            tenant_key=tenant_b_admin.tenant_key,
        )
        session.add(project)

        # Create agent job for Tenant B (work order - minimal fields)
        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            mission="Tenant B mission",
            job_type="tenant-b-agent",  # Required field
            tenant_key=tenant_b_admin.tenant_key,
        )
        session.add(agent_job)

        # Create agent execution for Tenant B (execution details with agent info)
        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            agent_display_name="Tenant B Agent",
            tenant_key=tenant_b_admin.tenant_key,
            status="working",
        )
        session.add(execution)

        # Create message for Tenant B
        msg = Message(
            project_id=project_id,
            to_agents=[str(uuid4())],
            content="Tenant B message - should not be visible to Tenant A",
            status="pending",
            tenant_key=tenant_b_admin.tenant_key,
            meta_data={"_from_agent": agent_id},
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
    from src.giljo_mcp.models import AgentJob, Product, Project
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = str(uuid4())  # Just use UUID, not "job_" prefix (DB varchar(36) limit)
    agent_id = str(uuid4())
    project_id = str(uuid4())
    product_id = str(uuid4())

    # Create job without messages
    async with db_manager.get_session_async() as session:
        # Create product first (required for project FK)
        product = Product(
            id=product_id,
            name=f"Empty Test Product {uuid4().hex[:8]}",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(product)

        # Create project (required for agent_job FK)
        project = Project(
            id=project_id,
            product_id=product_id,
            name=f"Empty Test Project {uuid4().hex[:8]}",
            description="Test project for empty messages test",
            mission="Test mission for empty messages test",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(project)

        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            mission="Empty mission",
            job_type="empty-agent",  # Required field
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(agent_job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            agent_display_name="Empty Agent",
            tenant_key=tenant_a_admin.tenant_key,
            status="working",
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
    assert "not found" in response.json()["message"].lower()


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
    fake_job_id = str(uuid4())

    response = await api_client.get(
        f"/api/agent-jobs/{fake_job_id}/messages",
        headers=auth_headers_a,
    )

    # Should return 404
    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


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
    from src.giljo_mcp.models import AgentJob, Message, Product, Project
    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = str(uuid4())  # Just use UUID, not "job_" prefix (DB varchar(36) limit)
    agent_id = str(uuid4())
    project_id = str(uuid4())
    product_id = str(uuid4())

    # Create job with long message
    long_content = "A" * 1000  # 1000 character message

    async with db_manager.get_session_async() as session:
        # Create product first (required for project FK)
        product = Product(
            id=product_id,
            name=f"Truncation Test Product {uuid4().hex[:8]}",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(product)

        # Create project (required for agent_job FK)
        project = Project(
            id=project_id,
            product_id=product_id,
            name=f"Truncation Test Project {uuid4().hex[:8]}",
            description="Test project for message truncation test",
            mission="Test mission for truncation test",
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(project)

        agent_job = AgentJob(
            job_id=job_id,
            project_id=project_id,
            mission="Test mission",
            job_type="test-agent",  # Required field
            tenant_key=tenant_a_admin.tenant_key,
        )
        session.add(agent_job)

        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            agent_display_name="Test Agent",
            tenant_key=tenant_a_admin.tenant_key,
            status="working",
        )
        session.add(execution)

        msg = Message(
            project_id=project_id,
            to_agents=[str(uuid4())],
            content=long_content,
            status="pending",
            tenant_key=tenant_a_admin.tenant_key,
            meta_data={"_from_agent": agent_id},
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
