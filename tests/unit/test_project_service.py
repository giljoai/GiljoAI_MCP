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
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from uuid import uuid4

from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.models import Project, MCPAgentJob, Message


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
        result = await service.create_project(
            name="Test Project",
            mission="Test mission",
            description="Test description",
            tenant_key="test-tenant"
        )

        # Assert
        assert result["success"] is True
        assert "project_id" in result
        assert result["name"] == "Test Project"
        assert result["tenant_key"] == "test-tenant"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_project_auto_generates_tenant_key(self, mock_db_manager):
        """Test that tenant_key is auto-generated if not provided"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.create_project(
            name="Test",
            mission="Mission"
        )

        # Assert
        assert result["success"] is True
        assert result["tenant_key"].startswith("tk_")

    @pytest.mark.asyncio
    async def test_create_project_error_handling(self, mock_db_manager):
        """Test error handling in create_project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Override to throw error
        db_manager.get_session_async = Mock(side_effect=Exception("Database error"))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.create_project(
            name="Test",
            mission="Mission"
        )

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_project_success(self, mock_db_manager):
        """Test successful project retrieval"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-id"
        mock_project.name = "Test Project"
        mock_project.mission = "Test Mission"
        mock_project.description = "Test Description"
        mock_project.status = "active"
        mock_project.staging_status = None
        mock_project.product_id = None
        mock_project.tenant_key = "test-tenant"
        mock_project.context_budget = 150000
        mock_project.context_used = 0
        mock_project.created_at = datetime.now()
        mock_project.updated_at = None
        mock_project.completed_at = None

        # Mock agent
        mock_agent = Mock(spec=MCPAgentJob)
        mock_agent.job_id = "agent-1"
        mock_agent.agent_type = "implementer"
        mock_agent.agent_name = "Test Agent"
        mock_agent.status = "active"

        # Mock two queries: get project, get agents
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),  # Get project
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_agent]))))  # Get agents
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project("test-id")

        # Assert
        assert result["success"] is True
        assert result["project"]["id"] == "test-id"
        assert result["project"]["name"] == "Test Project"
        assert result["project"]["mission"] == "Test Mission"
        assert result["project"]["agent_count"] == 1

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, mock_db_manager):
        """Test get_project when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project("nonexistent-id")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]

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
        mock_project1.context_budget = 150000
        mock_project1.context_used = 1000
        mock_project1.created_at = datetime.now()
        mock_project1.updated_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_project1])))
        ))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.list_projects(tenant_key="tenant1")

        # Assert
        assert result["success"] is True
        assert len(result["projects"]) == 1
        assert result["projects"][0]["id"] == "id1"
        assert result["projects"][0]["name"] == "Project 1"

    @pytest.mark.asyncio
    async def test_list_projects_no_tenant_context(self):
        """Test list_projects fails when no tenant context"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.list_projects()

        # Assert
        assert result["success"] is False
        assert "No tenant context" in result["error"]

    @pytest.mark.asyncio
    async def test_list_projects_with_status_filter(self, mock_db_manager):
        """Test listing projects with status filter"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[])))
        ))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.list_projects(status="active", tenant_key="tenant1")

        # Assert
        assert result["success"] is True
        assert isinstance(result["projects"], list)


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
            summary="Completed successfully"
        )

        # Assert
        assert result["success"] is True
        assert "completed successfully" in result["message"]
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_project_not_found(self, mock_db_manager):
        """Test completing non-existent project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=0))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.complete_project("nonexistent-id")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_cancel_project_with_reason(self, mock_db_manager):
        """Test cancelling project with reason"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=1))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.cancel_project(
            "test-id",
            reason="Requirements changed"
        )

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
        result = await service.restore_project("test-id")

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
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            Mock(scalar_one_or_none=Mock(return_value=None))  # No existing active
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.activate_project("test-project-id")

        # Assert
        assert result["success"] is True
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
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=new_project)),  # Get new project
            Mock(scalar_one_or_none=Mock(return_value=existing_project))  # Check existing active
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.activate_project("new-project-id")

        # Assert
        assert result["success"] is True
        assert new_project.status == "active"
        assert existing_project.status == "paused"  # Auto-deactivated

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

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=mock_project)
        ))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.deactivate_project(
            "test-project-id",
            reason="Testing pause"
        )

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

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=mock_project)
        ))

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
        job_counts_data = [
            ("completed", 3),
            ("active", 1),
            ("pending", 2),
            ("failed", 1)
        ]

        # Mock multiple queries: get project, job counts, last activity, product
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),  # Get project
            Mock(all=Mock(return_value=job_counts_data)),  # Job counts
            Mock(scalar=Mock(return_value=datetime.utcnow())),  # Last activity
            Mock(scalar_one_or_none=Mock(return_value=mock_product))  # Get product
        ])

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
        assert summary["failed_jobs"] == 1
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

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=mock_project)
        ))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        updates = {
            "name": "New Name",
            "description": "New Description",
            "mission": "New Mission",
            "config_data": {"new": "data"}
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
        mock_project.context_budget = 150000

        # Track created jobs
        created_jobs = []
        def capture_job(job):
            created_jobs.append(job)

        session.add = Mock(side_effect=capture_job)

        # Mock database queries: project fetch, instance_number query
        call_count = [0]
        async def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Call 1: Fetch project
            if call_count[0] == 1:
                return Mock(scalar_one_or_none=Mock(return_value=mock_project))
            # Call 2: Get max instance number
            elif call_count[0] == 2:
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
        assert created_jobs[0].agent_type == "orchestrator"


class TestProjectServiceStatus:
    """Test status and metrics methods"""

    @pytest.mark.asyncio
    async def test_get_project_status_with_agents(self, mock_db_manager):
        """Test getting comprehensive project status"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-id"
        mock_project.name = "Test Project"
        mock_project.mission = "Mission"
        mock_project.status = "active"
        mock_project.staging_status = None
        mock_project.tenant_key = "tenant1"
        mock_project.product_id = None
        mock_project.context_budget = 150000
        mock_project.context_used = 5000
        mock_project.created_at = datetime.now()
        mock_project.completed_at = None

        # Mock agent job
        mock_agent = Mock(spec=MCPAgentJob)
        mock_agent.agent_type = "implementer"
        mock_agent.status = "active"

        # Mock message count
        mock_messages = [Mock(), Mock()]

        # Mock multiple queries: project, agents, messages
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_agent])))),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=mock_messages))))
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project_status("test-id")

        # Assert
        assert result["success"] is True
        assert result["project"]["id"] == "test-id"
        assert result["project"]["name"] == "Test Project"
        assert len(result["agents"]) == 1
        assert result["agents"][0]["name"] == "implementer"
        assert result["pending_messages"] == 2

    @pytest.mark.asyncio
    async def test_get_project_status_no_project_id(self, mock_db_manager):
        """Test getting status without project_id finds active project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        mock_project = Mock(spec=Project)
        mock_project.id = "active-id"
        mock_project.name = "Active Project"
        mock_project.mission = "Mission"
        mock_project.status = "active"
        mock_project.staging_status = None
        mock_project.tenant_key = "tenant1"
        mock_project.product_id = None
        mock_project.context_budget = 150000
        mock_project.context_used = 0
        mock_project.created_at = datetime.now()
        mock_project.completed_at = None

        # Mock multiple queries: project, agents, messages
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project_status()

        # Assert
        assert result["success"] is True
        assert result["project"]["status"] == "active"

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
        mock_project.context_used = 1000
        mock_project.context_budget = 150000

        # Mock session
        from giljo_mcp.models import Session as SessionModel
        mock_session = Mock(spec=SessionModel)
        mock_session.id = "session-id"

        # Mock multiple queries: project, session
        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            Mock(scalar_one_or_none=Mock(return_value=mock_session))
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        with patch('giljo_mcp.tenant.current_tenant') as mock_current_tenant:
            result = await service.switch_project("new-project-id")

        # Assert
        assert result["success"] is True
        assert result["project_id"] == "new-project-id"
        assert result["name"] == "New Project"
        assert result["tenant_key"] == "tenant2"
        tenant_manager.set_current_tenant.assert_called_once_with("tenant2")
        mock_current_tenant.set.assert_called_once_with("tenant2")

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
        session.execute = AsyncMock(side_effect=[
            Mock(rowcount=1),  # Update result
            Mock(scalar_one_or_none=Mock(return_value=mock_project))  # Get project
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        with patch.object(service, '_broadcast_mission_update', new_callable=AsyncMock) as mock_broadcast:
            result = await service.update_project_mission(
                "test-id",
                "New mission statement"
            )

        # Assert
        assert result["success"] is True
        assert "Mission updated" in result["message"]
        mock_broadcast.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_project_mission_not_found(self, mock_db_manager):
        """Test updating mission for non-existent project"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute = AsyncMock(return_value=Mock(rowcount=0))

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.update_project_mission("nonexistent-id", "Mission")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]


class TestProjectServiceHelpers:
    """Test private helper methods"""

    @pytest.mark.asyncio
    async def test_broadcast_mission_update_success(self, mock_db_manager):
        """Test WebSocket broadcast for mission update"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_client_instance

            await service._broadcast_mission_update(
                "project-id",
                "New mission",
                "tenant1"
            )

            # Verify post was called
            mock_client_instance.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_mission_update_failure_graceful(self, mock_db_manager):
        """Test that broadcast failures don't crash the service"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert (should not raise)
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.side_effect = Exception("Network error")

            # This should log error but not raise
            await service._broadcast_mission_update(
                "project-id",
                "New mission",
                "tenant1"
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
        result = await service.create_project(
            name="Full Project",
            mission="Full Mission",
            description="Full Description",
            product_id="product-123",
            tenant_key="tenant-456",
            status="active",
            context_budget=200000
        )

        # Assert
        assert result["success"] is True
        assert result["product_id"] == "product-123"
        assert result["status"] == "active"

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
            (service.cancel_project, ["test-id"]),
            (service.restore_project, ["test-id"]),
        ]

        for method, args in methods_to_test:
            result = await method(*args)
            assert result["success"] is False
            assert "error" in result
