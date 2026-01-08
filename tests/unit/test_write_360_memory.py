"""
Unit tests for write_360_memory MCP tool.

Tests the write_360_memory tool for creating 360 Memory history entries.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.tools.write_360_memory import write_360_memory
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager with session management."""
    manager = MagicMock()

    # Mock async context manager for session
    mock_session = AsyncMock(spec=AsyncSession)

    async def mock_execute(stmt):
        """Mock execute that returns mock results."""
        result = MagicMock()
        result.scalar_one_or_none = MagicMock()
        return result

    mock_session.execute = mock_execute
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    async def mock_get_session():
        yield mock_session

    manager.get_session_async = MagicMock(return_value=mock_get_session())
    return manager


@pytest.fixture
def mock_project():
    """Mock Project instance."""
    project = MagicMock(spec=Project)
    project.id = "project-123"
    project.name = "Test Project"
    project.tenant_key = "tenant-abc"
    project.product_id = "product-456"
    project.created_at = datetime(2025, 1, 1, 10, 0, 0)
    project.completed_at = datetime(2025, 1, 5, 15, 30, 0)
    project.meta_data = {"test_coverage": 0.85}
    return project


@pytest.fixture
def mock_product():
    """Mock Product instance."""
    product = MagicMock(spec=Product)
    product.id = "product-456"
    product.tenant_key = "tenant-abc"
    product.product_memory = {
        "sequential_history": []
    }
    product.updated_at = datetime(2025, 1, 1, 10, 0, 0)
    return product


@pytest.mark.asyncio
async def test_write_360_memory_project_completion(mock_db_manager, mock_project, mock_product):
    """Test writing a project_completion entry."""
    # Setup mocks
    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select:
        mock_session = AsyncMock()

        # Mock project query
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        # Mock product query
        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

        # Call function
        result = await write_360_memory(
            project_id="project-123",
            tenant_key="tenant-abc",
            summary="Completed feature X implementation",
            key_outcomes=["Implemented feature X", "Added tests"],
            decisions_made=["Used approach A over B"],
            entry_type="project_completion",
            author_job_id="job-789",
            db_manager=mock_db_manager
        )

        # Assertions
        assert result["success"] is True
        assert result["sequence_number"] == 1
        assert "message" in result

        # Verify product memory was updated
        assert len(mock_product.product_memory["sequential_history"]) == 1
        entry = mock_product.product_memory["sequential_history"][0]
        assert entry["sequence"] == 1
        assert entry["type"] == "project_completion"
        assert entry["project_id"] == "project-123"
        assert entry["project_name"] == "Test Project"
        assert entry["summary"] == "Completed feature X implementation"
        assert entry["key_outcomes"] == ["Implemented feature X", "Added tests"]
        assert entry["decisions_made"] == ["Used approach A over B"]
        assert entry["author_job_id"] == "job-789"
        assert "timestamp" in entry


@pytest.mark.asyncio
async def test_write_360_memory_handover_closeout(mock_db_manager, mock_project, mock_product):
    """Test writing a handover_closeout entry."""
    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select:
        mock_session = AsyncMock()

        # Mock project and product queries
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

        # Call function
        result = await write_360_memory(
            project_id="project-123",
            tenant_key="tenant-abc",
            summary="Handover to successor orchestrator",
            key_outcomes=["Context preserved", "State transferred"],
            decisions_made=["Triggered succession at 90% capacity"],
            entry_type="handover_closeout",
            author_job_id="orch-001",
            db_manager=mock_db_manager
        )

        # Assertions
        assert result["success"] is True
        assert result["sequence_number"] == 1

        # Verify entry type
        entry = mock_product.product_memory["sequential_history"][0]
        assert entry["type"] == "handover_closeout"
        assert entry["author_job_id"] == "orch-001"


@pytest.mark.asyncio
async def test_write_360_memory_increments_sequence(mock_db_manager, mock_project, mock_product):
    """Test that multiple entries increment sequence numbers."""
    # Add existing entries to product memory
    mock_product.product_memory = {
        "sequential_history": [
            {"sequence": 1, "type": "project_completion", "summary": "First entry"},
            {"sequence": 2, "type": "handover_closeout", "summary": "Second entry"}
        ]
    }

    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select:
        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

        # Call function
        result = await write_360_memory(
            project_id="project-123",
            tenant_key="tenant-abc",
            summary="Third entry",
            key_outcomes=["Outcome 3"],
            decisions_made=["Decision 3"],
            db_manager=mock_db_manager
        )

        # Verify sequence incremented
        assert result["success"] is True
        assert result["sequence_number"] == 3

        # Verify all entries preserved
        assert len(mock_product.product_memory["sequential_history"]) == 3
        assert mock_product.product_memory["sequential_history"][2]["sequence"] == 3


@pytest.mark.asyncio
async def test_write_360_memory_with_github_integration(mock_db_manager, mock_project, mock_product):
    """Test writing entry with GitHub integration enabled."""
    # Configure GitHub integration
    mock_product.product_memory = {
        "sequential_history": [],
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

    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select, \
         patch('giljo_mcp.tools.write_360_memory._fetch_github_commits', return_value=mock_commits) as mock_fetch:

        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

        # Call function
        result = await write_360_memory(
            project_id="project-123",
            tenant_key="tenant-abc",
            summary="Completed with GitHub commits",
            key_outcomes=["Feature completed"],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        # Verify GitHub commits fetched
        assert result["success"] is True
        assert result["git_commits_count"] == 1

        entry = mock_product.product_memory["sequential_history"][0]
        assert len(entry["git_commits"]) == 1
        assert entry["git_commits"][0]["sha"] == "abc123"


@pytest.mark.asyncio
async def test_write_360_memory_without_github_integration(mock_db_manager, mock_project, mock_product):
    """Test writing entry with GitHub integration disabled."""
    # GitHub integration disabled
    mock_product.product_memory = {
        "sequential_history": [],
        "git_integration": {
            "enabled": False
        }
    }

    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select:
        mock_session = AsyncMock()

        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = mock_product

        mock_session.execute.side_effect = [project_result, product_result]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

        # Call function
        result = await write_360_memory(
            project_id="project-123",
            tenant_key="tenant-abc",
            summary="Completed without GitHub",
            key_outcomes=["Manual summary"],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        # Verify no commits fetched
        assert result["success"] is True
        assert result["git_commits_count"] == 0

        entry = mock_product.product_memory["sequential_history"][0]
        assert entry["git_commits"] == []


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
        project_id="project-123",
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
    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select:
        mock_session = AsyncMock()

        # Mock project not found
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = None

        mock_session.execute.return_value = project_result

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

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
    with patch('giljo_mcp.tools.write_360_memory.select') as mock_select:
        mock_session = AsyncMock()

        # Mock project found but product not found
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        product_result = MagicMock()
        product_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [project_result, product_result]

        async def mock_get_session():
            yield mock_session

        mock_db_manager.get_session_async.return_value = mock_get_session()

        # Call function
        result = await write_360_memory(
            project_id="project-123",
            tenant_key="tenant-abc",
            summary="Test",
            key_outcomes=[],
            decisions_made=[],
            db_manager=mock_db_manager
        )

        assert result["success"] is False
        assert "Product not found" in result["error"]
