# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""SAAS-009b Bug 2: missing optional commit fields must not crash write_360_memory.

Before the fix, passing a commit dict without ``files_changed`` / ``lines_added``
could raise ``TypeError: unsupported operand type(s) for -: 'int' and 'NoneType'``.
After the fix, missing/None values are normalized to ``0`` at the schema boundary
(``GitCommitEntry``) so downstream arithmetic is always safe, while genuinely
required fields (``sha``, ``message``) still produce a clear pydantic
ValidationError.
"""

from __future__ import annotations

import random
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from giljo_mcp.models import Project
from giljo_mcp.schemas.jsonb_validators import GitCommitEntry, validate_git_commits
from giljo_mcp.tools.write_360_memory import write_360_memory


@pytest_asyncio.fixture
async def linked_project(db_session, test_tenant_key, test_product):
    """A project linked to test_product (write_360_memory requires product link)."""
    project = Project(
        id=str(uuid.uuid4()),
        name="SAAS-009b Commit-Field Project",
        description="Project for optional commit field tests",
        mission="Test mission",
        status="active",
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    return project


# ---- Schema-level normalization (fast, no DB) ----


class TestGitCommitEntryOptionalFields:
    """Bug 2: optional commit fields must not crash the validator."""

    def test_missing_optional_fields_normalize_to_zero(self):
        commit = GitCommitEntry(sha="abc123", message="msg", author="a")
        assert commit.files_changed == 0
        assert commit.lines_added == 0

    def test_explicit_none_normalizes_to_zero(self):
        commit = GitCommitEntry(
            sha="abc123",
            message="msg",
            author="a",
            files_changed=None,
            lines_added=None,
        )
        assert commit.files_changed == 0
        assert commit.lines_added == 0

    def test_validate_git_commits_handles_missing_optional_fields(self):
        """The bug repro commit dict from today's session must validate cleanly."""
        result = validate_git_commits(
            [
                {
                    "sha": "141374a7a4f4adc2c631a565cd782dc99e98acb9",
                    "message": "fix: remove psycopg2 import from install.py",
                    "author": "GiljoAi",
                    "date": "2026-04-21T14:04:39-04:00",
                    # NO files_changed, NO lines_added — this is what crashed today
                }
            ]
        )
        assert result is not None
        assert len(result) == 1
        assert result[0]["sha"].startswith("141374a7")
        assert result[0]["files_changed"] == 0
        assert result[0]["lines_added"] == 0

    def test_required_sha_still_enforced(self):
        """Regression guard — genuinely required fields still produce a clear error."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            validate_git_commits([{"message": "no sha", "author": "me"}])


# ---- End-to-end: write_360_memory with commit missing optional fields ----


@pytest.mark.asyncio
async def test_write_360_memory_commit_without_optional_fields_succeeds(
    db_session, test_tenant_key, test_product, linked_project
):
    """Bug 2: commit dict with no files_changed/lines_added must not raise TypeError."""
    mock_db_manager = MagicMock()

    with patch(
        "giljo_mcp.tools.write_360_memory._check_and_emit_tuning_staleness",
        new_callable=AsyncMock,
    ):
        result = await write_360_memory(
            project_id=str(linked_project.id),
            tenant_key=test_tenant_key,
            summary="Summary with minimal commit",
            key_outcomes=["Outcome A"],
            decisions_made=["Decision A"],
            entry_type="session_handover",
            git_commits=[
                {
                    "sha": "141374a7a4f4adc2c631a565cd782dc99e98acb9",
                    "message": "fix: remove psycopg2 import from install.py",
                    "author": "GiljoAi",
                    "date": "2026-04-21T14:04:39-04:00",
                    # NO files_changed, NO lines_added
                }
            ],
            db_manager=mock_db_manager,
            session=db_session,
        )

    assert result.get("entry_id") is not None
    assert result.get("git_commits_count") == 1
