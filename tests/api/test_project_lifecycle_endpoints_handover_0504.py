"""
Comprehensive unit tests for project lifecycle endpoints - Handover 0504.

Tests all 6 new/updated endpoints:
1. POST /projects/{id}/activate - Activate project (lifecycle.py)
2. POST /projects/{id}/deactivate - Deactivate project (lifecycle.py)
3. POST /projects/{id}/cancel-staging - Cancel staging (lifecycle.py)
4. GET /projects/{id}/summary - Get project summary (status.py)
5. POST /projects/{id}/launch - Launch orchestrator (lifecycle.py)
6. PATCH /projects/{id} - Update project (crud.py)

Tests follow production-grade patterns:
- Mock ProjectService responses
- Test success and error cases
- Validate response schemas
- >80% coverage target
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.endpoints.projects import crud, lifecycle, status
from api.endpoints.projects.models import ProjectResponse, ProjectUpdate
from src.giljo_mcp.models.schemas import ProjectLaunchResponse, ProjectSummaryResponse


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_user():
    """Create mock user for authentication."""
    user = MagicMock()
    user.username = "test_user"
    user.tenant_key = "test_tenant"
    user.id = "user-123"
    return user


@pytest.fixture
def mock_project_service():
    """Create mock ProjectService."""
    return AsyncMock()


@pytest.fixture
def sample_project_dict():
    """Sample project data returned by service."""
    return {
        "id": "proj-123",
        "alias": "proj-alias",
        "name": "Test Project",
        "description": "Test description",
        "mission": "Test mission",
        "status": "active",
        "product_id": "prod-456",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completed_at": None,
        "context_budget": 150000,
        "context_used": 5000,
        "agent_count": 3,
        "message_count": 10,
        "agents": []
    }


# ============================================================================
# Tests for POST /projects/{id}/activate
# ============================================================================

class TestActivateProject:
    """Tests for activate_project endpoint."""

    @pytest.mark.asyncio
    async def test_activate_project_success(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test successful project activation."""
        # Setup mock service responses
        mock_project_service.activate_project.return_value = {
            "success": True
        }
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": sample_project_dict
        }

        # Call endpoint
        response = await lifecycle.activate_project(
            project_id="proj-123",
            force=False,
            current_user=mock_user,
            project_service=mock_project_service
        )

        # Assertions
        assert isinstance(response, ProjectResponse)
        assert response.id == "proj-123"
        assert response.name == "Test Project"
        assert response.status == "active"
        assert response.agent_count == 3
        assert response.message_count == 10

        # Verify service calls
        mock_project_service.activate_project.assert_called_once_with(
            project_id="proj-123",
            force=False
        )
        mock_project_service.get_project.assert_called_once_with(
            project_id="proj-123"
        )

    @pytest.mark.asyncio
    async def test_activate_project_with_force(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test project activation with force flag."""
        mock_project_service.activate_project.return_value = {
            "success": True
        }
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": sample_project_dict
        }

        response = await lifecycle.activate_project(
            project_id="proj-123",
            force=True,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectResponse)
        mock_project_service.activate_project.assert_called_once_with(
            project_id="proj-123",
            force=True
        )

    @pytest.mark.asyncio
    async def test_activate_project_not_found(
        self, mock_user, mock_project_service
    ):
        """Test activation when project not found."""
        mock_project_service.activate_project.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.activate_project(
                project_id="proj-999",
                force=False,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_activate_project_activation_failed(
        self, mock_user, mock_project_service
    ):
        """Test activation when activation fails."""
        mock_project_service.activate_project.return_value = {
            "success": False,
            "error": "Cannot activate project in cancelled status"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.activate_project(
                project_id="proj-123",
                force=False,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 400
        assert "Cannot activate" in exc_info.value.detail


# ============================================================================
# Tests for POST /projects/{id}/deactivate
# ============================================================================

class TestDeactivateProject:
    """Tests for deactivate_project endpoint."""

    @pytest.mark.asyncio
    async def test_deactivate_project_success(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test successful project deactivation."""
        deactivated_project = sample_project_dict.copy()
        deactivated_project["status"] = "paused"

        mock_project_service.deactivate_project.return_value = {
            "success": True
        }
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": deactivated_project
        }

        response = await lifecycle.deactivate_project(
            project_id="proj-123",
            reason=None,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectResponse)
        assert response.id == "proj-123"
        assert response.status == "paused"
        mock_project_service.deactivate_project.assert_called_once_with(
            project_id="proj-123",
            reason=None
        )

    @pytest.mark.asyncio
    async def test_deactivate_project_with_reason(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test deactivation with reason."""
        deactivated_project = sample_project_dict.copy()
        deactivated_project["status"] = "paused"

        mock_project_service.deactivate_project.return_value = {
            "success": True
        }
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": deactivated_project
        }

        response = await lifecycle.deactivate_project(
            project_id="proj-123",
            reason="User requested pause",
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectResponse)
        mock_project_service.deactivate_project.assert_called_once_with(
            project_id="proj-123",
            reason="User requested pause"
        )

    @pytest.mark.asyncio
    async def test_deactivate_project_not_found(
        self, mock_user, mock_project_service
    ):
        """Test deactivation when project not found."""
        mock_project_service.deactivate_project.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.deactivate_project(
                project_id="proj-999",
                reason=None,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_deactivate_project_invalid_state(
        self, mock_user, mock_project_service
    ):
        """Test deactivation when project in invalid state."""
        mock_project_service.deactivate_project.return_value = {
            "success": False,
            "error": "Cannot deactivate project with status: inactive"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.deactivate_project(
                project_id="proj-123",
                reason=None,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 400
        assert "Cannot deactivate" in exc_info.value.detail


# ============================================================================
# Tests for POST /projects/{id}/cancel-staging
# ============================================================================

class TestCancelStaging:
    """Tests for cancel_project_staging endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_staging_success(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test successful staging cancellation."""
        cancelled_project = sample_project_dict.copy()
        cancelled_project["status"] = "cancelled"

        mock_project_service.cancel_staging.return_value = {
            "success": True
        }
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": cancelled_project
        }

        response = await lifecycle.cancel_project_staging(
            project_id="proj-123",
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectResponse)
        assert response.id == "proj-123"
        assert response.status == "cancelled"
        mock_project_service.cancel_staging.assert_called_once_with(
            project_id="proj-123"
        )

    @pytest.mark.asyncio
    async def test_cancel_staging_not_found(
        self, mock_user, mock_project_service
    ):
        """Test staging cancellation when project not found."""
        mock_project_service.cancel_staging.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.cancel_project_staging(
                project_id="proj-999",
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cancel_staging_invalid_state(
        self, mock_user, mock_project_service
    ):
        """Test staging cancellation when not in staging state."""
        mock_project_service.cancel_staging.return_value = {
            "success": False,
            "error": "Project is not in staging status"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.cancel_project_staging(
                project_id="proj-123",
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 400
        assert "staging" in exc_info.value.detail.lower()


# ============================================================================
# Tests for GET /projects/{id}/summary
# ============================================================================

class TestGetProjectSummary:
    """Tests for get_project_summary endpoint."""

    @pytest.mark.asyncio
    async def test_get_summary_success(
        self, mock_user, mock_project_service
    ):
        """Test successful summary retrieval."""
        summary_data = {
            "id": "proj-123",
            "name": "Test Project",
            "status": "active",
            "mission": "Test mission",
            "total_jobs": 10,
            "completed_jobs": 7,
            "failed_jobs": 1,
            "active_jobs": 1,
            "pending_jobs": 1,
            "completion_percentage": 70.0,
            "created_at": datetime.now(timezone.utc),
            "activated_at": datetime.now(timezone.utc),
            "last_activity_at": datetime.now(timezone.utc),
            "product_id": "prod-456",
            "product_name": "Test Product"
        }

        mock_project_service.get_project_summary.return_value = {
            "success": True,
            "data": summary_data
        }

        response = await status.get_project_summary(
            project_id="proj-123",
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectSummaryResponse)
        assert response.id == "proj-123"
        assert response.name == "Test Project"
        assert response.status == "active"
        assert response.total_jobs == 10
        assert response.completed_jobs == 7
        assert response.completion_percentage == 70.0
        assert response.product_id == "prod-456"

        mock_project_service.get_project_summary.assert_called_once_with(
            project_id="proj-123"
        )

    @pytest.mark.asyncio
    async def test_get_summary_not_found(
        self, mock_user, mock_project_service
    ):
        """Test summary retrieval when project not found."""
        mock_project_service.get_project_summary.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        with pytest.raises(HTTPException) as exc_info:
            await status.get_project_summary(
                project_id="proj-999",
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_summary_server_error(
        self, mock_user, mock_project_service
    ):
        """Test summary retrieval with server error."""
        mock_project_service.get_project_summary.return_value = {
            "success": False,
            "error": "Database connection failed"
        }

        with pytest.raises(HTTPException) as exc_info:
            await status.get_project_summary(
                project_id="proj-123",
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 500
        assert "Database connection" in exc_info.value.detail


# ============================================================================
# Tests for POST /projects/{id}/launch
# ============================================================================

class TestLaunchProject:
    """Tests for launch_project endpoint."""

    @pytest.mark.asyncio
    async def test_launch_project_success(
        self, mock_user, mock_project_service
    ):
        """Test successful project launch."""
        launch_data = {
            "project_id": "proj-123",
            "orchestrator_job_id": "orch-job-456",
            "launch_prompt": "Launch orchestrator for Test Project...",
            "status": "active"
        }

        mock_project_service.launch_project.return_value = {
            "success": True,
            "data": launch_data
        }

        response = await lifecycle.launch_project(
            project_id="proj-123",
            launch_config=None,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectLaunchResponse)
        assert response.project_id == "proj-123"
        assert response.orchestrator_job_id == "orch-job-456"
        assert response.status == "active"
        assert "Launch orchestrator" in response.launch_prompt

        mock_project_service.launch_project.assert_called_once_with(
            project_id="proj-123",
            launch_config=None
        )

    @pytest.mark.asyncio
    async def test_launch_project_with_config(
        self, mock_user, mock_project_service
    ):
        """Test project launch with custom config."""
        launch_config = {
            "auto_activate": True,
            "agent_config": {"max_agents": 5}
        }
        launch_data = {
            "project_id": "proj-123",
            "orchestrator_job_id": "orch-job-456",
            "launch_prompt": "Launch orchestrator with custom config...",
            "status": "active"
        }

        mock_project_service.launch_project.return_value = {
            "success": True,
            "data": launch_data
        }

        response = await lifecycle.launch_project(
            project_id="proj-123",
            launch_config=launch_config,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectLaunchResponse)
        mock_project_service.launch_project.assert_called_once_with(
            project_id="proj-123",
            launch_config=launch_config
        )

    @pytest.mark.asyncio
    async def test_launch_project_not_found(
        self, mock_user, mock_project_service
    ):
        """Test launch when project not found."""
        mock_project_service.launch_project.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.launch_project(
                project_id="proj-999",
                launch_config=None,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_launch_project_launch_failed(
        self, mock_user, mock_project_service
    ):
        """Test launch when launch operation fails."""
        mock_project_service.launch_project.return_value = {
            "success": False,
            "error": "Orchestrator already running for project"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.launch_project(
                project_id="proj-123",
                launch_config=None,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 400
        assert "Orchestrator" in exc_info.value.detail


# ============================================================================
# Tests for PATCH /projects/{id}
# ============================================================================

class TestUpdateProject:
    """Tests for update_project endpoint."""

    @pytest.mark.asyncio
    async def test_update_project_all_fields(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test updating all project fields."""
        updated_project = sample_project_dict.copy()
        updated_project["name"] = "Updated Name"
        updated_project["description"] = "Updated description"
        updated_project["mission"] = "Updated mission"
        updated_project["status"] = "paused"

        mock_project_service.update_project.return_value = {
            "success": True,
            "data": updated_project
        }

        updates = ProjectUpdate(
            name="Updated Name",
            description="Updated description",
            mission="Updated mission",
            status="paused"
        )

        response = await crud.update_project(
            project_id="proj-123",
            updates=updates,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectResponse)
        assert response.id == "proj-123"
        assert response.name == "Updated Name"
        assert response.description == "Updated description"
        assert response.mission == "Updated mission"
        assert response.status == "paused"

        # Verify service call with correct update dict
        call_args = mock_project_service.update_project.call_args
        assert call_args[1]["project_id"] == "proj-123"
        update_dict = call_args[1]["updates"]
        assert update_dict["name"] == "Updated Name"
        assert update_dict["description"] == "Updated description"
        assert update_dict["mission"] == "Updated mission"
        assert update_dict["status"] == "paused"

    @pytest.mark.asyncio
    async def test_update_project_single_field(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test updating a single field."""
        updated_project = sample_project_dict.copy()
        updated_project["mission"] = "New mission only"

        mock_project_service.update_project.return_value = {
            "success": True,
            "data": updated_project
        }

        updates = ProjectUpdate(mission="New mission only")

        response = await crud.update_project(
            project_id="proj-123",
            updates=updates,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert isinstance(response, ProjectResponse)
        assert response.mission == "New mission only"

        # Only mission should be in update dict
        call_args = mock_project_service.update_project.call_args
        update_dict = call_args[1]["updates"]
        assert "mission" in update_dict
        assert "name" not in update_dict
        assert "description" not in update_dict

    @pytest.mark.asyncio
    async def test_update_project_no_fields(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test update with no fields provided."""
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": sample_project_dict
        }

        updates = ProjectUpdate()

        response = await crud.update_project(
            project_id="proj-123",
            updates=updates,
            current_user=mock_user,
            project_service=mock_project_service
        )

        # Should return current project without calling update
        assert isinstance(response, ProjectResponse)
        assert response.id == "proj-123"
        mock_project_service.update_project.assert_not_called()
        mock_project_service.get_project.assert_called_once_with(
            project_id="proj-123"
        )

    @pytest.mark.asyncio
    async def test_update_project_not_found(
        self, mock_user, mock_project_service
    ):
        """Test update when project not found."""
        mock_project_service.update_project.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        updates = ProjectUpdate(name="New Name")

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_project(
                project_id="proj-999",
                updates=updates,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_update_project_update_failed(
        self, mock_user, mock_project_service
    ):
        """Test update when update operation fails."""
        mock_project_service.update_project.return_value = {
            "success": False,
            "error": "Cannot update project in cancelled status"
        }

        updates = ProjectUpdate(name="New Name")

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_project(
                project_id="proj-123",
                updates=updates,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 400
        assert "Cannot update" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_project_no_fields_not_found(
        self, mock_user, mock_project_service
    ):
        """Test update with no fields when project not found."""
        mock_project_service.get_project.return_value = {
            "success": False,
            "error": "Project not found: proj-999"
        }

        updates = ProjectUpdate()

        with pytest.raises(HTTPException) as exc_info:
            await crud.update_project(
                project_id="proj-999",
                updates=updates,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_activate_already_active_project(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test activating an already active project."""
        mock_project_service.activate_project.return_value = {
            "success": True
        }
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": sample_project_dict
        }

        # Should succeed - idempotent operation
        response = await lifecycle.activate_project(
            project_id="proj-123",
            force=False,
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert response.status == "active"

    @pytest.mark.asyncio
    async def test_deactivate_inactive_project(
        self, mock_user, mock_project_service
    ):
        """Test deactivating an inactive project."""
        mock_project_service.deactivate_project.return_value = {
            "success": False,
            "error": "Cannot deactivate project with status: inactive"
        }

        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.deactivate_project(
                project_id="proj-123",
                reason=None,
                current_user=mock_user,
                project_service=mock_project_service
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_launch_project_empty_response_data(
        self, mock_user, mock_project_service
    ):
        """Test launch with missing data fields."""
        mock_project_service.launch_project.return_value = {
            "success": True,
            "data": {}
        }

        with pytest.raises(Exception):
            # Should fail validation due to missing required fields
            await lifecycle.launch_project(
                project_id="proj-123",
                launch_config=None,
                current_user=mock_user,
                project_service=mock_project_service
            )

    @pytest.mark.asyncio
    async def test_summary_with_all_optional_fields_none(
        self, mock_user, mock_project_service
    ):
        """Test summary with optional fields as None."""
        summary_data = {
            "id": "proj-123",
            "name": "Test Project",
            "status": "active",
            "mission": None,  # Optional
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "active_jobs": 0,
            "pending_jobs": 0,
            "completion_percentage": 0.0,
            "created_at": datetime.now(timezone.utc),
            "activated_at": None,  # Optional
            "last_activity_at": None,  # Optional
            "product_id": "prod-456",
            "product_name": "Test Product"
        }

        mock_project_service.get_project_summary.return_value = {
            "success": True,
            "data": summary_data
        }

        response = await status.get_project_summary(
            project_id="proj-123",
            current_user=mock_user,
            project_service=mock_project_service
        )

        assert response.mission is None
        assert response.activated_at is None
        assert response.last_activity_at is None
        assert response.total_jobs == 0


# ============================================================================
# Response Schema Validation Tests
# ============================================================================

class TestResponseSchemas:
    """Tests to validate response schema compliance."""

    @pytest.mark.asyncio
    async def test_project_response_schema_validation(
        self, mock_user, mock_project_service, sample_project_dict
    ):
        """Test ProjectResponse schema validation."""
        mock_project_service.activate_project.return_value = {"success": True}
        mock_project_service.get_project.return_value = {
            "success": True,
            "project": sample_project_dict
        }

        response = await lifecycle.activate_project(
            project_id="proj-123",
            force=False,
            current_user=mock_user,
            project_service=mock_project_service
        )

        # Validate all required fields are present
        assert hasattr(response, 'id')
        assert hasattr(response, 'alias')
        assert hasattr(response, 'name')
        assert hasattr(response, 'description')
        assert hasattr(response, 'mission')
        assert hasattr(response, 'status')
        assert hasattr(response, 'product_id')
        assert hasattr(response, 'created_at')
        assert hasattr(response, 'updated_at')
        assert hasattr(response, 'completed_at')
        assert hasattr(response, 'context_budget')
        assert hasattr(response, 'context_used')
        assert hasattr(response, 'agent_count')
        assert hasattr(response, 'message_count')
        assert hasattr(response, 'agents')

    @pytest.mark.asyncio
    async def test_project_summary_response_schema_validation(
        self, mock_user, mock_project_service
    ):
        """Test ProjectSummaryResponse schema validation."""
        summary_data = {
            "id": "proj-123",
            "name": "Test Project",
            "status": "active",
            "mission": "Test mission",
            "total_jobs": 10,
            "completed_jobs": 7,
            "failed_jobs": 1,
            "active_jobs": 1,
            "pending_jobs": 1,
            "completion_percentage": 70.0,
            "created_at": datetime.now(timezone.utc),
            "activated_at": datetime.now(timezone.utc),
            "last_activity_at": datetime.now(timezone.utc),
            "product_id": "prod-456",
            "product_name": "Test Product"
        }

        mock_project_service.get_project_summary.return_value = {
            "success": True,
            "data": summary_data
        }

        response = await status.get_project_summary(
            project_id="proj-123",
            current_user=mock_user,
            project_service=mock_project_service
        )

        # Validate all required fields are present
        assert hasattr(response, 'id')
        assert hasattr(response, 'name')
        assert hasattr(response, 'status')
        assert hasattr(response, 'mission')
        assert hasattr(response, 'total_jobs')
        assert hasattr(response, 'completed_jobs')
        assert hasattr(response, 'failed_jobs')
        assert hasattr(response, 'active_jobs')
        assert hasattr(response, 'pending_jobs')
        assert hasattr(response, 'completion_percentage')
        assert hasattr(response, 'created_at')
        assert hasattr(response, 'activated_at')
        assert hasattr(response, 'last_activity_at')
        assert hasattr(response, 'product_id')
        assert hasattr(response, 'product_name')

        # Validate field types
        assert isinstance(response.completion_percentage, float)
        assert 0.0 <= response.completion_percentage <= 100.0

    @pytest.mark.asyncio
    async def test_project_launch_response_schema_validation(
        self, mock_user, mock_project_service
    ):
        """Test ProjectLaunchResponse schema validation."""
        launch_data = {
            "project_id": "proj-123",
            "orchestrator_job_id": "orch-job-456",
            "launch_prompt": "Launch orchestrator...",
            "status": "active"
        }

        mock_project_service.launch_project.return_value = {
            "success": True,
            "data": launch_data
        }

        response = await lifecycle.launch_project(
            project_id="proj-123",
            launch_config=None,
            current_user=mock_user,
            project_service=mock_project_service
        )

        # Validate all required fields are present
        assert hasattr(response, 'project_id')
        assert hasattr(response, 'orchestrator_job_id')
        assert hasattr(response, 'launch_prompt')
        assert hasattr(response, 'status')

        # Validate field types
        assert isinstance(response.project_id, str)
        assert isinstance(response.orchestrator_job_id, str)
        assert isinstance(response.launch_prompt, str)
        assert isinstance(response.status, str)
