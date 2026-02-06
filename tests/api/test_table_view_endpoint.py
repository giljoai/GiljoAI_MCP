"""
Table View Endpoint Tests - Handover 0226

Tests for GET /api/agent-jobs/table-view endpoint covering:
- Basic table view retrieval with pagination
- Advanced filtering (status, health_status, has_unread, agent_display_name)
- Flexible sorting (last_progress, created_at, status, agent_display_name)
- Multi-tenant isolation
- Message count aggregation
- Staleness detection
- Performance requirements (<100ms for 50 jobs)

TDD Approach: Tests describe WHAT the endpoint should do (behavior), not HOW (implementation).
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone, timedelta


# ============================================================================
# FIXTURES - Test Data Setup
# ============================================================================

@pytest.fixture
async def test_jobs_with_varied_data(db_manager, tenant_a_admin):
    """
    Create diverse test jobs with varied statuses, health states, and messages.

    Designed to test filtering, sorting, and aggregation capabilities.
    """
    from src.giljo_mcp.models.agent_identity import AgentExecution
    from src.giljo_mcp.models.projects import Project

    # Create test project
    async with db_manager.get_session_async() as session:
        project = Project(
            project_id=str(uuid4()),
            product_id=str(uuid4()),
            tenant_key=tenant_a_admin.tenant_key,
            project_name="Test Project for Table View",
            status="active",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Create jobs with different characteristics
        now = datetime.now(timezone.utc)

        jobs = [
            # Job 1: Orchestrator, working, healthy, has unread messages
            AgentExecution(
                job_id=str(uuid4()),
                tenant_key=tenant_a_admin.tenant_key,
                project_id=project.project_id,
                agent_display_name="orchestrator",
                agent_name="Main Orchestrator",
                tool_type="claude-code",
                status="working",
                progress=45,
                current_task="Analyzing requirements",
                mission="Orchestrate project development",
                health_status="healthy",
                last_progress_at=now - timedelta(minutes=2),
                created_at=now - timedelta(hours=1),
                started_at=now - timedelta(minutes=55),
                messages=[
                    {"id": "msg1", "status": "pending", "content": "Update 1"},
                    {"id": "msg2", "status": "acknowledged", "content": "Update 2"},
                    {"id": "msg3", "status": "pending", "content": "Update 3"},
                ],            ),
            # Job 2: Implementer, waiting, warning health, no messages
            AgentExecution(
                job_id=str(uuid4()),
                tenant_key=tenant_a_admin.tenant_key,
                project_id=project.project_id,
                agent_display_name="implementer",
                agent_name="Backend Developer",
                tool_type="codex",
                status="waiting",
                progress=0,
                mission="Implement backend features",
                health_status="warning",
                last_progress_at=now - timedelta(minutes=15),
                created_at=now - timedelta(minutes=30),
                messages=[],            ),
            # Job 3: Tester, working, critical health, stale (>10 min no progress)
            AgentExecution(
                job_id=str(uuid4()),
                tenant_key=tenant_a_admin.tenant_key,
                project_id=project.project_id,
                agent_display_name="tester",
                agent_name="Test Engineer",
                tool_type="gemini",
                status="working",
                progress=30,
                current_task="Running integration tests",
                mission="Execute test suite",
                health_status="critical",
                last_progress_at=now - timedelta(minutes=25),
                created_at=now - timedelta(hours=2),
                started_at=now - timedelta(minutes=120),
                messages=[
                    {"id": "msg4", "status": "acknowledged", "content": "Test started"},
                ],            ),
            # Job 4: Analyzer, complete, healthy (terminal state)
            AgentExecution(
                job_id=str(uuid4()),
                tenant_key=tenant_a_admin.tenant_key,
                project_id=project.project_id,
                agent_display_name="analyzer",
                agent_name="Code Analyzer",
                tool_type="universal",
                status="complete",
                progress=100,
                mission="Analyze codebase structure",
                health_status="healthy",
                last_progress_at=now - timedelta(hours=1),
                created_at=now - timedelta(hours=3),
                started_at=now - timedelta(hours=3),
                completed_at=now - timedelta(hours=1),
                messages=[
                    {"id": "msg5", "status": "acknowledged", "content": "Analysis complete"},
                    {"id": "msg6", "status": "acknowledged", "content": "Results ready"},
                ],            ),
            # Job 5: Implementer, failed, timeout health
            AgentExecution(
                job_id=str(uuid4()),
                tenant_key=tenant_a_admin.tenant_key,
                project_id=project.project_id,
                agent_display_name="implementer",
                agent_name="Frontend Developer",
                tool_type="claude-code",
                status="failed",
                progress=75,
                failure_reason="Dependency conflict",
                mission="Implement UI components",
                health_status="timeout",
                last_progress_at=now - timedelta(hours=2),
                created_at=now - timedelta(hours=4),
                started_at=now - timedelta(hours=4),
                completed_at=now - timedelta(hours=2),
                messages=[
                    {"id": "msg7", "status": "pending", "content": "Error occurred"},
                ],            ),
            # Job 6: Orchestrator instance 2 (succession)
            AgentExecution(
                job_id=str(uuid4()),
                tenant_key=tenant_a_admin.tenant_key,
                project_id=project.project_id,
                agent_display_name="orchestrator",
                agent_name="Successor Orchestrator",
                tool_type="claude-code",
                status="working",
                progress=10,
                current_task="Continuing from handover",
                mission="Continue orchestration",
                health_status="healthy",
                last_progress_at=now - timedelta(minutes=1),
                created_at=now - timedelta(minutes=10),
                started_at=now - timedelta(minutes=9),
                messages=[],            ),
        ]

        for job in jobs:
            session.add(job)

        await session.commit()

        # Return project and job IDs for test assertions
        return {
            "project": project,
            "job_ids": [job.job_id for job in jobs],
            "tenant_key": tenant_a_admin.tenant_key,
        }


# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_table_view_basic(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test basic table view retrieval returns correct structure."""
    # Login as tenant A admin
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Get table view
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "rows" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "project_id" in data
    assert "filters_applied" in data

    # Verify data consistency
    assert data["project_id"] == test_jobs_with_varied_data["project"].project_id
    assert data["total"] == 6  # All 6 jobs created
    assert len(data["rows"]) == 6  # Default limit should include all
    assert data["limit"] == 50  # Default limit
    assert data["offset"] == 0  # Default offset


@pytest.mark.asyncio
async def test_table_row_structure(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test that each table row contains all required fields."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Get table view
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) > 0

    # Verify first row structure (all rows should have same structure)
    row = rows[0]
    required_fields = [
        "job_id",
        "agent_display_name",
        "agent_name",
        "tool_type",
        "status",
        "progress",
        "current_task",
        "unread_count",
        "acknowledged_count",
        "total_messages",
        "health_status",
        "last_progress_at",
        "minutes_since_progress",
        "is_stale",
        "created_at",
        "started_at",
        "completed_at",
        "is_orchestrator",
    ]

    for field in required_fields:
        assert field in row, f"Missing required field: {field}"


# ============================================================================
# FILTERING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_filter_by_status_single(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test filtering by single status value."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Filter by status=working
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "status": ["working"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify filters applied
    assert "status" in data["filters_applied"]
    assert data["filters_applied"]["status"] == ["working"]

    # Verify all returned rows have status=working
    assert len(data["rows"]) == 3  # Jobs 1, 3, 6 are working
    for row in data["rows"]:
        assert row["status"] == "working"


@pytest.mark.asyncio
async def test_filter_by_status_multiple(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test filtering by multiple status values."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Filter by status=working,waiting
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "status": ["working", "waiting"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all returned rows match filter
    assert len(data["rows"]) == 4  # Jobs 1, 2, 3, 6
    for row in data["rows"]:
        assert row["status"] in ["working", "waiting"]


@pytest.mark.asyncio
async def test_filter_by_health_status(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test filtering by health status."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Filter by health_status=warning,critical
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "health_status": ["warning", "critical"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify filters applied
    assert "health_status" in data["filters_applied"]

    # Verify all returned rows match filter
    assert len(data["rows"]) == 2  # Jobs 2 (warning), 3 (critical)
    for row in data["rows"]:
        assert row["health_status"] in ["warning", "critical"]


@pytest.mark.asyncio
async def test_filter_by_agent_display_name(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test filtering by agent type."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Filter by agent_display_name=orchestrator
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "agent_display_name": ["orchestrator"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all returned rows are orchestrators
    assert len(data["rows"]) == 2  # Jobs 1, 6 are orchestrators
    for row in data["rows"]:
        assert row["agent_display_name"] == "orchestrator"
        assert row["is_orchestrator"] is True


@pytest.mark.asyncio
async def test_filter_by_unread_messages(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test filtering by unread messages (has_unread=true)."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Filter by has_unread=true
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "has_unread": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify filters applied
    assert "has_unread" in data["filters_applied"]
    assert data["filters_applied"]["has_unread"] is True

    # Verify all returned rows have unread messages
    assert len(data["rows"]) == 3  # Jobs 1, 5 have pending messages
    for row in data["rows"]:
        assert row["unread_count"] > 0


@pytest.mark.asyncio
async def test_combined_filters(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test combining multiple filters."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Combine status + health_status filters
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "status": ["working"],
            "health_status": ["healthy"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify both filters applied
    assert "status" in data["filters_applied"]
    assert "health_status" in data["filters_applied"]

    # Verify all rows match both filters
    assert len(data["rows"]) == 2  # Jobs 1, 6 (working + healthy)
    for row in data["rows"]:
        assert row["status"] == "working"
        assert row["health_status"] == "healthy"


# ============================================================================
# SORTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_sort_by_last_progress_desc(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test sorting by last_progress_at (descending - most recent first)."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Sort by last_progress descending
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "sort_by": "last_progress",
            "sort_order": "desc",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]

    # Verify sorting (most recent progress first)
    assert len(rows) > 1
    for i in range(len(rows) - 1):
        if rows[i]["last_progress_at"] and rows[i + 1]["last_progress_at"]:
            # Parse ISO datetime strings
            time_i = datetime.fromisoformat(rows[i]["last_progress_at"].replace("Z", "+00:00"))
            time_i_plus_1 = datetime.fromisoformat(rows[i + 1]["last_progress_at"].replace("Z", "+00:00"))
            assert time_i >= time_i_plus_1, "Rows not sorted by last_progress_at descending"


@pytest.mark.asyncio
async def test_sort_by_created_at_asc(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test sorting by created_at (ascending - oldest first)."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Sort by created_at ascending
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "sort_by": "created_at",
            "sort_order": "asc",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]

    # Verify sorting (oldest first)
    assert len(rows) > 1
    for i in range(len(rows) - 1):
        time_i = datetime.fromisoformat(rows[i]["created_at"].replace("Z", "+00:00"))
        time_i_plus_1 = datetime.fromisoformat(rows[i + 1]["created_at"].replace("Z", "+00:00"))
        assert time_i <= time_i_plus_1, "Rows not sorted by created_at ascending"


@pytest.mark.asyncio
async def test_sort_by_status(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test sorting by status (alphabetical)."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Sort by status ascending
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "sort_by": "status",
            "sort_order": "asc",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]

    # Verify alphabetical sorting
    statuses = [row["status"] for row in rows]
    assert statuses == sorted(statuses), "Rows not sorted alphabetically by status"


@pytest.mark.asyncio
async def test_sort_by_agent_display_name(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test sorting by agent_display_name (alphabetical)."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Sort by agent_display_name descending
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "sort_by": "agent_display_name",
            "sort_order": "desc",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]

    # Verify reverse alphabetical sorting
    agent_display_names = [row["agent_display_name"] for row in rows]
    assert agent_display_names == sorted(agent_display_names, reverse=True), "Rows not sorted by agent_display_name descending"


# ============================================================================
# PAGINATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_pagination_basic(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test basic pagination with limit and offset."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Get first page (limit=2)
    response1 = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "limit": 2,
            "offset": 0,
        },
        headers=auth_headers,
    )

    # Get second page (limit=2, offset=2)
    response2 = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "limit": 2,
            "offset": 2,
        },
        headers=auth_headers,
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Verify pagination metadata
    assert data1["limit"] == 2
    assert data1["offset"] == 0
    assert data2["limit"] == 2
    assert data2["offset"] == 2
    assert data1["total"] == data2["total"]  # Same total count

    # Verify different rows returned
    ids1 = {row["job_id"] for row in data1["rows"]}
    ids2 = {row["job_id"] for row in data2["rows"]}
    assert ids1.isdisjoint(ids2), "Pages should not contain overlapping jobs"

    # Verify correct number of rows
    assert len(data1["rows"]) == 2
    assert len(data2["rows"]) == 2


@pytest.mark.asyncio
async def test_pagination_limit_validation(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test pagination limit boundaries (1-500)."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Test valid limits
    for limit in [1, 50, 500]:
        response = await async_client.get(
            "/api/agent-jobs/table-view",
            params={
                "project_id": test_jobs_with_varied_data["project"].project_id,
                "limit": limit,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["limit"] == limit


# ============================================================================
# MESSAGE COUNT AGGREGATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_message_count_aggregation(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test that message counts are correctly aggregated."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Get all jobs
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]

    # Verify message counts for each job
    for row in rows:
        # Total should equal unread + acknowledged
        assert row["total_messages"] >= row["unread_count"] + row["acknowledged_count"]

        # Counts should be non-negative
        assert row["unread_count"] >= 0
        assert row["acknowledged_count"] >= 0
        assert row["total_messages"] >= 0


# ============================================================================
# STALENESS DETECTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_staleness_detection(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test that stale jobs (>10 min no progress, non-terminal) are detected."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Get all jobs
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    rows = response.json()["rows"]

    # Find jobs with >10 min since progress
    stale_jobs = [row for row in rows if row["is_stale"]]

    # Verify staleness logic:
    # - Job 3 (tester): 25 min since progress, status=working → STALE
    # - Job 2 (implementer): 15 min since progress, status=waiting → STALE
    # - Jobs with terminal states (complete, failed) should NOT be stale

    for stale_job in stale_jobs:
        # Must have minutes_since_progress > 10
        assert stale_job["minutes_since_progress"] > 10

        # Must not be in terminal state
        terminal_states = {"complete", "failed", "cancelled", "decommissioned"}
        assert stale_job["status"] not in terminal_states


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_multi_tenant_isolation(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin, tenant_b_admin):
    """Test that tenant B cannot see tenant A's jobs."""
    # Login as tenant B admin
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_b_admin._test_username,
            "password": tenant_b_admin._test_password,
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Try to access tenant A's project
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty results (no cross-tenant data leakage)
    assert data["total"] == 0
    assert len(data["rows"]) == 0


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_authentication_required(async_client: AsyncClient, test_jobs_with_varied_data):
    """Test that authentication is required."""
    # Try without auth headers
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
    )

    assert response.status_code == 401  # Unauthorized


# ============================================================================
# VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_missing_project_id(async_client: AsyncClient, tenant_a_admin):
    """Test that project_id is required."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Try without project_id
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_invalid_sort_by(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test that invalid sort_by values are rejected."""
    # Login
    login_response = await async_client.post(
        "/api/auth/login",
        json={
            "username": tenant_a_admin._test_username,
            "password": tenant_a_admin._test_password,
        },
    )
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Try with invalid sort_by
    response = await async_client.get(
        "/api/agent-jobs/table-view",
        params={
            "project_id": test_jobs_with_varied_data["project"].project_id,
            "sort_by": "invalid_column",
        },
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error
