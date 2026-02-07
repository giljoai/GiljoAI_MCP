"""
Unit tests for ProjectService - Deleted Project State Handling

BEHAVIOR TESTS (Not Implementation):
- Deleted projects cannot be activated
- Deleted projects cannot be deactivated
- Status transitions properly reject deleted projects

TDD RED Phase - These tests MUST FAIL initially
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.models import Project
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


class TestDeletedProjectStateHandling:
    """Test that deleted projects cannot undergo status transitions"""

    @pytest.mark.asyncio
    async def test_cannot_activate_deleted_project(self, mock_db_manager):
        """
        BEHAVIOR: Activating a deleted project MUST fail with clear error message

        This prevents UI bugs where deleted projects trigger 400 errors
        when users try to activate them from stale state.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock a deleted project
        deleted_project = Mock(spec=Project)
        deleted_project.id = "deleted-proj-123"
        deleted_project.status = "deleted"
        deleted_project.deleted_at = datetime.now(timezone.utc)
        deleted_project.tenant_key = "test-tenant"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=deleted_project)
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.activate_project("deleted-proj-123")

        # Assert - BEHAVIOR: Must fail with descriptive error
        assert result["success"] is False, "Should not allow activating deleted project"
        assert "deleted" in result["error"].lower(), "Error message must mention project is deleted"

    @pytest.mark.asyncio
    async def test_cannot_deactivate_deleted_project(self, mock_db_manager):
        """
        BEHAVIOR: Deactivating a deleted project MUST fail with clear error message

        Prevents 400 errors when UI tries to deactivate deleted projects.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock a deleted project
        deleted_project = Mock(spec=Project)
        deleted_project.id = "deleted-proj-456"
        deleted_project.status = "deleted"
        deleted_project.deleted_at = datetime.now(timezone.utc)
        deleted_project.tenant_key = "test-tenant"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=deleted_project)
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.deactivate_project("deleted-proj-456")

        # Assert - BEHAVIOR: Must fail with descriptive error
        assert result["success"] is False, "Should not allow deactivating deleted project"
        assert "deleted" in result["error"].lower(), "Error message must mention project is deleted"

    @pytest.mark.asyncio
    async def test_delete_project_sets_status_deleted(self, mock_db_manager):
        """
        BEHAVIOR: Deleting a project MUST set status='deleted'

        Ensures status field is properly updated for filtering.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock an active project
        active_project = Mock(spec=Project)
        active_project.id = "active-proj-789"
        active_project.status = "active"
        active_project.deleted_at = None
        active_project.tenant_key = "test-tenant"
        active_project.updated_at = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=active_project)
        session.execute = AsyncMock(return_value=mock_result)

        service = ProjectService(db_manager, tenant_manager)

        # Act
        result = await service.delete_project("active-proj-789")

        # Assert - BEHAVIOR: Status MUST be set to 'deleted'
        assert result["success"] is True
        assert active_project.status == "deleted", "Project status must be set to 'deleted'"
        assert active_project.deleted_at is not None, "deleted_at timestamp must be set"
