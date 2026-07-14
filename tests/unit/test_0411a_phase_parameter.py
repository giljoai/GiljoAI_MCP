# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tests for Handover 0411a: Phase parameter additions.

Tests cover (BE-6118: the pure ToolAccessor.spawn_job pass-through was deleted, so
its phase-forwarding case moved out — phase storage is covered by the service-layer
tests/services/test_spawn_agent_phase.py and the advertised @mcp.tool phase param
by TestMCPToolSchemaPhase below + test_be6042d_mcp_tool_registry_surface.py):
1. SDK tool registration includes phase for spawn_job
2. JobResponse model accepts optional phase field
3. job_to_response converter maps phase from job dict
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from api.endpoints.agent_jobs.models import JobResponse
from api.endpoints.agent_jobs.status import job_to_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        "created_at": datetime.now(tz=UTC),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. SDK tool schema includes phase for spawn_job
# ---------------------------------------------------------------------------


class TestMCPToolSchemaPhase:
    """Tests that the spawn_job tool schema advertises the phase property."""

    def test_phase_in_sdk_tool_registration(self):
        """spawn_job registered via SDK must include 'phase' parameter."""
        import inspect

        from api.endpoints.mcp_sdk_server import spawn_job

        sig = inspect.signature(spawn_job)
        assert "phase" in sig.parameters, "phase not in spawn_job SDK tool signature"

    def test_phase_type_is_optional_int(self):
        """The phase parameter should be typed as int | None."""
        import inspect

        from api.endpoints.mcp_sdk_server import spawn_job

        sig = inspect.signature(spawn_job)
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
            created_at=datetime.now(tz=UTC),
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
            created_at=datetime.now(tz=UTC),
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
            created_at=datetime.now(tz=UTC),
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
            created_at=datetime.now(tz=UTC),
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
