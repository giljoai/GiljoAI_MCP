"""
Tests for ProjectService exception handling (Handover 0480c)
Updated 0731c: Added typed return validation tests.

Verifies that ProjectService raises appropriate exceptions instead of
returning {"success": False, ...} dicts.
Also verifies typed returns for happy path scenarios.
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.schemas.service_responses import (
    OperationResult,
    ProjectData,
    ProjectDetail,
    ProjectMissionUpdateResult,
    SoftDeleteResult,
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
        """Test get_project raises ValidationError when tenant_key is missing"""
        with pytest.raises(ValidationError) as exc_info:
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
            await project_service.restore_project("nonexistent-id", tenant_key=test_tenant_key)

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


class TestProjectServiceTypedReturns:
    """Test that ProjectService methods return typed models (Handover 0731c)"""

    @pytest.mark.asyncio
    async def test_get_project_returns_project_detail(
        self, project_service: ProjectService, test_tenant_key: str, active_project
    ):
        """Test get_project returns ProjectDetail typed model"""
        result = await project_service.get_project(active_project.id, test_tenant_key)
        assert isinstance(result, ProjectDetail)
        assert result.id == str(active_project.id)
        assert result.name == "Active Test Project"
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_update_project_mission_returns_typed(
        self, project_service: ProjectService, test_tenant_key: str, active_project
    ):
        """Test update_project_mission returns ProjectMissionUpdateResult"""
        result = await project_service.update_project_mission(
            active_project.id, "Updated mission text", test_tenant_key
        )
        assert isinstance(result, ProjectMissionUpdateResult)
        assert result.project_id == active_project.id
        assert result.message == "Mission updated successfully"

    @pytest.mark.asyncio
    async def test_cancel_staging_returns_project_data(
        self, project_service: ProjectService, test_tenant_key: str, db_session
    ):
        """Test cancel_staging returns ProjectData typed model"""
        from src.giljo_mcp.models.projects import Project as ProjectModel

        # Create a project in staging status for cancel_staging to work
        project = ProjectModel(
            id=str(uuid4()),
            name="Staging Project",
            mission="Test mission",
            description="Test description",
            tenant_key=test_tenant_key,
            status="staging",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        result = await project_service.cancel_staging(project.id)
        assert isinstance(result, ProjectData)
        assert result.status == "cancelled"
        assert result.name == "Staging Project"

    @pytest.mark.asyncio
    async def test_update_project_returns_project_data(
        self, project_service: ProjectService, test_tenant_key: str, active_project
    ):
        """Test update_project returns ProjectData typed model"""
        result = await project_service.update_project(
            active_project.id, {"name": "Updated Name"}
        )
        assert isinstance(result, ProjectData)
        assert result.name == "Updated Name"
        assert result.id == active_project.id

    @pytest.mark.asyncio
    async def test_restore_project_returns_operation_result(
        self, project_service: ProjectService, test_tenant_key: str, db_session
    ):
        """Test restore_project returns OperationResult typed model"""
        from src.giljo_mcp.models.projects import Project

        # Create a completed project to restore
        project = Project(
            id=str(uuid4()),
            name="Completed Project",
            mission="Test mission",
            description="Test description",
            tenant_key=test_tenant_key,
            status="completed",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        result = await project_service.restore_project(project.id, tenant_key=test_tenant_key)
        assert isinstance(result, OperationResult)
        assert "restored" in result.message.lower()

    @pytest.mark.asyncio
    async def test_delete_project_returns_soft_delete_result(
        self, project_service: ProjectService, test_tenant_key: str, active_project
    ):
        """Test delete_project returns SoftDeleteResult typed model"""
        result = await project_service.delete_project(active_project.id)
        assert isinstance(result, SoftDeleteResult)
        assert result.message == "Project deleted successfully"
        assert result.deleted_at is not None


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
