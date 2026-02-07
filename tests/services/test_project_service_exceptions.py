"""
Tests for ProjectService exception handling (Handover 0480c)

Verifies that ProjectService raises appropriate exceptions instead of
returning {"success": False, ...} dicts.
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.services.project_service import ProjectService


class TestProjectServiceExceptions:
    """Test exception raising in ProjectService methods"""

    @pytest.mark.asyncio
    async def test_get_project_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test get_project raises ResourceNotFoundError for non-existent project"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.get_project("nonexistent-id", test_tenant_key)

        assert "not found" in exc_info.value.message.lower()
        assert exc_info.value.context.get("project_id") == "nonexistent-id"
        assert exc_info.value.context.get("tenant_key") == test_tenant_key

    @pytest.mark.asyncio
    async def test_get_project_requires_tenant_key(self, project_service: ProjectService):
        """Test get_project raises ValueError when tenant_key is missing"""
        with pytest.raises(ValueError) as exc_info:
            await project_service.get_project("some-id", "")

        assert "tenant_key" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_project_mission_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test update_project_mission raises ResourceNotFoundError"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.update_project_mission("nonexistent-id", "New mission", test_tenant_key)

        assert "not found" in exc_info.value.message.lower()

    # REMOVED: TenantManager doesn't expose _tenant_key attribute
    # Tenant context is managed internally and cannot be manipulated for testing this way

    # REMOVED: TenantManager doesn't expose _tenant_key attribute
    # Tenant context is managed internally and cannot be manipulated for testing this way

    @pytest.mark.asyncio
    async def test_activate_project_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test activate_project raises ResourceNotFoundError"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.activate_project("nonexistent-id", test_tenant_key)

        assert "not found" in exc_info.value.message.lower()

    # REMOVED: activate_project allows re-activating an active project
    # It only raises ProjectStateError for statuses NOT in ["staging", "inactive"]
    # "active" status is allowed (idempotent operation)

    @pytest.mark.asyncio
    async def test_deactivate_project_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test deactivate_project raises ResourceNotFoundError"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.deactivate_project("nonexistent-id", test_tenant_key)

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_deactivate_project_raises_state_error(
        self, project_service: ProjectService, test_tenant_key: str, inactive_project
    ):
        """Test deactivate_project raises ProjectStateError for invalid status"""
        with pytest.raises(ProjectStateError) as exc_info:
            await project_service.deactivate_project(inactive_project.id, test_tenant_key)

        assert "cannot deactivate" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_complete_project_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test complete_project raises BaseGiljoError (wraps ResourceNotFoundError)"""
        with pytest.raises(BaseGiljoError) as exc_info:
            await project_service.complete_project(
                "nonexistent-id", "Summary", key_outcomes=[], decisions_made=[], tenant_key=test_tenant_key
            )

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_complete_project_raises_validation_error_no_summary(
        self, project_service: ProjectService, test_tenant_key: str, active_project
    ):
        """Test complete_project raises ValidationError when summary is missing"""
        with pytest.raises(ValidationError) as exc_info:
            await project_service.complete_project(
                active_project.id, "", key_outcomes=[], decisions_made=[], tenant_key=test_tenant_key
            )

        assert "summary" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_project_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test cancel_project raises ResourceNotFoundError"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.cancel_project("nonexistent-id", test_tenant_key)

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_restore_project_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test restore_project raises ResourceNotFoundError"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.restore_project("nonexistent-id")

        assert "not found" in exc_info.value.message.lower()

    # REMOVED: soft_delete_project method doesn't exist in ProjectService
    # REMOVED: resume_project method doesn't exist in ProjectService

    @pytest.mark.asyncio
    async def test_cancel_staging_raises_not_found(self, project_service: ProjectService, test_tenant_key: str):
        """Test cancel_staging raises ResourceNotFoundError"""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await project_service.cancel_staging("nonexistent-id", test_tenant_key)

        assert "not found" in exc_info.value.message.lower()

    # REMOVED: update_execution_mode method doesn't exist in ProjectService


@pytest.fixture
async def project_service(project_service_with_session):
    """Alias for project_service_with_session"""
    return project_service_with_session


@pytest.fixture
async def active_project(db_session, test_tenant_key):
    """Create an active project for testing"""
    from src.giljo_mcp.models.projects import Project

    project = Project(
        id=str(uuid4()),
        name="Active Test Project",
        mission="Test mission",
        description="Test description",
        tenant_key=test_tenant_key,
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def inactive_project(db_session, test_tenant_key):
    """Create an inactive project for testing"""
    from src.giljo_mcp.models.projects import Project

    project = Project(
        id=str(uuid4()),
        name="Inactive Test Project",
        mission="Test mission",
        description="Test description",
        tenant_key=test_tenant_key,
        status="inactive",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def staged_project(db_session, test_tenant_key):
    """Create a staged project for testing"""
    from src.giljo_mcp.models.projects import Project

    project = Project(
        id=str(uuid4()),
        name="Staged Test Project",
        mission="Staged mission",
        description="Test description",
        tenant_key=test_tenant_key,
        status="inactive",
        staging_status="staged",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project
