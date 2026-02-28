"""
Comprehensive integration tests for Agent Jobs REST API (Handover 0019).

Test-Driven Development (TDD) approach:
1. Write tests FIRST to define expected behavior
2. Tests will initially fail (no endpoints exist yet)
3. Implement endpoints to make tests pass
4. Refactor while keeping tests passing

Test Coverage:
- Endpoint availability (all routes respond)
- Authorization (admin vs user access)
- Multi-tenant isolation
- Request validation
- Response schemas
- Status transitions
- Error handling (404, 400, 403, 500)
- Complete workflows (create → acknowledge → complete)
"""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution


# Test Fixtures


@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    app = create_app()

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create admin user for testing."""
    from src.giljo_mcp.auth.auth_manager import AuthManager

    auth_manager = AuthManager(None)  # No db_manager needed for password hashing

    user = User(
        username="admin_test",
        email="admin@test.com",
        password_hash=auth_manager.hash_password("test_password"),
        role="admin",
        tenant_key="test_tenant",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create regular user for testing."""
    from src.giljo_mcp.auth.auth_manager import AuthManager

    auth_manager = AuthManager(None)

    user = User(
        username="user_test",
        email="user@test.com",
        password_hash=auth_manager.hash_password("test_password"),
        role="developer",
        tenant_key="test_tenant",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def other_tenant_user(db_session: AsyncSession) -> User:
    """Create user from different tenant for isolation testing."""
    from src.giljo_mcp.auth.auth_manager import AuthManager

    auth_manager = AuthManager(None)

    user = User(
        username="other_admin",
        email="other@test.com",
        password_hash=auth_manager.hash_password("test_password"),
        role="admin",
        tenant_key="other_tenant",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


def override_current_user(user: User):
    """Override dependency to inject test user."""

    async def _get_current_user():
        return user

    return _get_current_user


@pytest_asyncio.fixture
async def authenticated_client(
    api_client: AsyncClient, admin_user: User
) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """Create authenticated client with admin user."""
    # Override authentication dependency
    from api.app import app

    app.dependency_overrides[get_current_active_user] = override_current_user(admin_user)

    yield api_client, admin_user

    # Cleanup
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_job(db_session: AsyncSession, admin_user: User) -> AgentExecution:
    """Create test job for testing."""
    job = AgentExecution(
        tenant_key=admin_user.tenant_key,
        agent_display_name="implementer",
        mission="Test implementation task",
        status="waiting",
        spawned_by=None,
        context_chunks=["chunk_1", "chunk_2"],
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    return job


# Test: Job CRUD Operations


@pytest.mark.asyncio
async def test_create_job_success(authenticated_client: tuple[AsyncClient, User]):
    """Test successful job creation with valid data."""
    client, user = authenticated_client

    response = await client.post(
        "/api/agent-jobs",
        json={
            "agent_display_name": "implementer",
            "mission": "Implement user authentication",
            "context_chunks": ["chunk_1", "chunk_2"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["message"] == "Job created successfully"


@pytest.mark.asyncio
async def test_create_job_missing_required_fields(authenticated_client: tuple[AsyncClient, User]):
    """Test job creation fails with missing required fields."""
    client, user = authenticated_client

    # Missing agent_display_name
    response = await client.post("/api/agent-jobs", json={"mission": "Test mission"})

    assert response.status_code == 422
    error_detail = response.json()["detail"]
    assert any("agent_display_name" in str(err.get("loc", [])) for err in error_detail)


@pytest.mark.asyncio
async def test_create_job_admin_only(api_client: AsyncClient, regular_user: User):
    """Test only admins can create jobs."""
    # Override with regular user
    from api.app import app

    app.dependency_overrides[get_current_active_user] = override_current_user(regular_user)

    response = await api_client.post(
        "/api/agent-jobs", json={"agent_display_name": "implementer", "mission": "Test mission"}
    )

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_jobs_success(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test listing jobs with filters."""
    client, user = authenticated_client

    # List all jobs
    response = await client.get("/api/agent-jobs")

    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert data["total"] >= 1

    # Verify job in list
    jobs = data["jobs"]
    job_ids = [job["job_id"] for job in jobs]
    assert test_job.job_id in job_ids


@pytest.mark.asyncio
async def test_list_jobs_filter_by_status(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test filtering jobs by status."""
    client, user = authenticated_client

    # Filter by pending status
    response = await client.get("/api/agent-jobs?status=pending")

    assert response.status_code == 200
    data = response.json()

    # All jobs should have pending status
    for job in data["jobs"]:
        assert job["status"] == "pending"


@pytest.mark.asyncio
async def test_list_jobs_filter_by_agent_display_name(
    authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution
):
    """Test filtering jobs by agent type."""
    client, user = authenticated_client

    response = await client.get(f"/api/agent-jobs?agent_display_name={test_job.agent_display_name}")

    assert response.status_code == 200
    data = response.json()

    for job in data["jobs"]:
        assert job["agent_display_name"] == test_job.agent_display_name


@pytest.mark.asyncio
async def test_get_job_success(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test getting job details."""
    client, user = authenticated_client

    response = await client.get(f"/api/agent-jobs/{test_job.job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == test_job.job_id
    assert data["agent_display_name"] == test_job.agent_display_name
    assert data["mission"] == test_job.mission
    assert data["status"] == test_job.status


@pytest.mark.asyncio
async def test_get_job_not_found(authenticated_client: tuple[AsyncClient, User]):
    """Test getting non-existent job returns 404."""
    client, user = authenticated_client

    response = await client.get("/api/agent-jobs/nonexistent_job_id")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_job_success(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test updating job status."""
    client, user = authenticated_client

    response = await client.patch(f"/api/agent-jobs/{test_job.job_id}", json={"status": "active"})

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == test_job.job_id
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_delete_job_admin_only(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test only admins can delete jobs."""
    client, user = authenticated_client

    response = await client.delete(f"/api/agent-jobs/{test_job.job_id}")

    assert response.status_code == 204


# Test: Multi-Tenant Isolation


@pytest.mark.asyncio
async def test_multi_tenant_isolation_list_jobs(
    api_client: AsyncClient, other_tenant_user: User, test_job: AgentExecution, db_session: AsyncSession
):
    """Test jobs are isolated by tenant_key in list endpoint."""
    # Create job for other tenant
    other_job = AgentExecution(
        tenant_key=other_tenant_user.tenant_key,
        agent_display_name="tester",
        mission="Other tenant job",
        status="waiting",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(other_job)
    await db_session.commit()

    # Override with other tenant user
    from api.app import app

    app.dependency_overrides[get_current_active_user] = override_current_user(other_tenant_user)

    response = await api_client.get("/api/agent-jobs")

    assert response.status_code == 200
    data = response.json()

    # Should only see other_job, not test_job
    job_ids = [job["job_id"] for job in data["jobs"]]
    assert other_job.job_id in job_ids
    assert test_job.job_id not in job_ids

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multi_tenant_isolation_get_job(
    api_client: AsyncClient, other_tenant_user: User, test_job: AgentExecution
):
    """Test cannot access job from different tenant."""
    # Override with other tenant user
    from api.app import app

    app.dependency_overrides[get_current_active_user] = override_current_user(other_tenant_user)

    response = await api_client.get(f"/api/agent-jobs/{test_job.job_id}")

    # Should return 404 (not 403) to avoid leaking job existence
    assert response.status_code == 404

    app.dependency_overrides.clear()


# Test: Job Status Management


@pytest.mark.asyncio
async def test_complete_job_success(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test completing a job (active -> completed)."""
    client, user = authenticated_client

    # First acknowledge job
    await client.post(f"/api/agent-jobs/{test_job.job_id}/acknowledge")

    # Then complete it
    response = await client.post(
        f"/api/agent-jobs/{test_job.job_id}/complete", json={"result": {"files_modified": 3, "tests_passed": True}}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == test_job.job_id
    assert data["status"] == "completed"
    assert "completed_at" in data
    assert "Job completed successfully" in data["message"]


@pytest.mark.asyncio
async def test_complete_job_invalid_status_transition(
    authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution
):
    """Test completing job from invalid status fails."""
    client, user = authenticated_client

    # Try to complete job in pending status (should be active first)
    response = await client.post(f"/api/agent-jobs/{test_job.job_id}/complete", json={"result": {}})

    assert response.status_code == 400
    assert "Invalid status transition" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fail_job_success(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test failing a job."""
    client, user = authenticated_client

    response = await client.post(
        f"/api/agent-jobs/{test_job.job_id}/fail",
        json={"error": {"type": "DatabaseError", "message": "Connection timeout"}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == test_job.job_id
    assert data["status"] == "blocked"
    assert "completed_at" in data
    assert "Job failed" in data["message"]


# Test: Agent Messaging


@pytest.mark.asyncio
async def test_send_message_to_job(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test sending message to a job."""
    client, user = authenticated_client

    response = await client.post(
        f"/api/agent-jobs/{test_job.job_id}/messages",
        json={
            "role": "agent",
            "type": "status",
            "content": {"progress": 50, "current_task": "Implementing authentication"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "message_id" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_get_job_messages(
    authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution, db_session: AsyncSession
):
    """Test getting messages for a job."""
    client, user = authenticated_client

    # Add message to job
    test_job.messages = [
        {"role": "system", "type": "status", "content": {"message": "Job started"}, "timestamp": "2025-10-19T10:00:00Z"}
    ]
    await db_session.commit()

    response = await client.get(f"/api/agent-jobs/{test_job.job_id}/messages")

    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert len(data["messages"]) >= 1


@pytest.mark.asyncio
async def test_acknowledge_message(
    authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution, db_session: AsyncSession
):
    """Test acknowledging a message."""
    client, user = authenticated_client

    # Add message to job
    test_job.messages = [
        {
            "role": "agent",
            "type": "request",
            "content": {"action": "approve"},
            "timestamp": "2025-10-19T10:00:00Z",
            "acknowledged": False,
        }
    ]
    await db_session.commit()

    response = await client.post(f"/api/agent-jobs/{test_job.job_id}/messages/0/acknowledge")

    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] is True


# Test: Job Coordination


@pytest.mark.asyncio
async def test_spawn_children_jobs(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test spawning child jobs."""
    client, user = authenticated_client

    response = await client.post(
        f"/api/agent-jobs/{test_job.job_id}/spawn-children",
        json={
            "children": [
                {"agent_display_name": "implementer", "mission": "Implement frontend", "context_chunks": ["chunk_1"]},
                {"agent_display_name": "tester", "mission": "Write tests", "context_chunks": ["chunk_2"]},
            ]
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["parent_job_id"] == test_job.job_id
    assert len(data["child_job_ids"]) == 2
    assert "spawned successfully" in data["message"]


@pytest.mark.asyncio
async def test_get_job_hierarchy(
    authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution, db_session: AsyncSession
):
    """Test getting job hierarchy (parent + children)."""
    client, user = authenticated_client

    # Create child jobs
    child1 = AgentExecution(
        tenant_key=test_job.tenant_key,
        agent_display_name="implementer",
        mission="Child job 1",
        status="waiting",
        spawned_by=test_job.job_id,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    child2 = AgentExecution(
        tenant_key=test_job.tenant_key,
        agent_display_name="tester",
        mission="Child job 2",
        status="waiting",
        spawned_by=test_job.job_id,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )

    db_session.add_all([child1, child2])
    await db_session.commit()

    response = await client.get(f"/api/agent-jobs/{test_job.job_id}/hierarchy")

    assert response.status_code == 200
    data = response.json()
    assert data["parent"]["job_id"] == test_job.job_id
    assert data["total_children"] == 2
    assert len(data["children"]) == 2


@pytest.mark.asyncio
async def test_get_hierarchy_no_children(authenticated_client: tuple[AsyncClient, User], test_job: AgentExecution):
    """Test hierarchy endpoint with job that has no children."""
    client, user = authenticated_client

    response = await client.get(f"/api/agent-jobs/{test_job.job_id}/hierarchy")

    assert response.status_code == 200
    data = response.json()
    assert data["parent"]["job_id"] == test_job.job_id
    assert data["total_children"] == 0
    assert data["children"] == []


# Test: Error Handling


@pytest.mark.asyncio
async def test_job_not_found_returns_404(authenticated_client: tuple[AsyncClient, User]):
    """Test all endpoints return 404 for non-existent jobs."""
    client, user = authenticated_client

    endpoints = [
        ("/api/agent-jobs/nonexistent", "get"),
        ("/api/agent-jobs/nonexistent", "patch"),
        ("/api/agent-jobs/nonexistent", "delete"),
        ("/api/agent-jobs/nonexistent/acknowledge", "post"),
        ("/api/agent-jobs/nonexistent/complete", "post"),
        ("/api/agent-jobs/nonexistent/fail", "post"),
        ("/api/agent-jobs/nonexistent/messages", "get"),
        ("/api/agent-jobs/nonexistent/messages", "post"),
        ("/api/agent-jobs/nonexistent/hierarchy", "get"),
    ]

    for endpoint, method in endpoints:
        if method == "get":
            response = await client.get(endpoint)
        elif method == "post":
            response = await client.post(endpoint, json={})
        elif method == "patch":
            response = await client.patch(endpoint, json={})
        elif method == "delete":
            response = await client.delete(endpoint)

        assert response.status_code == 404, f"Endpoint {method.upper()} {endpoint} should return 404"


@pytest.mark.asyncio
async def test_invalid_status_transition_returns_400(
    authenticated_client: tuple[AsyncClient, User], db_session: AsyncSession, admin_user: User
):
    """Test invalid status transitions return 400."""
    client, user = authenticated_client

    # Create completed job
    completed_job = AgentExecution(
        tenant_key=admin_user.tenant_key,
        agent_display_name="implementer",
        mission="Completed job",
        status="completed",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(completed_job)
    await db_session.commit()
    await db_session.refresh(completed_job)

    # Try to acknowledge completed job (invalid transition)
    response = await client.post(f"/api/agent-jobs/{completed_job.job_id}/acknowledge")

    assert response.status_code == 400
    assert "Invalid status transition" in response.json()["detail"]


# Test: Complete Workflows


@pytest.mark.asyncio
async def test_complete_job_workflow(authenticated_client: tuple[AsyncClient, User], db_session: AsyncSession):
    """Test complete job workflow: create → acknowledge → update → complete."""
    client, user = authenticated_client

    # Step 1: Create job
    create_response = await client.post(
        "/api/agent-jobs",
        json={"agent_display_name": "implementer", "mission": "Implement feature X", "context_chunks": ["chunk_1"]},
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["job_id"]

    # Step 2: Acknowledge job
    ack_response = await client.post(f"/api/agent-jobs/{job_id}/acknowledge")
    assert ack_response.status_code == 200
    assert ack_response.json()["status"] == "active"

    # Step 3: Send progress message
    msg_response = await client.post(
        f"/api/agent-jobs/{job_id}/messages", json={"role": "agent", "type": "status", "content": {"progress": 75}}
    )
    assert msg_response.status_code == 201

    # Step 4: Complete job
    complete_response = await client.post(f"/api/agent-jobs/{job_id}/complete", json={"result": {"success": True}})
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"

    # Step 5: Verify final state
    get_response = await client.get(f"/api/agent-jobs/{job_id}")
    assert get_response.status_code == 200
    final_job = get_response.json()
    assert final_job["status"] == "completed"
    assert final_job["acknowledged"] is True
    assert final_job["started_at"] is not None
    assert final_job["completed_at"] is not None


@pytest.mark.asyncio
async def test_job_spawn_hierarchy_workflow(authenticated_client: tuple[AsyncClient, User]):
    """Test job spawning and hierarchy workflow."""
    client, user = authenticated_client

    # Step 1: Create parent job
    parent_response = await client.post(
        "/api/agent-jobs", json={"agent_display_name": "orchestrator", "mission": "Coordinate implementation"}
    )
    assert parent_response.status_code == 201
    parent_job_id = parent_response.json()["job_id"]

    # Step 2: Spawn child jobs
    spawn_response = await client.post(
        f"/api/agent-jobs/{parent_job_id}/spawn-children",
        json={
            "children": [
                {"agent_display_name": "implementer", "mission": "Backend implementation"},
                {"agent_display_name": "implementer", "mission": "Frontend implementation"},
                {"agent_display_name": "tester", "mission": "Integration tests"},
            ]
        },
    )
    assert spawn_response.status_code == 201
    child_job_ids = spawn_response.json()["child_job_ids"]
    assert len(child_job_ids) == 3

    # Step 3: Get hierarchy
    hierarchy_response = await client.get(f"/api/agent-jobs/{parent_job_id}/hierarchy")
    assert hierarchy_response.status_code == 200
    hierarchy = hierarchy_response.json()
    assert hierarchy["total_children"] == 3
    assert len(hierarchy["children"]) == 3

    # Step 4: Complete all child jobs
    for child_id in child_job_ids:
        # Acknowledge
        await client.post(f"/api/agent-jobs/{child_id}/acknowledge")
        # Complete
        await client.post(f"/api/agent-jobs/{child_id}/complete", json={"result": {"success": True}})

    # Step 5: Verify all children completed
    for child_id in child_job_ids:
        child_response = await client.get(f"/api/agent-jobs/{child_id}")
        assert child_response.status_code == 200
        assert child_response.json()["status"] == "completed"
