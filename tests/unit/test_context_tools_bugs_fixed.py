"""
Unit tests for context tools bug fixes (Handover 0316 Phase 2)

Tests verify that get_tech_stack and get_architecture read from
Product.config_data JSONB column (not direct columns).

Bug 1: get_tech_stack.py accessed product.programming_languages (non-existent)
Bug 2: get_architecture.py accessed product.architecture_notes (non-existent)

Both should access product.config_data JSONB.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture
from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack


@pytest.mark.asyncio
async def test_get_tech_stack_from_config_data():
    """Test get_tech_stack reads from config_data JSONB (not direct columns)"""
    # Create properly configured mock
    mock_product = MagicMock()
    mock_product.config_data = {
        "tech_stack": {
            "languages": ["Python", "TypeScript"],
            "frontend": ["Vue 3"],
            "backend": ["FastAPI"],
            "database": ["PostgreSQL"],
            "infrastructure": ["Docker"],
            "dev_tools": ["Git"],
        }
    }

    # Mock database session and manager
    mock_session = AsyncMock()
    mock_result = MagicMock()  # NOT AsyncMock - scalar_one_or_none is synchronous
    mock_result.scalar_one_or_none.return_value = mock_product  # Regular return, not async
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Create async context manager
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    # Call the function (sections="all")
    result = await get_tech_stack(
        product_id="test-id", tenant_key="test-tenant", sections="all", db_manager=mock_db_manager
    )

    # Verify correct data extraction from config_data
    assert result["data"]["programming_languages"] == ["Python", "TypeScript"]
    assert result["data"]["frontend_frameworks"] == ["Vue 3"]
    assert result["data"]["backend_frameworks"] == ["FastAPI"]
    assert result["data"]["databases"] == ["PostgreSQL"]
    assert result["data"]["infrastructure"] == ["Docker"]
    assert result["data"]["dev_tools"] == ["Git"]
    assert result["metadata"]["estimated_tokens"] > 0


@pytest.mark.asyncio
async def test_get_tech_stack_required_sections():
    """Test get_tech_stack returns only required fields when sections='required'"""
    mock_product = MagicMock()
    mock_product.config_data = {
        "tech_stack": {
            "languages": ["Python"],
            "frontend": ["Vue 3"],
            "backend": ["FastAPI"],
            "database": ["PostgreSQL"],
        }
    }

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    # Call with sections="required"
    result = await get_tech_stack(
        product_id="test-id", tenant_key="test-tenant", sections="required", db_manager=mock_db_manager
    )

    # Should only return required fields
    assert result["data"]["programming_languages"] == ["Python"]
    assert result["data"]["frameworks"] == ["Vue 3", "FastAPI"]  # Combined frontend + backend
    assert result["data"]["database"] == ["PostgreSQL"]

    # Should NOT include infrastructure, dev_tools
    assert "infrastructure" not in result["data"]
    assert "dev_tools" not in result["data"]


@pytest.mark.asyncio
async def test_get_tech_stack_empty_config_data():
    """Test get_tech_stack handles empty config_data gracefully"""
    mock_product = MagicMock()
    mock_product.config_data = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    result = await get_tech_stack(
        product_id="test-id", tenant_key="test-tenant", sections="all", db_manager=mock_db_manager
    )

    # Should return empty lists, not crash
    assert result["data"]["programming_languages"] == []
    assert result["data"]["frontend_frameworks"] == []
    assert result["data"]["backend_frameworks"] == []
    assert result["data"]["databases"] == []


@pytest.mark.asyncio
async def test_get_tech_stack_missing_tech_stack_key():
    """Test get_tech_stack handles missing tech_stack key in config_data"""
    mock_product = MagicMock()
    mock_product.config_data = {"other_data": "value"}

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    result = await get_tech_stack(
        product_id="test-id", tenant_key="test-tenant", sections="all", db_manager=mock_db_manager
    )

    # Should return empty lists
    assert result["data"]["programming_languages"] == []
    assert result["data"]["frontend_frameworks"] == []


# ========== Architecture Tests ==========


@pytest.mark.asyncio
async def test_get_architecture_from_config_data():
    """Test get_architecture reads from config_data JSONB (not architecture_notes column)"""
    mock_product = MagicMock()
    mock_product.config_data = {
        "architecture": {
            "pattern": "Microservices",
            "design_patterns": "Repository, Service Layer",
            "api_style": "RESTful",
            "notes": "Full architecture notes here with detailed explanation...",
        }
    }

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    result = await get_architecture(
        product_id="test-id", tenant_key="test-tenant", depth="detailed", db_manager=mock_db_manager
    )

    # Verify correct data extraction
    assert result["data"]["primary_pattern"] == "Microservices"
    assert result["data"]["design_patterns"] == "Repository, Service Layer"
    assert result["data"]["api_style"] == "RESTful"
    assert result["data"]["architecture_notes"] == "Full architecture notes here with detailed explanation..."
    assert result["metadata"]["truncated"] is False


@pytest.mark.asyncio
async def test_get_architecture_overview_truncation():
    """Test get_architecture truncates long content in overview mode"""
    # Create long strings to trigger truncation
    long_design_patterns = "A" * 150  # > 100 chars
    long_notes = "B" * 300  # > 200 chars

    mock_product = MagicMock()
    mock_product.config_data = {
        "architecture": {
            "pattern": "Microservices",
            "design_patterns": long_design_patterns,
            "api_style": "RESTful",
            "notes": long_notes,
        }
    }

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    result = await get_architecture(
        product_id="test-id", tenant_key="test-tenant", depth="overview", db_manager=mock_db_manager
    )

    # Verify truncation occurred
    assert result["metadata"]["truncated"] is True
    assert len(result["data"]["design_patterns"]) <= 103  # 100 + "..."
    assert len(result["data"]["architecture_notes"]) <= 203  # 200 + "..."
    assert result["data"]["design_patterns"].endswith("...")
    assert result["data"]["architecture_notes"].endswith("...")


@pytest.mark.asyncio
async def test_get_architecture_empty_config_data():
    """Test get_architecture handles empty config_data gracefully"""
    mock_product = MagicMock()
    mock_product.config_data = None

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    result = await get_architecture(
        product_id="test-id", tenant_key="test-tenant", depth="detailed", db_manager=mock_db_manager
    )

    # Should return empty strings, not crash
    assert result["data"]["primary_pattern"] == ""
    assert result["data"]["design_patterns"] == ""
    assert result["data"]["api_style"] == ""
    assert result["data"]["architecture_notes"] == ""
    assert result["metadata"]["estimated_tokens"] == 0


@pytest.mark.asyncio
async def test_get_architecture_missing_architecture_key():
    """Test get_architecture handles missing architecture key in config_data"""
    mock_product = MagicMock()
    mock_product.config_data = {"other_data": "value"}

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_db_manager = Mock()
    mock_db_manager.get_session_async = Mock(return_value=mock_session)

    result = await get_architecture(
        product_id="test-id", tenant_key="test-tenant", depth="detailed", db_manager=mock_db_manager
    )

    # Should return empty strings
    assert result["data"]["primary_pattern"] == ""
    assert result["data"]["architecture_notes"] == ""
