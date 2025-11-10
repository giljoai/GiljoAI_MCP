"""
Unit tests for ProductService (Handover 0127b)

Tests cover:
- CRUD operations (create, get, list, update)
- Lifecycle management (activate, deactivate, delete, restore)
- Metrics and statistics
- Cascade impact analysis
- Error handling and edge cases

Target: >80% line coverage
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from uuid import uuid4

from giljo_mcp.services.product_service import ProductService
from giljo_mcp.models import Product, Project, Task, VisionDocument


class TestProductServiceCRUD:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_product_success(self):
        """Test successful product creation"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock no existing product
        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.create_product(
            name="Test Product",
            description="Test description",
            project_path="/test/path"
        )

        # Assert
        assert result["success"] is True
        assert "product_id" in result
        assert result["name"] == "Test Product"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_product_duplicate_name(self):
        """Test creating product with duplicate name fails"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock existing product with same name
        existing_product = Mock()
        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=existing_product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.create_product(
            name="Duplicate Product",
            description="Test"
        )

        # Assert
        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_get_product_success(self):
        """Test successful product retrieval"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock product
        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.description = "Test description"
        product.vision_path = None
        product.project_path = "/test"
        product.is_active = True
        product.config_data = {"key": "value"}
        product.created_at = datetime.now(timezone.utc)
        product.updated_at = datetime.now(timezone.utc)

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_product("test-id", include_metrics=False)

        # Assert
        assert result["success"] is True
        assert result["product"]["id"] == "test-id"
        assert result["product"]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_get_product_not_found(self):
        """Test get_product returns error when product not found"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_product("nonexistent-id")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_list_products_success(self):
        """Test successful product listing"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock products
        product1 = Mock()
        product1.id = "id1"
        product1.name = "Product 1"
        product1.description = "Desc 1"
        product1.vision_path = None
        product1.project_path = None
        product1.is_active = True
        product1.config_data = {}
        product1.created_at = datetime.now(timezone.utc)
        product1.updated_at = None

        session.execute = AsyncMock(return_value=Mock(
            scalars=Mock(return_value=Mock(
                all=Mock(return_value=[product1])
            ))
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.list_products(include_metrics=False)

        # Assert
        assert result["success"] is True
        assert len(result["products"]) == 1
        assert result["products"][0]["name"] == "Product 1"

    @pytest.mark.asyncio
    async def test_update_product_success(self):
        """Test successful product update"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock product
        product = Mock()
        product.id = "test-id"
        product.name = "Old Name"
        product.description = "Old Description"

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_product(
            "test-id",
            name="New Name",
            description="New Description"
        )

        # Assert
        assert result["success"] is True
        assert result["product"]["name"] == "New Name"
        session.commit.assert_awaited_once()


class TestProductServiceLifecycle:
    """Test lifecycle management"""

    @pytest.mark.asyncio
    async def test_activate_product_success(self):
        """Test successful product activation"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock target product
        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.is_active = False
        product.updated_at = None

        # Mock existing active product to deactivate
        active_product = Mock()
        active_product.is_active = True

        session.execute = AsyncMock(side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=product)),  # Get target product
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[active_product])))),  # Get active products
        ])
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.activate_product("test-id")

        # Assert
        assert result["success"] is True
        assert result["product"]["is_active"] is True
        assert result["deactivated_count"] == 1
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivate_product_success(self):
        """Test successful product deactivation"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.is_active = True

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.deactivate_product("test-id")

        # Assert
        assert result["success"] is True
        assert product.is_active is False
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_product_success(self):
        """Test successful product soft delete"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        product = Mock()
        product.id = "test-id"
        product.deleted_at = None
        product.is_active = True

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))
        session.commit = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.delete_product("test-id")

        # Assert
        assert result["success"] is True
        assert product.deleted_at is not None
        assert product.is_active is False
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_restore_product_success(self):
        """Test successful product restoration"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.deleted_at = datetime.now(timezone.utc)

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=product)
        ))
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.restore_product("test-id")

        # Assert
        assert result["success"] is True
        assert product.deleted_at is None
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_deleted_products(self):
        """Test listing soft-deleted products"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        # Mock deleted product
        product = Mock()
        product.id = "deleted-id"
        product.name = "Deleted Product"
        product.description = "Test"
        product.deleted_at = datetime.now(timezone.utc)

        # Mock execute calls
        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: get deleted products
                return AsyncMock(
                    scalars=Mock(return_value=Mock(
                        all=Mock(return_value=[product])
                    ))
                )
            else:  # Subsequent calls: count queries
                return AsyncMock(scalar=Mock(return_value=0))

        session.execute = mock_execute

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.list_deleted_products()

        # Assert
        assert result["success"] is True
        assert len(result["products"]) == 1
        assert "days_until_purge" in result["products"][0]


class TestProductServiceMetrics:
    """Test metrics and statistics"""

    @pytest.mark.asyncio
    async def test_get_product_statistics(self):
        """Test getting product statistics"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.is_active = True
        product.created_at = datetime.now(timezone.utc)
        product.updated_at = None

        # Mock execute calls for product and metrics
        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: get product
                return AsyncMock(scalar_one_or_none=Mock(return_value=product))
            else:  # Subsequent calls: count queries
                return AsyncMock(scalar=Mock(return_value=5))

        session.execute = mock_execute

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_product_statistics("test-id")

        # Assert
        assert result["success"] is True
        assert result["statistics"]["product_id"] == "test-id"
        assert result["statistics"]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_get_cascade_impact(self):
        """Test cascade impact analysis"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"

        # Mock execute calls
        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: get product
                return AsyncMock(scalar_one_or_none=Mock(return_value=product))
            else:  # Subsequent calls: count queries
                return AsyncMock(scalar=Mock(return_value=10))

        session.execute = mock_execute

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_cascade_impact("test-id")

        # Assert
        assert result["success"] is True
        assert result["impact"]["product_id"] == "test-id"
        assert "total_projects" in result["impact"]
        assert "warning" in result["impact"]

    @pytest.mark.asyncio
    async def test_get_active_product_found(self):
        """Test getting active product when one exists"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        product = Mock()
        product.id = "active-id"
        product.name = "Active Product"
        product.description = "Test"
        product.project_path = "/test"
        product.config_data = {}

        # Mock execute calls
        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: get active product
                return AsyncMock(scalar_one_or_none=Mock(return_value=product))
            else:  # Subsequent calls: metrics
                return AsyncMock(scalar=Mock(return_value=0))

        session.execute = mock_execute

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_active_product()

        # Assert
        assert result["success"] is True
        assert result["product"]["id"] == "active-id"
        assert result["product"]["name"] == "Active Product"

    @pytest.mark.asyncio
    async def test_get_active_product_none(self):
        """Test getting active product when none exists"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_active_product()

        # Assert
        assert result["success"] is True
        assert result["product"] is None
        assert "No active product" in result["message"]


class TestProductServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_create_product_database_error(self):
        """Test error handling in create_product"""
        # Arrange
        db_manager = Mock()

        db_manager.get_session_async = AsyncMock(
            side_effect=Exception("Database error")
        )

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.create_product(
            name="Test",
            description="Test"
        )

        # Assert
        assert result["success"] is False
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_activate_product_not_found(self):
        """Test activating nonexistent product"""
        # Arrange
        db_manager = Mock()
        session = AsyncMock()

        db_manager.get_session_async = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=session),
            __aexit__=AsyncMock()
        ))

        session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.activate_product("nonexistent-id")

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]
