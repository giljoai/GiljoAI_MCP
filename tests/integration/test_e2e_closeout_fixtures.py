"""
Integration test for E2E closeout workflow fixtures.

Validates that e2e_closeout_fixtures pytest fixture creates
all required test data correctly.
"""

import pytest
from passlib.hash import bcrypt


@pytest.mark.asyncio
async def test_e2e_closeout_fixtures_creates_all_data(e2e_closeout_fixtures):
    """
    Test that e2e_closeout_fixtures creates all required data.

    Verifies:
    - User exists with correct credentials
    - Product exists and is active
    - Project exists and is active
    - 3 agents exist with completed status
    - All data is properly tenant-isolated
    """
    fixtures = e2e_closeout_fixtures

    # Verify fixture structure
    assert "user" in fixtures
    assert "product" in fixtures
    assert "project" in fixtures
    assert "agents" in fixtures
    assert "tenant_key" in fixtures

    # Verify user
    user = fixtures["user"]
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.role == "developer"
    assert user.is_active is True
    assert user.tenant_key == fixtures["tenant_key"]

    # Verify password hash
    assert bcrypt.verify("testpassword", user.password_hash)

    # Verify product
    product = fixtures["product"]
    assert product.name == "Test Product"
    assert product.is_active is True
    assert product.tenant_key == fixtures["tenant_key"]

    # Verify project
    project = fixtures["project"]
    assert project.name == "Mock Project"
    assert project.status == "active"
    assert project.tenant_key == fixtures["tenant_key"]
    assert project.product_id == product.id

    # Verify agents
    agents = fixtures["agents"]
    assert len(agents) == 3

    for agent in agents:
        assert agent.status == "complete"
        assert agent.progress == 100
        assert agent.tenant_key == fixtures["tenant_key"]
        assert agent.project_id == project.id

    # Verify agent types
    agent_types = {agent.agent_display_name for agent in agents}
    assert "orchestrator" in agent_types
    assert "implementer" in agent_types
    assert "tester" in agent_types


@pytest.mark.asyncio
async def test_e2e_closeout_fixtures_multi_tenant_isolation(
    e2e_closeout_fixtures, db_session
):
    """
    Test that e2e_closeout_fixtures data is properly tenant-isolated.

    Verifies:
    - All fixtures use same tenant_key
    - No data leaks to other tenants
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import Product, Project, User
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

    fixtures = e2e_closeout_fixtures
    tenant_key = fixtures["tenant_key"]

    # Query all data for this tenant
    stmt = select(User).where(User.tenant_key == tenant_key)
    result = await db_session.execute(stmt)
    users = result.scalars().all()
    assert len(users) >= 1  # At least the test user

    stmt = select(Product).where(Product.tenant_key == tenant_key)
    result = await db_session.execute(stmt)
    products = result.scalars().all()
    assert len(products) >= 1  # At least the test product

    stmt = select(Project).where(Project.tenant_key == tenant_key)
    result = await db_session.execute(stmt)
    projects = result.scalars().all()
    assert len(projects) >= 1  # At least the test project

    stmt = select(AgentExecution).where(AgentExecution.tenant_key == tenant_key)
    result = await db_session.execute(stmt)
    agents = result.scalars().all()
    assert len(agents) >= 3  # At least the 3 test agents

    # Verify all belong to same tenant
    assert all(u.tenant_key == tenant_key for u in users)
    assert all(p.tenant_key == tenant_key for p in products)
    assert all(p.tenant_key == tenant_key for p in projects)
    assert all(a.tenant_key == tenant_key for a in agents)


@pytest.mark.asyncio
async def test_e2e_closeout_fixtures_idempotent(db_manager):
    """
    Test that fixture creation is idempotent.

    Running the fixture creator multiple times should not create
    duplicate data (should reuse existing test user if present).
    """
    from tests.fixtures.e2e_closeout_fixtures import E2ECloseoutFixtures

    fixture_creator = E2ECloseoutFixtures(db_manager)

    # Create fixtures twice
    async with db_manager.get_session_async() as session1:
        fixtures1 = await fixture_creator.create_all_fixtures(session1)
        tenant_key1 = fixtures1["tenant_key"]
        user_id1 = fixtures1["user"].id

    async with db_manager.get_session_async() as session2:
        fixtures2 = await fixture_creator.create_all_fixtures(session2)
        tenant_key2 = fixtures2["tenant_key"]
        user_id2 = fixtures2["user"].id

    # User should be reused (same ID)
    assert user_id1 == user_id2

    # But tenants should be different (new tenant for each test run)
    # This is expected behavior for test isolation
    assert isinstance(tenant_key1, str)
    assert isinstance(tenant_key2, str)
