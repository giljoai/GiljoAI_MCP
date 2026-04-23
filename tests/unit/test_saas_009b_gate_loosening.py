# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""SAAS-009b Bug 1: GIT_COMMITS_REQUIRED gate loosening.

Before the fix, write_360_memory enforced the GIT_COMMITS_REQUIRED gate for
every entry_type whenever git integration was enabled. After the fix, only
``entry_type == 'project_completion'`` is gated; ``session_handover`` and
``handover_closeout`` may legitimately have no commits yet.
"""

from __future__ import annotations

import random
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from giljo_mcp.models import Project
from giljo_mcp.models.settings import Settings
from giljo_mcp.tools.write_360_memory import write_360_memory


@pytest_asyncio.fixture
async def linked_project(db_session, test_tenant_key, test_product):
    """A project linked to test_product (write_360_memory requires product link)."""
    project = Project(
        id=str(uuid.uuid4()),
        name="SAAS-009b Gate Test Project",
        description="Project for gate loosening tests",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest_asyncio.fixture
async def git_integration_enabled(db_session, test_tenant_key):
    """Enable git integration in the settings table for this tenant."""
    settings = Settings(
        tenant_key=test_tenant_key,
        category="integrations",
        settings_data={"git_integration": {"enabled": True}},
    )
    db_session.add(settings)
    await db_session.commit()
    return settings


@pytest.mark.asyncio
async def test_session_handover_succeeds_without_git_commits(
    db_session, test_tenant_key, test_product, linked_project, git_integration_enabled
):
    """Bug 1: entry_type='session_handover' must succeed with no git_commits."""
    mock_db_manager = MagicMock()

    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Session handover summary",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="session_handover",
            db_manager=mock_db_manager,
            session=db_session,
        )

    assert result.get("entry_id") is not None
    assert result.get("git_commits_count") == 0
    assert result.get("entry_type") == "session_handover"


@pytest.mark.asyncio
async def test_handover_closeout_succeeds_without_git_commits(
    db_session, test_tenant_key, test_product, linked_project, git_integration_enabled
):
    """Bug 1: entry_type='handover_closeout' must also succeed with no git_commits."""
    mock_db_manager = MagicMock()

    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Handover closeout summary",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="handover_closeout",
            db_manager=mock_db_manager,
            session=db_session,
        )

    assert result.get("entry_id") is not None
    assert result.get("git_commits_count") == 0


@pytest.mark.asyncio
async def test_project_completion_without_commits_still_gated(
    db_session, test_tenant_key, test_product, linked_project, git_integration_enabled
):
    """Regression: entry_type='project_completion' without commits must still fail."""
    mock_db_manager = MagicMock()

    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Project completion with no commits",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="project_completion",
            db_manager=mock_db_manager,
            session=db_session,
        )

    assert result.get("success") is False
    assert result.get("error") == "GIT_COMMITS_REQUIRED"
