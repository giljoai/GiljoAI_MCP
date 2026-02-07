"""
Integration tests for empty state API resilience.

Tests that API endpoints return empty arrays (200 OK) instead of errors
when database is empty (fresh install scenario).

This ensures graceful degradation when no data exists:
- List endpoints return [] not 400/500
- Stats endpoints return [] not errors
- No cascading failures from missing data

Test Pattern:
1. Use clean database (no seeded data)
2. Make authenticated requests to list endpoints
3. Verify 200 OK status
4. Verify empty array response (or empty object with zero counts)

Handover Reference: Empty state API resilience testing
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_messages_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    List messages should return empty array when no projects exist.

    Scenario: Fresh install with no projects created yet.
    Expected: GET /api/v1/messages/ returns [] with 200 OK.
    Actual (before fix): May return 400/500 if no project context exists.
    """
    response = await async_client.get("/api/v1/messages/", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert response.json() == [], f"Expected empty array, got {response.json()}"


@pytest.mark.asyncio
async def test_list_tasks_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    List tasks should return empty array when no tasks exist.

    Scenario: Fresh install with no tasks created.
    Expected: GET /api/v1/tasks/ returns [] with 200 OK.
    """
    response = await async_client.get("/api/v1/tasks/", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert response.json() == [], f"Expected empty array, got {response.json()}"


@pytest.mark.asyncio
async def test_list_jobs_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    List jobs should return empty result when no jobs exist.

    Scenario: Fresh install with no agent jobs created.
    Expected: GET /api/agent-jobs/ returns {jobs: [], total: 0} with 200 OK.
    """
    response = await async_client.get("/api/agent-jobs/", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

    data = response.json()
    assert isinstance(data, dict), f"Expected dict response, got {type(data)}"
    assert data.get("jobs") == [], f"Expected empty jobs array, got {data.get('jobs')}"
    assert data.get("total") == 0, f"Expected total count 0, got {data.get('total')}"


@pytest.mark.asyncio
async def test_list_projects_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    List projects should return empty array when no projects exist.

    Scenario: Fresh install with no projects created.
    Expected: GET /api/projects/ returns [] with 200 OK.
    """
    response = await async_client.get("/api/projects/", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert response.json() == [], f"Expected empty array, got {response.json()}"


@pytest.mark.asyncio
async def test_stats_projects_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    Project stats should return empty array when no projects exist.

    Scenario: Fresh install with no projects.
    Expected: GET /api/v1/stats/projects returns [] with 200 OK.
    """
    response = await async_client.get("/api/v1/stats/projects", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert response.json() == [], f"Expected empty array, got {response.json()}"


@pytest.mark.asyncio
async def test_stats_agents_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    Agent stats should return empty array when no agents exist.

    Scenario: Fresh install with no agent jobs.
    Expected: GET /api/v1/stats/agents returns [] with 200 OK.
    """
    response = await async_client.get("/api/v1/stats/agents", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert response.json() == [], f"Expected empty array, got {response.json()}"


@pytest.mark.asyncio
async def test_get_products_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    Get products should return empty array when no products exist.

    Scenario: Fresh install with no products created.
    Expected: GET /api/products/ returns [] with 200 OK.
    """
    response = await async_client.get("/api/products/", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

    data = response.json()
    # Response may be [] or {"products": []}
    if isinstance(data, list):
        assert data == [], f"Expected empty array, got {data}"
    elif isinstance(data, dict):
        assert data.get("products") == [], f"Expected empty products array, got {data.get('products')}"


@pytest.mark.asyncio
async def test_get_agent_templates_empty_database(async_client: AsyncClient, auth_headers_developer):
    """
    Get agent templates should return empty array when no templates exist.

    Scenario: Fresh install with no agent templates configured.
    Expected: GET /api/agent-templates/ returns [] with 200 OK.

    Note: Some systems may seed default templates, in which case this test
    verifies the endpoint handles the empty state gracefully even if seeding occurs.
    """
    response = await async_client.get("/api/agent-templates/", cookies=auth_headers_developer)

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"

    data = response.json()
    # Verify response is a list (may be empty or contain seeded defaults)
    assert isinstance(data, list), f"Expected list response, got {type(data)}"
    # In fresh install, expect empty array (unless system seeds defaults)
    # Test passes if endpoint returns 200 with valid list structure


class TestEmptyStateEdgeCases:
    """
    Edge case tests for empty state scenarios.

    Tests boundary conditions and error handling when database is empty.
    """

    @pytest.mark.asyncio
    async def test_list_messages_with_pagination_empty(self, async_client: AsyncClient, auth_headers_developer):
        """
        List messages with pagination should handle empty state.

        Scenario: Pagination parameters provided but no data exists.
        Expected: Returns empty array with appropriate pagination metadata.
        """
        response = await async_client.get(
            "/api/v1/messages/", params={"skip": 0, "limit": 10}, cookies=auth_headers_developer
        )

        assert response.status_code == 200
        data = response.json()
        # Response structure may vary - accept [] or {items: [], total: 0}
        if isinstance(data, list):
            assert data == []
        elif isinstance(data, dict):
            assert data.get("items", data.get("messages", [])) == []

    @pytest.mark.asyncio
    async def test_list_jobs_with_filters_empty(self, async_client: AsyncClient, auth_headers_developer):
        """
        List jobs with filters should handle empty state.

        Scenario: Status filter provided but no jobs exist.
        Expected: Returns empty result set with 200 OK.
        """
        response = await async_client.get(
            "/api/agent-jobs/", params={"status": "active"}, cookies=auth_headers_developer
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert data.get("jobs") == []
        assert data.get("total") == 0

    @pytest.mark.asyncio
    async def test_stats_with_date_range_empty(self, async_client: AsyncClient, auth_headers_developer):
        """
        Stats endpoints with date range filters should handle empty state.

        Scenario: Date range filters provided but no data exists.
        Expected: Returns empty stats with 200 OK.
        """
        from datetime import datetime, timedelta

        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()

        response = await async_client.get(
            "/api/v1/stats/projects",
            params={"start_date": start_date, "end_date": end_date},
            cookies=auth_headers_developer,
        )

        assert response.status_code == 200
        # Stats should return empty array or zero counts, not error
        data = response.json()
        if isinstance(data, list):
            assert data == []
        elif isinstance(data, dict):
            # Accept any zero-count stats structure
            assert all(v == 0 for v in data.values() if isinstance(v, (int, float)))
