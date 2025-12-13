"""
Test for ProjectService.launch_project() field priority propagation (TDD).

This test verifies that when launching a project, the user's field_priority_config
is properly fetched and passed to the orchestrator job's job_metadata.

EXPECTED BEHAVIOR:
- launch_project() should fetch the current user's field_priority_config
- The field_priority_config should be included in orchestrator job_metadata
- The user_id should also be included in job_metadata for context tracking

Author: TDD Implementor Agent
Date: 2025-11-30
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.models import Project, MCPAgentJob, User


@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.delete = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    db_manager.get_tenant_session_async = Mock(return_value=session)
    return db_manager, session


class TestProjectServiceFieldPriorities:
    """Test field priority propagation in launch_project."""

    @pytest.mark.asyncio
    async def test_launch_project_passes_field_priorities_to_job_metadata(self, mock_db_manager):
        """
        Test that launch_project() fetches user field_priority_config and passes it to job_metadata.

        This is the FAILING TEST (RED phase of TDD).
        Expected to fail until ProjectService.launch_project() is fixed.
        """
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

        # Mock user with field_priority_config
        mock_user = Mock(spec=User)
        mock_user.id = "test-user-id"
        mock_user.field_priority_config = {
            "priorities": {
                "product_name": 1,
                "product_description": 1,
                "vision_documents": 2,
                "tech_stack": 2,
                "architecture": 3,
                "360_memory": 3,
                "git_history": 4
            }
        }
        mock_user.depth_config = {
            "vision_chunking": "medium",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_template_detail": "standard"
        }

        # Mock orchestrator job that will be created
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.id = "orchestrator-job-123"
        mock_job.job_id = "orchestrator-job-123"
        mock_job.status = "waiting"
        mock_job.job_metadata = {}  # Will be set by create_job

        # Mock activate_project to avoid nested calls
        async def mock_activate(*args, **kwargs):
            # Just set project status to active
            mock_project.status = "active"
            return {"success": True}

        # Configure session execute to return project, user, and instance number
        call_count = [0]
        async def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            # Call 1: Fetch project (in launch_project)
            if call_count[0] == 1:
                return Mock(scalar_one_or_none=Mock(return_value=mock_project))
            # Call 2: Fetch user
            elif call_count[0] == 2:
                return Mock(scalar_one_or_none=Mock(return_value=mock_user))
            # Call 3: Get max instance number (func.max/coalesce query)
            elif call_count[0] == 3:
                return Mock(scalar=Mock(return_value=0))  # Return 0 so instance_number becomes 1
            # Default: return None (for any other queries)
            return Mock(scalar_one_or_none=Mock(return_value=None))

        session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        # Mock session.add to capture the job being created
        created_jobs = []
        def capture_job(job):
            created_jobs.append(job)
            # Simulate database setting the job_id
            if not hasattr(job, 'job_id') or not job.job_id:
                job.job_id = "orchestrator-job-123"
            if not hasattr(job, 'id') or not job.id:
                job.id = "orchestrator-job-123"

        session.add = Mock(side_effect=capture_job)

        service = ProjectService(db_manager, tenant_manager)

        # Mock activate_project to bypass complex activation logic
        service.activate_project = mock_activate

        # Act - Pass user_id as parameter (like API endpoints do)
        result = await service.launch_project(
            project_id="test-project-id",
            user_id="test-user-id"
        )

        # Assert
        assert result["success"] is True, f"Expected success, got: {result}"
        assert len(created_jobs) == 1, "Expected exactly one orchestrator job to be created"

        orchestrator_job = created_jobs[0]

        # CRITICAL ASSERTIONS: Verify field_priorities and user_id in job_metadata
        assert orchestrator_job.job_metadata is not None, "job_metadata should not be None"
        assert "field_priorities" in orchestrator_job.job_metadata, \
            "job_metadata must contain 'field_priorities'"
        assert "user_id" in orchestrator_job.job_metadata, \
            "job_metadata must contain 'user_id'"

        # Verify the actual field priorities match the user's config
        expected_priorities = mock_user.field_priority_config["priorities"]
        actual_priorities = orchestrator_job.job_metadata["field_priorities"]
        assert actual_priorities == expected_priorities, \
            f"Expected priorities {expected_priorities}, got {actual_priorities}"

        # Verify user_id matches
        assert orchestrator_job.job_metadata["user_id"] == "test-user-id", \
            "user_id in job_metadata should match the current user"

        # Verify depth_config is also passed
        if "depth_config" in orchestrator_job.job_metadata:
            assert orchestrator_job.job_metadata["depth_config"] == mock_user.depth_config

    @pytest.mark.asyncio
    async def test_launch_project_handles_missing_user_config_gracefully(self, mock_db_manager):
        """
        Test that launch_project() handles missing user field_priority_config gracefully.

        When user has no field_priority_config, job_metadata should use empty dict.
        """
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

        # Mock user WITHOUT field_priority_config
        mock_user = Mock(spec=User)
        mock_user.id = "test-user-id"
        mock_user.field_priority_config = None
        mock_user.depth_config = None

        # Configure session execute
        call_count = [0]
        async def mock_execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return Mock(scalar_one_or_none=Mock(return_value=mock_project))
            elif call_count[0] == 2:
                return Mock(scalar_one_or_none=Mock(return_value=mock_user))
            elif call_count[0] == 3:
                return Mock(scalar=Mock(return_value=0))
            return Mock(scalar_one_or_none=Mock(return_value=None))

        session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        created_jobs = []
        def capture_job(job):
            created_jobs.append(job)
            if not hasattr(job, 'job_id') or not job.job_id:
                job.job_id = "orchestrator-job-123"
            if not hasattr(job, 'id') or not job.id:
                job.id = "orchestrator-job-123"

        session.add = Mock(side_effect=capture_job)

        service = ProjectService(db_manager, tenant_manager)

        # Mock activate_project
        async def mock_activate_2(*args, **kwargs):
            mock_project.status = "active"
            return {"success": True}
        service.activate_project = mock_activate_2

        # Act - Pass user_id as parameter
        result = await service.launch_project(
            project_id="test-project-id",
            user_id="test-user-id"
        )

        # Assert
        assert result["success"] is True
        assert len(created_jobs) == 1

        orchestrator_job = created_jobs[0]

        # Should still have job_metadata with user_id, but field_priorities can be empty
        assert orchestrator_job.job_metadata is not None
        assert "user_id" in orchestrator_job.job_metadata
        assert orchestrator_job.job_metadata["user_id"] == "test-user-id"

        # field_priorities should be empty dict when user has no config
        assert "field_priorities" in orchestrator_job.job_metadata
        assert orchestrator_job.job_metadata["field_priorities"] == {}
