# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Tests for JobLifecycleService (Sprint 002f -- P1 security-critical).

Covers:
- spawn_job happy path and error paths
- Predecessor context injection
- Display name collision resolution
- Template resolution
- Orchestrator duplicate prevention
- Tenant isolation on every query
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from giljo_mcp.exceptions import (
    AlreadyExistsError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.services.job_lifecycle_service import JobLifecycleService


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


def _make_project(project_id=PROJECT_ID, status="active", execution_mode="multi_terminal"):
    """Create a mock Project model."""
    project = MagicMock()
    project.id = project_id
    project.name = "Test Project"
    project.status = status
    project.tenant_key = TENANT_KEY
    project.execution_mode = execution_mode
    project.staging_status = None
    project.updated_at = None
    return project


def _make_service(session, tenant_key=TENANT_KEY):
    """Create a JobLifecycleService with injected test session."""
    db_manager = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value=tenant_key)
    return JobLifecycleService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=session,
    )


# ---------------------------------------------------------------------------
# spawn_job tests
# ---------------------------------------------------------------------------


class TestSpawnJob:
    """Tests for JobLifecycleService.spawn_job."""

    @pytest.mark.asyncio
    async def test_spawn_project_not_found_raises(self):
        """Raises ResourceNotFoundError when project does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError, match="Project not found"):
            await service.spawn_job(
                agent_display_name="impl-1",
                agent_name="implementer",
                mission="Do something",
                project_id="nonexistent",
                tenant_key=TENANT_KEY,
            )

    @pytest.mark.asyncio
    async def test_spawn_into_completed_project_raises(self):
        """Raises ProjectStateError when project is completed."""
        project = _make_project(status="completed")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ProjectStateError, match="Cannot modify project"):
            await service.spawn_job(
                agent_display_name="impl-1",
                agent_name="implementer",
                mission="Do something",
                project_id=PROJECT_ID,
                tenant_key=TENANT_KEY,
            )

    @pytest.mark.asyncio
    async def test_spawn_into_cancelled_project_raises(self):
        """Raises ProjectStateError when project is cancelled."""
        project = _make_project(status="cancelled")
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = project
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ProjectStateError, match="Cannot modify project"):
            await service.spawn_job(
                agent_display_name="impl-1",
                agent_name="implementer",
                mission="Do something",
                project_id=PROJECT_ID,
                tenant_key=TENANT_KEY,
            )


# ---------------------------------------------------------------------------
# _build_predecessor_context tests
# ---------------------------------------------------------------------------


class TestBuildPredecessorContext:
    """Tests for predecessor context injection."""

    @pytest.mark.asyncio
    async def test_predecessor_not_found_raises(self):
        """Raises ResourceNotFoundError when predecessor job does not exist."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ResourceNotFoundError, match="Predecessor job"):
            await service._build_predecessor_context(
                session=session,
                predecessor_job_id="nonexistent",
                tenant_key=TENANT_KEY,
                project_id=PROJECT_ID,
                mission="Fix bugs",
                agent_display_name="fixer",
            )

    @pytest.mark.asyncio
    async def test_predecessor_wrong_project_raises(self):
        """Raises ValidationError when predecessor belongs to different project."""
        pred_job = MagicMock()
        pred_job.project_id = "other-project"
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pred_job
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(ValidationError, match="different project"):
            await service._build_predecessor_context(
                session=session,
                predecessor_job_id="pred-job-1",
                tenant_key=TENANT_KEY,
                project_id=PROJECT_ID,
                mission="Fix bugs",
                agent_display_name="fixer",
            )

    @pytest.mark.asyncio
    async def test_predecessor_context_prepended_to_mission(self):
        """Predecessor context is prepended to mission string."""
        pred_job = MagicMock()
        pred_job.project_id = PROJECT_ID

        pred_execution = MagicMock()
        pred_execution.agent_display_name = "original-agent"
        pred_execution.result = {"summary": "Did some work", "commits": ["abc123"]}

        session = _make_session()

        call_count = 0
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = pred_job
        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = pred_execution

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_job_result
            return mock_exec_result

        session.execute = AsyncMock(side_effect=side_effect)

        service = _make_service(session)
        result = await service._build_predecessor_context(
            session=session,
            predecessor_job_id="pred-job-1",
            tenant_key=TENANT_KEY,
            project_id=PROJECT_ID,
            mission="Fix the bugs",
            agent_display_name="fixer",
        )

        assert "PREDECESSOR CONTEXT" in result
        assert "Fix the bugs" in result
        assert "original-agent" in result


# ---------------------------------------------------------------------------
# _resolve_display_name tests
# ---------------------------------------------------------------------------


class TestResolveDisplayName:
    """Tests for display name collision resolution."""

    @pytest.mark.asyncio
    async def test_unique_name_returned_as_is(self):
        """When name has no collision, it is returned unchanged."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        result = await service._resolve_display_name(session, "impl-frontend", TENANT_KEY, PROJECT_ID)
        assert result == "impl-frontend"

    @pytest.mark.asyncio
    async def test_collision_auto_suffixes(self):
        """When name collides, a numeric suffix is appended."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("impl-1",)]
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        result = await service._resolve_display_name(session, "impl-1", TENANT_KEY, PROJECT_ID)
        assert result == "impl-1-2"

    @pytest.mark.asyncio
    async def test_collision_finds_next_available_suffix(self):
        """When both name and name-2 are taken, returns name-3."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("impl-1",), ("impl-1-2",)]
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        result = await service._resolve_display_name(session, "impl-1", TENANT_KEY, PROJECT_ID)
        assert result == "impl-1-3"


# ---------------------------------------------------------------------------
# _validate_spawn_agent tests
# ---------------------------------------------------------------------------


class TestValidateSpawnAgent:
    """Tests for agent name validation and display name collision."""

    @pytest.mark.asyncio
    async def test_invalid_agent_name_raises(self):
        """Raises ValidationError when agent_name not in active templates."""
        session = _make_session()

        # Template lookup returns no matching names
        mock_template_result = MagicMock()
        mock_template_result.fetchall.return_value = [("implementer",), ("tester",)]
        session.execute = AsyncMock(return_value=mock_template_result)

        service = _make_service(session)
        with pytest.raises(ValidationError, match="Invalid agent_name"):
            await service._validate_spawn_agent(
                session=session,
                agent_display_name="my-agent",
                agent_name="nonexistent-template",
                tenant_key=TENANT_KEY,
                project_id=PROJECT_ID,
                parent_job_id=None,
            )

    @pytest.mark.asyncio
    async def test_duplicate_orchestrator_raises(self):
        """Raises AlreadyExistsError when active orchestrator exists."""
        existing_orch = MagicMock()
        existing_orch.agent_id = "existing-agent-id"
        existing_orch.status = "working"

        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_orch
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        with pytest.raises(AlreadyExistsError, match="Orchestrator already exists"):
            await service._validate_spawn_agent(
                session=session,
                agent_display_name="orchestrator",
                agent_name="orchestrator",
                tenant_key=TENANT_KEY,
                project_id=PROJECT_ID,
                parent_job_id=None,
            )

    @pytest.mark.asyncio
    async def test_orchestrator_succession_allowed(self):
        """Orchestrator succession (parent_job_id matches) is allowed."""
        existing_orch = MagicMock()
        existing_orch.agent_id = "existing-agent-id"
        existing_orch.status = "working"

        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_orch
        session.execute = AsyncMock(return_value=mock_result)

        service = _make_service(session)
        result = await service._validate_spawn_agent(
            session=session,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            tenant_key=TENANT_KEY,
            project_id=PROJECT_ID,
            parent_job_id="existing-agent-id",
        )
        assert result == "orchestrator"


# ---------------------------------------------------------------------------
# _build_agent_prompt tests
# ---------------------------------------------------------------------------


class TestBuildAgentPrompt:
    """Tests for thin agent prompt construction."""

    def test_prompt_contains_job_id(self):
        """The prompt includes the job_id for get_agent_mission."""
        service = _make_service(_make_session())
        prompt = service._build_agent_prompt(
            agent_name="implementer",
            agent_display_name="impl-1",
            project_name="My Project",
            job_id="job-123",
        )
        assert "mcp__giljo_mcp__get_agent_mission" in prompt
        assert 'job_id="job-123"' in prompt

    def test_prompt_does_not_pass_tenant_key(self):
        """
        The prompt MUST NOT instruct agents to pass tenant_key — the server
        auto-injects it from the API key session. Documenting it as a
        parameter would contradict the never-pass-tenant_key contract.
        """
        service = _make_service(_make_session())
        prompt = service._build_agent_prompt(
            agent_name="implementer",
            agent_display_name="impl-1",
            project_name="My Project",
            job_id="job-abc",
        )
        # No interpolated tenant_key value, no "tenant_key=" parameter form.
        assert TENANT_KEY not in prompt
        assert 'tenant_key="' not in prompt

    def test_orchestrator_prompt_includes_staging_rules(self):
        """Orchestrator prompt includes STAGING RULES section."""
        service = _make_service(_make_session())
        prompt = service._build_agent_prompt(
            agent_name="orchestrator",
            agent_display_name="orchestrator",
            project_name="My Project",
            job_id="job-456",
        )
        assert "STAGING RULES" in prompt

    def test_non_orchestrator_prompt_no_staging_rules(self):
        """Non-orchestrator prompt does not include STAGING RULES."""
        service = _make_service(_make_session())
        prompt = service._build_agent_prompt(
            agent_name="implementer",
            agent_display_name="impl-1",
            project_name="My Project",
            job_id="job-789",
        )
        assert "STAGING RULES" not in prompt


# ---------------------------------------------------------------------------
# _resolve_spawn_template tests
# ---------------------------------------------------------------------------


class TestResolveSpawnTemplate:
    """Tests for template ID resolution at spawn time."""

    @pytest.mark.asyncio
    async def test_template_found_returns_id(self):
        """When template exists, returns its ID."""
        template = MagicMock()
        template.id = "tmpl-abc"

        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = template
        session.execute = AsyncMock(return_value=mock_result)

        project = _make_project()
        service = _make_service(session)
        mission, template_id = await service._resolve_spawn_template(
            session=session,
            project=project,
            agent_name="implementer",
            mission="Do work",
            tenant_key=TENANT_KEY,
            agent_display_name="impl-1",
        )

        assert template_id == "tmpl-abc"
        assert mission == "Do work"

    @pytest.mark.asyncio
    async def test_template_not_found_returns_none(self):
        """When no matching template, returns None template_id."""
        session = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        project = _make_project()
        service = _make_service(session)
        mission, template_id = await service._resolve_spawn_template(
            session=session,
            project=project,
            agent_name="unknown",
            mission="Do work",
            tenant_key=TENANT_KEY,
            agent_display_name="impl-1",
        )

        assert template_id is None
        assert mission == "Do work"
