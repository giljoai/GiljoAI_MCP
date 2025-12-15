"""
Unit tests for fetch_context unified tool (Handover 0350a).

Tests the unified context dispatcher that replaces 9 individual tools
with a single entry point, saving ~720 tokens in MCP schema overhead.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


@pytest.mark.asyncio
async def test_fetch_context_all_categories():
    """Test fetching all categories via ['all'] parameter."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    # Mock all 9 internal tools
    mock_returns = {
        'get_product_context': {"data": {"product_name": "Test"}, "metadata": {"estimated_tokens": 100}},
        'get_vision_document': {"data": {"chunks": []}, "metadata": {"estimated_tokens": 500}},
        'get_tech_stack': {"data": {"languages": ["Python"]}, "metadata": {"estimated_tokens": 200}},
        'get_architecture': {"data": {"patterns": []}, "metadata": {"estimated_tokens": 300}},
        'get_testing': {"data": {"frameworks": []}, "metadata": {"estimated_tokens": 150}},
        'get_360_memory': {"data": {"history": []}, "metadata": {"estimated_tokens": 1000}},
        'get_git_history': {"data": {"commits": []}, "metadata": {"estimated_tokens": 800}},
        'get_agent_templates': {"data": {"templates": []}, "metadata": {"estimated_tokens": 400}},
        'get_project': {"data": {"project_name": "Test Project"}, "metadata": {"estimated_tokens": 250}},
    }

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=mock_returns['get_product_context']),
        get_vision_document=AsyncMock(return_value=mock_returns['get_vision_document']),
        get_tech_stack=AsyncMock(return_value=mock_returns['get_tech_stack']),
        get_architecture=AsyncMock(return_value=mock_returns['get_architecture']),
        get_testing=AsyncMock(return_value=mock_returns['get_testing']),
        get_360_memory=AsyncMock(return_value=mock_returns['get_360_memory']),
        get_git_history=AsyncMock(return_value=mock_returns['get_git_history']),
        get_agent_templates=AsyncMock(return_value=mock_returns['get_agent_templates']),
        get_project=AsyncMock(return_value=mock_returns['get_project']),
    ):
        result = await fetch_context(
            product_id="test-uuid-123",
            tenant_key="tenant-abc",
            categories=["all"],
            db_manager=MagicMock()
        )

        # Verify response structure
        assert result["source"] == "fetch_context"
        assert "data" in result
        assert "metadata" in result

        # Verify all 9 categories present
        assert len(result["data"]) == 9
        assert "product_core" in result["data"]
        assert "vision_documents" in result["data"]
        assert "tech_stack" in result["data"]
        assert "architecture" in result["data"]
        assert "testing" in result["data"]
        assert "memory_360" in result["data"]
        assert "git_history" in result["data"]
        assert "agent_templates" in result["data"]
        assert "project" in result["data"]

        # Verify token aggregation (sum of all categories)
        expected_tokens = sum(v["metadata"]["estimated_tokens"] for v in mock_returns.values())
        assert result["metadata"]["estimated_tokens"] == expected_tokens  # 3700 total


@pytest.mark.asyncio
async def test_fetch_context_specific_categories():
    """Test fetching only specified categories."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    mock_product = {"data": {"product_name": "Test"}, "metadata": {"estimated_tokens": 100}}
    mock_tech = {"data": {"languages": ["Python"]}, "metadata": {"estimated_tokens": 200}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=mock_product),
        get_tech_stack=AsyncMock(return_value=mock_tech),
        get_vision_document=AsyncMock(),  # Should NOT be called
    ) as mocks:
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack"],
            db_manager=MagicMock()
        )

        # Verify only requested categories returned
        assert len(result["data"]) == 2
        assert "product_core" in result["data"]
        assert "tech_stack" in result["data"]
        assert "vision_documents" not in result["data"]

        # Verify correct tools were called
        mocks['get_product_context'].assert_called_once()
        mocks['get_tech_stack'].assert_called_once()
        mocks['get_vision_document'].assert_not_called()

        # Verify token aggregation
        assert result["metadata"]["estimated_tokens"] == 300


@pytest.mark.asyncio
async def test_fetch_context_invalid_category():
    """Test error handling for invalid category names."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    result = await fetch_context(
        product_id="test-uuid",
        tenant_key="tenant-abc",
        categories=["invalid_category", "another_invalid"],
        db_manager=MagicMock()
    )

    # Should return error response
    assert "error" in result
    assert "invalid_category" in result["error"]
    assert "another_invalid" in result["error"]
    assert "valid_categories" in result
    assert result["metadata"]["estimated_tokens"] == 0


@pytest.mark.asyncio
async def test_fetch_context_depth_override():
    """Test depth_config overrides default depths."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    mock_vision = {"data": {"chunks": []}, "metadata": {"estimated_tokens": 5000}}
    mock_templates = {"data": {"templates": []}, "metadata": {"estimated_tokens": 400}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_vision_document=AsyncMock(return_value=mock_vision),
        get_agent_templates=AsyncMock(return_value=mock_templates),
    ) as mocks:
        await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["vision_documents", "agent_templates"],
            depth_config={
                "vision_documents": "light",
                "agent_templates": "minimal"
            },
            db_manager=MagicMock()
        )

        # Verify depth overrides passed to tools
        vision_call = mocks['get_vision_document'].call_args.kwargs
        assert vision_call.get("chunking") == "light"

        templates_call = mocks['get_agent_templates'].call_args.kwargs
        assert templates_call.get("detail") == "minimal"


@pytest.mark.asyncio
async def test_fetch_context_structured_format():
    """Test structured format returns nested data by category."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    mock_product = {"data": {"product_name": "Test", "features": ["A", "B"]}, "metadata": {"estimated_tokens": 100}}
    mock_tech = {"data": {"languages": ["Python", "JavaScript"]}, "metadata": {"estimated_tokens": 200}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=mock_product),
        get_tech_stack=AsyncMock(return_value=mock_tech),
    ):
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack"],
            format="structured",
            db_manager=MagicMock()
        )

        # Verify structured format (nested by category)
        assert result["metadata"]["format"] == "structured"
        assert isinstance(result["data"], dict)
        assert "product_core" in result["data"]
        assert "tech_stack" in result["data"]
        assert result["data"]["product_core"]["product_name"] == "Test"
        assert result["data"]["tech_stack"]["languages"] == ["Python", "JavaScript"]


@pytest.mark.asyncio
async def test_fetch_context_flat_format():
    """Test flat format merges all data with prefixed keys."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    mock_product = {"data": {"product_name": "Test", "features": ["A"]}, "metadata": {"estimated_tokens": 100}}
    mock_tech = {"data": {"languages": ["Python"]}, "metadata": {"estimated_tokens": 200}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=mock_product),
        get_tech_stack=AsyncMock(return_value=mock_tech),
    ):
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack"],
            format="flat",
            db_manager=MagicMock()
        )

        # Verify flat format (merged with category prefixes)
        assert result["metadata"]["format"] == "flat"
        assert isinstance(result["data"], dict)
        assert "product_core_product_name" in result["data"]
        assert "product_core_features" in result["data"]
        assert "tech_stack_languages" in result["data"]
        assert result["data"]["product_core_product_name"] == "Test"


@pytest.mark.asyncio
async def test_fetch_context_token_aggregation():
    """Test token counts are summed correctly across all categories."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    # Create varied token counts
    mock_returns = {
        'get_product_context': {"data": {}, "metadata": {"estimated_tokens": 100}},
        'get_tech_stack': {"data": {}, "metadata": {"estimated_tokens": 250}},
        'get_architecture': {"data": {}, "metadata": {"estimated_tokens": 500}},
    }

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=mock_returns['get_product_context']),
        get_tech_stack=AsyncMock(return_value=mock_returns['get_tech_stack']),
        get_architecture=AsyncMock(return_value=mock_returns['get_architecture']),
    ):
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack", "architecture"],
            db_manager=MagicMock()
        )

        # Verify token aggregation (100 + 250 + 500 = 850)
        assert result["metadata"]["estimated_tokens"] == 850


@pytest.mark.asyncio
async def test_fetch_context_error_handling():
    """Test errors from one tool don't crash entire fetch."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    mock_product = {"data": {"product_name": "Test"}, "metadata": {"estimated_tokens": 100}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=mock_product),
        get_tech_stack=AsyncMock(side_effect=Exception("Database error")),
        get_architecture=AsyncMock(return_value={"data": {}, "metadata": {"estimated_tokens": 300}}),
    ):
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack", "architecture"],
            db_manager=MagicMock()
        )

        # Should have successful categories
        assert "product_core" in result["data"]
        assert "architecture" in result["data"]

        # Failed category should be missing
        assert "tech_stack" not in result["data"]

        # Should have error metadata
        assert "errors" in result
        assert len(result["errors"]) == 1
        assert result["errors"][0]["category"] == "tech_stack"
        assert "Database error" in result["errors"][0]["error"]

        # Token count should only include successful categories
        assert result["metadata"]["estimated_tokens"] == 400  # 100 + 300


@pytest.mark.asyncio
async def test_fetch_context_default_categories():
    """Test default categories parameter behavior."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    # Create minimal mocks for all 9 tools
    minimal_mock = {"data": {}, "metadata": {"estimated_tokens": 0}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=minimal_mock),
        get_vision_document=AsyncMock(return_value=minimal_mock),
        get_tech_stack=AsyncMock(return_value=minimal_mock),
        get_architecture=AsyncMock(return_value=minimal_mock),
        get_testing=AsyncMock(return_value=minimal_mock),
        get_360_memory=AsyncMock(return_value=minimal_mock),
        get_git_history=AsyncMock(return_value=minimal_mock),
        get_agent_templates=AsyncMock(return_value=minimal_mock),
        get_project=AsyncMock(return_value=minimal_mock),
    ):
        # Call without categories parameter (should default to ["all"])
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            db_manager=MagicMock()
        )

        # Should fetch all 9 categories
        assert len(result["data"]) == 9


@pytest.mark.asyncio
async def test_fetch_context_project_category_requires_project_id():
    """Test project category validation requires project_id."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    with patch(
        'src.giljo_mcp.tools.context_tools.fetch_context.get_project',
        new_callable=AsyncMock
    ) as mock_project:
        # This should be handled gracefully inside _fetch_category
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["project"],
            project_id=None,  # Missing required parameter
            db_manager=MagicMock()
        )

        # Should handle missing project_id gracefully
        # (returns empty data with error in metadata)
        assert "project" in result["data"]
        # The tool should return empty data, not crash


@pytest.mark.asyncio
async def test_fetch_context_apply_user_config_false():
    """Test apply_user_config=False uses only default depths."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    mock_vision = {"data": {}, "metadata": {"estimated_tokens": 0}}

    with patch(
        'src.giljo_mcp.tools.context_tools.fetch_context.get_vision_document',
        new_callable=AsyncMock
    ) as mock_tool:
        mock_tool.return_value = mock_vision

        await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["vision_documents"],
            apply_user_config=False,
            db_manager=MagicMock()
        )

        # Verify default depth was used (medium)
        call_kwargs = mock_tool.call_args.kwargs
        assert call_kwargs.get("chunking") == "medium"


@pytest.mark.asyncio
async def test_fetch_context_metadata_includes_depth_config():
    """Test metadata includes applied depth configuration."""
    from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context

    minimal_mock = {"data": {}, "metadata": {"estimated_tokens": 0}}

    with patch.multiple(
        'src.giljo_mcp.tools.context_tools.fetch_context',
        get_product_context=AsyncMock(return_value=minimal_mock),
        get_tech_stack=AsyncMock(return_value=minimal_mock),
    ):
        result = await fetch_context(
            product_id="test-uuid",
            tenant_key="tenant-abc",
            categories=["product_core", "tech_stack"],
            depth_config={"tech_stack": "required"},
            apply_user_config=True,
            db_manager=MagicMock()
        )

        # Verify metadata includes depth config info
        assert "depth_config_applied" in result["metadata"]
        assert result["metadata"]["apply_user_config"] is True
        # Should show the effective depth (default + override)
        assert result["metadata"]["depth_config_applied"]["tech_stack"] == "required"
