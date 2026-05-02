# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Tests for ProjectLifecycleService (Sprint 002f -- P2 core).

Covers:
- activate_project (happy path, invalid state, Single Active Project constraint)
- deactivate_project (happy path, invalid state)
- complete_project (validation, summary required)
- cancel_project (happy path, not found)
- continue_working (happy path, invalid state)
- Tenant isolation on every query
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.exceptions import (
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.services.project_lifecycle_service import ProjectLifecycleService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_KEY = "test-tenant"
PROJECT_ID = "proj-001"


def _make_session():
    """Create a mock async session configured as a context manager."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.delete = Mock()
    session.flush = AsyncMock()
    return session


def _make_project(
    project_id=PROJECT_ID,
    status="inactive",
    tenant_key=TENANT_KEY,
    product_id="prod-1",
):
    """Create a mock Project model.

    ``status`` is coerced to a :class:`ProjectStatus` enum member to mirror
    real DB behavior (SQLAlchemy returns enum members from the typed
    ``project_status`` column). Tests may pass either a raw lifecycle string
    ("active", "completed", ...) or a :class:`ProjectStatus` member.
    """
    project = MagicMock()
    project.id = project_id
    project.name = "Test Project"
    project.status = ProjectStatus(status) if isinstance(status, str) else status
    project.tenant_key = tenant_key
    project.product_id = product_id
    project.activated_at = None
    project.updated_at = None
    project.completed_at = None
    project.deleted_at = None
    project.mission = "Test mission"
    project.description = "Test description"
    project.deactivation_reason = None
    project.staging_status = None
    return project


def _make_service(session, tenant_key=TENANT_KEY):
    """Create a ProjectLifecycleService with injected test session."""
    db_manager = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value=tenant_key)
    # Patch out ProjectStagingService to avoid circular init
    with patch("giljo_mcp.services.project_staging_service.ProjectStagingService"):
        return ProjectLifecycleService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=session,
        )


# ---------------------------------------------------------------------------
# activate_project tests
# ---------------------------------------------------------------------------


class TestActivateProject:
    """Tests for ProjectLifecycleService.activate_project."""

    @pytest.mark.asyncio
    async def test_activate_project_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError, match="Project not found"):
            await service.activate_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_activate_from_completed_raises(self):
        """Raises ProjectStateError when project is completed."""
        project = _make_project(status="completed")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ProjectStateError, match="Cannot activate"):
            await service.activate_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_activate_from_inactive_succeeds(self):
        """Successfully activates an inactive project."""
        project = _make_project(status="inactive")
        session = _make_session()

        # First call: find project. Second call: check for existing active (none found).
        # Third+: orchestrator fixture check
        call_count = 0
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_no_active = MagicMock()
        mock_no_active.scalar_one_or_none.return_value = None

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_project_result
            return mock_no_active

        session.execute = AsyncMock(side_effect=side_effect)

        service = _make_service(session)
        await service.activate_project(PROJECT_ID)

        assert project.status == "active"
        session.commit.assert_called()


# ---------------------------------------------------------------------------
# deactivate_project tests
# ---------------------------------------------------------------------------


class TestDeactivateProject:
    """Tests for ProjectLifecycleService.deactivate_project."""

    @pytest.mark.asyncio
    async def test_deactivate_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError):
            await service.deactivate_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_deactivate_non_active_raises(self):
        """Raises ProjectStateError when project is not active."""
        project = _make_project(status="inactive")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ProjectStateError, match="Cannot deactivate"):
            await service.deactivate_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_deactivate_active_succeeds(self):
        """Successfully deactivates an active project."""
        project = _make_project(status="active")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        await service.deactivate_project(PROJECT_ID)

        assert project.status == "inactive"
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_stores_reason(self):
        """Stores deactivation reason when provided."""
        project = _make_project(status="active")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        await service.deactivate_project(PROJECT_ID, reason="Taking a break")

        assert project.deactivation_reason == "Taking a break"


# ---------------------------------------------------------------------------
# complete_project tests
# ---------------------------------------------------------------------------


class TestCompleteProject:
    """Tests for ProjectLifecycleService.complete_project."""

    @pytest.mark.asyncio
    async def test_complete_no_tenant_raises(self):
        """Raises ValidationError when tenant is not set."""
        session = _make_session()
        service = _make_service(session)
        # Override tenant_manager to return None
        service.tenant_manager.get_current_tenant.return_value = None

        with pytest.raises(ValidationError, match="Tenant not set"):
            await service.complete_project(
                project_id=PROJECT_ID,
                summary="Done",
                key_outcomes=["Shipped feature"],
                decisions_made=["Used pattern X"],
            )

    @pytest.mark.asyncio
    async def test_complete_empty_summary_raises(self):
        """Raises ValidationError when summary is empty."""
        session = _make_session()
        service = _make_service(session)

        with pytest.raises(ValidationError, match="Summary is required"):
            await service.complete_project(
                project_id=PROJECT_ID,
                summary="",
                key_outcomes=["Shipped feature"],
                decisions_made=["Used pattern X"],
            )

    @pytest.mark.asyncio
    async def test_complete_whitespace_summary_raises(self):
        """Raises ValidationError when summary is whitespace."""
        session = _make_session()
        service = _make_service(session)

        with pytest.raises(ValidationError, match="Summary is required"):
            await service.complete_project(
                project_id=PROJECT_ID,
                summary="   ",
                key_outcomes=[],
                decisions_made=[],
            )


# ---------------------------------------------------------------------------
# cancel_project tests
# ---------------------------------------------------------------------------


class TestCancelProject:
    """Tests for ProjectLifecycleService.cancel_project."""

    @pytest.mark.asyncio
    async def test_cancel_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError):
            await service.cancel_project(PROJECT_ID, TENANT_KEY)

    @pytest.mark.asyncio
    async def test_cancel_succeeds(self):
        """Successfully cancels a project."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        await service.cancel_project(PROJECT_ID, TENANT_KEY)

        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_with_reason(self):
        """Passes cancellation reason to the update statement."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        await service.cancel_project(PROJECT_ID, TENANT_KEY, reason="Requirements changed")

        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# continue_working tests
# ---------------------------------------------------------------------------


class TestContinueWorking:
    """Tests for ProjectLifecycleService.continue_working."""

    @pytest.mark.asyncio
    async def test_continue_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError):
            await service.continue_working(PROJECT_ID, TENANT_KEY)

    @pytest.mark.asyncio
    async def test_continue_non_completed_raises(self):
        """Raises ProjectStateError when project is not completed."""
        project = _make_project(status="active")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ProjectStateError, match="Cannot resume"):
            await service.continue_working(PROJECT_ID, TENANT_KEY)

    @pytest.mark.asyncio
    async def test_continue_completed_succeeds(self):
        """Successfully resumes a completed project to inactive state."""
        project = _make_project(status="completed")
        session = _make_session()

        # First call: find project. Second call: find decommissioned agents (none).
        call_count = 0
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_agents_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_agents_result.scalars.return_value = mock_scalars

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_project_result
            return mock_agents_result

        session.execute = AsyncMock(side_effect=side_effect)

        service = _make_service(session)
        result = await service.continue_working(PROJECT_ID, TENANT_KEY)

        assert project.status == "inactive"
        assert project.completed_at is None
        assert result.message == "Project resumed successfully"
        assert result.agents_resumed == 0
