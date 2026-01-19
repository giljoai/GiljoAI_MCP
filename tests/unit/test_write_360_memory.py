"""
Unit tests for write_360_memory MCP tool (updated for 0390c).

Tests the write_360_memory tool for creating 360 Memory entries in the
product_memory_entries table instead of JSONB array.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.tools.write_360_memory import write_360_memory
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry


class AsyncContextManager:
    """Helper class for async context manager mocking."""
    def __init__(self, mock_session):
        self.mock_session = mock_session

    async def __aenter__(self):
        return self.mock_session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager with session management."""
    manager = MagicMock()
    return manager


@pytest.fixture
def mock_project():
    """Mock Project instance."""
    project = MagicMock(spec=Project)
    project.id = "550e8400-e29b-41d4-a716-446655440001"  # Valid UUID
    project.name = "Test Project"
    project.tenant_key = "tenant-abc"
    project.product_id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
    project.created_at = datetime(2025, 1, 1, 10, 0, 0)
    project.completed_at = datetime(2025, 1, 5, 15, 30, 0)
    project.meta_data = {"test_coverage": 0.85}
    return project


@pytest.fixture
def mock_product():
    """Mock Product instance."""
    product = MagicMock(spec=Product)
    product.id = "550e8400-e29b-41d4-a716-446655440002"  # Valid UUID
    product.tenant_key = "tenant-abc"
    product.product_memory = {}  # Empty for git config
    product.updated_at = datetime(2025, 1, 1, 10, 0, 0)
    return product


@pytest.mark.asyncio
async def test_write_360_memory_project_completion(mock_db_manager, mock_project, mock_product):
    """Test writing a project_completion entry."""
    with patch('src.giljo_mcp.tools.write_360_memory.select'), \
         patch('src.giljo_mcp.tools.write_360_memory.ProductMemoryRepository') as mock_repo_class:

        mock_session = AsyncMock()

        # Mock queries
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        execution_result = MagicMock()
        mock_execution = MagicMock()
        mock_execution.agent_name = "Test Agent"
        mock_execution.agent_display_name = "Test Agent Display"
        mock_job = MagicMock()
        mock_job.job_type = "orchestrator"
        mock_execution.job = mock_job
        execution_result.scalar_one_or_none.return_value = mock_execution

        mock_session.execute.side_effect = [project_result, product_result, execution_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_next_sequence.return_value = 1
        mock_entry = MagicMock(spec=ProductMemoryEntry)
        mock_entry.id = "entry-uuid-123"
        mock_entry.sequence = 1
        mock_repo.create_entry.return_value = mock_entry
        mock_repo_class.return_value = mock_repo

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="550e8400-e29b-41d4-a716-446655440001",
            tenant_key="tenant-abc",
            summary="Completed feature X implementation",
            key_outcomes=["Implemented feature X", "Added tests"],
            decisions_made=["Used approach A over B"],
            entry_type="project_completion",
            author_job_id="550e8400-e29b-41d4-a716-446655440789",  # Valid UUID
            db_manager=mock_db_manager
        )

        # Assertions
        assert result["success"] is True
        assert result["sequence_number"] == 1
        assert result["entry_id"] == "entry-uuid-123"
        assert "message" in result

        # Verify repository methods called
        mock_repo.get_next_sequence.assert_called_once()
        mock_repo.create_entry.assert_called_once()


@pytest.mark.asyncio
async def test_write_360_memory_handover_closeout(mock_db_manager, mock_project, mock_product):
    """Test writing a handover_closeout entry."""
    with patch('src.giljo_mcp.tools.write_360_memory.select'), \
         patch('src.giljo_mcp.tools.write_360_memory.ProductMemoryRepository') as mock_repo_class:

        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        execution_result = MagicMock()
        mock_execution = MagicMock()
        mock_execution.agent_name = "Orchestrator"
        mock_execution.agent_display_name = "Orchestrator Display"
        mock_job = MagicMock()
        mock_job.job_type = "orchestrator"
        mock_execution.job = mock_job
        execution_result.scalar_one_or_none.return_value = mock_execution

        mock_session.execute.side_effect = [project_result, product_result, execution_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_next_sequence.return_value = 1
        mock_entry = MagicMock(spec=ProductMemoryEntry)
        mock_entry.id = "entry-uuid-456"
        mock_entry.sequence = 1
        mock_repo.create_entry.return_value = mock_entry
        mock_repo_class.return_value = mock_repo

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="550e8400-e29b-41d4-a716-446655440001",
            tenant_key="tenant-abc",
            summary="Handover to successor orchestrator",
            key_outcomes=["Context preserved", "State transferred"],
            decisions_made=["Triggered succession at 90% capacity"],
            entry_type="handover_closeout",
            author_job_id="550e8400-e29b-41d4-a716-446655440999",  # Valid UUID
            db_manager=mock_db_manager
        )

        # Assertions
        assert result["success"] is True
        assert result["sequence_number"] == 1
        assert result["entry_id"] == "entry-uuid-456"


@pytest.mark.asyncio
async def test_write_360_memory_increments_sequence(mock_db_manager, mock_project, mock_product):
    """Test that repository returns correct sequence number."""
    with patch('src.giljo_mcp.tools.write_360_memory.select'), \
         patch('src.giljo_mcp.tools.write_360_memory.ProductMemoryRepository') as mock_repo_class:

        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock repository - return sequence 3 (simulating 2 existing entries)
        mock_repo = AsyncMock()
        mock_repo.get_next_sequence.return_value = 3
        mock_entry = MagicMock(spec=ProductMemoryEntry)
        mock_entry.id = "entry-uuid-789"
        mock_entry.sequence = 3
        mock_repo.create_entry.return_value = mock_entry
        mock_repo_class.return_value = mock_repo

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="550e8400-e29b-41d4-a716-446655440001",
            tenant_key="tenant-abc",
            summary="Third entry",
            key_outcomes=["Outcome 3"],
            decisions_made=["Decision 3"],
            db_manager=mock_db_manager
        )

        # Verify sequence incremented
        assert result["success"] is True
        assert result["sequence_number"] == 3


@pytest.mark.asyncio
async def test_write_360_memory_with_github_integration(mock_db_manager, mock_project, mock_product):
    """Test writing entry with GitHub integration enabled."""
    # Configure GitHub integration
    mock_product.product_memory = {
        "git_integration": {
            "enabled": True,
            "repo_owner": "test-owner",
            "repo_name": "test-repo",
            "access_token": "ghp_test123"
        }
    }

    mock_commits = [
        {
            "sha": "abc123",
            "message": "feat: Add feature X",
            "author": "John Doe",
            "date": "2025-01-02T10:00:00Z"
        }
    ]

    with patch('src.giljo_mcp.tools.write_360_memory.select'), \
         patch('src.giljo_mcp.tools.write_360_memory._fetch_github_commits', return_value=mock_commits), \
         patch('src.giljo_mcp.tools.write_360_memory.ProductMemoryRepository') as mock_repo_class:

        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_next_sequence.return_value = 1
        mock_entry = MagicMock(spec=ProductMemoryEntry)
        mock_entry.id = "entry-uuid-git"
        mock_entry.sequence = 1
        mock_repo.create_entry.return_value = mock_entry
        mock_repo_class.return_value = mock_repo

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="550e8400-e29b-41d4-a716-446655440001",
            tenant_key="tenant-abc",
            summary="Completed with GitHub commits",
            key_outcomes=["Feature completed"],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        # Verify GitHub commits fetched
        assert result["success"] is True
        assert result["git_commits_count"] == 1

        # Verify create_entry was called with git_commits
        call_kwargs = mock_repo.create_entry.call_args[1]
        assert len(call_kwargs["git_commits"]) == 1
        assert call_kwargs["git_commits"][0]["sha"] == "abc123"


@pytest.mark.asyncio
async def test_write_360_memory_without_github_integration(mock_db_manager, mock_project, mock_product):
    """Test writing entry with GitHub integration disabled."""
    mock_product.product_memory = {
        "git_integration": {
            "enabled": False
        }
    }

    with patch('src.giljo_mcp.tools.write_360_memory.select'), \
         patch('src.giljo_mcp.tools.write_360_memory.ProductMemoryRepository') as mock_repo_class:

        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_next_sequence.return_value = 1
        mock_entry = MagicMock(spec=ProductMemoryEntry)
        mock_entry.id = "entry-uuid-nogit"
        mock_entry.sequence = 1
        mock_repo.create_entry.return_value = mock_entry
        mock_repo_class.return_value = mock_repo

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="550e8400-e29b-41d4-a716-446655440001",
            tenant_key="tenant-abc",
            summary="Completed without GitHub",
            key_outcomes=["Manual summary"],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        # Verify no commits fetched
        assert result["success"] is True
        assert result["git_commits_count"] == 0

        # Verify create_entry was called with empty git_commits
        call_kwargs = mock_repo.create_entry.call_args[1]
        assert call_kwargs["git_commits"] == []


@pytest.mark.asyncio
async def test_write_360_memory_missing_project_id():
    """Test error handling for missing project_id."""
    result = await write_360_memory(
        project_id="",
        tenant_key="tenant-abc",
        summary="Test",
        key_outcomes=[],
        decisions_made=[],
        db_manager=MagicMock()
    )

    assert result["success"] is False
    assert "project_id is required" in result["error"]


@pytest.mark.asyncio
async def test_write_360_memory_missing_summary():
    """Test error handling for missing summary."""
    result = await write_360_memory(
        project_id="550e8400-e29b-41d4-a716-446655440001",
        tenant_key="tenant-abc",
        summary="",
        key_outcomes=[],
        decisions_made=[],
        db_manager=MagicMock()
    )

    assert result["success"] is False
    assert "summary is required" in result["error"]


@pytest.mark.asyncio
async def test_write_360_memory_project_not_found(mock_db_manager):
    """Test error handling when project not found."""
    with patch('src.giljo_mcp.tools.write_360_memory.select'):
        mock_session = AsyncMock()

        # Mock project not found
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = project_result

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="nonexistent-project",
            tenant_key="tenant-abc",
            summary="Test",
            key_outcomes=[],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        assert result["success"] is False
        assert "not found or unauthorized" in result["error"]


@pytest.mark.asyncio
async def test_write_360_memory_product_not_found(mock_db_manager, mock_project):
    """Test error handling when product not found."""
    with patch('src.giljo_mcp.tools.write_360_memory.select'):
        mock_session = AsyncMock()

        # Mock project found but product not found
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [project_result, product_result]

        mock_db_manager.get_session_async = MagicMock(return_value=AsyncContextManager(mock_session))

        # Call function
        result = await write_360_memory(
            project_id="550e8400-e29b-41d4-a716-446655440001",
            tenant_key="tenant-abc",
            summary="Test",
            key_outcomes=[],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        assert result["success"] is False
        assert "Product not found" in result["error"]
