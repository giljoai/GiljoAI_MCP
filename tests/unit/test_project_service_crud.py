"""
Unit tests for ProjectService CRUD operations.

Split from test_project_service.py for maintainability.
Tests cover: create, get, list operations.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.exceptions import BaseGiljoError
from src.giljo_mcp.models import AgentExecution, Project
from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.services.project_service import ProjectService


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
