"""
Simplified integration tests for Handover 0316.

Tests basic functionality without complex mocking.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_9_context_tools_importable():
    """Test all 9 context tools can be imported without errors (Handover 0316 alignment fix)."""
    # This test verifies no import errors
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

    # Verify all 9 functions are callable (imported directly from __init__.py)
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
        assert callable(tool), f"{tool.__name__ if hasattr(tool, '__name__') else tool} is not callable"

    assert len(tools) == 9, f"Expected 9 context tools, found {len(tools)}"


@pytest.mark.integration
def test_product_model_has_quality_standards_field():
    """Test Product model has quality_standards field (Handover 0316 Phase 1)."""
    # Create product instance
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
def test_project_model_context_budget_field_deprecated():
    """Test Project model has context_budget field but it's deprecated (Handover 0316)."""
    project = Project(
        id="test-id",
        tenant_key="test-tenant",
        product_id="product-id",
        name="Test Project",
        alias="ABC123",
        description="Test",
        mission="Test mission",
    )

    # context_budget field exists but is deprecated (will be removed in v4.0)
    assert hasattr(project, "context_budget"), "context_budget field exists (deprecated, will be removed in v4.0)"

    # Verify field is not returned in get_project context tool output (tested in E2E tests)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_product_service_update_quality_standards_exists():
    """Test ProductService has update_quality_standards method."""
    from src.giljo_mcp.services.product_service import ProductService

    # Verify method exists
    assert hasattr(ProductService, "update_quality_standards")

    # Verify it's an async method
    import inspect

    assert inspect.iscoroutinefunction(ProductService.update_quality_standards)


@pytest.mark.integration
def test_context_tools_registered_in_init():
    """Test all 9 context tools are registered in __init__.py."""
    from src.giljo_mcp.tools import context_tools

    # Check __init__.py exports all 9 tools
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
    """Test get_tech_stack reads from config_data (not direct columns)."""
    from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack

    # Create mock db_manager with session
    db_manager = MagicMock()
    session = AsyncMock()

    # Create product with config_data
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

    # Mock session.execute to return product
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=product)
    session.execute = AsyncMock(return_value=mock_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = MagicMock(return_value=session)

    # Call get_tech_stack
    result = await get_tech_stack(product_id="test-id", tenant_key="test-tenant", sections="all", db_manager=db_manager)

    # Verify it extracted data from config_data
    assert result["data"]["programming_languages"] == ["Python", "TypeScript"]
    assert result["data"]["frontend_frameworks"] == ["Vue 3"]
    assert result["data"]["backend_frameworks"] == ["FastAPI"]
    assert result["data"]["databases"] == ["PostgreSQL"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bug_fix_get_architecture_uses_config_data():
    """Test get_architecture reads from config_data (not direct columns)."""
    from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture

    # Create mock db_manager
    db_manager = MagicMock()
    session = AsyncMock()

    # Create product with config_data
    product = Product(
        id="test-id",
        tenant_key="test-tenant",
        name="Test",
        config_data={
            "architecture": {
                "pattern": "Microservices",
                "design_patterns": "Repository, Service Layer",
                "api_style": "RESTful",
                "notes": "Test notes",
            }
        },
    )

    # Mock session
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=product)
    session.execute = AsyncMock(return_value=mock_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    db_manager.get_session_async = MagicMock(return_value=session)

    # Call get_architecture
    result = await get_architecture(
        product_id="test-id", tenant_key="test-tenant", depth="detailed", db_manager=db_manager
    )

    # Verify it extracted data from config_data
    assert result["data"]["primary_pattern"] == "Microservices"
    assert result["data"]["design_patterns"] == "Repository, Service Layer"
    assert result["data"]["api_style"] == "RESTful"
    assert result["data"]["architecture_notes"] == "Test notes"
