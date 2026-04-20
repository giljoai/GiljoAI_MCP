# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for ProjectStagingService (Sprint 002e extraction)."""

from unittest.mock import MagicMock

import pytest

from giljo_mcp.exceptions import ProjectStateError, ResourceNotFoundError
from giljo_mcp.services.project_staging_service import ProjectStagingService


@pytest.fixture
def staging_service(db_session, test_tenant_key):
    """Create a ProjectStagingService with a test session."""
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return ProjectStagingService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


def test_check_staging_allowed_raises_when_staging():
    """check_staging_allowed raises ProjectStateError when staging_status is 'staging'."""
    project = MagicMock()
    project.staging_status = "staging"
    project.id = "test-id"

    service = ProjectStagingService(MagicMock(), MagicMock())
    with pytest.raises(ProjectStateError):
        service.check_staging_allowed(project)


def test_check_staging_allowed_passes_when_not_staging():
    """check_staging_allowed does not raise when staging_status is None."""
    project = MagicMock()
    project.staging_status = None
    project.id = "test-id"

    service = ProjectStagingService(MagicMock(), MagicMock())
    service.check_staging_allowed(project)


@pytest.mark.asyncio
async def test_restage_raises_for_missing_project(staging_service, test_tenant_key):
    """restage raises ResourceNotFoundError for non-existent project."""
    with pytest.raises(ResourceNotFoundError):
        await staging_service.restage("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_unstage_raises_for_missing_project(staging_service, test_tenant_key):
    """unstage raises ResourceNotFoundError for non-existent project."""
    with pytest.raises(ResourceNotFoundError):
        await staging_service.unstage("00000000-0000-0000-0000-000000000000")
