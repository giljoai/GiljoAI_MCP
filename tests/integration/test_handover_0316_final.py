"""
Final integration tests for Handover 0316 - Context Field Alignment.

Verifies:
1. All 9 context tools are importable and callable
2. Product model has quality_standards field (Phase 1)
3. ProductService.update_quality_standards() exists (Phase 5)
4. Bug fixes: get_tech_stack and get_architecture use config_data (Phase 2)
5. New tools: get_product_context, get_project, get_testing work (Phase 3)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.models.products import Product


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_9_context_tools_importable():
    """Test all 9 context tools can be imported without errors (Handover 0316 alignment fix)."""
    from src.giljo_mcp.tools.context_tools import (
        get_360_memory,
        get_agent_templates,
        get_architecture,
        get_git_history,
        get_product_context,
        get_project,
        get_tech_stack,
        get_testing,
        get_vision_document,
    )

    # Verify all 9 tools are callable functions
    tools = [
        get_360_memory,
        get_agent_templates,
        get_architecture,
        get_git_history,
        get_product_context,
        get_project,
        get_tech_stack,
        get_testing,
        get_vision_document,
    ]

    for tool in tools:
        assert callable(tool), f"{tool.__name__} is not callable"

    assert len(tools) == 9, f"Expected 9 context tools, found {len(tools)}"


@pytest.mark.integration
def test_product_model_has_quality_standards_field():
    """Test Product model has quality_standards field (Handover 0316 Phase 1)."""
    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test Product",
        description="Test",
        quality_standards="80% coverage required",
    )

    assert hasattr(product, "quality_standards")
    assert product.quality_standards == "80% coverage required"


@pytest.mark.integration
def test_product_config_data_field_exists():
    """Test Product model has config_data JSONB field."""
    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test Product",
        config_data={"tech_stack": {"languages": ["Python"]}, "architecture": {"pattern": "Microservices"}},
    )

    assert hasattr(product, "config_data")
    assert product.config_data is not None
    assert "tech_stack" in product.config_data
    assert "architecture" in product.config_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_product_service_update_quality_standards_exists():
    """Test ProductService has update_quality_standards method."""
    from src.giljo_mcp.services.product_service import ProductService

    assert hasattr(ProductService, "update_quality_standards")

    import inspect

    assert inspect.iscoroutinefunction(ProductService.update_quality_standards)


@pytest.mark.integration
def test_context_tools_registered_in_init():
    """Test all 9 context tools are registered in __init__.py."""
    from src.giljo_mcp.tools import context_tools

    expected_tools = [
        "get_360_memory",
        "get_agent_templates",
        "get_architecture",
        "get_git_history",
        "get_product_context",
        "get_project",
        "get_tech_stack",
        "get_testing",
        "get_vision_document",
    ]

    for tool_name in expected_tools:
        assert hasattr(context_tools, tool_name), f"{tool_name} not exported from context_tools __init__.py"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bug_fix_get_tech_stack_uses_config_data():
    """Test get_tech_stack reads from config_data (Bug Fix Phase 2)."""
    from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack

    db_manager = MagicMock()
    session = AsyncMock()

    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test",
        config_data={
            "tech_stack": {
                "languages": ["Python", "TypeScript"],
                "frontend": ["Vue 3"],
                "backend": ["FastAPI"],
                "database": ["PostgreSQL"],
            }
        },
    )

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=product)
    session.execute = AsyncMock(return_value=mock_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = MagicMock(return_value=session)

    result = await get_tech_stack(product_id="test-id", tenant_key="test-tenant", sections="all", db_manager=db_manager)

    assert result["data"]["programming_languages"] == ["Python", "TypeScript"]
    assert result["data"]["frontend_frameworks"] == ["Vue 3"]
    assert result["data"]["backend_frameworks"] == ["FastAPI"]
    assert result["data"]["databases"] == ["PostgreSQL"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bug_fix_get_architecture_uses_config_data():
    """Test get_architecture reads from config_data (Bug Fix Phase 2)."""
    from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture

    db_manager = MagicMock()
    session = AsyncMock()

    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test",
        config_data={
            "architecture": {
                "pattern": "Microservices",
                "design_patterns": "Repository, Service Layer",
                "api_style": "RESTful",
                "notes": "Test architecture notes",
            }
        },
    )

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=product)
    session.execute = AsyncMock(return_value=mock_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = MagicMock(return_value=session)

    result = await get_architecture(
        product_id="test-id", tenant_key="test-tenant", depth="detailed", db_manager=db_manager
    )

    assert result["data"]["primary_pattern"] == "Microservices"
    assert result["data"]["design_patterns"] == "Repository, Service Layer"
    assert result["data"]["api_style"] == "RESTful"
    assert result["data"]["architecture_notes"] == "Test architecture notes"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_tool_get_product_context():
    """Test new get_product_context tool (Phase 3)."""
    from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context

    db_manager = MagicMock()
    session = AsyncMock()

    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test Product",
        description="Test Description",
        config_data={"features": {"core": ["Feature 1", "Feature 2"]}},
    )

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=product)
    session.execute = AsyncMock(return_value=mock_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = MagicMock(return_value=session)

    result = await get_product_context(
        product_id="test-id", tenant_key="test-tenant", include_metadata=False, db_manager=db_manager
    )

    assert result["source"] == "product_context"
    assert result["data"]["product_name"] == "Test Product"
    assert result["data"]["product_description"] == "Test Description"  # Correct key name
    assert result["data"]["core_features"] == ["Feature 1", "Feature 2"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_tool_get_testing():
    """Test new get_testing tool (Phase 3)."""
    from src.giljo_mcp.tools.context_tools.get_testing import get_testing

    db_manager = MagicMock()
    session = AsyncMock()

    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test Product",
        quality_standards="80% coverage",
        config_data={"test_config": {"strategy": "TDD", "coverage_target": 80, "frameworks": ["pytest", "jest"]}},
    )

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=product)
    session.execute = AsyncMock(return_value=mock_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = MagicMock(return_value=session)

    result = await get_testing(product_id="test-id", tenant_key="test-tenant", depth="full", db_manager=db_manager)

    assert result["source"] == "testing"
    assert result["data"]["quality_standards"] == "80% coverage"
    assert result["data"]["testing_strategy"] == "TDD"
    assert result["data"]["coverage_target"] == 80
    assert result["data"]["testing_frameworks"] == ["pytest", "jest"]
