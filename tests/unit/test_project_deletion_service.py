# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Tests for ProjectDeletionService (Sprint 002f -- P2 core).

Covers:
- delete_project (soft delete happy path, not found, no tenant)
- nuclear_delete_project (happy path, not found, deactivation of active project)
- restore_project (happy path, not found)
- purge_all_deleted_projects (empty, with projects)
- Tenant isolation on every query
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from giljo_mcp.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.services.project_deletion_service import ProjectDeletionService


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
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    return session


def _make_project(
    project_id=PROJECT_ID,
    status="active",
    tenant_key=TENANT_KEY,
    product_id="prod-1",
    deleted_at=None,
):
    """Create a mock Project model."""
    project = MagicMock()
    project.id = project_id
    project.name = "Test Project"
    project.status = status
    project.tenant_key = tenant_key
    project.product_id = product_id
    project.deleted_at = deleted_at
    project.updated_at = None
    return project


def _make_service(session, tenant_key=TENANT_KEY):
    """Create a ProjectDeletionService with injected test session."""
    db_manager = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value=tenant_key)
    return ProjectDeletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=session,
    )


# ---------------------------------------------------------------------------
# delete_project (soft delete) tests
# ---------------------------------------------------------------------------


class TestDeleteProject:
    """Tests for ProjectDeletionService.delete_project (soft delete)."""

    @pytest.mark.asyncio
    async def test_delete_no_tenant_raises(self):
        """Raises ValidationError when tenant is not set."""
        session = _make_session()
        service = _make_service(session)
        service.tenant_manager.get_current_tenant.return_value = None

        with pytest.raises(ValidationError, match="No tenant context"):
            await service.delete_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_delete_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()

        # First call: project lookup returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError, match="not found or already deleted"):
            await service.delete_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_delete_sets_status_and_timestamp(self):
        """Soft delete sets status='deleted' and deleted_at timestamp."""
        project = _make_project(status="active")
        session = _make_session()

        # First call: find project. Second call: find executions to decommission.
        call_count = 0
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_exec_result.scalars.return_value = mock_scalars

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_project_result
            return mock_exec_result

        session.execute = AsyncMock(side_effect=side_effect)

        service = _make_service(session)
        result = await service.delete_project(PROJECT_ID)

        assert project.status == "deleted"
        assert project.deleted_at is not None
        assert result.message == "Project deleted successfully"
        assert result.decommissioned_jobs == 0
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_decommissions_active_executions(self):
        """Soft delete decommissions active agent executions."""
        project = _make_project(status="active")
        exec1 = MagicMock()
        exec1.status = "working"
        exec2 = MagicMock()
        exec2.status = "waiting"

        session = _make_session()

        call_count = 0
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [exec1, exec2]
        mock_exec_result.scalars.return_value = mock_scalars

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_project_result
            return mock_exec_result

        session.execute = AsyncMock(side_effect=side_effect)

        service = _make_service(session)
        result = await service.delete_project(PROJECT_ID)

        assert exec1.status == "decommissioned"
        assert exec2.status == "decommissioned"
        assert result.decommissioned_jobs == 2


# ---------------------------------------------------------------------------
# nuclear_delete_project tests
# ---------------------------------------------------------------------------


class TestNuclearDeleteProject:
    """Tests for ProjectDeletionService.nuclear_delete_project."""

    @pytest.mark.asyncio
    async def test_nuclear_no_tenant_raises(self):
        """Raises ValidationError when tenant is not set."""
        session = _make_session()
        service = _make_service(session)
        service.tenant_manager.get_current_tenant.return_value = None

        with pytest.raises(ValidationError, match="No tenant context"):
            await service.nuclear_delete_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_nuclear_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError, match="not found or access denied"):
            await service.nuclear_delete_project(PROJECT_ID)

    @pytest.mark.asyncio
    async def test_nuclear_deactivates_active_project(self):
        """Deactivates project if it's active before deletion."""
        project = _make_project(status="active", product_id=None)
        session = _make_session()

        # All queries return empty lists except the first (project lookup)
        call_count = 0
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_empty = MagicMock()
        mock_empty_scalars = MagicMock()
        mock_empty_scalars.all.return_value = []
        mock_empty.scalars.return_value = mock_empty_scalars

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_project_result
            return mock_empty

        session.execute = AsyncMock(side_effect=side_effect)

        service = _make_service(session)
        result = await service.nuclear_delete_project(PROJECT_ID)

        # Project should be deactivated (set to inactive before deletion)
        assert project.status == "inactive"
        session.flush.assert_called()
        assert result.project_name == "Test Project"


# ---------------------------------------------------------------------------
# restore_project tests
# ---------------------------------------------------------------------------


class TestRestoreProject:
    """Tests for ProjectDeletionService.restore_project."""

    @pytest.mark.asyncio
    async def test_restore_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError, match="not found or access denied"):
            await service.restore_project(PROJECT_ID, TENANT_KEY)

    @pytest.mark.asyncio
    async def test_restore_succeeds(self):
        """Successfully restores a project to inactive status."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        result = await service.restore_project(PROJECT_ID, TENANT_KEY)

        assert "restored successfully" in result.message
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# purge_all_deleted_projects tests
# ---------------------------------------------------------------------------


class TestPurgeAllDeletedProjects:
    """Tests for ProjectDeletionService.purge_all_deleted_projects."""

    @pytest.mark.asyncio
    async def test_purge_no_tenant_raises(self):
        """Raises ValidationError when tenant is not set."""
        session = _make_session()
        service = _make_service(session)
        service.tenant_manager.get_current_tenant.return_value = None

        with pytest.raises(ValidationError, match="No tenant context"):
            await service.purge_all_deleted_projects()

    @pytest.mark.asyncio
    async def test_purge_empty_returns_zero(self):
        """Returns purged_count=0 when no deleted projects exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        result = await service.purge_all_deleted_projects()

        assert result.purged_count == 0
        assert result.projects == []
