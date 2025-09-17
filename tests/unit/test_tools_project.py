"""
Unit tests for MCP Project Tools.
Tests project management tools including creation, listing, and status operations.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Note: project functions are now methods of ToolAccessor class
from src.giljo_mcp.enums import ProjectStatus
from tests.fixtures.base_fixtures import TestData
from tests.fixtures.base_test import BaseAsyncTest


class TestProjectTools(BaseAsyncTest):
    """Test suite for MCP Project Tools"""

    def setup_method(self, method):
        """Setup test method"""
        super().setup_method(method)
        self.tenant_key = TestData.generate_tenant_key()
        self.project_id = str(uuid.uuid4())

    # ==================== Create Project Tests ====================

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_create_project_success(self, mock_get_db):
        """Test successful project creation via MCP tool"""
        # Setup mock database
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Call tool
        result = await create_project(
            name="Test Project",
            mission="Build amazing features",
            tenant_key=self.tenant_key,
            project_type="development",
        )

        # Assertions
        assert result["success"] is True
        assert "project_id" in result
        assert result["name"] == "Test Project"
        assert result["mission"] == "Build amazing features"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_create_project_with_metadata(self, mock_get_db):
        """Test creating project with metadata"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        metadata = {"priority": "high", "team": "alpha", "deadline": "2024-12-31"}

        result = await create_project(
            name="Priority Project", mission="Critical mission", tenant_key=self.tenant_key, metadata=metadata
        )

        assert result["success"] is True
        # Check that metadata was passed to the project
        call_args = mock_session.add.call_args[0][0]
        assert call_args.metadata == metadata

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_create_project_duplicate_name(self, mock_get_db):
        """Test creating project with duplicate name"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        # Simulate duplicate key error
        mock_session.add = Mock()
        mock_session.commit = AsyncMock(side_effect=Exception("Unique constraint violated"))
        mock_session.rollback = AsyncMock()

        result = await create_project(name="Duplicate Project", mission="Test mission", tenant_key=self.tenant_key)

        assert result["success"] is False
        assert "error" in result
        mock_session.rollback.assert_called_once()

    # ==================== List Projects Tests ====================

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_list_projects_all(self, mock_get_db):
        """Test listing all projects for a tenant"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        # Create mock projects
        projects = [
            Mock(
                id=str(uuid.uuid4()),
                name="Project 1",
                status=ProjectStatus.ACTIVE.value,
                created_at="2024-01-01T00:00:00",
            ),
            Mock(
                id=str(uuid.uuid4()),
                name="Project 2",
                status=ProjectStatus.COMPLETED.value,
                created_at="2024-01-02T00:00:00",
            ),
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = projects
        mock_session.query.return_value = mock_query

        result = await list_projects(tenant_key=self.tenant_key)

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["projects"]) == 2
        mock_query.filter_by.assert_called_with(tenant_key=self.tenant_key)

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_list_projects_by_status(self, mock_get_db):
        """Test listing projects filtered by status"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        active_projects = [
            Mock(
                id=str(uuid.uuid4()),
                name="Active Project",
                status=ProjectStatus.ACTIVE.value,
                created_at="2024-01-01T00:00:00",
            )
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.order_by.return_value.all.return_value = active_projects
        mock_session.query.return_value = mock_query

        result = await list_projects(tenant_key=self.tenant_key, status="active")

        assert result["success"] is True
        assert result["count"] == 1
        assert result["projects"][0]["status"] == ProjectStatus.ACTIVE.value

    # ==================== Get Project Status Tests ====================

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_get_project_status_success(self, mock_get_db):
        """Test getting project status"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        # Create mock project with agents
        mock_project = Mock(
            id=self.project_id,
            name="Test Project",
            status=ProjectStatus.ACTIVE.value,
            mission="Test mission",
            metadata={"context_used": 50000, "context_budget": 150000},
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
        )

        mock_agents = [
            Mock(name="orchestrator", status="active"),
            Mock(name="analyzer", status="active"),
            Mock(name="implementer", status="handoff"),
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_query.filter_by.return_value.all.return_value = mock_agents
        mock_session.query.side_effect = [mock_query, mock_query]

        result = await get_project_status(project_id=self.project_id)

        assert result["success"] is True
        assert result["project"]["name"] == "Test Project"
        assert result["project"]["status"] == ProjectStatus.ACTIVE.value
        assert result["context"]["used"] == 50000
        assert result["context"]["remaining"] == 100000
        assert result["context"]["percentage"] == 33.33
        assert result["agents"]["total"] == 3
        assert result["agents"]["active"] == 2

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_get_project_status_not_found(self, mock_get_db):
        """Test getting status for non-existent project"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        result = await get_project_status(project_id="non_existent_id")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    # ==================== Update Project Tests ====================

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_update_project_mission(self, mock_get_db):
        """Test updating project mission"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_project = Mock(id=self.project_id, name="Test Project", mission="Old mission", metadata={})

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        new_mission = "Updated mission with new objectives"

        result = await update_project(project_id=self.project_id, mission=new_mission)

        assert result["success"] is True
        assert mock_project.mission == new_mission
        assert "mission_updated_at" in mock_project.metadata
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_update_project_metadata(self, mock_get_db):
        """Test updating project metadata"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_project = Mock(id=self.project_id, metadata={"existing": "data"})

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        new_metadata = {"priority": "high", "deadline": "2024-12-31"}

        result = await update_project(project_id=self.project_id, metadata=new_metadata)

        assert result["success"] is True
        assert "existing" in mock_project.metadata  # Preserves existing
        assert mock_project.metadata["priority"] == "high"
        assert mock_project.metadata["deadline"] == "2024-12-31"

    # ==================== Close Project Tests ====================

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_close_project_success(self, mock_get_db):
        """Test closing a project"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_project = Mock(id=self.project_id, name="Test Project", status=ProjectStatus.ACTIVE.value, metadata={})

        # Mock agents to deactivate
        mock_agents = [Mock(name="agent1", status="active"), Mock(name="agent2", status="active")]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_query.filter_by.return_value.all.return_value = mock_agents
        mock_session.query.side_effect = [mock_query, mock_query]
        mock_session.commit = AsyncMock()

        result = await close_project(project_id=self.project_id, summary="Project completed successfully")

        assert result["success"] is True
        assert mock_project.status == ProjectStatus.COMPLETED.value
        assert mock_project.metadata["completion_summary"] == "Project completed successfully"
        assert all(agent.status == "inactive" for agent in mock_agents)
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_close_already_closed_project(self, mock_get_db):
        """Test closing an already closed project"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_project = Mock(id=self.project_id, status=ProjectStatus.COMPLETED.value)

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query

        result = await close_project(project_id=self.project_id)

        assert result["success"] is False
        assert "already completed" in result["error"].lower()

    # ==================== Activate Project Tests ====================

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_activate_project_success(self, mock_get_db):
        """Test activating a paused project"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_project = Mock(id=self.project_id, name="Test Project", status=ProjectStatus.PAUSED.value, metadata={})

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await activate_project(project_id=self.project_id)

        assert result["success"] is True
        assert mock_project.status == ProjectStatus.ACTIVE.value
        assert "activated_at" in mock_project.metadata
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.giljo_mcp.tools.project.get_db_manager")
    async def test_activate_completed_project_fails(self, mock_get_db):
        """Test that completed projects cannot be activated"""
        mock_db_manager = Mock()
        mock_session = self.create_async_mock("session")
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_get_db.return_value = mock_db_manager

        mock_project = Mock(id=self.project_id, status=ProjectStatus.COMPLETED.value)

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query

        result = await activate_project(project_id=self.project_id)

        assert result["success"] is False
        assert "cannot activate" in result["error"].lower()
