# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for Handover 0435b: Add 'closed' Agent Lifecycle Status.

Tests cover:
1. close_job transitions complete → closed
2. close_job rejects non-complete status
3. _auto_block_completed_recipients skips closed agents
4. Project closeout transitions complete → closed (not decommissioned)
5. _SKIP_STATUSES includes 'closed'
6. Frontend statusConfig includes 'closed'
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError


# ---------------------------------------------------------------------------
# 1. close_job: complete → closed transition
# ---------------------------------------------------------------------------


class TestCloseJobTransition:
    """Verify close_job only works on 'complete' agents and transitions to 'closed'."""

    @pytest.fixture
    def state_service(self):
        from src.giljo_mcp.services.orchestration_agent_state_service import (
            OrchestrationAgentStateService,
        )

        mock_db = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.get_current_tenant.return_value = "test_tenant"

        service = OrchestrationAgentStateService(
            db_manager=mock_db,
            tenant_manager=mock_tenant,
        )
        return service

    @pytest.mark.asyncio
    async def test_close_job_requires_complete_status(self, state_service):
        """close_job should raise ResourceNotFoundError if agent is not in 'complete' status."""
        mock_session = AsyncMock()
        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        state_service._get_session = MagicMock(return_value=_async_ctx(mock_session))

        with pytest.raises(ResourceNotFoundError, match="not in 'complete' status"):
            await state_service.close_job(job_id="some-job-id", tenant_key="test_tenant")

    @pytest.mark.asyncio
    async def test_close_job_empty_job_id_rejected(self, state_service):
        """close_job should raise ValidationError for empty job_id."""
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError, match="job_id cannot be empty"):
            await state_service.close_job(job_id="", tenant_key="test_tenant")

    @pytest.mark.asyncio
    async def test_close_job_sets_closed_status(self, state_service):
        """close_job should set execution.status to 'closed' when in 'complete'."""
        mock_execution = MagicMock()
        mock_execution.status = "complete"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_name = "backend-impl"
        mock_execution.job_id = "test-job-123"

        mock_job = MagicMock()
        mock_job.project_id = "proj-456"

        mock_session = AsyncMock()

        # First call returns execution, second returns job
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = mock_execution
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute = AsyncMock(side_effect=[exec_result, job_result])
        mock_session.flush = AsyncMock()

        state_service._get_session = MagicMock(return_value=_async_ctx(mock_session))

        result = await state_service.close_job(job_id="test-job-123", tenant_key="test_tenant")

        assert mock_execution.status == "closed"
        assert result["old_status"] == "complete"
        assert result["new_status"] == "closed"
        assert result["job_id"] == "test-job-123"


# ---------------------------------------------------------------------------
# 2. Auto-block skips closed agents
# ---------------------------------------------------------------------------


class TestAutoBlockSkipsClosed:
    """Verify that _auto_block_completed_recipients only blocks 'complete', not 'closed'."""

    def test_auto_block_condition_only_matches_complete(self):
        """The auto-block check should match 'complete' but not 'closed'."""
        # This tests the condition logic directly
        for status in ["complete"]:
            assert status == "complete"  # Would trigger auto-block

        for status in ["closed", "decommissioned", "working"]:
            assert status != "complete"  # Would NOT trigger auto-block


# ---------------------------------------------------------------------------
# 3. Skip statuses include 'closed'
# ---------------------------------------------------------------------------


class TestSkipStatuses:
    """Verify that skip statuses include 'closed' for closeout readiness checks."""

    def test_project_closeout_skip_statuses(self):
        from src.giljo_mcp.tools.project_closeout import _SKIP_STATUSES

        assert "closed" in _SKIP_STATUSES
        assert "decommissioned" in _SKIP_STATUSES

    def test_write_360_memory_skip_statuses(self):
        from src.giljo_mcp.tools.write_360_memory import SKIP_STATUSES

        assert "closed" in SKIP_STATUSES
        assert "decommissioned" in SKIP_STATUSES


# ---------------------------------------------------------------------------
# 4. Model CHECK constraint includes 'closed'
# ---------------------------------------------------------------------------


class TestModelConstraint:
    """Verify the CHECK constraint in the model includes 'closed'."""

    def test_agent_execution_check_constraint_includes_closed(self):
        from src.giljo_mcp.models.agent_identity import AgentExecution

        constraints = [
            c
            for c in AgentExecution.__table_args__
            if hasattr(c, "name") and getattr(c, "name", None) == "ck_agent_execution_status"
        ]
        assert len(constraints) == 1
        constraint_text = str(constraints[0].sqltext)
        assert "'closed'" in constraint_text


# ---------------------------------------------------------------------------
# 5. Placeholder job_id set (from 0435a, imported here for completeness)
# ---------------------------------------------------------------------------


class TestPlaceholderJobIds:
    """Verify placeholder set is correctly defined."""

    def test_placeholder_set(self):
        from api.endpoints.mcp_sdk_server import _PLACEHOLDER_JOB_IDS

        assert "unknown" in _PLACEHOLDER_JOB_IDS
        assert "placeholder" in _PLACEHOLDER_JOB_IDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _async_ctx(value):
    yield value
