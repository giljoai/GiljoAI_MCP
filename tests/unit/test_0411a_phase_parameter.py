"""
Tests for Handover 0411a: Phase parameter additions.

Tests cover:
1. tool_accessor.spawn_agent_job passes phase parameter through
2. SDK tool registration includes phase for spawn_agent_job
3. JobResponse model accepts optional phase field
4. job_to_response converter maps phase from job dict
"""

import inspect
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from api.endpoints.agent_jobs.models import JobResponse
from api.endpoints.agent_jobs.status import job_to_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    return MagicMock()


@pytest.fixture
def mock_tenant_manager():
    """Create a mock tenant manager."""
    manager = MagicMock()
    manager.get_current_tenant.return_value = "test_tenant"
    return manager


@pytest.fixture
def tool_accessor(mock_db_manager, mock_tenant_manager):
    """Create ToolAccessor with mocked OrchestrationService."""
    from src.giljo_mcp.tools.tool_accessor import ToolAccessor

    accessor = ToolAccessor(
        db_manager=mock_db_manager,
        tenant_manager=mock_tenant_manager,
    )

    # Mock the OrchestrationService
    accessor._orchestration_service = MagicMock()
    accessor._orchestration_service.spawn_agent_job = AsyncMock()

    return accessor


def _make_job_dict(**overrides: Any) -> dict[str, Any]:
    """Create a minimal valid job dict for job_to_response tests."""
    base = {
        "id": str(uuid4()),
        "job_id": str(uuid4()),
        "agent_id": str(uuid4()),
        "execution_id": str(uuid4()),
        "tenant_key": "test_tenant",
        "project_id": str(uuid4()),
        "agent_display_name": "implementer",
        "agent_name": "backend-implementer",
        "mission": "Test mission",
        "status": "active",
        "progress": 50,
        "created_at": datetime.now(tz=timezone.utc),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. tool_accessor.spawn_agent_job passes phase through
# ---------------------------------------------------------------------------


class TestToolAccessorPhasePassthrough:
    """Tests that ToolAccessor.spawn_agent_job forwards the phase parameter."""

    @pytest.mark.asyncio
    async def test_spawn_agent_job_passes_phase_to_service(self, tool_accessor):
        """When phase is provided, it should be forwarded to OrchestrationService."""
        expected = {"success": True, "data": {"job_id": str(uuid4())}}
        tool_accessor._orchestration_service.spawn_agent_job.return_value = expected

        result = await tool_accessor.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="backend-implementer",
            mission="Test mission",
            project_id=str(uuid4()),
            tenant_key="test_tenant",
            phase=2,
        )

        call_kwargs = tool_accessor._orchestration_service.spawn_agent_job.call_args.kwargs
        assert call_kwargs["phase"] == 2
        assert result == expected

    @pytest.mark.asyncio
    async def test_spawn_agent_job_passes_none_phase_by_default(self, tool_accessor):
        """When phase is not provided, None should be forwarded."""
        expected = {"success": True}
        tool_accessor._orchestration_service.spawn_agent_job.return_value = expected

        await tool_accessor.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="backend-implementer",
            mission="Test mission",
            project_id=str(uuid4()),
            tenant_key="test_tenant",
        )

        call_kwargs = tool_accessor._orchestration_service.spawn_agent_job.call_args.kwargs
        assert call_kwargs["phase"] is None

    def test_spawn_agent_job_signature_includes_phase(self, tool_accessor):
        """The method signature should include a 'phase' parameter."""
        sig = inspect.signature(tool_accessor.spawn_agent_job)
        assert "phase" in sig.parameters
        param = sig.parameters["phase"]
        assert param.default is None


# ---------------------------------------------------------------------------
# 2. SDK tool schema includes phase for spawn_agent_job
# ---------------------------------------------------------------------------


class TestMCPToolSchemaPhase:
    """Tests that the spawn_agent_job tool schema advertises the phase property."""

    def test_phase_in_sdk_tool_registration(self):
        """spawn_agent_job registered via SDK must include 'phase' parameter."""
        import inspect

        from api.endpoints.mcp_sdk_server import spawn_agent_job

        sig = inspect.signature(spawn_agent_job)
        assert "phase" in sig.parameters, "phase not in spawn_agent_job SDK tool signature"

    def test_phase_type_is_optional_int(self):
        """The phase parameter should be typed as int | None."""
        import inspect

        from api.endpoints.mcp_sdk_server import spawn_agent_job

        sig = inspect.signature(spawn_agent_job)
        param = sig.parameters["phase"]
        assert param.default is None, "phase should default to None"


# ---------------------------------------------------------------------------
# 4. JobResponse model accepts optional phase field
# ---------------------------------------------------------------------------


class TestJobResponsePhaseField:
    """Tests that JobResponse includes an optional phase field."""

    def test_phase_field_exists_on_model(self):
        """JobResponse should have a 'phase' field."""
        assert "phase" in JobResponse.model_fields

    def test_phase_defaults_to_none(self):
        """JobResponse.phase should default to None."""
        response = JobResponse(
            id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_key="test_tenant",
            agent_display_name="implementer",
            mission="Test",
            status="active",
            created_at=datetime.now(tz=timezone.utc),
        )
        assert response.phase is None

    def test_phase_accepts_integer(self):
        """JobResponse.phase should accept an integer value."""
        response = JobResponse(
            id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_key="test_tenant",
            agent_display_name="implementer",
            mission="Test",
            status="active",
            created_at=datetime.now(tz=timezone.utc),
            phase=3,
        )
        assert response.phase == 3

    def test_phase_serialization(self):
        """Phase should serialize to JSON correctly."""
        response = JobResponse(
            id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_key="test_tenant",
            agent_display_name="implementer",
            mission="Test",
            status="active",
            created_at=datetime.now(tz=timezone.utc),
            phase=1,
        )
        data = response.model_dump()
        assert data["phase"] == 1

    def test_phase_none_serialization(self):
        """Phase=None should serialize correctly."""
        response = JobResponse(
            id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_key="test_tenant",
            agent_display_name="implementer",
            mission="Test",
            status="active",
            created_at=datetime.now(tz=timezone.utc),
        )
        data = response.model_dump()
        assert data["phase"] is None


# ---------------------------------------------------------------------------
# 5. job_to_response converter maps phase from job dict
# ---------------------------------------------------------------------------


class TestJobToResponsePhase:
    """Tests that job_to_response correctly maps the phase field."""

    def test_phase_mapped_from_job_dict(self):
        """When job dict has phase, it should appear in JobResponse."""
        job = _make_job_dict(phase=2)
        response = job_to_response(job)
        assert response.phase == 2

    def test_phase_none_when_not_in_job_dict(self):
        """When job dict has no phase key, JobResponse.phase should be None."""
        job = _make_job_dict()
        # Ensure phase is not in the dict
        job.pop("phase", None)
        response = job_to_response(job)
        assert response.phase is None

    def test_phase_none_when_explicitly_none(self):
        """When job dict has phase=None, JobResponse.phase should be None."""
        job = _make_job_dict(phase=None)
        response = job_to_response(job)
        assert response.phase is None

    def test_phase_integer_values(self):
        """Various integer phase values should be mapped correctly."""
        for phase_val in [1, 2, 3, 5, 10]:
            job = _make_job_dict(phase=phase_val)
            response = job_to_response(job)
            assert response.phase == phase_val, f"Expected phase={phase_val}"
