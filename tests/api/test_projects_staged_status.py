"""
Tests for staged status in project CRUD operations (TDD Implementation).

This test module validates that the staging_status field is properly:
- Included in project list responses
- Returned as a valid field (can be null/None)
- Correctly mapped from the Project model

Test Strategy (TDD):
1. RED: Write tests first - they should FAIL initially
2. GREEN: Implement minimum code to make tests pass
3. REFACTOR: Clean up and optimize

Coverage:
- GET /api/v1/projects/ includes staging_status field
- staging_status field can be null/None for new projects
- staging_status field can contain valid status values
- Field is properly serialized in ProjectResponse schema
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================


@pytest.fixture
async def test_user(db_manager):
    """Create test user with unique credentials."""
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"staged_test_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"staged_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("test_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "test_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def test_user_token(api_client: AsyncClient, test_user):
    """Get JWT token for test user."""
    response = await api_client.post(
        "/api/auth/login",
        json={
            "username": test_user._test_username,
            "password": test_user._test_password,
        },
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None, "access_token cookie not set"
    return access_token


@pytest.fixture
async def test_product(db_manager, test_user):
    """Create test product for project association."""
    from src.giljo_mcp.models import Product

    async with db_manager.get_session_async() as session:
        product = Product(
            name=f"Test Product {uuid4().hex[:6]}",
            description="Product for staging status tests",
            tenant_key=test_user.tenant_key,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


@pytest.fixture
async def test_project(api_client: AsyncClient, test_user_token, test_product):
    """Create test project via API."""
    headers = {"Cookie": f"access_token={test_user_token}"}

    response = await api_client.post(
        "/api/v1/projects/",
        headers=headers,
        json={
            "name": f"Test Project {uuid4().hex[:6]}",
            "description": "Project for staging status tests",
            "mission": "Test mission",
            "product_id": test_product.id,
            "status": "inactive",
        },
    )
    assert response.status_code == 201
    return response.json()


# ============================================================================
# TESTS - Staged Status Field Presence
# ============================================================================


@pytest.mark.asyncio
async def test_list_projects_includes_staging_status_field(
    api_client: AsyncClient,
    test_user_token,
    test_project,
):
    """
    Test that GET /api/v1/projects/ includes staging_status field.

    Expected behavior:
    - All projects in list response have staging_status field
    - Field can be null/None (default state)
    - Field is properly serialized in JSON response

    This is the PRIMARY test - it will FAIL until we implement the feature.
    """
    headers = {"Cookie": f"access_token={test_user_token}"}

    response = await api_client.get("/api/v1/projects/", headers=headers)

    assert response.status_code == 200
    projects = response.json()

    # Verify we have at least one project
    assert len(projects) > 0, "Should have at least one test project"

    # CRITICAL: Verify staging_status field exists in response
    first_project = projects[0]
    assert "staging_status" in first_project, (
        "staging_status field missing from ProjectResponse. This test should FAIL initially (RED phase)"
    )

    # Verify field can be null (default state for new projects)
    # Note: This assertion should pass even if staging_status is None
    assert first_project["staging_status"] is None or isinstance(first_project["staging_status"], str), (
        "staging_status should be None or a string"
    )


@pytest.mark.asyncio
async def test_project_without_agents_has_null_staging_status(
    api_client: AsyncClient,
    test_user_token,
    test_product,
):
    """
    Test that new projects without agents have null staging_status.

    Expected behavior:
    - New projects start with staging_status = null
    - No agents assigned means agent_count = 0
    - Project is in "unstaged" state
    """
    headers = {"Cookie": f"access_token={test_user_token}"}

    # Create fresh project
    create_response = await api_client.post(
        "/api/v1/projects/",
        headers=headers,
        json={
            "name": f"Unstaged Project {uuid4().hex[:6]}",
            "description": "Project with no agents",
            "mission": "Test mission",
            "product_id": test_product.id,
            "status": "inactive",
        },
    )
    assert create_response.status_code == 201
    project = create_response.json()

    # Verify new project has null staging_status
    assert "staging_status" in project, "staging_status field should exist"
    assert project["staging_status"] is None, "New project should have null staging_status"
    assert project["agent_count"] == 0, "New project should have 0 agents"


@pytest.mark.asyncio
async def test_project_with_staging_status_set(
    db_manager,
    api_client: AsyncClient,
    test_user_token,
    test_user,
    test_product,
):
    """
    Test that projects with staging_status set return the correct value.

    Expected behavior:
    - Manually set staging_status is returned in API response
    - Valid status values: staging, staged, cancelled, launching, active
    - Field is properly serialized from database
    """
    from src.giljo_mcp.models import Project

    # Create project with staging_status directly in database
    async with db_manager.get_session_async() as session:
        project = Project(
            name=f"Staged Project {uuid4().hex[:6]}",
            description="Project with staging status",
            mission="Test mission",
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
            staging_status="staged",  # Set staging_status
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        project_id = project.id

    # Fetch via API
    headers = {"Cookie": f"access_token={test_user_token}"}
    response = await api_client.get("/api/v1/projects/", headers=headers)

    assert response.status_code == 200
    projects = response.json()

    # Find our staged project
    staged_project = next((p for p in projects if p["id"] == project_id), None)

    assert staged_project is not None, "Should find staged project in list"
    assert "staging_status" in staged_project, "staging_status field should exist"
    assert staged_project["staging_status"] == "staged", "staging_status should be 'staged'"


@pytest.mark.asyncio
async def test_get_single_project_includes_staging_status(
    api_client: AsyncClient,
    test_user_token,
    test_project,
):
    """
    Test that GET /api/v1/projects/{id} includes staging_status field.

    Expected behavior:
    - Single project GET returns staging_status
    - Field is consistent with list endpoint
    """
    headers = {"Cookie": f"access_token={test_user_token}"}
    project_id = test_project["id"]

    response = await api_client.get(f"/api/v1/projects/{project_id}", headers=headers)

    assert response.status_code == 200
    project = response.json()

    # Verify staging_status field exists
    assert "staging_status" in project, "staging_status field should exist in single project response"


@pytest.mark.asyncio
async def test_staging_status_field_schema_validation(
    api_client: AsyncClient,
    test_user_token,
    test_project,
):
    """
    Test that staging_status field validates correctly in ProjectResponse schema.

    Expected behavior:
    - Field accepts null/None values
    - Field accepts valid string status values
    - Field is optional (can be omitted from updates)
    - Response schema properly serializes the field
    """
    headers = {"Cookie": f"access_token={test_user_token}"}

    # Get project list
    response = await api_client.get("/api/v1/projects/", headers=headers)
    assert response.status_code == 200

    projects = response.json()
    assert len(projects) > 0

    # Verify schema includes staging_status with correct type
    for project in projects:
        assert "staging_status" in project
        staging_status = project["staging_status"]

        # Must be None or string
        assert staging_status is None or isinstance(staging_status, str), (
            f"staging_status should be None or str, got {type(staging_status)}"
        )

        # If string, should be valid status value
        if staging_status:
            valid_statuses = [
                "staged",
            ]
            assert staging_status in valid_statuses, f"staging_status '{staging_status}' not in valid statuses"


# ============================================================================
# TESTS - Integration with Agent Count
# ============================================================================


@pytest.mark.asyncio
async def test_project_staging_status_with_agent_count(
    db_manager,
    api_client: AsyncClient,
    test_user_token,
    test_user,
    test_product,
):
    """
    Test relationship between staging_status and agent_count.

    Expected behavior:
    - Projects can have staging_status set independently of agent_count
    - Both fields are present in API response
    - Frontend can use either/both for "Staged" determination

    Note: This test validates the data structure is present for the frontend
    'Staged' column logic (agent_count > 0 OR staging_status == 'staged')
    """
    from src.giljo_mcp.models import Project

    # Create project with staging_status set
    async with db_manager.get_session_async() as session:
        project = Project(
            name=f"Staged Project {uuid4().hex[:6]}",
            description="Project with staging status",
            mission="Test mission",
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
            staging_status="staged",  # Set staging_status
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        project_id = project.id

    # Fetch via API
    headers = {"Cookie": f"access_token={test_user_token}"}
    response = await api_client.get("/api/v1/projects/", headers=headers)

    assert response.status_code == 200
    projects = response.json()

    # Find our staged project
    staged_project = next((p for p in projects if p["id"] == project_id), None)

    assert staged_project is not None, "Should find staged project in list"
    assert "staging_status" in staged_project, "staging_status field should exist"
    assert "agent_count" in staged_project, "agent_count field should exist"

    # Verify staging_status is correctly returned
    assert staged_project["staging_status"] == "staged", "staging_status should be 'staged'"

    # Frontend logic can now use: agent_count > 0 OR staging_status == 'staged'
    # This project qualifies via staging_status alone
    assert staged_project["staging_status"] == "staged", "Project should be considered 'staged' by frontend logic"
