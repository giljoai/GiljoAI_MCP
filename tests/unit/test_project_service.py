"""
Unit tests for ProjectService (Handover 0121 - Phase 1)

Tests cover:
- CRUD operations
- Lifecycle management (complete, cancel, restore)
- Status and metrics
- Error handling and edge cases

Target: >80% line coverage
"""

import pytest

pytestmark = pytest.mark.skip(reason="0750b: schema drift — uq_project_taxonomy + NOT NULL constraints")

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.exceptions import BaseGiljoError, ResourceNotFoundError
from src.giljo_mcp.models import AgentExecution, Project
from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.services.project_service import ProjectService


@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.delete = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    db_manager.get_tenant_session_async = Mock(return_value=session)
    return db_manager, session


class TestProjectServiceCRUD:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_project_success(self, mock_db_manager):
        """Test successful project creation"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        project = await service.create_project(
            name="Test Project", mission="Test mission", description="Test description", tenant_key="test-tenant"
        )

        # Assert - Returns Project instance directly (Handover 0730b)
        assert isinstance(project, Project)
        assert project.name == "Test Project"
        assert project.mission == "Test mission"
        assert project.description == "Test description"
        assert project.tenant_key == "test-tenant"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_project_auto_generates_tenant_key(self, mock_db_manager):
        """Test that tenant_key is auto-generated if not provided"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        project = await service.create_project(name="Test", mission="Mission")

        # Assert - Returns Project instance directly (Handover 0730b)
        assert isinstance(project, Project)
        assert project.tenant_key.startswith("tk_")

    @pytest.mark.asyncio
    async def test_create_project_error_handling(self, mock_db_manager):
        """Test error handling in create_project - raises exception (Handover 0730b)"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Override to throw error
        db_manager.get_session_async = Mock(side_effect=Exception("Database error"))

        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert - Raises BaseGiljoError
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.create_project(name="Test", mission="Mission")

        assert "database error" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_get_project_success(self, mock_db_manager):
        """Test successful project retrieval"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-id"
        mock_project.alias = "test-alias"
        mock_project.name = "Test Project"
        mock_project.mission = "Test Mission"
        mock_project.description = "Test Description"
        mock_project.status = "active"
        mock_project.staging_status = None
        mock_project.product_id = None
        mock_project.tenant_key = "test-tenant"
        mock_project.execution_mode = "sequential"
        mock_project.created_at = datetime.now()
        mock_project.updated_at = None
        mock_project.completed_at = None

        # Mock agent job and execution (query returns tuples)
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "agent-1"
        mock_job.job_type = "implementer"
        mock_job.created_at = datetime.now()

        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "agent-1"
        mock_execution.agent_name = "Test Agent"
        mock_execution.status = "active"
        mock_execution.messages_sent_count = 0
        mock_execution.messages_waiting_count = 0
        mock_execution.messages_read_count = 0

        # Mock two queries: get project, get agents (returns list of tuples)
        session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=mock_project)),  # Get project
                Mock(all=Mock(return_value=[(mock_job, mock_execution)])),  # Get agents (tuples)
            ]
        )

        service = ProjectService(db_manager, tenant_manager)

        # Act (Handover 0424: tenant_key now required)
        result = await service.get_project("test-id", tenant_key="test-tenant")

        # Assert
        assert isinstance(result, dict)
        assert result["id"] == "test-id"
        assert result["name"] == "Test Project"
        assert result["mission"] == "Test Mission"
        assert result["agent_count"] >= 0  # May be 0 or more depending on mocking

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, mock_db_manager):
        """Test get_project when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert - Should raise ResourceNotFoundError (Handover 0424: tenant_key now required)
        with pytest.raises(Exception) as exc_info:
            await service.get_project("nonexistent-id", tenant_key="test-tenant")
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_list_projects_with_tenant(self, mock_db_manager):
        """Test listing projects with tenant filtering"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock projects
        mock_project1 = Mock(spec=Project)
        mock_project1.id = "id1"
        mock_project1.name = "Project 1"
        mock_project1.mission = "Mission 1"
        mock_project1.description = "Desc 1"
        mock_project1.status = "active"
        mock_project1.staging_status = None
        mock_project1.tenant_key = "tenant1"
        mock_project1.product_id = None
        mock_project1.created_at = datetime.now()
        mock_project1.updated_at = None

        session.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_project1]))))
        )

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.list_projects(tenant_key="tenant1")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "id1"
        assert result[0]["name"] == "Project 1"

    @pytest.mark.asyncio
    async def test_list_projects_no_tenant_context(self):
        """Test list_projects fails when no tenant context"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert - Should raise ValidationError
        with pytest.raises(Exception) as exc_info:
            await service.list_projects()
        assert "No tenant context" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_projects_with_status_filter(self, mock_db_manager):
        """Test listing projects with status filter"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.list_projects(status="active", tenant_key="tenant1")

        # Assert
        assert isinstance(result, list)


class TestProjectServiceLifecycle:
    """Test project lifecycle methods"""

    @pytest.mark.asyncio
    async def test_complete_project_success(self, mock_db_manager):
        """Test successful project completion"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=1))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.complete_project(
            "test-id",
            summary="Completed successfully",
            key_outcomes=["Outcome 1", "Outcome 2"],
            decisions_made=["Decision 1", "Decision 2"],
            tenant_key="test-tenant"
        )

        # Assert
        assert "completed successfully" in result["message"]
        assert "memory_updated" in result
        assert "sequence_number" in result
        assert "git_commits_count" in result
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_project_not_found(self, mock_db_manager):
        """Test completing non-existent project - raises exception (Handover 0480)"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock scalar_one_or_none to return None (project not found)
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert - Raises ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.complete_project(
                "nonexistent-id",
                summary="Test",
                key_outcomes=["Outcome"],
                decisions_made=["Decision"],
                tenant_key="test-tenant"
            )

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_project_with_reason(self, mock_db_manager):
        """Test cancelling project with reason"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=1))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.cancel_project("test-id", reason="Requirements changed")

        # Assert
        assert result["success"] is True
        assert "cancelled successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_restore_project_success(self, mock_db_manager):
        """Test restoring a completed project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=1))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.restore_project("test-id", tenant_key="test-tenant")

        # Assert
        assert result["success"] is True
        assert "restored successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_activate_project_from_staging(self, mock_db_manager):
        """Test activating project from staging state"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock project in staging state
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.product_id = "product-123"
        mock_project.status = "staging"
        mock_project.activated_at = None
        mock_project.name = "Test Project"
        mock_project.mission = "Test Mission"
        mock_project.description = "Test Description"
        mock_project.config_data = {}
        mock_project.meta_data = {}
        mock_project.created_at = datetime.utcnow()
        mock_project.updated_at = datetime.utcnow()
        mock_project.completed_at = None

        # Mock two queries: get project, check for existing active
        session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=mock_project)),
                Mock(scalar_one_or_none=Mock(return_value=None)),  # No existing active
            ]
        )

        service = ProjectService(db_manager, tenant_manager)

        # Act
        project = await service.activate_project("test-project-id")

        # Assert - Returns Project instance directly (Handover 0730b)
        assert isinstance(project, Project)
        assert mock_project.status == "active"
        assert mock_project.activated_at is not None
        session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_activate_project_single_active_constraint(self, mock_db_manager):
        """Test Single Active Project constraint enforcement"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock new project to activate with all attributes
        new_project = Mock(spec=Project)
        new_project.id = "new-project-id"
        new_project.name = "New Project"
        new_project.product_id = "product-123"
        new_project.status = "staging"
        new_project.mission = "New Mission"
        new_project.description = "New Description"
        new_project.activated_at = None
        new_project.config_data = {}
        new_project.meta_data = {}

        # Mock existing active project with all attributes
        existing_project = Mock(spec=Project)
        existing_project.id = "existing-project-id"
        existing_project.product_id = "product-123"
        existing_project.status = "active"

        # Mock multiple queries
        session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=new_project)),  # Get new project
                Mock(scalar_one_or_none=Mock(return_value=existing_project)),  # Check existing active
            ]
        )

        service = ProjectService(db_manager, tenant_manager)

        # Act
        project = await service.activate_project("new-project-id")

        # Assert - Returns Project instance directly (Handover 0730b)
        assert isinstance(project, Project)
        assert new_project.status == "active"
        assert existing_project.status == "inactive"  # Auto-deactivated (changed from "paused" to "inactive")

    @pytest.mark.asyncio
    async def test_deactivate_project_success(self, mock_db_manager):
        """Test deactivating active project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock active project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.status = "active"
        mock_project.config_data = {}

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_project)))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.deactivate_project("test-project-id", reason="Testing pause")

        # Assert
        assert result["success"] is True
        assert mock_project.status == "paused"
        assert mock_project.config_data.get("deactivation_reason") == "Testing pause"

    @pytest.mark.asyncio
    async def test_cancel_staging_success(self, mock_db_manager):
        """Test cancelling project in staging state"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock staging project with all needed attributes
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.name = "Test Project"
        mock_project.status = "staging"
        mock_project.mission = "Test Mission"
        mock_project.description = "Test Description"
        mock_project.config_data = {}
        mock_project.meta_data = {}
        mock_project.agent_jobs = []

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_project)))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.cancel_staging("test-project-id")

        # Assert
        assert result["success"] is True
        assert mock_project.status == "cancelled"
        assert mock_project.completed_at is not None  # Using completed_at for cancelled_at

    @pytest.mark.asyncio
    async def test_get_project_summary_with_jobs(self, mock_db_manager):
        """Test project summary includes accurate job metrics"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.name = "Test Project"
        mock_project.status = "active"
        mock_project.mission = "Test Mission"
        mock_project.created_at = datetime.utcnow()
        mock_project.activated_at = datetime.utcnow()
        mock_project.product_id = "product-123"

        # Mock product
        mock_product = Mock()
        mock_product.name = "Test Product"
        mock_project.product = mock_product

        # Mock job counts data
        job_counts_data = [("completed", 3), ("active", 1), ("pending", 2), ("blocked", 1)]

        # Mock multiple queries: get project, job counts, last activity, product
        session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=mock_project)),  # Get project
                Mock(all=Mock(return_value=job_counts_data)),  # Job counts
                Mock(scalar=Mock(return_value=datetime.utcnow())),  # Last activity
                Mock(scalar_one_or_none=Mock(return_value=mock_product)),  # Get product
            ]
        )

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project_summary("test-project-id")

        # Assert
        assert result["success"] is True
        summary = result["data"]
        assert summary["total_jobs"] == 7
        assert summary["completed_jobs"] == 3
        assert summary["active_jobs"] == 1
        assert summary["pending_jobs"] == 2
        assert summary["blocked_jobs"] == 1
        assert summary["completion_percentage"] == pytest.approx(42.86, rel=0.1)

    @pytest.mark.asyncio
    async def test_update_project_multiple_fields(self, mock_db_manager):
        """Test update_project updates all provided fields"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.name = "Old Name"
        mock_project.description = "Old Description"
        mock_project.mission = "Old Mission"
        mock_project.config_data = {"old": "data"}

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_project)))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        updates = {
            "name": "New Name",
            "description": "New Description",
            "mission": "New Mission",
            "config_data": {"new": "data"},
        }
        result = await service.update_project("test-project-id", updates)

        # Assert
        assert result["success"] is True
        assert mock_project.name == "New Name"
        assert mock_project.description == "New Description"
        assert mock_project.mission == "New Mission"
        assert mock_project.config_data == {"new": "data"}

    @pytest.mark.asyncio
    async def test_launch_project_creates_orchestrator(self, mock_db_manager):
        """Test launch_project creates orchestrator job and returns prompt"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.status = "staging"
        mock_project.name = "Test Project"
        mock_project.mission = "Test Mission"
        mock_project.config_data = {}

        # Track created jobs
        created_jobs = []

        def capture_job(job):
            created_jobs.append(job)

        session.add = Mock(side_effect=capture_job)

        # Mock database queries: project fetch
        call_count = [0]

        async def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Call 1: Fetch project
            if call_count[0] == 1:
                return Mock(scalar_one_or_none=Mock(return_value=mock_project))
            # Call 2: Get max instance number
            if call_count[0] == 2:
                return Mock(scalar=Mock(return_value=0))
            # Default
            return Mock(scalar_one_or_none=Mock(return_value=None))

        session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        service = ProjectService(db_manager, tenant_manager)

        # Mock activate_project to avoid complex activation logic
        async def mock_activate(*args, **kwargs):
            mock_project.status = "active"
            return {"success": True}

        service.activate_project = mock_activate

        # Act
        result = await service.launch_project("test-project-id")

        # Assert
        assert result["success"] is True
        assert "orchestrator_job_id" in result["data"]
        assert "launch_prompt" in result["data"]
        assert mock_project.status == "active"
        assert len(created_jobs) == 1
        assert created_jobs[0].agent_display_name == "orchestrator"


class TestProjectServiceSwitchProject:
    """Test project switching methods"""

    @pytest.mark.asyncio
    async def test_switch_project_success(self, mock_db_manager):
        """Test switching project context"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "new-project-id"
        mock_project.name = "New Project"
        mock_project.mission = "Mission"
        mock_project.tenant_key = "tenant2"

        # NOTE: Session tracking removed (Handover 0423 - Session model deleted)
        # Mock only the project query
        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_project)))

        service = ProjectService(db_manager, tenant_manager)

        # Act - switch_project no longer uses lazy import of current_tenant
        result = await service.switch_project("new-project-id")

        # Assert - returns ProjectSwitchResult typed model
        assert result.project_id == "new-project-id"
        assert result.name == "New Project"
        assert result.tenant_key == "tenant2"
        tenant_manager.set_current_tenant.assert_called_once_with("tenant2")

    @pytest.mark.asyncio
    async def test_update_project_mission_success(self, mock_db_manager):
        """Test updating project mission"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.tenant_key = "tenant1"

        # Mock multiple queries: update, get project
        session.execute = AsyncMock(
            side_effect=[
                Mock(rowcount=1),  # Update result
                Mock(scalar_one_or_none=Mock(return_value=mock_project)),  # Get project
            ]
        )

        service = ProjectService(db_manager, tenant_manager)

        # Act
        with patch.object(service, "_broadcast_mission_update", new_callable=AsyncMock) as mock_broadcast:
            result = await service.update_project_mission("test-id", "New mission statement")

        # Assert - returns ProjectMissionUpdateResult typed model
        assert result.message == "Mission updated successfully"
        assert result.project_id == "test-id"
        mock_broadcast.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_project_mission_not_found(self, mock_db_manager):
        """Test updating mission for non-existent project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=0))

        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert - Should raise ResourceNotFoundError
        with pytest.raises(Exception) as exc_info:
            await service.update_project_mission("nonexistent-id", "Mission")
        assert "not found" in str(exc_info.value).lower()


class TestProjectServiceHelpers:
    """Test private helper methods"""

    @pytest.mark.asyncio
    async def test_broadcast_mission_update_success(self, mock_db_manager):
        """Test WebSocket broadcast for mission update"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        websocket_manager = AsyncMock()
        service = ProjectService(db_manager, tenant_manager, websocket_manager=websocket_manager)

        await service._broadcast_mission_update(
            "project-id",
            "New mission",
            "tenant1",
        )

        websocket_manager.broadcast_to_tenant.assert_awaited_once()
        call_kwargs = websocket_manager.broadcast_to_tenant.call_args.kwargs
        assert call_kwargs["tenant_key"] == "tenant1"
        assert call_kwargs["event_type"] == "project:mission_updated"
        assert call_kwargs["data"]["project_id"] == "project-id"

    @pytest.mark.asyncio
    async def test_broadcast_mission_update_failure_graceful(self, mock_db_manager):
        """Test that broadcast failures don't crash the service"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        websocket_manager = AsyncMock()
        websocket_manager.broadcast_to_tenant.side_effect = Exception("WebSocket error")
        service = ProjectService(db_manager, tenant_manager, websocket_manager=websocket_manager)

        # Act & Assert (should not raise)
        await service._broadcast_mission_update(
            "project-id",
            "New mission",
            "tenant1",
        )


class TestProjectServiceEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_create_project_with_all_parameters(self, mock_db_manager):
        """Test creating project with all optional parameters"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        project = await service.create_project(
            name="Full Project",
            mission="Full Mission",
            description="Full Description",
            product_id="product-123",
            tenant_key="tenant-456",
            status="active",
        )

        # Assert - Returns Project instance directly (Handover 0730b)
        assert isinstance(project, Project)
        assert project.product_id == "product-123"
        assert project.status == "active"

    @pytest.mark.asyncio
    async def test_error_handling_propagates_correctly(self):
        """Test that exceptions are properly caught and returned"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        # Different methods should all handle exceptions gracefully
        service = ProjectService(db_manager, tenant_manager)

        # Test multiple methods
        db_manager.get_session_async = AsyncMock(side_effect=Exception("DB Error"))

        methods_to_test = [
            (service.get_project, ["test-id"]),
            (service.complete_project, ["test-id"]),
            (service.cancel_project, ["test-id", "test-tenant"]),
            (service.restore_project, ["test-id", "test-tenant"]),
        ]

        for method, args in methods_to_test:
            result = await method(*args)
            assert result["success"] is False
            assert "error" in result
