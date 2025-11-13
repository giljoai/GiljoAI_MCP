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


class TestProjectServiceCRUD:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_project_success(self):
        """Test successful project creation"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock project with ID
        created_project = Mock()
        created_project.id = "test-project-id"
        session.add = Mock()
        session.commit = AsyncMock()

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
    async def test_create_project_auto_generates_tenant_key(self):
        """Test that tenant_key is auto-generated if not provided"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        created_project = Mock()
        created_project.id = "test-id"
        session.add = Mock()
        session.commit = AsyncMock()

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
    async def test_create_project_error_handling(self):
        """Test error handling in create_project"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        db_manager.get_session_async = AsyncMock(
            side_effect=Exception("Database error")
        )

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
    async def test_get_project_success(self):
        """Test successful project retrieval"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        # Mock query result
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_project)
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project("test-id")

        # Assert
        assert result["success"] is True
        assert result["project"]["id"] == "test-id"
        assert result["project"]["name"] == "Test Project"
        assert result["project"]["mission"] == "Test Mission"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self):
        """Test get_project when project doesn't exist"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project("nonexistent-id")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_list_projects_with_tenant(self):
        """Test listing projects with tenant filtering"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_tenant_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_project1])))
        session.execute = AsyncMock(return_value=mock_result)

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
    async def test_list_projects_with_status_filter(self):
        """Test listing projects with status filter"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_tenant_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.list_projects(status="active", tenant_key="tenant1")

        # Assert
        assert result["success"] is True
        assert isinstance(result["projects"], list)


class TestProjectServiceLifecycle:
    """Test project lifecycle methods"""

    @pytest.mark.asyncio
    async def test_complete_project_success(self):
        """Test successful project completion"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        mock_result = Mock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

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
    async def test_complete_project_not_found(self):
        """Test completing non-existent project"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        mock_result = Mock()
        mock_result.rowcount = 0
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.complete_project("nonexistent-id")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_cancel_project_with_reason(self):
        """Test cancelling project with reason"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        mock_result = Mock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

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
    async def test_restore_project_success(self):
        """Test restoring a completed project"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        mock_result = Mock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.restore_project("test-id")

        # Assert
        assert result["success"] is True
        assert "restored successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_activate_project_from_staging(self):
        """Test activating project from staging state"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        # Mock query for existing project
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        session.execute = AsyncMock(return_value=mock_result)
        
        # Mock query for checking existing active project
        mock_active_check = AsyncMock()
        mock_active_check.scalar_one_or_none.return_value = None  # No existing active project
        
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.activate_project("test-project-id")

        # Assert
        assert result["success"] is True
        assert mock_project.status == "active"
        assert mock_project.activated_at is not None
        session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_activate_project_single_active_constraint(self):
        """Test Single Active Project constraint enforcement"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock new project to activate
        new_project = Mock(spec=Project)
        new_project.id = "new-project-id"
        new_project.product_id = "product-123"
        new_project.status = "staging"
        new_project.activated_at = None

        # Mock existing active project
        existing_project = Mock(spec=Project)
        existing_project.id = "existing-project-id"
        existing_project.product_id = "product-123"
        existing_project.status = "active"

        # Setup execute mock to return different projects based on query
        execute_call_count = [0]
        
        async def execute_side_effect(*args, **kwargs):
            execute_call_count[0] += 1
            mock_result = AsyncMock()
            if execute_call_count[0] == 1:  # First call: get new project
                mock_result.scalar_one_or_none.return_value = new_project
            elif execute_call_count[0] == 2:  # Second call: check for existing active
                mock_result.scalar_one_or_none.return_value = existing_project
            else:  # Update queries
                mock_result.scalar_one_or_none.return_value = None
            return mock_result

        session.execute = AsyncMock(side_effect=execute_side_effect)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.activate_project("new-project-id")

        # Assert
        assert result["success"] is True
        assert new_project.status == "active"
        assert existing_project.status == "paused"  # Auto-deactivated

    @pytest.mark.asyncio
    async def test_deactivate_project_success(self):
        """Test deactivating active project"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock active project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.status = "active"
        mock_project.config_data = {}

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

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
    async def test_cancel_staging_success(self):
        """Test cancelling project in staging state"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock staging project with pending jobs
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.status = "staging"
        mock_project.agent_jobs = []

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.cancel_staging("test-project-id")

        # Assert
        assert result["success"] is True
        assert mock_project.status == "cancelled"
        assert mock_project.completed_at is not None  # Using completed_at for cancelled_at

    @pytest.mark.asyncio
    async def test_get_project_summary_with_jobs(self):
        """Test project summary includes accurate job metrics"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        # Mock job counts
        job_counts_data = [
            ("completed", 3),
            ("active", 1),
            ("pending", 2),
            ("failed", 1)
        ]
        
        mock_job_counts = Mock()
        mock_job_counts.all.return_value = job_counts_data

        # Mock last activity
        mock_last_activity = Mock()
        mock_last_activity.scalar.return_value = datetime.utcnow()

        execute_call_count = [0]
        
        async def execute_side_effect(*args, **kwargs):
            execute_call_count[0] += 1
            if execute_call_count[0] == 1:  # Get project
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = mock_project
                return mock_result
            elif execute_call_count[0] == 2:  # Job counts
                return mock_job_counts
            else:  # Last activity
                return mock_last_activity

        session.execute = AsyncMock(side_effect=execute_side_effect)

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
    async def test_update_project_multiple_fields(self):
        """Test update_project updates all provided fields"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.name = "Old Name"
        mock_project.description = "Old Description"
        mock_project.mission = "Old Mission"
        mock_project.config_data = {"old": "data"}

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

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
    async def test_launch_project_creates_orchestrator(self):
        """Test launch_project creates orchestrator job and returns prompt"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant.return_value = "test-tenant"
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "test-project-id"
        mock_project.status = "staging"
        mock_project.name = "Test Project"
        mock_project.mission = "Test Mission"

        # Mock orchestrator job
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.id = "orchestrator-job-123"
        mock_job.status = "pending"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        session.execute = AsyncMock(return_value=mock_result)
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProjectService(db_manager, tenant_manager)

        # Mock AgentJobManager
        with patch('giljo_mcp.services.project_service.AgentJobManager') as mock_ajm:
            mock_job_manager = AsyncMock()
            mock_job_manager.create_job.return_value = mock_job
            mock_ajm.return_value = mock_job_manager

            # Act
            result = await service.launch_project("test-project-id")

            # Assert
            assert result["success"] is True
            assert result["data"]["orchestrator_job_id"] == "orchestrator-job-123"
            assert "launch_prompt" in result["data"]
            assert mock_project.status == "active"


class TestProjectServiceStatus:
    """Test status and metrics methods"""

    @pytest.mark.asyncio
    async def test_get_project_status_with_agents(self):
        """Test getting comprehensive project status"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        # Setup execute calls
        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        agent_result = Mock()
        agent_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_agent])))

        message_result = Mock()
        message_result.scalars = Mock(return_value=Mock(all=Mock(return_value=mock_messages)))

        session.execute = AsyncMock(side_effect=[
            project_result,
            agent_result,
            message_result
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
    async def test_get_project_status_no_project_id(self):
        """Test getting status without project_id finds active project"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        agent_result = Mock()
        agent_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        message_result = Mock()
        message_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        session.execute = AsyncMock(side_effect=[
            project_result,
            agent_result,
            message_result
        ])

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.get_project_status()

        # Assert
        assert result["success"] is True
        assert result["project"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_switch_project_success(self):
        """Test switching project context"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

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

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        session_result = Mock()
        session_result.scalar_one_or_none = Mock(return_value=mock_session)

        session.execute = AsyncMock(side_effect=[
            project_result,
            session_result
        ])
        session.add = Mock()
        session.commit = AsyncMock()

        service = ProjectService(db_manager, tenant_manager)

        # Act
        with patch('giljo_mcp.services.project_service.current_tenant') as mock_current_tenant:
            result = await service.switch_project("new-project-id")

        # Assert
        assert result["success"] is True
        assert result["project_id"] == "new-project-id"
        assert result["name"] == "New Project"
        assert result["tenant_key"] == "tenant2"
        tenant_manager.set_current_tenant.assert_called_once_with("tenant2")

    @pytest.mark.asyncio
    async def test_update_project_mission_success(self):
        """Test updating project mission"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock update result
        update_result = Mock()
        update_result.rowcount = 1

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.tenant_key = "tenant1"

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        session.execute = AsyncMock(side_effect=[update_result, project_result])
        session.commit = AsyncMock()

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
    async def test_update_project_mission_not_found(self):
        """Test updating mission for non-existent project"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        update_result = Mock()
        update_result.rowcount = 0

        session.execute = AsyncMock(return_value=update_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.update_project_mission("nonexistent-id", "Mission")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]


class TestProjectServiceHelpers:
    """Test private helper methods"""

    @pytest.mark.asyncio
    async def test_broadcast_mission_update_success(self):
        """Test WebSocket broadcast for mission update"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert
        with patch('giljo_mcp.services.project_service.httpx.AsyncClient') as mock_client:
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
    async def test_broadcast_mission_update_failure_graceful(self):
        """Test that broadcast failures don't crash the service"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ProjectService(db_manager, tenant_manager)

        # Act & Assert (should not raise)
        with patch('giljo_mcp.services.project_service.httpx.AsyncClient') as mock_client:
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
    async def test_create_project_with_all_parameters(self):
        """Test creating project with all optional parameters"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        created_project = Mock()
        created_project.id = "test-id"
        session.add = Mock()
        session.commit = AsyncMock()

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
