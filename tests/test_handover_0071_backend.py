"""
Tests for Handover 0071 - Simplified Project State Management (Backend)

Test-driven development approach for backend refactoring.
"""

from datetime import datetime, timezone

import pytest

from src.giljo_mcp.enums import ProjectStatus
from src.giljo_mcp.models import Product, Project


class TestProjectStatusEnum:
    """Test ProjectStatus enum has correct values (Handover 0071)"""

    def test_active_status_exists(self):
        """ACTIVE status should exist"""
        assert hasattr(ProjectStatus, "ACTIVE")
        assert ProjectStatus.ACTIVE.value == "active"

    def test_inactive_status_exists(self):
        """INACTIVE status should exist (NEW)"""
        assert hasattr(ProjectStatus, "INACTIVE")
        assert ProjectStatus.INACTIVE.value == "inactive"

    def test_completed_status_exists(self):
        """COMPLETED status should exist"""
        assert hasattr(ProjectStatus, "COMPLETED")
        assert ProjectStatus.COMPLETED.value == "completed"

    def test_cancelled_status_exists(self):
        """CANCELLED status should exist"""
        assert hasattr(ProjectStatus, "CANCELLED")
        assert ProjectStatus.CANCELLED.value == "cancelled"

    def test_deleted_status_exists(self):
        """DELETED status should exist (Handover 0070)"""
        assert hasattr(ProjectStatus, "DELETED")
        assert ProjectStatus.DELETED.value == "deleted"

    def test_paused_status_removed(self):
        """PAUSED status should be removed"""
        assert not hasattr(ProjectStatus, "PAUSED")

    def test_archived_status_removed(self):
        """ARCHIVED status should be removed"""
        assert not hasattr(ProjectStatus, "ARCHIVED")

    def test_planning_status_removed(self):
        """PLANNING status should be removed"""
        assert not hasattr(ProjectStatus, "PLANNING")


class TestOrchestratorMethodsRemoved:
    """Test that pause/resume methods are removed from orchestrator"""

    def test_pause_project_method_removed(self):
        """pause_project() method should not exist"""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        assert not hasattr(ProjectOrchestrator, "pause_project")

    def test_resume_project_method_removed(self):
        """resume_project() method should not exist"""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        assert not hasattr(ProjectOrchestrator, "resume_project")

    def test_activate_project_method_exists(self):
        """activate_project() method should still exist"""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        assert hasattr(ProjectOrchestrator, "activate_project")

    def test_complete_project_method_exists(self):
        """complete_project() method should still exist"""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        assert hasattr(ProjectOrchestrator, "complete_project")


@pytest.mark.asyncio
class TestProductSwitchCascade:
    """Test product switching cascades to projects with 'inactive' status"""

    async def test_product_switch_sets_projects_to_inactive(self, test_client, test_user, test_db_session):
        """When switching products, active projects should be set to 'inactive'"""

        async with test_db_session() as session:
            # Create two products
            product1 = Product(
                name="Product 1", vision_statement="Product 1 vision", tenant_key=test_user.tenant_key, is_active=True
            )
            product2 = Product(
                name="Product 2", vision_statement="Product 2 vision", tenant_key=test_user.tenant_key, is_active=False
            )
            session.add_all([product1, product2])
            await session.flush()

            # Create active project under product1
            project1 = Project(
                name="Test Project",
                mission="Test mission",
                status="active",
                product_id=product1.id,
                tenant_key=test_user.tenant_key,
            )
            session.add(project1)
            await session.commit()

            # Switch to product2 (via API)
            response = await test_client.post(
                f"/api/products/{product2.id}/activate", headers={"Authorization": f"Bearer {test_user.token}"}
            )

            assert response.status_code == 200

            # Verify project1 is now inactive (not paused)
            await session.refresh(project1)
            assert project1.status == "inactive"


@pytest.mark.asyncio
class TestProjectDeactivateEndpoint:
    """Test new /projects/{id}/deactivate endpoint"""

    async def test_deactivate_active_project_success(self, test_client, test_user, test_db_session):
        """Should successfully deactivate an active project"""

        async with test_db_session() as session:
            # Create product and active project
            product = Product(
                name="Test Product", vision_statement="Vision", tenant_key=test_user.tenant_key, is_active=True
            )
            session.add(product)
            await session.flush()

            project = Project(
                name="Test Project",
                mission="Test mission",
                status="active",
                product_id=product.id,
                tenant_key=test_user.tenant_key,
            )
            session.add(project)
            await session.commit()
            project_id = project.id

        # Deactivate via API
        response = await test_client.post(
            f"/api/projects/{project_id}/deactivate", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"
        assert data["id"] == project_id

    async def test_deactivate_inactive_project_fails(self, test_client, test_user, test_db_session):
        """Should fail to deactivate a project that's not active"""

        async with test_db_session() as session:
            product = Product(
                name="Test Product", vision_statement="Vision", tenant_key=test_user.tenant_key, is_active=True
            )
            session.add(product)
            await session.flush()

            project = Project(
                name="Test Project",
                mission="Test mission",
                status="inactive",
                product_id=product.id,
                tenant_key=test_user.tenant_key,
            )
            session.add(project)
            await session.commit()
            project_id = project.id

        response = await test_client.post(
            f"/api/projects/{project_id}/deactivate", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 400
        assert "Only active projects can be deactivated" in response.json()["detail"]

    async def test_deactivate_nonexistent_project_fails(self, test_client, test_user):
        """Should fail with 404 for non-existent project"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await test_client.post(
            f"/api/projects/{fake_id}/deactivate", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 404

    async def test_deactivate_respects_tenant_isolation(
        self, test_client, test_user, other_tenant_user, test_db_session
    ):
        """Should not deactivate projects from other tenants"""

        async with test_db_session() as session:
            # Create project for other tenant
            product = Product(
                name="Other Product", vision_statement="Vision", tenant_key=other_tenant_user.tenant_key, is_active=True
            )
            session.add(product)
            await session.flush()

            project = Project(
                name="Other Project",
                mission="Mission",
                status="active",
                product_id=product.id,
                tenant_key=other_tenant_user.tenant_key,
            )
            session.add(project)
            await session.commit()
            project_id = project.id

        # Try to deactivate with different tenant
        response = await test_client.post(
            f"/api/projects/{project_id}/deactivate", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestProjectActivateValidation:
    """Test enhanced activate endpoint validation (single active per product)"""

    async def test_activate_blocks_if_another_active_exists(self, test_client, test_user, test_db_session):
        """Should fail to activate if another project is already active for same product"""

        async with test_db_session() as session:
            product = Product(
                name="Test Product", vision_statement="Vision", tenant_key=test_user.tenant_key, is_active=True
            )
            session.add(product)
            await session.flush()

            # Create two inactive projects
            project1 = Project(
                name="Project 1",
                mission="Mission 1",
                status="inactive",
                product_id=product.id,
                tenant_key=test_user.tenant_key,
            )
            project2 = Project(
                name="Project 2",
                mission="Mission 2",
                status="inactive",
                product_id=product.id,
                tenant_key=test_user.tenant_key,
            )
            session.add_all([project1, project2])
            await session.commit()
            project1_id = project1.id
            project2_id = project2.id

        # Activate project1 - should succeed
        response1 = await test_client.patch(
            f"/api/projects/{project1_id}",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {test_user.token}"},
        )
        assert response1.status_code == 200

        # Try to activate project2 - should fail
        response2 = await test_client.patch(
            f"/api/projects/{project2_id}",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {test_user.token}"},
        )
        assert response2.status_code == 400
        assert "already active" in response2.json()["detail"]
        assert "Project 1" in response2.json()["detail"]


@pytest.mark.asyncio
class TestDeletedProjectsProductScope:
    """Test list_deleted_projects filters by active product only"""

    async def test_deleted_projects_shows_only_active_product(self, test_client, test_user, test_db_session):
        """Should only show deleted projects from active product"""

        async with test_db_session() as session:
            # Create two products
            product1 = Product(
                name="Product 1",
                vision_statement="Vision 1",
                tenant_key=test_user.tenant_key,
                is_active=True,  # Active
            )
            product2 = Product(
                name="Product 2",
                vision_statement="Vision 2",
                tenant_key=test_user.tenant_key,
                is_active=False,  # Inactive
            )
            session.add_all([product1, product2])
            await session.flush()

            # Create deleted projects for both products
            deleted1 = Project(
                name="Deleted from Product 1",
                mission="Mission",
                status="deleted",
                product_id=product1.id,
                tenant_key=test_user.tenant_key,
                deleted_at=datetime.now(timezone.utc),
            )
            deleted2 = Project(
                name="Deleted from Product 2",
                mission="Mission",
                status="deleted",
                product_id=product2.id,
                tenant_key=test_user.tenant_key,
                deleted_at=datetime.now(timezone.utc),
            )
            session.add_all([deleted1, deleted2])
            await session.commit()

        # Get deleted projects
        response = await test_client.get(
            "/api/projects/deleted", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should only show deleted1 (from active product)
        assert len(data) == 1
        assert data[0]["name"] == "Deleted from Product 1"
        assert data[0]["product_name"] == "Product 1"

    async def test_deleted_projects_empty_if_no_active_product(self, test_client, test_user, test_db_session):
        """Should return empty list if no active product exists"""

        async with test_db_session() as session:
            # Create inactive product with deleted project
            product = Product(
                name="Inactive Product",
                vision_statement="Vision",
                tenant_key=test_user.tenant_key,
                is_active=False,  # No active product
            )
            session.add(product)
            await session.flush()

            deleted = Project(
                name="Deleted Project",
                mission="Mission",
                status="deleted",
                product_id=product.id,
                tenant_key=test_user.tenant_key,
                deleted_at=datetime.now(timezone.utc),
            )
            session.add(deleted)
            await session.commit()

        response = await test_client.get(
            "/api/projects/deleted", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
class TestWebSocketEvents:
    """Test WebSocket events are broadcast correctly"""

    async def test_deactivate_broadcasts_websocket_event(self, test_client, test_user, test_db_session, websocket_mock):
        """Should broadcast 'project:deactivated' WebSocket event"""

        async with test_db_session() as session:
            product = Product(
                name="Test Product", vision_statement="Vision", tenant_key=test_user.tenant_key, is_active=True
            )
            session.add(product)
            await session.flush()

            project = Project(
                name="Test Project",
                mission="Mission",
                status="active",
                product_id=product.id,
                tenant_key=test_user.tenant_key,
            )
            session.add(project)
            await session.commit()
            project_id = project.id

        # Deactivate
        response = await test_client.post(
            f"/api/projects/{project_id}/deactivate", headers={"Authorization": f"Bearer {test_user.token}"}
        )

        assert response.status_code == 200

        # Verify WebSocket broadcast
        websocket_mock.assert_broadcast_called_with(
            "project:deactivated", {"project_id": project_id, "status": "inactive", "tenant_key": test_user.tenant_key}
        )
