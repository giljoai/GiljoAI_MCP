# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for Project Closeout with ProductMemoryRepository (Handover 0390c)

TESTING STRATEGY:
- Test repository integration for sequence generation
- Test repository insert instead of JSONB append
- Test return format includes entry_id
- Test no JSONB mutation (no flag_modified calls)
- Test all field mappings to repository
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


def create_mock_db_session(project_mock, product_mock):
    """
    Helper function to create properly mocked async database session.

    Returns tuple of (mock_session, mock_db_manager) configured to return
    the given project and product mocks when queried.
    """
    mock_session = AsyncMock()
    mock_db_manager = MagicMock()
    mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

    # Mock database queries to return actual objects (not coroutines)
    call_counter = {"count": 0}

    async def mock_execute_side_effect(*args, **kwargs):
        mock_result = MagicMock()  # Use MagicMock not AsyncMock for result
        # Track which call this is (project, then product)
        if call_counter["count"] == 0:
            mock_result.scalar_one_or_none.return_value = project_mock
        else:
            mock_result.scalar_one_or_none.return_value = product_mock

        call_counter["count"] += 1
        return mock_result

    mock_session.execute.side_effect = mock_execute_side_effect
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.flush = AsyncMock()

    return mock_session, mock_db_manager


@pytest.fixture
def sample_product_id():
    """Sample product UUID"""
    return uuid4()


@pytest.fixture
def sample_project_id():
    """Sample project UUID"""
    return uuid4()


@pytest.fixture
def tenant_key():
    """Sample tenant key"""
    return f"tk_{uuid4().hex}"


@pytest.fixture
def mock_product(sample_product_id, tenant_key):
    """Mock Product instance with initialized product_memory"""
    product = MagicMock(spec=Product)
    product.id = sample_product_id
    product.tenant_key = tenant_key
    product.name = "Test Product"
    product.product_memory = {
        "git_integration": {
            "enabled": False,
        },
        "sequential_history": [],  # Should NOT be mutated
        "context": {},
    }
    product.updated_at = datetime.now(timezone.utc)
    return product


@pytest.fixture
def mock_project(sample_project_id, sample_product_id, tenant_key):
    """Mock Project instance"""
    project = MagicMock(spec=Project)
    project.id = sample_project_id
    project.product_id = sample_product_id
    project.tenant_key = tenant_key
    project.name = "Test Project Alpha"
    project.mission = "Test mission"
    project.status = "completed"
    project.created_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    project.completed_at = datetime(2025, 11, 16, 10, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2025, 11, 16, 10, 0, 0, tzinfo=timezone.utc)
    project.cancellation_reason = None
    project.deactivation_reason = None
    project.early_termination = False
    return project


@pytest.fixture
def mock_memory_entry():
    """Mock ProductMemoryEntry returned from repository"""
    entry = MagicMock(spec=ProductMemoryEntry)
    entry.id = uuid4()
    entry.sequence = 1
    entry.entry_type = "project_closeout"
    entry.source = "closeout_v1"
    return entry


class TestRepositoryIntegration:
    """Test integration with ProductMemoryRepository"""

    @pytest.mark.asyncio
    async def test_uses_repository_get_next_sequence(self, mock_product, mock_project, tenant_key, mock_memory_entry):
        """
        BEHAVIOR: Uses repository.get_next_sequence() for atomic sequence generation

        GIVEN: Product with existing memory entries
        WHEN: close_project_and_update_memory() is called
        THEN: Calls repository.get_next_sequence() for sequence number
        """
        from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        with patch("src.giljo_mcp.tools.project_closeout.ProductMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_next_sequence = AsyncMock(return_value=5)
            mock_repo.create_entry = AsyncMock(return_value=mock_memory_entry)

            result = await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Implemented user authentication with JWT",
                key_outcomes=["Secure token storage", "Refresh token rotation"],
                decisions_made=["Chose JWT over sessions"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            # Verify repository was used
            mock_repo.get_next_sequence.assert_called_once_with(session=mock_session, product_id=mock_product.id)
            assert "entry_id" in result
            assert "message" in result
            assert result["sequence_number"] == 5

    @pytest.mark.asyncio
    async def test_uses_repository_create_entry(self, mock_product, mock_project, tenant_key, mock_memory_entry):
        """
        BEHAVIOR: Uses repository.create_entry() to insert into table

        GIVEN: Valid project closeout data
        WHEN: close_project_and_update_memory() is called
        THEN: Calls repository.create_entry() with all required fields
        """
        from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        with patch("src.giljo_mcp.tools.project_closeout.ProductMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_next_sequence = AsyncMock(return_value=3)
            mock_repo.create_entry = AsyncMock(return_value=mock_memory_entry)

            await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1", "Outcome 2"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            # Verify create_entry was called with correct parameters
            mock_repo.create_entry.assert_called_once()
            call_kwargs = mock_repo.create_entry.call_args[1]

            assert call_kwargs["session"] == mock_session
            assert call_kwargs["tenant_key"] == tenant_key
            assert call_kwargs["product_id"] == mock_product.id
            assert call_kwargs["project_id"] == mock_project.id
            assert call_kwargs["sequence"] == 3
            assert call_kwargs["entry_type"] == "project_closeout"
            assert call_kwargs["source"] == "closeout_v1"
            assert call_kwargs["project_name"] == "Test Project Alpha"
            assert call_kwargs["summary"] == "Test summary"
            assert call_kwargs["key_outcomes"] == ["Outcome 1", "Outcome 2"]
            assert call_kwargs["decisions_made"] == ["Decision 1"]
            assert "timestamp" in call_kwargs
            assert "deliverables" in call_kwargs
            assert "metrics" in call_kwargs
            assert "priority" in call_kwargs
            assert "significance_score" in call_kwargs
            assert "token_estimate" in call_kwargs
            assert "tags" in call_kwargs

    @pytest.mark.asyncio
    async def test_does_not_mutate_jsonb_sequential_history(
        self, mock_product, mock_project, tenant_key, mock_memory_entry
    ):
        """
        BEHAVIOR: Does NOT append to JSONB product_memory.sequential_history

        GIVEN: Product with empty sequential_history
        WHEN: close_project_and_update_memory() is called
        THEN: sequential_history array is NOT modified
        """
        from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        initial_history = mock_product.product_memory["sequential_history"].copy()

        with patch("src.giljo_mcp.tools.project_closeout.ProductMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_next_sequence = AsyncMock(return_value=1)
            mock_repo.create_entry = AsyncMock(return_value=mock_memory_entry)

            await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            # Verify sequential_history was NOT mutated
            assert mock_product.product_memory["sequential_history"] == initial_history
            assert len(mock_product.product_memory["sequential_history"]) == 0

    @pytest.mark.asyncio
    async def test_return_includes_entry_id(self, mock_product, mock_project, tenant_key):
        """
        BEHAVIOR: Return format includes entry_id from repository

        GIVEN: Repository creates entry with UUID
        WHEN: close_project_and_update_memory() is called
        THEN: Result includes entry_id field
        """
        from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        entry_id = uuid4()
        mock_entry = MagicMock(spec=ProductMemoryEntry)
        mock_entry.id = entry_id
        mock_entry.sequence = 1

        with patch("src.giljo_mcp.tools.project_closeout.ProductMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_next_sequence = AsyncMock(return_value=1)
            mock_repo.create_entry = AsyncMock(return_value=mock_entry)

            result = await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            assert result["entry_id"] == str(entry_id)
            assert result["sequence_number"] == 1
            assert "message" in result

    @pytest.mark.asyncio
    async def test_all_field_mappings_preserved(self, mock_product, mock_project, tenant_key, mock_memory_entry):
        """
        BEHAVIOR: All field mappings from old format are preserved

        GIVEN: Full closeout data with all optional fields
        WHEN: close_project_and_update_memory() is called
        THEN: All fields are passed to repository.create_entry()
        """
        from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        # Enable git integration
        mock_product.product_memory["git_integration"] = {
            "enabled": True,
            "repo_name": "test-repo",
            "repo_owner": "test-owner",
        }

        with patch("src.giljo_mcp.tools.project_closeout.ProductMemoryRepository") as mock_repo_class:
            with patch("src.giljo_mcp.tools.project_closeout._fetch_github_commits") as mock_fetch:
                mock_fetch.return_value = [{"sha": "abc123", "message": "Test commit", "date": "2025-11-15T10:00:00Z"}]

                mock_repo = MagicMock()
                mock_repo_class.return_value = mock_repo
                mock_repo.get_next_sequence = AsyncMock(return_value=1)
                mock_repo.create_entry = AsyncMock(return_value=mock_memory_entry)

                await close_project_and_update_memory(
                    project_id=str(mock_project.id),
                    summary="Comprehensive test summary with details",
                    key_outcomes=["Outcome A", "Outcome B", "Outcome C"],
                    decisions_made=["Decision X", "Decision Y"],
                    tenant_key=tenant_key,
                    db_manager=mock_db_manager,
                )

                # Verify all computed fields were passed
                call_kwargs = mock_repo.create_entry.call_args[1]

                # Check git_commits
                assert len(call_kwargs["git_commits"]) == 1
                assert call_kwargs["git_commits"][0]["sha"] == "abc123"

                # Check deliverables (derived from key_outcomes)
                assert call_kwargs["deliverables"] == ["Outcome A", "Outcome B", "Outcome C"]

                # Check metrics
                assert "commits" in call_kwargs["metrics"]
                assert call_kwargs["metrics"]["commits"] == 1
                assert call_kwargs["metrics"]["test_coverage"] == 0.0

                # Check priority (should be 2 for key_outcomes present)
                assert call_kwargs["priority"] == 2

                # Check significance_score
                assert 0.0 <= call_kwargs["significance_score"] <= 1.0

                # Check token_estimate
                assert call_kwargs["token_estimate"] > 0

                # Check tags
                assert isinstance(call_kwargs["tags"], list)
                assert len(call_kwargs["tags"]) > 0

    @pytest.mark.asyncio
    async def test_git_commits_empty_when_disabled(self, mock_product, mock_project, tenant_key, mock_memory_entry):
        """
        BEHAVIOR: git_commits is empty array when GitHub disabled

        GIVEN: GitHub integration disabled
        WHEN: close_project_and_update_memory() is called
        THEN: git_commits field is empty array
        """
        from src.giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mock_session, mock_db_manager = create_mock_db_session(mock_project, mock_product)

        with patch("src.giljo_mcp.tools.project_closeout.ProductMemoryRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_next_sequence = AsyncMock(return_value=1)
            mock_repo.create_entry = AsyncMock(return_value=mock_memory_entry)

            await close_project_and_update_memory(
                project_id=str(mock_project.id),
                summary="Test summary",
                key_outcomes=["Outcome 1"],
                decisions_made=["Decision 1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
            )

            call_kwargs = mock_repo.create_entry.call_args[1]
            assert call_kwargs["git_commits"] == []
