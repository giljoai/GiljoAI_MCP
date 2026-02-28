"""
Unit tests for agent_jobs lifecycle endpoints - Handover 0124

Tests spawn, complete, and error endpoints using OrchestrationService.
Updated: Handover 0731d - mock returns use typed Pydantic models.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from api.endpoints.agent_jobs import lifecycle
from api.endpoints.agent_jobs.models import (
    JobCompleteRequest,
    JobErrorRequest,
    SpawnAgentRequest,
)
from src.giljo_mcp.schemas.service_responses import (
    CompleteJobResult,
    ErrorReportResult,
    SpawnResult,
)


class TestSpawnAgentJob:
    """Tests for spawn_agent_job endpoint."""

    @pytest.mark.asyncio
    async def test_spawn_agent_success(self):
        """Test successful agent spawn."""
        # Mock dependencies
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.role = "admin"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.spawn_agent_job.return_value = SpawnResult(
            job_id="job-123",
            agent_id="agent-456",
            agent_prompt="Test prompt",
            mission_stored=True,
            thin_client=True,
        )

        mock_ws_dep = AsyncMock()

        request = SpawnAgentRequest(agent_display_name="implementer", mission="Test mission", project_id="proj-123")

        # Call endpoint
        response = await lifecycle.spawn_agent_job(
            request=request, current_user=mock_user, orchestration_service=mock_service, ws_dep=mock_ws_dep
        )

        # Assertions
        assert response.success is True
        assert response.job_id == "job-123"
        mock_service.spawn_agent_job.assert_called_once()
        mock_ws_dep.broadcast_to_tenant.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_agent_non_admin_forbidden(self):
        """Test that non-admin users cannot spawn agents."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.role = "user"
        mock_user.tenant_key = "test_tenant"

        request = SpawnAgentRequest(agent_display_name="implementer", mission="Test mission", project_id="proj-123")

        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await lifecycle.spawn_agent_job(
                request=request, current_user=mock_user, orchestration_service=AsyncMock(), ws_dep=AsyncMock()
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_spawn_agent_service_error(self):
        """Test spawn agent with service error (exception-based, Handover 0731d)."""
        from src.giljo_mcp.exceptions import OrchestrationError

        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.role = "admin"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.spawn_agent_job.side_effect = OrchestrationError("Failed to spawn")

        request = SpawnAgentRequest(agent_display_name="implementer", mission="Test mission", project_id="proj-123")

        # Service raises OrchestrationError, propagates to global exception handler
        with pytest.raises(OrchestrationError):
            await lifecycle.spawn_agent_job(
                request=request, current_user=mock_user, orchestration_service=mock_service, ws_dep=AsyncMock()
            )


class TestCompleteJob:
    """Tests for complete_job endpoint."""

    @pytest.mark.asyncio
    async def test_complete_job_success(self):
        """Test successful job completion."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.complete_job.return_value = CompleteJobResult(
            status="success",
            job_id="job-123",
            message="Job completed successfully",
        )

        request = JobCompleteRequest(result="Task completed successfully")

        response = await lifecycle.complete_job(
            job_id="job-123", complete_request=request, current_user=mock_user, orchestration_service=mock_service
        )

        assert response.job_id == "job-123"
        assert response.status == "completed"
        mock_service.complete_job.assert_called_once()


class TestReportJobError:
    """Tests for report_job_error endpoint."""

    @pytest.mark.asyncio
    async def test_report_error_success(self):
        """Test successful error reporting."""
        mock_user = MagicMock()
        mock_user.username = "test_user"
        mock_user.tenant_key = "test_tenant"

        mock_service = AsyncMock()
        mock_service.report_error.return_value = ErrorReportResult(
            job_id="job-123",
            message="Error reported",
        )

        request = JobErrorRequest(error="Test error message")

        response = await lifecycle.report_job_error(
            job_id="job-123", error_request=request, current_user=mock_user, orchestration_service=mock_service
        )

        assert response.job_id == "job-123"
        assert response.status == "blocked"
        mock_service.report_error.assert_called_once()
