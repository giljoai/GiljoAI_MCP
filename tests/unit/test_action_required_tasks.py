# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for auto-creating tasks from action_required tags (BE-5022f, Task 1)
and auto-resolving them on job completion (BE-5022f, Task 2).

TDD: tests written before implementation.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from giljo_mcp.services.dto import MemoryEntryCreateParams


@pytest.fixture
def mock_db_manager():
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


@pytest.fixture
def sample_params():
    """Create sample MemoryEntryCreateParams with action_required tags."""
    return MemoryEntryCreateParams(
        tenant_key="test-tenant",
        product_id=uuid.uuid4(),
        sequence=1,
        entry_type="handover_closeout",
        source="agent",
        timestamp=datetime.now(timezone.utc),
        project_name="test-project",
        tags=["action_required:fix auth timeout", "refactor", "action_required:add retry logic"],
    )


@pytest.fixture
def sample_params_no_action(sample_params):
    """Params with no action_required tags."""
    sample_params.tags = ["refactor", "database", "cleanup"]
    return sample_params


def _make_memory_service(db_manager, session):
    """Create a ProductMemoryService with mocked repo."""
    from giljo_mcp.services.product_memory_service import ProductMemoryService

    mock_entry = Mock()
    mock_entry.id = str(uuid.uuid4())

    svc = ProductMemoryService(db_manager=db_manager, tenant_key="test-tenant", test_session=session)
    svc._repo = Mock()
    svc._repo.create_entry = AsyncMock(return_value=mock_entry)
    return svc


class TestActionRequiredTaskCreation:
    """Task 1: Post-write hook creates tasks from action_required tags."""

    @pytest.mark.asyncio
    async def test_creates_task_for_action_required_tag(self, mock_db_manager, sample_params):
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(return_value=None)

        mock_task_svc = AsyncMock()
        mock_task_svc.log_task = AsyncMock(return_value="task-id-1")

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            await svc.create_entry(params=sample_params)

            assert mock_task_svc.log_task.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_non_action_required_tags(self, mock_db_manager, sample_params_no_action):
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(return_value=None)

        mock_task_svc = AsyncMock()

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            await svc.create_entry(params=sample_params_no_action)

            mock_task_svc.log_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_duplicate_task(self, mock_db_manager, sample_params):
        """Idempotent: if task already exists, don't create a duplicate."""
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        existing_task = Mock()
        existing_task.id = "existing-task-id"

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(return_value=existing_task)

        mock_task_svc = AsyncMock()

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            await svc.create_entry(params=sample_params)

            mock_task_svc.log_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_extracts_correct_title_from_tag(self, mock_db_manager):
        """action_required:fix auth timeout -> title 'fix auth timeout'."""
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        params = MemoryEntryCreateParams(
            tenant_key="test-tenant",
            product_id=uuid.uuid4(),
            sequence=1,
            entry_type="handover_closeout",
            source="agent",
            timestamp=datetime.now(timezone.utc),
            project_name="test-project",
            tags=["action_required:fix auth timeout"],
        )

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(return_value=None)

        mock_task_svc = AsyncMock()
        mock_task_svc.log_task = AsyncMock(return_value="task-id-1")

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            await svc.create_entry(params=params)

            call_kwargs = mock_task_svc.log_task.call_args[1]
            assert call_kwargs["title"] == "fix auth timeout"
            assert call_kwargs["category"] == "360"
            assert call_kwargs["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_none_tags_no_error(self, mock_db_manager):
        """No tags at all should not cause errors."""
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        params = MemoryEntryCreateParams(
            tenant_key="test-tenant",
            product_id=uuid.uuid4(),
            sequence=1,
            entry_type="handover_closeout",
            source="agent",
            timestamp=datetime.now(timezone.utc),
            tags=None,
        )

        await svc.create_entry(params=params)

    @pytest.mark.asyncio
    async def test_task_creation_failure_does_not_break_entry(self, mock_db_manager, sample_params):
        """If task creation fails, the memory entry is still created."""
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(return_value=None)

        mock_task_svc = AsyncMock()
        mock_task_svc.log_task = AsyncMock(side_effect=Exception("DB error"))

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            entry = await svc.create_entry(params=sample_params)

            assert entry is not None
            svc._repo.create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_action_required_tag_with_empty_title(self, mock_db_manager):
        """Tag 'action_required:' with no title after colon is silently skipped."""
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        params = MemoryEntryCreateParams(
            tenant_key="test-tenant",
            product_id=uuid.uuid4(),
            sequence=1,
            entry_type="handover_closeout",
            source="agent",
            timestamp=datetime.now(timezone.utc),
            tags=["action_required:", "action_required:   "],
        )

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(return_value=None)
        mock_task_svc = AsyncMock()

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            entry = await svc.create_entry(params=params)

            assert entry is not None
            mock_task_svc.log_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_repo_lookup_failure_is_best_effort(self, mock_db_manager, sample_params):
        """If the idempotency check raises, the hook swallows the error gracefully."""
        db_manager, session = mock_db_manager
        svc = _make_memory_service(db_manager, session)

        mock_task_repo = Mock()
        mock_task_repo.find_by_category_and_title = AsyncMock(side_effect=Exception("DB connection lost"))
        mock_task_svc = AsyncMock()

        with (
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            entry = await svc.create_entry(params=sample_params)

            # Primary write still succeeds despite hook failure
            assert entry is not None
            svc._repo.create_entry.assert_called_once()


class TestAutoResolveOnCompletion:
    """Task 2: complete_job resolves action items from result dict."""

    @pytest.mark.asyncio
    async def test_resolves_matching_action_item(self, mock_db_manager):
        """When result contains resolved_action_items, matching tasks are completed."""
        db_manager, session = mock_db_manager

        from giljo_mcp.services.job_completion_service import JobCompletionService

        mock_tenant_manager = Mock()
        mock_tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        svc = JobCompletionService(
            db_manager=db_manager,
            tenant_manager=mock_tenant_manager,
            test_session=session,
        )

        result = {
            "summary": "Fixed the auth timeout",
            "resolved_action_items": ["fix auth timeout"],
        }

        mock_execution = Mock()
        mock_execution.id = str(uuid.uuid4())
        mock_execution.status = "working"
        mock_execution.started_at = datetime.now(timezone.utc)
        mock_execution.block_reason = None

        mock_job = Mock()
        mock_job.id = str(uuid.uuid4())
        mock_job.project_id = str(uuid.uuid4())
        mock_job.product_id = str(uuid.uuid4())
        mock_job.job_type = "implementer"
        mock_job.agent_display_name = "implementer"

        mock_task = Mock()
        mock_task.id = "task-123"
        mock_task.status = "pending"

        repo = Mock()
        repo.find_active_execution_for_completion = AsyncMock(return_value=mock_execution)
        repo.commit = AsyncMock()
        repo.check_360_memory_for_project = AsyncMock(return_value=False)

        mock_task_repo = Mock()
        mock_task_repo.find_pending_by_category_and_title = AsyncMock(return_value=mock_task)

        mock_task_svc = AsyncMock()

        with (
            patch(
                "giljo_mcp.services.job_completion_service.AgentCompletionRepository",
                return_value=repo,
            ),
            patch.object(svc, "_fetch_job_for_completion", AsyncMock(return_value=mock_job)),
            patch.object(svc, "_validate_completion_requirements", AsyncMock()),
            patch.object(
                svc,
                "_apply_completion_status",
                Mock(return_value=("working", 120)),
            ),
            patch.object(svc, "_finalize_job_if_last_execution", AsyncMock()),
            patch.object(svc, "_handle_completion_side_effects", AsyncMock()),
            patch.object(svc, "_broadcast_completion", AsyncMock()),
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            await svc.complete_job(job_id=str(mock_job.id), result=result)

            mock_task_svc.change_status.assert_called_once_with("task-123", "completed")

    @pytest.mark.asyncio
    async def test_no_resolved_action_items_no_error(self, mock_db_manager):
        """When result has no resolved_action_items key, no task resolution happens."""
        db_manager, session = mock_db_manager

        from giljo_mcp.services.job_completion_service import JobCompletionService

        mock_tenant_manager = Mock()
        mock_tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        svc = JobCompletionService(
            db_manager=db_manager,
            tenant_manager=mock_tenant_manager,
            test_session=session,
        )

        result = {"summary": "Did some work"}

        mock_execution = Mock()
        mock_execution.id = str(uuid.uuid4())
        mock_execution.status = "working"
        mock_execution.started_at = datetime.now(timezone.utc)
        mock_execution.block_reason = None

        mock_job = Mock()
        mock_job.id = str(uuid.uuid4())
        mock_job.project_id = str(uuid.uuid4())
        mock_job.product_id = str(uuid.uuid4())
        mock_job.job_type = "implementer"
        mock_job.agent_display_name = "implementer"

        repo = Mock()
        repo.find_active_execution_for_completion = AsyncMock(return_value=mock_execution)
        repo.commit = AsyncMock()
        repo.check_360_memory_for_project = AsyncMock(return_value=False)

        with (
            patch(
                "giljo_mcp.services.job_completion_service.AgentCompletionRepository",
                return_value=repo,
            ),
            patch.object(svc, "_fetch_job_for_completion", AsyncMock(return_value=mock_job)),
            patch.object(svc, "_validate_completion_requirements", AsyncMock()),
            patch.object(
                svc,
                "_apply_completion_status",
                Mock(return_value=("working", 120)),
            ),
            patch.object(svc, "_finalize_job_if_last_execution", AsyncMock()),
            patch.object(svc, "_handle_completion_side_effects", AsyncMock()),
            patch.object(svc, "_broadcast_completion", AsyncMock()),
        ):
            await svc.complete_job(job_id=str(mock_job.id), result=result)

    @pytest.mark.asyncio
    async def test_skips_already_completed_task(self, mock_db_manager):
        """When the matching task is already completed, don't try to re-complete."""
        db_manager, session = mock_db_manager

        from giljo_mcp.services.job_completion_service import JobCompletionService

        mock_tenant_manager = Mock()
        mock_tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        svc = JobCompletionService(
            db_manager=db_manager,
            tenant_manager=mock_tenant_manager,
            test_session=session,
        )

        result = {
            "summary": "Work done",
            "resolved_action_items": ["already done item"],
        }

        mock_execution = Mock()
        mock_execution.id = str(uuid.uuid4())
        mock_execution.status = "working"
        mock_execution.started_at = datetime.now(timezone.utc)
        mock_execution.block_reason = None

        mock_job = Mock()
        mock_job.id = str(uuid.uuid4())
        mock_job.project_id = str(uuid.uuid4())
        mock_job.product_id = str(uuid.uuid4())
        mock_job.job_type = "implementer"
        mock_job.agent_display_name = "implementer"

        repo = Mock()
        repo.find_active_execution_for_completion = AsyncMock(return_value=mock_execution)
        repo.commit = AsyncMock()
        repo.check_360_memory_for_project = AsyncMock(return_value=False)

        mock_task_repo = Mock()
        mock_task_repo.find_pending_by_category_and_title = AsyncMock(return_value=None)

        mock_task_svc = AsyncMock()

        with (
            patch(
                "giljo_mcp.services.job_completion_service.AgentCompletionRepository",
                return_value=repo,
            ),
            patch.object(svc, "_fetch_job_for_completion", AsyncMock(return_value=mock_job)),
            patch.object(svc, "_validate_completion_requirements", AsyncMock()),
            patch.object(
                svc,
                "_apply_completion_status",
                Mock(return_value=("working", 120)),
            ),
            patch.object(svc, "_finalize_job_if_last_execution", AsyncMock()),
            patch.object(svc, "_handle_completion_side_effects", AsyncMock()),
            patch.object(svc, "_broadcast_completion", AsyncMock()),
            patch(
                "giljo_mcp.repositories.task_repository.TaskRepository",
                return_value=mock_task_repo,
            ),
            patch(
                "giljo_mcp.services.task_service.TaskService",
                return_value=mock_task_svc,
            ),
        ):
            await svc.complete_job(job_id=str(mock_job.id), result=result)

            mock_task_svc.change_status.assert_not_called()


class TestExtractTagsIntegration:
    """Task 3: project_closeout._extract_tags() uses clean_tags() correctly."""

    def test_extract_tags_filters_stopwords(self):
        """Words like 'the', 'from' in summary are stripped from tags."""
        from giljo_mcp.tools.project_closeout import _extract_tags

        result = _extract_tags(
            summary="Refactored the database from scratch",
            key_outcomes=["Added auth module"],
            decisions_made=[],
        )
        # Stopwords filtered
        assert "the" not in result
        assert "from" not in result
        # Meaningful tokens kept
        assert "Refactored" in result or "refactored" in result.copy()

    def test_extract_tags_deduplicates_case_insensitively(self):
        """Same word appearing multiple times in different cases results in one tag."""
        from giljo_mcp.tools.project_closeout import _extract_tags

        result = _extract_tags(
            summary="auth",
            key_outcomes=["Auth was fixed"],
            decisions_made=["AUTH removed"],
        )
        # At most one entry for "auth" (case-insensitive dedup keeps first)
        lower_results = [t.lower() for t in result]
        assert lower_results.count("auth") == 1

    def test_extract_tags_caps_at_15(self):
        """More than 15 distinct tokens produces at most 15 tags."""
        from giljo_mcp.tools.project_closeout import _extract_tags

        # Generate 30 unique meaningful words
        summary = " ".join(f"word{i}" for i in range(30))
        result = _extract_tags(summary=summary, key_outcomes=[], decisions_made=[])
        assert len(result) <= 15

    def test_extract_tags_empty_inputs_return_empty(self):
        """Empty/None inputs produce an empty tag list."""
        from giljo_mcp.tools.project_closeout import _extract_tags

        result = _extract_tags(summary="", key_outcomes=[], decisions_made=[])
        assert result == []

        result = _extract_tags(summary=None, key_outcomes=None, decisions_made=None)
        assert result == []


class TestValidateTagsIntegration:
    """Task 3: write_360_memory._validate_tags() uses strip_tag_punctuation() correctly."""

    def test_validate_tags_strips_boundary_punctuation(self):
        """Boundary punctuation is stripped from agent-supplied tags."""
        from giljo_mcp.tools.write_360_memory import _validate_tags

        result = _validate_tags(["(refactor)", "database.", "!important!"])
        assert "refactor" in result
        assert "database" in result
        assert "important" in result

    def test_validate_tags_none_returns_empty(self):
        """None input produces empty list."""
        from giljo_mcp.tools.write_360_memory import _validate_tags

        assert _validate_tags(None) == []

    def test_validate_tags_rejects_non_list(self):
        """Non-list input raises ValidationError."""
        from giljo_mcp.exceptions import ValidationError
        from giljo_mcp.tools.write_360_memory import _validate_tags

        with pytest.raises(ValidationError):
            _validate_tags("not-a-list")

    def test_validate_tags_rejects_too_many(self):
        """More than MAX_TAGS raises ValidationError."""
        from giljo_mcp.exceptions import ValidationError
        from giljo_mcp.tools.write_360_memory import _validate_tags

        tags = [f"tag{i}" for i in range(21)]
        with pytest.raises(ValidationError, match="Too many tags"):
            _validate_tags(tags)

    def test_validate_tags_removes_tags_that_become_empty_after_strip(self):
        """Tags that reduce to empty after stripping punctuation are excluded."""
        from giljo_mcp.tools.write_360_memory import _validate_tags

        result = _validate_tags(["valid", "()", "(),:;.!?"])
        assert result == ["valid"]
