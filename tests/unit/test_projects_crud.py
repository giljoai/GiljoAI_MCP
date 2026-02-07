"""
Unit tests for projects CRUD endpoints - Handover 0125

Tests create, list, get, and update endpoints using ProjectService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.endpoints.projects import crud
from api.endpoints.projects.models import ProjectCreate, ProjectResponse, ProjectUpdate


class TestCreateProject:
    """Tests for create_project endpoint."""

    @pytest.mark.asyncio
    async def test_create_project_success(self):
        """Test successful project creation."""
        # Mock dependencies
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.create_project.return_value = {
            "success": True,
            "project_id": "proj-123",
            "name": "Test Project",
            "alias": "test-proj",
            "status": "inactive",
            "mission": "Test mission",
            "description": "Test description",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        request = ProjectCreate(
            name="Test Project", mission="Test mission", description="Test description", status="inactive"
        )

        # Call endpoint
        response = await crud.create_project(project=request, current_user=mock_user, project_service=mock_service)

        # Assertions
        assert isinstance(response, ProjectResponse)
        assert response.id == "proj-123"
        assert response.name == "Test Project"
        mock_service.create_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_project_service_error(self):
        """Test project creation with service error."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.create_project.return_value = {"success": False, "error": "Failed to create project"}

        request = ProjectCreate(name="Test Project", mission="Test mission")

        # Should raise 400
        with pytest.raises(HTTPException) as exc_info:
            await crud.create_project(project=request, current_user=mock_user, project_service=mock_service)

        assert exc_info.value.status_code == 400


class TestListProjects:
    """Tests for list_projects endpoint."""

    @pytest.mark.asyncio
    async def test_list_projects_success(self):
        """Test successful project listing."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.list_projects.return_value = {
            "success": True,
            "projects": [
                {
                    "id": "proj-1",
                    "alias": "proj-1",
                    "name": "Project 1",
                    "status": "active",
                    "mission": "Mission 1",
                    "description": "Desc 1",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "context_budget": 150000,
                    "context_used": 0,
                    "agent_count": 0,
                    "message_count": 0,
                }
            ],
        }

        response = await crud.list_projects(status_filter=None, current_user=mock_user, project_service=mock_service)

        assert len(response) == 1
        assert response[0].id == "proj-1"
        mock_service.list_projects.assert_called_once()


class TestGetProject:
    """Tests for get_project endpoint."""

    @pytest.mark.asyncio
    async def test_get_project_success(self):
        """Test successful project retrieval."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.get_project.return_value = {
            "success": True,
            "project": {
                "id": "proj-123",
                "alias": "proj-123",
                "name": "Test Project",
                "status": "active",
                "mission": "Test mission",
                "description": "Test desc",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "context_budget": 150000,
                "context_used": 0,
                "agent_count": 0,
                "message_count": 0,
            },
        }

        response = await crud.get_project(project_id="proj-123", current_user=mock_user, project_service=mock_service)

        assert response.id == "proj-123"
        assert response.name == "Test Project"
        mock_service.get_project.assert_called_once_with(project_id="proj-123")

    @pytest.mark.asyncio
    async def test_get_project_not_found(self):
        """Test get project when not found."""
        mock_user = MagicMock()
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.get_project.return_value = {"success": False, "error": "Project not found"}

        with pytest.raises(HTTPException) as exc_info:
            await crud.get_project(project_id="proj-123", current_user=mock_user, project_service=mock_service)

        assert exc_info.value.status_code == 404


class TestUpdateProject:
    """Tests for update_project endpoint."""

    @pytest.mark.asyncio
    async def test_update_project_mission(self):
        """Test updating project mission."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.update_project_mission.return_value = {"success": True}
        mock_service.get_project.return_value = {
            "success": True,
            "project": {
                "id": "proj-123",
                "alias": "proj-123",
                "name": "Test Project",
                "status": "active",
                "mission": "Updated mission",
                "description": "Test desc",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "context_budget": 150000,
                "context_used": 0,
                "agent_count": 0,
                "message_count": 0,
            },
        }

        updates = ProjectUpdate(mission="Updated mission")

        response = await crud.update_project(
            project_id="proj-123", updates=updates, current_user=mock_user, project_service=mock_service
        )

        assert response.mission == "Updated mission"
        mock_service.update_project_mission.assert_called_once()
