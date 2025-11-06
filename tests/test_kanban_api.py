"""
Comprehensive integration tests for Kanban Board API endpoints (Handover 0066).

Test-Driven Development (TDD) approach:
1. Write tests FIRST to define expected behavior
2. Tests will initially fail (endpoints don't exist yet)
3. Implement endpoints to make tests pass
4. Refactor while keeping tests passing

Test Coverage:
- GET /api/agent-jobs/kanban/{project_id} - Kanban board data
- GET /api/agent-jobs/{job_id}/message-thread - Message thread
- POST /api/agent-jobs/{job_id}/send-message - Send developer message
- Multi-tenant isolation
- Message count calculations (unread, acknowledged, sent)
- Error handling (404, 403)
"""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, Product, Project, User


# Test Fixtures


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for testing."""
    from passlib.hash import bcrypt

    user = User(
        username="admin_kanban",
        email="admin_kanban@test.com",
        password_hash=bcrypt.hash("test_password"),
        role="admin",
        tenant_key="kanban_tenant",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create regular user for testing."""
    from passlib.hash import bcrypt

    user = User(
        username="user_kanban",
        email="user_kanban@test.com",
        password_hash=bcrypt.hash("test_password"),
        role="user",
        tenant_key="kanban_tenant",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def other_tenant_user(db_session: AsyncSession) -> User:
    """Create user from different tenant for isolation testing."""
    from passlib.hash import bcrypt

    user = User(
        username="other_tenant_kanban",
        email="other_kanban@test.com",
        password_hash=bcrypt.hash("test_password"),
        role="admin",
        tenant_key="other_tenant",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, admin_user: User) -> Product:
    """Create test product."""
    product = Product(
        tenant_key=admin_user.tenant_key, name="Test Product", description="Test product for Kanban", is_active=True
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, admin_user: User, test_product: Product) -> Project:
    """Create test project."""
    project = Project(
        tenant_key=admin_user.tenant_key,
        product_id=test_product.id,
        name="Test Project",
        description="Test project for Kanban",
        mission="Test mission for Kanban project",
        status="active",
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest_asyncio.fixture
async def kanban_jobs(db_session: AsyncSession, admin_user: User, test_project: Project) -> dict:
    """Create sample jobs across all Kanban columns."""
    from datetime import datetime, timezone

    jobs = {"pending": [], "active": [], "completed": [], "blocked": []}

    # Pending jobs (2)
    for i in range(2):
        job = MCPAgentJob(
            tenant_key=admin_user.tenant_key,
            project_id=test_project.id,
            agent_type="implementer",
            mission=f"Pending task {i + 1}",
            status="pending",
            messages=[
                {
                    "from": "user",
                    "content": f"Initial message {i + 1}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "pending",
                }
            ],
        )
        db_session.add(job)
        await db_session.flush()
        jobs["pending"].append(job)

    # Active jobs (3)
    for i in range(3):
        job = MCPAgentJob(
            tenant_key=admin_user.tenant_key,
            project_id=test_project.id,
            agent_type="implementer",
            mission=f"Active task {i + 1}",
            status="active",
            acknowledged=True,
            started_at=datetime.now(timezone.utc),
            messages=[
                {
                    "from": "developer",
                    "content": f"Developer message {i + 1}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "pending",
                },
                {
                    "from": "agent",
                    "content": f"Agent response {i + 1}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "acknowledged",
                },
            ],
        )
        db_session.add(job)
        await db_session.flush()
        jobs["active"].append(job)

    # Completed jobs (1)
    job = MCPAgentJob(
        tenant_key=admin_user.tenant_key,
        project_id=test_project.id,
        agent_type="tester",
        mission="Completed task",
        status="completed",
        acknowledged=True,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        messages=[
            {
                "from": "developer",
                "content": "Start testing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "acknowledged",
            }
        ],
    )
    db_session.add(job)
    await db_session.flush()
    jobs["completed"].append(job)

    # Blocked jobs (1)
    job = MCPAgentJob(
        tenant_key=admin_user.tenant_key,
        project_id=test_project.id,
        agent_type="analyzer",
        mission="Blocked task",
        status="blocked",
        acknowledged=True,
        started_at=datetime.now(timezone.utc),
        messages=[
            {
                "from": "agent",
                "content": "Blocked on external dependency",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
        ],
    )
    db_session.add(job)
    await db_session.flush()
    jobs["blocked"].append(job)

    await db_session.commit()

    # Refresh all jobs
    for status_jobs in jobs.values():
        for job in status_jobs:
            await db_session.refresh(job)

    return jobs


def override_get_current_user(user: User):
    """Override dependency to return test user."""

    async def _override():
        return user

    return _override


# Test Cases: GET /api/agent-jobs/kanban/{project_id}


@pytest.mark.asyncio
async def test_get_kanban_board_success(
    api_client: AsyncClient, db_session: AsyncSession, admin_user: User, test_project: Project, kanban_jobs: dict
):
    """Test successful retrieval of Kanban board data."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/agent-jobs/kanban/{test_project.id}")

    assert response.status_code == 200

    data = response.json()
    assert "columns" in data
    assert len(data["columns"]) == 4

    # Verify column structure
    columns = {col["status"]: col for col in data["columns"]}
    assert "pending" in columns
    assert "active" in columns
    assert "completed" in columns
    assert "blocked" in columns

    # Verify job counts
    assert len(columns["pending"]["jobs"]) == 2
    assert len(columns["active"]["jobs"]) == 3
    assert len(columns["completed"]["jobs"]) == 1
    assert len(columns["blocked"]["jobs"]) == 1

    # Verify message counts in first pending job
    pending_job = columns["pending"]["jobs"][0]
    assert "message_counts" in pending_job
    assert "unread_messages" in pending_job["message_counts"]
    assert "acknowledged_messages" in pending_job["message_counts"]
    assert "sent_messages" in pending_job["message_counts"]


@pytest.mark.asyncio
async def test_get_kanban_board_message_counts(
    api_client: AsyncClient, db_session: AsyncSession, admin_user: User, test_project: Project, kanban_jobs: dict
):
    """Test message count calculations in Kanban board."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/agent-jobs/kanban/{test_project.id}")

    assert response.status_code == 200

    data = response.json()
    columns = {col["status"]: col for col in data["columns"]}

    # Check active job message counts
    active_job = columns["active"]["jobs"][0]
    counts = active_job["message_counts"]

    # Active jobs have: 1 developer message (sent), 1 agent message (acknowledged)
    assert counts["sent_messages"] >= 1  # At least 1 from developer
    assert counts["acknowledged_messages"] >= 1  # At least 1 acknowledged


@pytest.mark.asyncio
async def test_get_kanban_board_project_not_found(api_client: AsyncClient, db_session: AsyncSession, admin_user: User):
    """Test Kanban board retrieval with non-existent project."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent-jobs/kanban/nonexistent-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_kanban_board_multi_tenant_isolation(
    api_client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    other_tenant_user: User,
    test_project: Project,
    kanban_jobs: dict,
):
    """Test multi-tenant isolation for Kanban board."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(other_tenant_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/agent-jobs/kanban/{test_project.id}")

    assert response.status_code == 404  # Different tenant cannot see project


# Test Cases: GET /api/agent-jobs/{job_id}/message-thread


@pytest.mark.asyncio
async def test_get_message_thread_success(
    api_client: AsyncClient, db_session: AsyncSession, admin_user: User, kanban_jobs: dict
):
    """Test successful retrieval of message thread."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    job = kanban_jobs["active"][0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/agent-jobs/{job.job_id}/message-thread")

    assert response.status_code == 200

    data = response.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) > 0

    # Verify message structure
    message = data["messages"][0]
    assert "from" in message
    assert "content" in message
    assert "timestamp" in message
    assert "status" in message


@pytest.mark.asyncio
async def test_get_message_thread_chronological_order(
    api_client: AsyncClient, db_session: AsyncSession, admin_user: User, kanban_jobs: dict
):
    """Test message thread returns messages in chronological order."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    job = kanban_jobs["active"][0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/agent-jobs/{job.job_id}/message-thread")

    assert response.status_code == 200

    data = response.json()
    messages = data["messages"]

    # Verify chronological order
    if len(messages) > 1:
        for i in range(len(messages) - 1):
            assert messages[i]["timestamp"] <= messages[i + 1]["timestamp"]


@pytest.mark.asyncio
async def test_get_message_thread_job_not_found(api_client: AsyncClient, db_session: AsyncSession, admin_user: User):
    """Test message thread retrieval with non-existent job."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/agent-jobs/nonexistent-job-id/message-thread")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_message_thread_multi_tenant_isolation(
    api_client: AsyncClient, db_session: AsyncSession, other_tenant_user: User, kanban_jobs: dict
):
    """Test multi-tenant isolation for message thread."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(other_tenant_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    job = kanban_jobs["active"][0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/agent-jobs/{job.job_id}/message-thread")

    assert response.status_code == 404  # Different tenant cannot access


# Test Cases: POST /api/agent-jobs/{job_id}/send-message


@pytest.mark.asyncio
async def test_send_message_success(
    api_client: AsyncClient, db_session: AsyncSession, admin_user: User, kanban_jobs: dict
):
    """Test successful sending of developer message."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    job = kanban_jobs["active"][0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/agent-jobs/{job.job_id}/send-message", json={"content": "Test developer message"}
        )

    assert response.status_code == 201

    data = response.json()
    assert "message_id" in data
    assert data["content"] == "Test developer message"
    assert data["from"] == "developer"

    # Verify message was added to job
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job.job_id)
    result = await db_session.execute(stmt)
    updated_job = result.scalar_one()

    assert len(updated_job.messages) > len(job.messages)
    assert updated_job.messages[-1]["content"] == "Test developer message"
    assert updated_job.messages[-1]["from"] == "developer"


@pytest.mark.asyncio
async def test_send_message_empty_content(
    api_client: AsyncClient, db_session: AsyncSession, admin_user: User, kanban_jobs: dict
):
    """Test sending message with empty content."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    job = kanban_jobs["active"][0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/agent-jobs/{job.job_id}/send-message", json={"content": ""})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_send_message_job_not_found(api_client: AsyncClient, db_session: AsyncSession, admin_user: User):
    """Test sending message to non-existent job."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(admin_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent-jobs/nonexistent-job-id/send-message", json={"content": "Test message"}
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_multi_tenant_isolation(
    api_client: AsyncClient, db_session: AsyncSession, other_tenant_user: User, kanban_jobs: dict
):
    """Test multi-tenant isolation for sending messages."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(other_tenant_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    job = kanban_jobs["active"][0]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/agent-jobs/{job.job_id}/send-message", json={"content": "Test message"})

    assert response.status_code == 404  # Different tenant cannot access


@pytest.mark.asyncio
async def test_send_message_regular_user_access(
    api_client: AsyncClient, db_session: AsyncSession, regular_user: User, kanban_jobs: dict
):
    """Test regular users can send messages (not admin-only)."""
    app = create_app()
    app.dependency_overrides[get_current_active_user] = override_get_current_user(regular_user)
    app.dependency_overrides[get_db_session] = lambda: db_session

    # Create job for regular user's tenant
    job = MCPAgentJob(
        tenant_key=regular_user.tenant_key, agent_type="implementer", mission="Test mission", status="active"
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/agent-jobs/{job.job_id}/send-message", json={"content": "Regular user message"}
        )

    assert response.status_code == 201  # Regular users can send messages
