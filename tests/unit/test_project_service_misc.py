"""
Unit tests for ProjectService miscellaneous operations.

Split from test_project_service.py for maintainability.
Tests cover: project switching, mission updates, helper methods, edge cases.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.exceptions import BaseGiljoError
from src.giljo_mcp.models import Project
from src.giljo_mcp.services.project_service import ProjectService


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
