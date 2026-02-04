"""
Unit tests for new context tools (Handover 0316 Phase 3).

Tests for:
- get_product_context.py
- get_project.py
- get_testing.py

Follows TDD workflow: RED → GREEN → REFACTOR
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from datetime import datetime
from contextlib import asynccontextmanager


def create_mock_db_manager(mock_session):
    """
    Helper function to create a mock db_manager with properly configured
    async context manager for get_session_async().

    Args:
        mock_session: AsyncMock session object to yield from context manager

    Returns:
        Mock db_manager with get_session_async configured
    """
    @asynccontextmanager
    async def mock_get_session_async():
        yield mock_session

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = mock_get_session_async
    return mock_db_manager


@pytest.mark.asyncio
async def test_get_product_context_basic():
    """Test get_product_context returns basic product info"""
    from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context

    mock_product = MagicMock()
    mock_product.name = "GiljoAI MCP"
    mock_product.description = "Multi-tenant agent orchestration"
    mock_product.project_path = "/path/to/project"
    mock_product.is_active = True
    mock_product.created_at = datetime(2025, 11, 1, 10, 0, 0)
    mock_product.config_data = {"features": {"core": ["Feature 1", "Feature 2"]}}
    mock_product.meta_data = {}

    # Mock database session
    mock_session = AsyncMock()
    mock_result = MagicMock()  # scalar_one_or_none is synchronous
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_product_context(
        product_id="test-id",
        tenant_key="test-tenant",
        include_metadata=False,
        db_manager=mock_db_manager
    )

    assert result["source"] == "product_context"
    assert result["data"]["product_name"] == "GiljoAI MCP"
    assert result["data"]["product_description"] == "Multi-tenant agent orchestration"
    assert result["data"]["core_features"] == ["Feature 1", "Feature 2"]
    assert "meta_data" not in result["data"]  # Not included when include_metadata=False


@pytest.mark.asyncio
async def test_get_product_context_with_metadata():
    """Test get_product_context includes metadata when requested"""
    from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context

    mock_product = MagicMock()
    mock_product.name = "Test Product"
    mock_product.description = "Test"
    mock_product.project_path = "/test"
    mock_product.is_active = False
    mock_product.created_at = datetime(2025, 11, 1, 10, 0, 0)
    mock_product.config_data = {}
    mock_product.meta_data = {"custom_key": "custom_value"}

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_product_context(
        product_id="test-id",
        tenant_key="test-tenant",
        include_metadata=True,
        db_manager=mock_db_manager
    )

    assert result["data"]["meta_data"] == {"custom_key": "custom_value"}


@pytest.mark.asyncio
async def test_get_product_context_multi_tenant_isolation():
    """Test get_product_context filters by tenant_key"""
    from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Product not found (wrong tenant)
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_product_context(
        product_id="test-id",
        tenant_key="wrong-tenant",
        include_metadata=False,
        db_manager=mock_db_manager
    )

    assert "error" in result["metadata"]
    assert result["metadata"]["error"] == "product_not_found"


@pytest.mark.asyncio
async def test_get_project_description_basic():
    """Test get_project returns project info (excluding context_budget)"""
    from src.giljo_mcp.tools.context_tools.get_project import get_project

    mock_project = MagicMock()
    mock_project.name = "Test Project"
    mock_project.alias = "A1B2C3"
    mock_project.description = "Project description"
    mock_project.mission = "AI-generated mission"
    mock_project.status = "active"
    mock_project.staging_status = "staged"
    mock_project.context_used = 50000
    mock_project.orchestrator_summary = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_project
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_project(
        project_id="test-id",
        tenant_key="test-tenant",
        include_summary=False,
        db_manager=mock_db_manager
    )

    assert result["source"] == "project_description"
    assert result["data"]["project_name"] == "Test Project"
    assert result["data"]["context_used"] == 50000
    assert "context_budget" not in result["data"]  # EXCLUDED (deprecated)
    assert "orchestrator_summary" not in result["data"]  # Not included


@pytest.mark.asyncio
async def test_get_project_description_with_summary():
    """Test get_project includes summary when requested"""
    from src.giljo_mcp.tools.context_tools.get_project import get_project

    mock_project = MagicMock()
    mock_project.name = "Test Project"
    mock_project.alias = "A1B2C3"
    mock_project.description = "Description"
    mock_project.mission = "Mission"
    mock_project.status = "completed"
    mock_project.staging_status = None
    mock_project.context_used = 80000
    mock_project.orchestrator_summary = "Project completed successfully..."

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_project
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_project(
        project_id="test-id",
        tenant_key="test-tenant",
        include_summary=True,
        db_manager=mock_db_manager
    )

    assert result["data"]["orchestrator_summary"] == "Project completed successfully..."


@pytest.mark.asyncio
async def test_get_testing_config_complete():
    """Test get_testing returns full testing config"""
    from src.giljo_mcp.tools.context_tools.get_testing import get_testing

    mock_product = MagicMock()
    mock_product.quality_standards = "80% coverage, all tests passing, zero critical bugs"
    mock_product.config_data = {
        "test_config": {
            "strategy": "TDD with unit and integration tests",
            "coverage_target": 85,
            "frameworks": ["pytest", "jest"]
        },
        "test_commands": ["pytest tests/", "npm test"]
    }

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_testing(
        product_id="test-id",
        tenant_key="test-tenant",
        depth="full",
        db_manager=mock_db_manager
    )

    assert result["source"] == "testing"
    assert result["data"]["quality_standards"] == "80% coverage, all tests passing, zero critical bugs"
    assert result["data"]["testing_strategy"] == "TDD with unit and integration tests"
    assert result["data"]["coverage_target"] == 85
    assert result["data"]["testing_frameworks"] == ["pytest", "jest"]


@pytest.mark.asyncio
async def test_get_testing_depth_basic():
    """Test get_testing basic depth returns only strategy and coverage"""
    from src.giljo_mcp.tools.context_tools.get_testing import get_testing

    mock_product = MagicMock()
    mock_product.quality_standards = "Standards here"
    mock_product.config_data = {
        "test_config": {
            "strategy": "TDD",
            "coverage_target": 80,
            "frameworks": ["pytest"]
        }
    }

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_testing(
        product_id="test-id",
        tenant_key="test-tenant",
        depth="basic",
        db_manager=mock_db_manager
    )

    assert result["data"]["testing_strategy"] == "TDD"
    assert result["data"]["coverage_target"] == 80
    assert "testing_frameworks" not in result["data"]  # Not included in basic


@pytest.mark.asyncio
async def test_get_testing_empty_config_data():
    """Test get_testing handles empty config_data gracefully"""
    from src.giljo_mcp.tools.context_tools.get_testing import get_testing

    mock_product = MagicMock()
    mock_product.quality_standards = None
    mock_product.config_data = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Mock db_manager with async context manager
    mock_db_manager = create_mock_db_manager(mock_session)

    result = await get_testing(
        product_id="test-id",
        tenant_key="test-tenant",
        depth="full",
        db_manager=mock_db_manager
    )

    assert result["data"]["quality_standards"] == ""
    assert result["data"]["testing_strategy"] == ""
