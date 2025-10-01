"""
Test to validate PostgreSQL migration is working correctly.

These tests verify that:
1. PostgreSQL connection works
2. Transaction isolation provides proper test isolation
3. Basic CRUD operations work with PostgreSQL
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import Agent, Project


@pytest.mark.asyncio
async def test_postgresql_connection(db_manager):
    """Test that we can connect to PostgreSQL test database."""
    assert db_manager is not None
    assert db_manager.is_async is True
    assert "postgresql" in db_manager.database_url.lower()
    assert "giljo_mcp_test" in db_manager.database_url
    print(f"\n PostgreSQL connection successful: {db_manager.database_url}")


@pytest.mark.asyncio
async def test_transaction_isolation(db_session):
    """Test that transaction rollback provides test isolation."""
    # Create a project in this transaction
    project = Project(
        name="Test Isolation Project",
        mission="Testing transaction isolation",
        tenant_key="test_tenant_isolation_key",
    )

    db_session.add(project)
    await db_session.flush()  # Make it visible in this transaction

    # Verify it exists in current transaction
    result = await db_session.get(Project, project.id)
    assert result is not None
    assert result.name == "Test Isolation Project"
    print(f"\n Created project in transaction: {project.id}")

    # Transaction will be rolled back after this test


@pytest.mark.asyncio
async def test_isolation_verification(db_session):
    """Verify that previous test's data was rolled back."""
    # Try to find the project from the previous test
    result = await db_session.execute(
        select(Project).where(Project.tenant_key == "test_tenant_isolation_key")
    )
    project = result.scalar_one_or_none()

    # It should not exist because the previous test's transaction was rolled back
    assert project is None
    print("\n Transaction isolation verified - previous test data was rolled back")


@pytest.mark.asyncio
async def test_basic_crud(db_session):
    """Test basic CRUD operations with PostgreSQL."""
    # Create project
    project = Project(
        name="CRUD Test",
        mission="Test CRUD operations",
        tenant_key="test_crud_tenant",
    )

    db_session.add(project)
    await db_session.flush()

    # Query back
    queried_project = await db_session.get(Project, project.id)
    assert queried_project is not None
    assert queried_project.name == "CRUD Test"
    print(f"\n CRUD operations successful - created and queried project: {project.id}")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
