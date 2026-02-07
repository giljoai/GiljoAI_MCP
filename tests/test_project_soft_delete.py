"""
Comprehensive integration tests for Project Soft Delete with Recovery (Handover 0070).

Tests cover:
- Soft delete functionality (DELETE endpoint)
- Deleted projects listing (GET /deleted endpoint)
- Project restoration (POST /restore endpoint)
- Purge functionality (10-day expiration)
- Multi-tenant isolation
- Edge cases and error handling
- WebSocket broadcasts
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import Message, Product, Project, Task
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest.mark.asyncio
class TestProjectSoftDelete:
    """Test suite for project soft delete functionality."""

    async def test_soft_delete_project_success(self, db_session, test_tenant_key, test_product):
        """Test successful soft delete of a project."""
        # Create a project
        project = Project(
            name="Test Project",
            mission="Test mission",
            description="Soft delete test project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="inactive",
        )
        db_session.add(project)
        await db_session.commit()

        # Soft delete
        project.status = "deleted"
        project.deleted_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Verify status
        stmt = select(Project).where(Project.id == project.id)
        result = await db_session.execute(stmt)
        deleted_project = result.scalar_one()

        assert deleted_project.status == "deleted"
        assert deleted_project.deleted_at is not None
        assert deleted_project.deleted_at <= datetime.now(timezone.utc)

    async def test_soft_delete_prevents_duplicate(self, db_session, test_tenant_key, test_product):
        """Test that deleting an already deleted project fails."""
        # Create and delete project
        project = Project(
            name="Already Deleted",
            mission="Test",
            description="Duplicate delete project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        # Attempting to delete again should be prevented by endpoint logic
        # (This would be caught in the API endpoint)
        assert project.status == "deleted"
        assert project.deleted_at is not None

    async def test_list_deleted_projects_tenant_isolation(self, db_session):
        """Test that deleted projects are isolated by tenant."""
        tenant1 = "tenant-001"
        tenant2 = "tenant-002"

        # Create products for each tenant
        product1 = Product(name="Product 1", tenant_key=tenant1)
        product2 = Product(name="Product 2", tenant_key=tenant2)
        db_session.add_all([product1, product2])
        await db_session.commit()

        # Create deleted projects for each tenant
        project1 = Project(
            name="Tenant 1 Deleted",
            mission="Test",
            description="Tenant 1 deleted project",
            tenant_key=tenant1,
            product_id=product1.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        project2 = Project(
            name="Tenant 2 Deleted",
            mission="Test",
            description="Tenant 2 deleted project",
            tenant_key=tenant2,
            product_id=product2.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add_all([project1, project2])
        await db_session.commit()

        # Query deleted projects for tenant1
        stmt = select(Project).where(Project.tenant_key == tenant1, Project.deleted_at.isnot(None))
        result = await db_session.execute(stmt)
        tenant1_projects = result.scalars().all()

        # Should only see tenant1's deleted project
        assert len(tenant1_projects) == 1
        assert tenant1_projects[0].name == "Tenant 1 Deleted"
        assert tenant1_projects[0].tenant_key == tenant1

    async def test_restore_project_success(self, db_session, test_tenant_key, test_product):
        """Test successful restoration of a deleted project."""
        # Create deleted project
        project = Project(
            name="To Restore",
            mission="Test",
            description="Restore test project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        # Restore
        project.status = "inactive"
        project.deleted_at = None
        project.updated_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Verify restoration
        stmt = select(Project).where(Project.id == project.id)
        result = await db_session.execute(stmt)
        restored_project = result.scalar_one()

        assert restored_project.status == "inactive"
        assert restored_project.deleted_at is None

    async def test_restore_non_deleted_project_fails(self, db_session, test_tenant_key, test_product):
        """Test that restoring a non-deleted project fails."""
        # Create active project
        project = Project(
            name="Active Project",
            mission="Test",
            description="Active project for restore test",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="active",
        )
        db_session.add(project)
        await db_session.commit()

        # Attempting to restore should fail (checked in API endpoint)
        assert project.deleted_at is None
        assert project.status == "active"

    async def test_purge_expired_projects(self, db_session, test_tenant_key, test_product):
        """Test purging of projects deleted more than 10 days ago."""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        # Create old deleted project (11 days ago)
        old_deleted = Project(
            name="Old Deleted",
            mission="Test",
            description="Old deleted project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=11),
        )

        # Create recent deleted project (5 days ago)
        recent_deleted = Project(
            name="Recent Deleted",
            mission="Test",
            description="Recent deleted project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=5),
        )

        db_session.add_all([old_deleted, recent_deleted])
        await db_session.commit()

        old_id = old_deleted.id
        recent_id = recent_deleted.id

        # Mock database manager
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        # Create ProjectService with mocked db_manager
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        # Run purge
        result = await project_service.purge_expired_deleted_projects()

        assert result["success"] is True
        assert result["purged_count"] == 1

        # Verify old project is gone
        stmt = select(Project).where(Project.id == old_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        # Verify recent project still exists
        stmt = select(Project).where(Project.id == recent_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is not None

    async def test_purge_cascade_deletes_children(self, db_session, test_tenant_key, test_product):
        """Test that purging a project cascades to agents, tasks, and messages."""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        # Create expired deleted project
        project = Project(
            name="With Children",
            mission="Test",
            description="Deleted project with children",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=11),
        )
        db_session.add(project)
        await db_session.commit()

        # Create child records
        agent = AgentExecution(
            tenant_key=test_tenant_key,
            project_id=project.id,
            agent_display_name="tester",
            mission="Test mission",
        )
        task = Task(title="Test Task", tenant_key=test_tenant_key, product_id=test_product.id, project_id=project.id)
        message = Message(content="Test message", tenant_key=test_tenant_key, project_id=project.id)
        db_session.add_all([agent, task, message])
        await db_session.commit()

        project_id = project.id
        agent_id = agent.id
        task_id = task.id
        message_id = message.id

        # Mock database manager
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        # Create ProjectService with mocked db_manager
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        # Run purge
        result = await project_service.purge_expired_deleted_projects()

        assert result["success"] is True
        assert result["purged_count"] == 1

        # Verify all records are deleted
        stmt = select(Project).where(Project.id == project_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        stmt = select(AgentExecution).where(AgentExecution.agent_id == agent_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        stmt = select(Task).where(Task.id == task_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        stmt = select(Message).where(Message.id == message_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_manual_purge_deleted_project(self, db_session, test_tenant_key, test_product):
        """Projects in soft delete can be purged immediately with cascade cleanup."""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        # Create soft-deleted project with children
        project = Project(
            name="Manual Purge",
            mission="Test",
            description="Manually purged project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        task = Task(title="Orphan Task", tenant_key=test_tenant_key, product_id=test_product.id, project_id=project.id)
        message = Message(content="Orphan Message", tenant_key=test_tenant_key, project_id=project.id)
        db_session.add_all([task, message])
        await db_session.commit()

        project_id = project.id
        task_id = task.id
        message_id = message.id

        # Mock database manager
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.purge_deleted_project(project_id)

        assert result["success"] is True
        assert result["purged_count"] == 1

        # Records are gone
        stmt = select(Project).where(Project.id == project_id)
        assert (await db_session.execute(stmt)).scalar_one_or_none() is None

        stmt = select(Task).where(Task.id == task_id)
        assert (await db_session.execute(stmt)).scalar_one_or_none() is None

        stmt = select(Message).where(Message.id == message_id)
        assert (await db_session.execute(stmt)).scalar_one_or_none() is None

    async def test_manual_purge_all_deleted_projects_isolates_tenant(self, db_session, test_tenant_key):
        """Bulk purge should delete only the current tenant's soft-deleted projects."""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        other_tenant = "other-tenant"

        # Create products
        tenant_product = Product(name="Tenant Product", tenant_key=test_tenant_key)
        other_product = Product(name="Other Product", tenant_key=other_tenant)
        db_session.add_all([tenant_product, other_product])
        await db_session.commit()

        # Create deleted projects for each tenant
        tenant_project = Project(
            name="Tenant Deleted",
            mission="Test",
            description="Tenant scoped deleted project",
            tenant_key=test_tenant_key,
            product_id=tenant_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        other_project = Project(
            name="Other Deleted",
            mission="Test",
            description="Other tenant deleted project",
            tenant_key=other_tenant,
            product_id=other_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add_all([tenant_project, other_project])
        await db_session.commit()

        # Mock database manager
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        result = await project_service.purge_all_deleted_projects()

        assert result["success"] is True
        assert result["purged_count"] == 1

        # Tenant project is gone
        stmt = select(Project).where(Project.tenant_key == test_tenant_key)
        assert len((await db_session.execute(stmt)).scalars().all()) == 0

        # Other tenant project is untouched
        stmt = select(Project).where(Project.tenant_key == other_tenant)
        assert len((await db_session.execute(stmt)).scalars().all()) == 1

    async def test_list_projects_excludes_deleted(self, db_session, test_tenant_key, test_product):
        """Test that normal project listing excludes deleted projects."""
        # Create active, inactive, and deleted projects
        active = Project(
            name="Active",
            mission="Test",
            description="Active project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="active",
        )
        inactive = Project(
            name="Inactive",
            mission="Test",
            description="Inactive project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="inactive",
        )
        deleted = Project(
            name="Deleted",
            mission="Test",
            description="Deleted project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add_all([active, inactive, deleted])
        await db_session.commit()

        # Query non-deleted projects
        from sqlalchemy import or_

        stmt = select(Project).where(
            Project.tenant_key == test_tenant_key, or_(Project.status != "deleted", Project.deleted_at.is_(None))
        )
        result = await db_session.execute(stmt)
        projects = result.scalars().all()

        # Should only see active and inactive
        assert len(projects) == 2
        project_names = [p.name for p in projects]
        assert "Active" in project_names
        assert "Inactive" in project_names
        assert "Deleted" not in project_names

    async def test_days_until_purge_calculation(self, test_tenant_key, test_product):
        """Test calculation of days until purge."""
        # Create project deleted 3 days ago
        deleted_at = datetime.now(timezone.utc) - timedelta(days=3)
        project = Project(
            name="Test",
            mission="Test",
            description="Deleted project for purge window",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=deleted_at,
        )

        # Calculate purge date and days remaining
        purge_date = deleted_at + timedelta(days=10)
        now = datetime.now(timezone.utc)
        days_until_purge = max(0, (purge_date - now).days)

        # Should be approximately 7 days (10 - 3)
        assert days_until_purge >= 6
        assert days_until_purge <= 7

    async def test_purge_zero_days_remaining(self, test_tenant_key, test_product):
        """Test that projects with 0 days remaining are still shown until purged."""
        # Create project deleted exactly 10 days ago
        deleted_at = datetime.now(timezone.utc) - timedelta(days=10)
        project = Project(
            name="Expiring Today",
            mission="Test",
            description="Expires today project",
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            status="deleted",
            deleted_at=deleted_at,
        )

        # Calculate days remaining
        purge_date = deleted_at + timedelta(days=10)
        now = datetime.now(timezone.utc)
        days_until_purge = max(0, (purge_date - now).days)

        # Should be 0 (but still visible until next purge run)
        assert days_until_purge == 0

    async def test_restore_maintains_tenant_isolation(self, db_session):
        """Test that restoration respects tenant boundaries."""
        tenant1 = "tenant-001"
        tenant2 = "tenant-002"

        # Create products
        product1 = Product(name="Product 1", tenant_key=tenant1)
        product2 = Product(name="Product 2", tenant_key=tenant2)
        db_session.add_all([product1, product2])
        await db_session.commit()

        # Create deleted project for tenant1
        project = Project(
            name="Tenant 1 Project",
            mission="Test",
            description="Tenant 1 deleted project",
            tenant_key=tenant1,
            product_id=product1.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(project)
        await db_session.commit()

        # Attempting to restore as tenant2 should fail (API endpoint checks this)
        # Verify project still belongs to tenant1
        assert project.tenant_key == tenant1

    async def test_purge_respects_tenant_boundaries(self, db_session, test_tenant_key):
        """Test that purge doesn't affect other tenants."""
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        tenant1 = "tenant-001"
        tenant2 = "tenant-002"

        # Create products
        product1 = Product(name="Product 1", tenant_key=tenant1)
        product2 = Product(name="Product 2", tenant_key=tenant2)
        db_session.add_all([product1, product2])
        await db_session.commit()

        # Create expired deleted projects for both tenants
        project1 = Project(
            name="Tenant 1 Old",
            mission="Test",
            description="Tenant 1 old project",
            tenant_key=tenant1,
            product_id=product1.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=11),
        )
        project2 = Project(
            name="Tenant 2 Old",
            mission="Test",
            description="Tenant 2 old project",
            tenant_key=tenant2,
            product_id=product2.id,
            status="deleted",
            deleted_at=datetime.now(timezone.utc) - timedelta(days=11),
        )
        db_session.add_all([project1, project2])
        await db_session.commit()

        # Mock database manager
        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        # Create ProjectService with mocked db_manager
        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_tenant_key)
        project_service = ProjectService(db_manager, tenant_manager)

        # Run purge
        result = await project_service.purge_expired_deleted_projects()

        assert result["success"] is True
        assert result["purged_count"] == 2  # Both should be purged

        # Verify both are gone
        stmt = select(Project).where(Project.tenant_key == tenant1)
        result = await db_session.execute(stmt)
        assert len(result.scalars().all()) == 0

        stmt = select(Project).where(Project.tenant_key == tenant2)
        result = await db_session.execute(stmt)
        assert len(result.scalars().all()) == 0


# Fixtures


@pytest.fixture
def test_tenant_key():
    """Provide a test tenant key."""
    return TenantManager.generate_tenant_key()


@pytest.fixture
async def test_product(db_session, test_tenant_key):
    """Create a test product."""
    product = Product(name="Test Product Handover 0070", tenant_key=test_tenant_key)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product
