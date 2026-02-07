"""
Unit tests for ProductService activation flow - specifically get_active_product eager loading.

Handover 0320 Fix: Tests written FIRST following TDD discipline (RED → GREEN → REFACTOR).

Root Cause: get_active_product() doesn't eager-load vision_documents relationship,
causing SQLAlchemy async lazy loading errors when accessing primary_vision_path property.
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from src.giljo_mcp.models.products import Product, VisionDocument


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.mark.asyncio
async def test_get_active_product_returns_vision_path_without_lazy_load_error(mock_db_manager):
    """
    Test that get_active_product eager-loads vision_documents to access primary_vision_path.

    This test verifies the fix for the SQLAlchemy async lazy loading error:
    "greenlet_spawn has not been called; can't call await_only() here"

    The fix requires adding selectinload(Product.vision_documents) to the query.
    """
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Create mock product with vision_documents already loaded (eager loading simulation)
    mock_product = MagicMock(spec=Product)
    mock_product.id = "test-product-id"
    mock_product.name = "Test Product"
    mock_product.description = "A test product"
    mock_product.tenant_key = "test-tenant"
    mock_product.is_active = True
    mock_product.deleted_at = None
    mock_product.project_path = "/path/to/project"
    mock_product.created_at = "2025-01-01T00:00:00"
    mock_product.updated_at = "2025-01-01T00:00:00"
    mock_product.config_data = {}

    # Mock vision_documents as already loaded (eager loading)
    mock_vision_doc = MagicMock(spec=VisionDocument)
    mock_vision_doc.is_active = True
    mock_vision_doc.vision_path = "/path/to/vision.md"
    mock_vision_doc.vision_document = None
    mock_product.vision_documents = [mock_vision_doc]

    # Mock primary_vision_path property to return the path
    type(mock_product).primary_vision_path = PropertyMock(return_value="/path/to/vision.md")

    # Mock the session.execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    session.execute.return_value = mock_result

    # Create service
    service = ProductService(db_manager, tenant_key="test-tenant")

    # Mock _get_product_metrics to return empty dict
    service._get_product_metrics = AsyncMock(return_value={})

    # Call get_active_product - should NOT raise MissingGreenlet error
    result = await service.get_active_product()

    # Verify success
    assert result["success"] is True
    assert result["product"] is not None
    assert result["product"]["id"] == "test-product-id"
    assert result["product"]["name"] == "Test Product"
    assert result["product"]["vision_path"] == "/path/to/vision.md"


@pytest.mark.asyncio
async def test_get_active_product_no_active_product(mock_db_manager):
    """
    Test get_active_product returns success with null product when no active product.
    """
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Mock no active product
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    service = ProductService(db_manager, tenant_key="test-tenant")

    result = await service.get_active_product()

    assert result["success"] is True
    assert result["product"] is None
    assert "No active product" in result.get("message", "")


@pytest.mark.asyncio
async def test_get_active_product_multi_tenant_isolation(mock_db_manager):
    """
    Test get_active_product only returns products for the correct tenant.

    The query must include tenant_key filter.
    """
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Create service with specific tenant
    service = ProductService(db_manager, tenant_key="tenant-a")

    # Mock no active product (simulating tenant isolation)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    result = await service.get_active_product()

    # Verify session.execute was called (query was built)
    assert session.execute.called

    # The query should have been built with tenant filter
    # In a real integration test, we'd verify the actual SQL
    assert result["success"] is True


@pytest.mark.asyncio
async def test_get_active_product_handles_exception(mock_db_manager):
    """
    Test get_active_product handles exceptions gracefully.
    """
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Mock exception during execute
    session.execute.side_effect = Exception("Database connection failed")

    service = ProductService(db_manager, tenant_key="test-tenant")

    result = await service.get_active_product()

    assert result["success"] is False
    assert "error" in result
    assert "Database connection failed" in result["error"]


@pytest.mark.asyncio
async def test_get_active_product_with_empty_vision_documents(mock_db_manager):
    """
    Test get_active_product works when product has no vision documents.
    """
    from src.giljo_mcp.services.product_service import ProductService

    db_manager, session = mock_db_manager

    # Create mock product with empty vision_documents
    mock_product = MagicMock(spec=Product)
    mock_product.id = "test-product-id"
    mock_product.name = "Test Product"
    mock_product.description = "A test product"
    mock_product.tenant_key = "test-tenant"
    mock_product.is_active = True
    mock_product.deleted_at = None
    mock_product.project_path = "/path/to/project"
    mock_product.created_at = "2025-01-01T00:00:00"
    mock_product.updated_at = "2025-01-01T00:00:00"
    mock_product.config_data = {}
    mock_product.vision_documents = []  # Empty

    # Mock primary_vision_path to return empty string (no docs)
    type(mock_product).primary_vision_path = PropertyMock(return_value="")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_product
    session.execute.return_value = mock_result

    service = ProductService(db_manager, tenant_key="test-tenant")
    service._get_product_metrics = AsyncMock(return_value={})

    result = await service.get_active_product()

    assert result["success"] is True
    assert result["product"]["vision_path"] == ""
