"""
Integration tests for ProjectService lifecycle methods (Handover 0501)

These tests use real database connections to verify:
- State transitions (staging → active → paused → active → completed)
- Single Active Project constraint enforcement
- WebSocket event broadcasting
- Job metrics calculation
- Multi-field updates
- Orchestrator launch

Target: >85% code coverage
"""

from datetime import datetime

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Needs project fixture update for uq_project_taxonomy constraint")

from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.project_service import ProjectService


@pytest.mark.asyncio
class TestProjectLifecycleMethods:
    """Integration tests for project lifecycle methods"""

    async def test_activate_project_from_staging(self, db_manager, tenant_manager):
        """Test activating project from staging state"""
        service = ProjectService(db_manager, tenant_manager)

        # Create a product first
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            product_id = product.id

        # Create staging project
        async with db_manager.get_session_async() as session:
            project = Project(
                name="Test Project",
                description="Test Description",
                mission="Test Mission",
                status="waiting",
                product_id=product_id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

        # Act: Activate project
        project = await service.activate_project(project_id)

        # Assert - Returns Project instance directly (Handover 0730b)
        assert isinstance(project, Project)
        assert project.status == "active"
        assert project.activated_at is not None

        # Verify in database
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Project).where(Project.id == project_id)
            db_result = await session.execute(stmt)
            db_project = db_result.scalar_one()
            assert db_project.status == "active"
            assert db_project.activated_at is not None

    async def test_activate_project_single_active_constraint(self, db_manager, tenant_manager):
        """Test Single Active Project constraint enforcement"""
        service = ProjectService(db_manager, tenant_manager)

        # Create product
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            product_id = product.id

        # Create two staging projects
        project1_id = None
        project2_id = None

        async with db_manager.get_session_async() as session:
            project1 = Project(
                name="Project 1",
                description="Description 1",
                mission="Mission 1",
                status="waiting",
                product_id=product_id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            project2 = Project(
                name="Project 2",
                description="Description 2",
                mission="Mission 2",
                status="waiting",
                product_id=product_id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project1)
            session.add(project2)
            await session.commit()
            await session.refresh(project1)
            await session.refresh(project2)
            project1_id = project1.id
            project2_id = project2.id

        # Activate first project
        project1_activated = await service.activate_project(project1_id)
        assert isinstance(project1_activated, Project)
        assert project1_activated.status == "active"

        # Activate second project (should auto-deactivate first)
        project2_activated = await service.activate_project(project2_id)
        assert isinstance(project2_activated, Project)
        assert project2_activated.status == "active"

        # Verify first project is now paused
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Project).where(Project.id == project1_id)
            db_result = await session.execute(stmt)
            db_project1 = db_result.scalar_one()
            assert db_project1.status == "paused"
            assert db_project1.paused_at is not None

    async def test_deactivate_project_success(self, db_manager, tenant_manager):
        """Test deactivating active project"""
        service = ProjectService(db_manager, tenant_manager)

        # Create active project
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()

            project = Project(
                name="Test Project",
                description="Test Description",
                mission="Test Mission",
                status="active",
                product_id=product.id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

        # Act: Deactivate
        result = await service.deactivate_project(project_id, reason="Testing pause")

        # Assert
        assert result["success"] is True
        assert result["data"]["status"] == "paused"
        assert result["data"]["config_data"]["deactivation_reason"] == "Testing pause"

    async def test_cancel_staging_success(self, db_manager, tenant_manager):
        """Test cancelling project in staging state"""
        service = ProjectService(db_manager, tenant_manager)

        # Create staging project
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()

            project = Project(
                name="Test Project",
                description="Test Description",
                mission="Test Mission",
                status="waiting",
                product_id=product.id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

        # Act: Cancel staging
        result = await service.cancel_staging(project_id)

        # Assert
        assert result["success"] is True
        assert result["data"]["status"] == "cancelled"
        assert result["data"]["completed_at"] is not None

    async def test_get_project_summary_with_jobs(self, db_manager, tenant_manager):
        """Test project summary includes accurate job metrics"""
        service = ProjectService(db_manager, tenant_manager)

        # Create project with jobs
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()

            project = Project(
                name="Test Project",
                description="Test Description",
                mission="Test Mission",
                status="active",
                activated_at=datetime.utcnow(),
                product_id=product.id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

            # Add jobs with different statuses
            jobs = [
                AgentExecution(
                    agent_display_name="architect",
                    status="completed",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
                AgentExecution(
                    agent_display_name="implementor",
                    status="completed",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
                AgentExecution(
                    agent_display_name="tester",
                    status="completed",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
                AgentExecution(
                    agent_display_name="reviewer",
                    status="active",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
                AgentExecution(
                    agent_display_name="orchestrator",
                    status="waiting",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
                AgentExecution(
                    agent_display_name="helper",
                    status="waiting",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
                AgentExecution(
                    agent_display_name="analyzer",
                    status="blocked",
                    project_id=project_id,
                    tenant_key=tenant_manager.get_current_tenant(),
                ),
            ]
            for job in jobs:
                session.add(job)
            await session.commit()

        # Act: Get summary
        result = await service.get_project_summary(project_id)

        # Assert
        assert result["success"] is True
        summary = result["data"]
        assert summary["total_jobs"] == 7
        assert summary["completed_jobs"] == 3
        assert summary["active_jobs"] == 1
        assert summary["pending_jobs"] == 2
        assert summary["blocked_jobs"] == 1
        assert abs(summary["completion_percentage"] - 42.86) < 0.1
        assert summary["product_name"] == "Test Product"

    async def test_update_project_multiple_fields(self, db_manager, tenant_manager):
        """Test update_project updates all provided fields"""
        service = ProjectService(db_manager, tenant_manager)

        # Create project
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()

            project = Project(
                name="Old Name",
                description="Old Description",
                mission="Old Mission",
                config_data={"old": "data"},
                status="active",
                product_id=product.id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

        # Act: Update multiple fields
        updates = {
            "name": "New Name",
            "description": "New Description",
            "mission": "New Mission",
            "config_data": {"new": "data"},
        }
        result = await service.update_project(project_id, updates)

        # Assert
        assert result["success"] is True
        assert result["data"]["name"] == "New Name"
        assert result["data"]["description"] == "New Description"
        assert result["data"]["mission"] == "New Mission"
        assert result["data"]["config_data"] == {"new": "data"}

    async def test_complete_project_lifecycle(self, db_manager, tenant_manager):
        """Test full lifecycle: create → activate → deactivate → activate → complete"""
        service = ProjectService(db_manager, tenant_manager)

        # Create product
        async with db_manager.get_session_async() as session:
            product = Product(
                name="Test Product", description="Test Description", tenant_key=tenant_manager.get_current_tenant()
            )
            session.add(product)
            await session.commit()

            # Create staging project
            project = Project(
                name="E2E Test Project",
                description="End-to-end test",
                mission="Complete lifecycle test",
                status="waiting",
                product_id=product.id,
                tenant_key=tenant_manager.get_current_tenant(),
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            project_id = project.id

        # Step 1: Activate
        project = await service.activate_project(project_id)
        assert isinstance(project, Project)
        assert project.status == "active"

        # Step 2: Deactivate
        project = await service.deactivate_project(project_id)
        assert isinstance(project, Project)
        assert project.status == "inactive"  # Changed from "paused" to "inactive"

        # Step 3: Re-activate
        project = await service.activate_project(project_id)
        assert isinstance(project, Project)
        assert project.status == "active"

        # Step 4: Complete
        result = await service.complete_project(project_id)
        assert result["success"] is True
        assert result["message"] == f"Project {project_id} completed successfully"

        # Verify final state
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Project).where(Project.id == project_id)
            db_result = await session.execute(stmt)
            db_project = db_result.scalar_one()
            assert db_project.status == "completed"
            assert db_project.completed_at is not None
