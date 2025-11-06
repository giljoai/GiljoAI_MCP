"""
Integration tests for deleted projects endpoint (Handover 0070).

Tests the /api/v1/projects/deleted endpoint to verify:
- Route ordering is correct (doesn't conflict with /{project_id})
- Soft-deleted projects are returned correctly
- Multi-tenant isolation
- Purge countdown calculation
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project, User


@pytest.mark.asyncio
async def test_deleted_endpoint_route_ordering(client: AsyncClient, test_user: User, auth_headers: dict):
    """
    Test that /deleted route doesn't conflict with /{project_id} route.

    This test ensures the route ordering fix is working correctly.
    Before fix: /deleted was matched by /{project_id} with project_id="deleted"
    After fix: /deleted is matched by its specific route
    """
    # Call the /deleted endpoint
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    # Should succeed (200) or return empty list, NOT 404
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Should return a list (even if empty)
    data = response.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"


@pytest.mark.asyncio
async def test_list_deleted_projects_empty(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test listing deleted projects when none exist."""
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_deleted_projects_with_data(
    client: AsyncClient, async_session: AsyncSession, test_user: User, test_product: Product, auth_headers: dict
):
    """Test listing deleted projects with soft-deleted data."""
    # Create a project and soft delete it
    project = Project(
        name="Test Deleted Project",
        alias="ABC123",
        mission="Test mission",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="deleted",
        deleted_at=datetime.now(timezone.utc) - timedelta(days=2),  # Deleted 2 days ago
    )
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    # List deleted projects
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    deleted_project = data[0]
    assert deleted_project["id"] == project.id
    assert deleted_project["alias"] == "ABC123"
    assert deleted_project["name"] == "Test Deleted Project"
    assert deleted_project["product_id"] == test_product.id
    assert deleted_project["product_name"] == test_product.name
    assert "deleted_at" in deleted_project
    assert "days_until_purge" in deleted_project
    assert "purge_date" in deleted_project

    # Days until purge should be ~8 (10 days - 2 days elapsed)
    days_until_purge = deleted_project["days_until_purge"]
    assert 7 <= days_until_purge <= 8, f"Expected ~8 days, got {days_until_purge}"


@pytest.mark.asyncio
async def test_deleted_projects_purge_countdown(
    client: AsyncClient, async_session: AsyncSession, test_user: User, test_product: Product, auth_headers: dict
):
    """Test purge countdown calculation for various deletion dates."""
    # Create projects deleted at different times
    projects = [
        ("Recent", 1),  # 1 day ago -> 9 days until purge
        ("Midway", 5),  # 5 days ago -> 5 days until purge
        ("Near", 9),  # 9 days ago -> 1 day until purge
        ("Overdue", 11),  # 11 days ago -> 0 days (should be purged but test data)
    ]

    for name, days_ago in projects:
        project = Project(
            name=f"Deleted {name}",
            alias=f"DEL{days_ago:02d}",
            mission="Test mission",
            tenant_key=test_user.tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        async_session.add(project)

    await async_session.commit()

    # List deleted projects
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4

    # Verify countdown calculations
    countdown_map = {p["name"]: p["days_until_purge"] for p in data}

    assert 8 <= countdown_map["Deleted Recent"] <= 9
    assert 4 <= countdown_map["Deleted Midway"] <= 5
    assert 0 <= countdown_map["Deleted Near"] <= 1
    assert countdown_map["Deleted Overdue"] == 0  # Max 0 for overdue


@pytest.mark.asyncio
async def test_deleted_projects_multi_tenant_isolation(
    client: AsyncClient, async_session: AsyncSession, test_user: User, test_product: Product, auth_headers: dict
):
    """Test that deleted projects are isolated by tenant."""
    # Create deleted project for test user's tenant
    project1 = Project(
        name="User1 Deleted",
        alias="USR1DL",
        mission="Test",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="deleted",
        deleted_at=datetime.now(timezone.utc),
    )
    async_session.add(project1)

    # Create deleted project for different tenant
    other_tenant_key = "other-tenant-key"
    project2 = Project(
        name="User2 Deleted",
        alias="USR2DL",
        mission="Test",
        tenant_key=other_tenant_key,
        product_id=test_product.id,
        status="deleted",
        deleted_at=datetime.now(timezone.utc),
    )
    async_session.add(project2)

    await async_session.commit()

    # List deleted projects (should only see tenant's projects)
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "User1 Deleted"
    assert data[0]["alias"] == "USR1DL"


@pytest.mark.asyncio
async def test_deleted_projects_excludes_active(
    client: AsyncClient, async_session: AsyncSession, test_user: User, test_product: Product, auth_headers: dict
):
    """Test that active projects are not included in deleted list."""
    # Create active project
    active_project = Project(
        name="Active Project",
        alias="ACTIVE",
        mission="Test",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="active",
        deleted_at=None,
    )
    async_session.add(active_project)

    # Create deleted project
    deleted_project = Project(
        name="Deleted Project",
        alias="DELPRO",
        mission="Test",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="deleted",
        deleted_at=datetime.now(timezone.utc),
    )
    async_session.add(deleted_project)

    await async_session.commit()

    # List deleted projects
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Deleted Project"


@pytest.mark.asyncio
async def test_deleted_projects_without_product(
    client: AsyncClient, async_session: AsyncSession, test_user: User, auth_headers: dict
):
    """Test deleted projects without associated product (product_id=NULL)."""
    # Create deleted project without product
    project = Project(
        name="Orphan Deleted",
        alias="ORPHAN",
        mission="Test",
        tenant_key=test_user.tenant_key,
        product_id=None,
        status="deleted",
        deleted_at=datetime.now(timezone.utc),
    )
    async_session.add(project)
    await async_session.commit()

    # List deleted projects
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Orphan Deleted"
    assert data[0]["product_id"] is None
    assert data[0]["product_name"] is None


@pytest.mark.asyncio
async def test_deleted_projects_response_schema(
    client: AsyncClient, async_session: AsyncSession, test_user: User, test_product: Product, auth_headers: dict
):
    """Test deleted projects response matches expected schema."""
    # Create deleted project
    project = Project(
        name="Schema Test",
        alias="SCHEMA",
        mission="Test",
        tenant_key=test_user.tenant_key,
        product_id=test_product.id,
        status="deleted",
        deleted_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    async_session.add(project)
    await async_session.commit()

    # List deleted projects
    response = await client.get("/api/v1/projects/deleted", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    project_data = data[0]

    # Verify all required fields exist
    required_fields = [
        "id",
        "alias",
        "name",
        "product_id",
        "product_name",
        "deleted_at",
        "days_until_purge",
        "purge_date",
    ]
    for field in required_fields:
        assert field in project_data, f"Missing field: {field}"

    # Verify field types
    assert isinstance(project_data["id"], str)
    assert isinstance(project_data["alias"], str)
    assert isinstance(project_data["name"], str)
    assert isinstance(project_data["days_until_purge"], int)
    assert project_data["days_until_purge"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
