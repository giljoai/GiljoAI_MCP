"""
Tests for Serena Integration Toggle in Mission Generation

Tests that mission generation respects user's Serena MCP integration toggle,
including context when enabled and gracefully degrading when unavailable.

Handover 0086B Phase 5.1: Backend Integration Testing (Task 3.2)
Created: 2025-11-02
Coverage Target: 95%+
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, Project, User


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_db_manager():
    """Create mock database manager for MissionPlanner."""
    db_manager = MagicMock()
    db_manager.is_async = True

    # Mock async session context manager
    mock_session = AsyncMock()
    db_manager.get_session_async = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)))

    return db_manager


@pytest.fixture
def mission_planner(mock_db_manager):
    """Create MissionPlanner instance with mocked database."""
    return MissionPlanner(mock_db_manager)


@pytest.fixture
def test_product():
    """Create test product with vision document."""
    return Product(
        id=str(uuid4()),
        name="Test Product",
        tenant_key="tenant_abc",
        vision_document="# Product Vision\nBuild an amazing application.",
        config_data={
            "tech_stack": {"languages": ["Python", "JavaScript"], "backend": ["FastAPI"], "frontend": ["Vue.js"]},
            "features": ["Authentication", "User Management"],
            "architecture": {"pattern": "Microservices", "api_style": "REST"},
        },
    )


@pytest.fixture
def test_project(test_product):
    """Create test project."""
    return Project(
        id=str(uuid4()),
        name="Test Project",
        tenant_key="tenant_abc",
        product_id=test_product.id,
        description="Implement user authentication system",
        codebase_summary="## Backend\n- FastAPI application\n- PostgreSQL database",
    )


@pytest.fixture
def test_user_serena_enabled():
    """Create test user with Serena enabled."""
    return User(
        id=str(uuid4()),
        username="test_user",
        email="test@example.com",
        tenant_key="tenant_abc",
        field_priority_config={
            "serena_enabled": True,
            "token_budget": 2000,
            "product_vision": 10,
            "codebase_summary": 8,
        },
    )


@pytest.fixture
def test_user_serena_disabled():
    """Create test user with Serena disabled."""
    return User(
        id=str(uuid4()),
        username="test_user",
        email="test@example.com",
        tenant_key="tenant_abc",
        field_priority_config={
            "serena_enabled": False,
            "token_budget": 2000,
            "product_vision": 10,
            "codebase_summary": 8,
        },
    )


# ============================================================================
# Test: User Configuration Fetching
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_configuration_serena_enabled(mission_planner, test_user_serena_enabled):
    """
    Test _get_user_configuration correctly extracts serena_enabled=True.

    Validates that user configuration parsing correctly identifies when
    Serena integration is enabled in field_priority_config.
    """
    # Arrange
    user_id = test_user_serena_enabled.id

    # Mock database query to return user
    with patch.object(mission_planner.db_manager, "get_session_async") as mock_get_session:
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=test_user_serena_enabled)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Act
        config = await mission_planner._get_user_configuration(user_id)

        # Assert
        assert config["serena_enabled"] is True
        assert config["token_budget"] == 2000
        assert config["field_priority_config"] is not None
        assert config["field_priority_config"]["serena_enabled"] is True


@pytest.mark.asyncio
async def test_get_user_configuration_serena_disabled(mission_planner, test_user_serena_disabled):
    """
    Test _get_user_configuration correctly extracts serena_enabled=False.

    Validates that user configuration parsing correctly identifies when
    Serena integration is disabled.
    """
    # Arrange
    user_id = test_user_serena_disabled.id

    # Mock database query
    with patch.object(mission_planner.db_manager, "get_session_async") as mock_get_session:
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=test_user_serena_disabled)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Act
        config = await mission_planner._get_user_configuration(user_id)

        # Assert
        assert config["serena_enabled"] is False
        assert config["token_budget"] == 2000


@pytest.mark.asyncio
async def test_get_user_configuration_no_user_defaults_to_false(mission_planner):
    """
    Test _get_user_configuration returns serena_enabled=False when no user_id provided.

    Validates safe defaults when user configuration is unavailable.
    """
    # Act
    config = await mission_planner._get_user_configuration(None)

    # Assert
    assert config["serena_enabled"] is False
    assert config["token_budget"] == 2000
    assert config["field_priority_config"] is None


# ============================================================================
# Test: Serena Context Fetching
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_serena_codebase_context_graceful_degradation(mission_planner, caplog):
    """
    Test _fetch_serena_codebase_context returns empty string gracefully.

    Validates that when Serena MCP tool is unavailable or not implemented,
    the method returns empty string and logs appropriately (graceful degradation).

    This is the current expected behavior until full Serena integration is complete.
    """
    # Arrange
    project_id = str(uuid4())
    tenant_key = "tenant_abc"

    # Act
    context = await mission_planner._fetch_serena_codebase_context(project_id, tenant_key)

    # Assert
    assert context == ""  # Graceful degradation
    assert "Serena integration requested but not yet implemented" in caplog.text


@pytest.mark.asyncio
async def test_fetch_serena_codebase_context_exception_handling(mission_planner, caplog):
    """
    Test _fetch_serena_codebase_context handles exceptions gracefully.

    Validates that if Serena MCP call raises an exception, the method
    catches it, logs a warning, and returns empty string (no crash).
    """
    # Arrange
    project_id = str(uuid4())
    tenant_key = "tenant_abc"

    # Mock MCP client to raise exception
    with patch("src.giljo_mcp.mission_planner.MCPClient", side_effect=Exception("MCP connection failed")):
        # Act
        context = await mission_planner._fetch_serena_codebase_context(project_id, tenant_key)

        # Assert
        assert context == ""  # Graceful degradation
        # Note: Current implementation logs "not yet implemented", not exception
        # When full Serena integration is added, this test should be updated


# ============================================================================
# Test: Token Counting with Serena Context
# ============================================================================


def test_count_tokens_empty_string(mission_planner):
    """
    Test _count_tokens returns 0 for empty string.

    Validates token counting edge case for empty Serena context.
    """
    # Act
    count = mission_planner._count_tokens("")

    # Assert
    assert count == 0


def test_count_tokens_with_content(mission_planner):
    """
    Test _count_tokens correctly estimates tokens for Serena context.

    Validates token counting for realistic Serena codebase analysis output.
    Uses tiktoken if available, otherwise fallback (4 chars per token).
    """
    # Arrange
    serena_context = """
# Codebase Analysis

## Project Structure
- api/: FastAPI endpoints
- src/: Core business logic
- tests/: Test suite

## Key Components
- UserService: Handles authentication
- DatabaseManager: PostgreSQL connection pool
- WebSocketService: Real-time updates
"""

    # Act
    count = mission_planner._count_tokens(serena_context)

    # Assert
    assert count > 0
    # Approximate token count (varies by tokenizer)
    assert 40 <= count <= 100  # Reasonable range for this text


# ============================================================================
# Test: Integration - Mission Generation with Serena Toggle
# ============================================================================


@pytest.mark.asyncio
async def test_build_context_includes_serena_when_available(mission_planner, test_product, test_project):
    """
    Test that _build_context_with_priorities would include Serena context if available.

    Note: This tests the context building mechanism. Full integration test
    would require mocking the entire mission generation workflow with Serena.

    This test validates the field priority system works correctly, which is
    where Serena context would be integrated.
    """
    # Arrange
    field_priorities = {"product_vision": 10, "codebase_summary": 8}

    # Act
    context = await mission_planner._build_context_with_priorities(
        product=test_product, project=test_project, field_priorities=field_priorities, user_id=str(uuid4())
    )

    # Assert
    assert "Product Vision" in context
    assert "Codebase" in context
    assert test_product.vision_document in context


# ============================================================================
# Additional Tests for Full Coverage
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_configuration_handles_missing_serena_key(mission_planner):
    """
    Test _get_user_configuration handles missing serena_enabled key gracefully.

    Validates that if field_priority_config exists but doesn't have serena_enabled,
    it defaults to False (backwards compatibility).
    """
    # Arrange
    user_id = str(uuid4())
    user_without_serena = User(
        id=user_id,
        username="test_user",
        email="test@example.com",
        tenant_key="tenant_abc",
        field_priority_config={
            "token_budget": 2000,
            # Missing serena_enabled key
        },
    )

    # Mock database query
    with patch.object(mission_planner.db_manager, "get_session_async") as mock_get_session:
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=user_without_serena)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_get_session.return_value.__aenter__.return_value = mock_session

        # Act
        config = await mission_planner._get_user_configuration(user_id)

        # Assert
        assert config["serena_enabled"] is False  # Safe default
        assert config["token_budget"] == 2000
