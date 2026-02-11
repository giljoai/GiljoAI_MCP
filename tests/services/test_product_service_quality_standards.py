"""
Unit tests for ProductService.update_quality_standards method.

Handover 0316: Phase 5 - Service Layer Updates
Tests written FIRST following TDD discipline (RED -> GREEN -> REFACTOR).

Handover 0731b: Updated assertions for typed returns (Product ORM model)
instead of dict[str, Any] wrappers.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.models.products import Product


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)  # Don't suppress exceptions
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.mark.asyncio
async def test_update_quality_standards_success(mock_db_manager):
    """Test update_quality_standards updates quality_standards field successfully."""
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Mock product
    mock_product = MagicMock(spec=Product)
    mock_product.id = "test-product-id"
    mock_product.tenant_key = "test-tenant"
    mock_product.quality_standards = None

    # Session.get returns product
    session.get.return_value = mock_product

    # Create service
    service = ProductService(db_manager, tenant_key="test-tenant")

    # Update quality_standards
    result = await service.update_quality_standards(
        product_id="test-product-id", quality_standards="80% coverage, zero critical bugs", tenant_key="test-tenant"
    )

    # Verify product updated
    assert mock_product.quality_standards == "80% coverage, zero critical bugs"
    assert session.commit.called
    # 0731b: Returns Product ORM model
    assert isinstance(result, Product)
    assert result.quality_standards == "80% coverage, zero critical bugs"


@pytest.mark.asyncio
async def test_update_quality_standards_multi_tenant_isolation(mock_db_manager):
    """Test update_quality_standards enforces multi-tenant isolation."""
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Mock product with different tenant_key
    mock_product = MagicMock(spec=Product)
    mock_product.id = "test-product-id"
    mock_product.tenant_key = "other-tenant"  # Different tenant

    session.get.return_value = mock_product

    service = ProductService(db_manager, tenant_key="test-tenant")

    # Should raise ValueError (wrong tenant)
    with pytest.raises(ValueError, match="Product .* not found"):
        await service.update_quality_standards(
            product_id="test-product-id",
            quality_standards="Standards here",
            tenant_key="test-tenant",  # Different from product.tenant_key
        )


@pytest.mark.asyncio
async def test_update_quality_standards_product_not_found(mock_db_manager):
    """Test update_quality_standards handles missing product."""
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    session.get.return_value = None  # Product not found

    service = ProductService(db_manager, tenant_key="test-tenant")

    with pytest.raises(ValueError, match="Product .* not found"):
        await service.update_quality_standards(
            product_id="nonexistent-id", quality_standards="Standards", tenant_key="test-tenant"
        )


@pytest.mark.asyncio
async def test_update_quality_standards_emits_websocket_event(mock_db_manager):
    """Test update_quality_standards calls _emit_websocket_event for real-time UI updates."""
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    mock_product = MagicMock(spec=Product)
    mock_product.id = "test-product-id"
    mock_product.tenant_key = "test-tenant"
    mock_product.quality_standards = None

    session.get.return_value = mock_product

    service = ProductService(db_manager, tenant_key="test-tenant")

    # Mock the _emit_websocket_event method
    service._emit_websocket_event = AsyncMock()

    await service.update_quality_standards(
        product_id="test-product-id", quality_standards="80% coverage", tenant_key="test-tenant"
    )

    # Verify WebSocket event was called
    service._emit_websocket_event.assert_called_once()
    call_args = service._emit_websocket_event.call_args

    # Check call arguments
    assert call_args[1]["event_type"] == "product_updated"
    event_data = call_args[1]["data"]
    assert event_data["product_id"] == "test-product-id"
    assert "quality_standards" in event_data


@pytest.mark.asyncio
async def test_update_quality_standards_updates_existing_value(mock_db_manager):
    """Test update_quality_standards can update existing quality_standards."""
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    mock_product = MagicMock(spec=Product)
    mock_product.id = "test-product-id"
    mock_product.tenant_key = "test-tenant"
    mock_product.quality_standards = "Old standards: 70% coverage"

    session.get.return_value = mock_product

    service = ProductService(db_manager, tenant_key="test-tenant")

    result = await service.update_quality_standards(
        product_id="test-product-id",
        quality_standards="New standards: 90% coverage, TDD required",
        tenant_key="test-tenant",
    )

    # Verify old value replaced
    assert mock_product.quality_standards == "New standards: 90% coverage, TDD required"
    # 0731b: Returns Product ORM model
    assert isinstance(result, Product)
    assert result.quality_standards == "New standards: 90% coverage, TDD required"
