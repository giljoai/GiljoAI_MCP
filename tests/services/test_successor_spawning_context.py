# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Successor Spawning Tests - Context Injection and Regression

Split from test_successor_spawning.py (Handover 0497e).

Validates:
1. spawn_agent_job with predecessor_job_id injects predecessor context into mission
2. Predecessor context includes completion summary and commits (with truncation)
4. Invalid predecessor_job_id for incomplete predecessors handled gracefully
6. Spawn without predecessor_job_id preserves existing behavior (regression)
"""

import random
import uuid

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import AgentJob, Project


# Fixtures `tenant_key`, `agent_templates`, `project`, `service`,
# `other_tenant_key`, `other_tenant_templates`, `other_project`,
# and helper `_spawn_and_complete` are provided by tests/services/conftest.py.


# ============================================================================
# Test 1: Spawn with predecessor injects context into mission
# ============================================================================


@pytest.mark.asyncio
class TestSpawnWithPredecessor:
    """Verify that spawning with predecessor_job_id injects predecessor context."""

    async def test_mission_contains_predecessor_context(
        self, db_session, service, project, tenant_key
    ):
        """Successor mission should contain PREDECESSOR CONTEXT section."""
        from tests.services.conftest import _spawn_and_complete

        predecessor_result = {
            "summary": "Implemented auth module with JWT tokens",
            "artifacts": ["src/auth.py", "tests/test_auth.py"],
            "commits": ["abc123 feat: add auth module"],
        }
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, predecessor_result
        )

        # Spawn successor with predecessor reference
        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix the JWT validation bug found by tester",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        # Read the stored mission from DB
        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "## PREDECESSOR CONTEXT" in job.mission
        assert pred_spawn.job_id in job.mission
        assert "Implemented auth module with JWT tokens" in job.mission
        assert "abc123 feat: add auth module" in job.mission
        assert "Fix the JWT validation bug found by tester" in job.mission
        assert "get_agent_result" in job.mission

    async def test_predecessor_job_id_in_spawn_result(
        self, service, project, tenant_key
    ):
        """SpawnResult should include the predecessor_job_id."""
        from tests.services.conftest import _spawn_and_complete

        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, {"summary": "Done"}
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix issues",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        assert successor.predecessor_job_id == pred_spawn.job_id


# ============================================================================
# Test 2: Predecessor context truncation
# ============================================================================


@pytest.mark.asyncio
class TestPredecessorContextTruncation:
    """Verify summary truncation and commits capping."""

    async def test_long_summary_truncated_at_2000_chars(
        self, db_session, service, project, tenant_key
    ):
        """Summaries over 2000 chars should be truncated with [TRUNCATED] marker."""
        from tests.services.conftest import _spawn_and_complete

        long_summary = "A" * 3000
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, {"summary": long_summary}
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix it",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "[TRUNCATED]" in job.mission
        # The full 3000-char summary should NOT be in the mission
        assert long_summary not in job.mission

    async def test_commits_capped_at_10(
        self, db_session, service, project, tenant_key
    ):
        """Commits list should be capped at 10 entries."""
        from tests.services.conftest import _spawn_and_complete

        many_commits = [f"commit_{i}" for i in range(20)]
        pred_spawn = await _spawn_and_complete(
            service, project.id, tenant_key, {"summary": "Done", "commits": many_commits}
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix it",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        # commit_9 (10th entry) should be present, commit_10 should not
        assert "commit_9" in job.mission
        assert "commit_10" not in job.mission
        assert "... and 10 more" in job.mission


# ============================================================================
# Test 4: Predecessor with no completion result
# ============================================================================


@pytest.mark.asyncio
class TestPredecessorNoResult:
    """Verify graceful handling when predecessor has no stored result."""

    async def test_predecessor_not_completed_still_injects_context(
        self, db_session, service, project, tenant_key
    ):
        """If predecessor exists but isn't complete, context still injected with defaults."""
        # Spawn predecessor but do NOT complete it
        pred_spawn = await service.spawn_agent_job(
            agent_display_name="predecessor",
            agent_name="specialist-1",
            mission="Still working",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        successor = await service.spawn_agent_job(
            agent_display_name="successor",
            agent_name="tdd-implementor",
            mission="Fix the issues",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=pred_spawn.job_id,
        )

        stmt = select(AgentJob).where(AgentJob.job_id == successor.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "## PREDECESSOR CONTEXT" in job.mission
        assert "No summary available" in job.mission
        assert "Fix the issues" in job.mission


# ============================================================================
# Test 6: Regression - Spawn without predecessor unchanged
# ============================================================================


@pytest.mark.asyncio
class TestSpawnWithoutPredecessorRegression:
    """Verify existing behavior unchanged when predecessor_job_id is not provided."""

    async def test_spawn_without_predecessor_works(
        self, db_session, service, project, tenant_key
    ):
        """Normal spawn (no predecessor) should work exactly as before."""
        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="specialist-1",
            mission="Implement the feature",
            project_id=project.id,
            tenant_key=tenant_key,
        )

        assert result.job_id is not None
        assert result.agent_id is not None
        assert result.predecessor_job_id is None
        assert result.mission_stored is True

        # Verify mission does NOT contain predecessor context
        stmt = select(AgentJob).where(AgentJob.job_id == result.job_id)
        res = await db_session.execute(stmt)
        job = res.scalar_one()

        assert "PREDECESSOR CONTEXT" not in job.mission
        assert "Implement the feature" in job.mission

    async def test_spawn_with_none_predecessor_works(
        self, service, project, tenant_key
    ):
        """Explicitly passing predecessor_job_id=None should work as normal."""
        result = await service.spawn_agent_job(
            agent_display_name="implementer-2",
            agent_name="specialist-1",
            mission="Normal mission",
            project_id=project.id,
            tenant_key=tenant_key,
            predecessor_job_id=None,
        )

        assert result.job_id is not None
        assert result.predecessor_job_id is None
