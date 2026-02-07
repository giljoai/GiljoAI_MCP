"""
Filter Options Endpoint Tests - Handover 0226

Tests for GET /api/agent-jobs/filter-options endpoint covering:
- Available filter options retrieval
- Distinct value aggregation
- Multi-tenant isolation
- Empty results handling
- Authentication enforcement

TDD Approach: Tests describe WHAT the endpoint should return, not HOW it computes it.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_get_filter_options_basic(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test basic filter options retrieval returns correct structure."""
    # Login
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

    # Get filter options
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "statuses" in data
    assert "agent_display_names" in data
    assert "health_statuses" in data
    assert "tool_types" in data
    assert "has_unread_jobs" in data

    # Verify data types
    assert isinstance(data["statuses"], list)
    assert isinstance(data["agent_display_names"], list)
    assert isinstance(data["health_statuses"], list)
    assert isinstance(data["tool_types"], list)
    assert isinstance(data["has_unread_jobs"], bool)


@pytest.mark.asyncio
async def test_filter_options_contains_expected_values(
    async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin
):
    """Test that filter options contain expected values from test data."""
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

    # Get filter options
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify expected statuses (from test fixture):
    # working, waiting, complete, failed
    expected_statuses = {"working", "waiting", "complete", "failed"}
    assert set(data["statuses"]) == expected_statuses

    # Verify expected agent_display_names (from test fixture):
    # orchestrator, implementer, tester, analyzer
    expected_agent_display_names = {"orchestrator", "implementer", "tester", "analyzer"}
    assert set(data["agent_display_names"]) == expected_agent_display_names

    # Verify expected health_statuses (from test fixture):
    # healthy, warning, critical, timeout
    expected_health_statuses = {"healthy", "warning", "critical", "timeout"}
    assert set(data["health_statuses"]) == expected_health_statuses

    # Verify expected tool_types (from test fixture):
    # claude-code, codex, gemini, universal
    expected_tool_types = {"claude-code", "codex", "gemini", "universal"}
    assert set(data["tool_types"]) == expected_tool_types

    # Verify has_unread_jobs (jobs 1 and 5 have pending messages)
    assert data["has_unread_jobs"] is True


# ============================================================================
# SORTING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_filter_options_are_sorted(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test that filter options are returned in sorted order."""
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

    # Get filter options
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all lists are sorted
    assert data["statuses"] == sorted(data["statuses"]), "Statuses not sorted"
    assert data["agent_display_names"] == sorted(data["agent_display_names"]), "Agent types not sorted"
    assert data["health_statuses"] == sorted(data["health_statuses"]), "Health statuses not sorted"
    assert data["tool_types"] == sorted(data["tool_types"]), "Tool types not sorted"


# ============================================================================
# DISTINCT VALUES TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_filter_options_are_distinct(async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin):
    """Test that filter options contain no duplicates."""
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

    # Get filter options
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify no duplicates (length equals unique set length)
    assert len(data["statuses"]) == len(set(data["statuses"])), "Duplicate statuses found"
    assert len(data["agent_display_names"]) == len(set(data["agent_display_names"])), (
        "Duplicate agent_display_names found"
    )
    assert len(data["health_statuses"]) == len(set(data["health_statuses"])), "Duplicate health_statuses found"
    assert len(data["tool_types"]) == len(set(data["tool_types"])), "Duplicate tool_types found"


# ============================================================================
# EMPTY RESULTS TESTS
# ============================================================================


@pytest.fixture
async def empty_project(db_manager, tenant_a_admin):
    """Create a project with no jobs."""
    from src.giljo_mcp.models.projects import Project

    async with db_manager.get_session_async() as session:
        project = Project(
            project_id=str(uuid4()),
            product_id=str(uuid4()),
            tenant_key=tenant_a_admin.tenant_key,
            project_name="Empty Project",
            status="active",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.mark.asyncio
async def test_filter_options_empty_project(async_client: AsyncClient, empty_project, tenant_a_admin):
    """Test filter options for project with no jobs."""
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

    # Get filter options for empty project
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": empty_project.project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify empty lists
    assert data["statuses"] == []
    assert data["agent_display_names"] == []
    assert data["health_statuses"] == []
    assert data["tool_types"] == []
    assert data["has_unread_jobs"] is False


# ============================================================================
# UNREAD MESSAGES DETECTION TESTS
# ============================================================================


@pytest.fixture
async def project_without_unread(db_manager, tenant_a_admin):
    """Create a project with jobs but no unread messages."""
    from src.giljo_mcp.models.agent_identity import AgentExecution
    from src.giljo_mcp.models.projects import Project

    async with db_manager.get_session_async() as session:
        project = Project(
            project_id=str(uuid4()),
            product_id=str(uuid4()),
            tenant_key=tenant_a_admin.tenant_key,
            project_name="No Unread Project",
            status="active",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Create job with only acknowledged messages
        job = AgentExecution(
            job_id=str(uuid4()),
            tenant_key=tenant_a_admin.tenant_key,
            project_id=project.project_id,
            agent_display_name="implementer",
            tool_type="claude-code",
            status="working",
            mission="Test mission",
            messages=[
                {"id": "msg1", "status": "acknowledged", "content": "Read message"},
                {"id": "msg2", "status": "acknowledged", "content": "Another read message"},
            ],
        )
        session.add(job)
        await session.commit()

        return project


@pytest.mark.asyncio
async def test_has_unread_false_when_no_pending(async_client: AsyncClient, project_without_unread, tenant_a_admin):
    """Test that has_unread_jobs is false when no pending messages exist."""
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

    # Get filter options
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": project_without_unread.project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should be false (no pending messages)
    assert data["has_unread_jobs"] is False


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_filter_options_multi_tenant_isolation(
    async_client: AsyncClient, test_jobs_with_varied_data, tenant_a_admin, tenant_b_admin
):
    """Test that tenant B cannot see tenant A's filter options."""
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

    # Try to get filter options for tenant A's project
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Should return empty results (no cross-tenant data leakage)
    assert data["statuses"] == []
    assert data["agent_display_names"] == []
    assert data["health_statuses"] == []
    assert data["tool_types"] == []
    assert data["has_unread_jobs"] is False


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_filter_options_authentication_required(async_client: AsyncClient, test_jobs_with_varied_data):
    """Test that authentication is required."""
    # Try without auth headers
    response = await async_client.get(
        "/api/agent-jobs/filter-options",
        params={"project_id": test_jobs_with_varied_data["project"].project_id},
    )

    assert response.status_code == 401  # Unauthorized


# ============================================================================
# VALIDATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_filter_options_missing_project_id(async_client: AsyncClient, tenant_a_admin):
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
        "/api/agent-jobs/filter-options",
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error
