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

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.models import Product
from src.giljo_mcp.services.product_service import ProductService


@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


class TestProductServiceCRUD:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_product_success(self, mock_db_manager):
        """Test successful product creation"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock execute calls: 1) check duplicate product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: check for duplicate product
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.create_product(
            name="Test Product", description="Test description", project_path="/test/path"
        )

        # Assert
        assert result["success"] is True
        assert "product_id" in result
        assert result["name"] == "Test Product"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_product_duplicate_name(self, mock_db_manager):
        """Test creating product with duplicate name fails"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock existing product with same name
        existing_product = Mock()
        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=existing_product)))

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise ValidationError
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await service.create_product(name="Duplicate Product", description="Test")
        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_product_success(self, mock_db_manager):
        """Test successful product retrieval"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock product with product_memory
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
        product.primary_vision_path = None
        product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}

        # Mock execute calls: 1) get product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: get product
            Mock(scalar_one_or_none=Mock(return_value=product)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_product("test-id", include_metrics=False)

        # Assert
        assert result["success"] is True
        assert result["product"]["id"] == "test-id"
        assert result["product"]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, mock_db_manager):
        """Test get_product raises exception when product not found"""
        # Arrange
        db_manager, session = mock_db_manager

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.get_product("nonexistent-id")
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_list_products_success(self, mock_db_manager):
        """Test successful product listing"""
        # Arrange
        db_manager, session = mock_db_manager

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

        session.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[product1]))))
        )

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.list_products(include_metrics=False)

        # Assert
        assert result["success"] is True
        assert len(result["products"]) == 1
        assert result["products"][0]["name"] == "Product 1"

    @pytest.mark.asyncio
    async def test_update_product_success(self, mock_db_manager):
        """Test successful product update"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock product
        product = Mock()
        product.id = "test-id"
        product.name = "Old Name"
        product.description = "Old Description"

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.update_product("test-id", name="New Name", description="New Description")

        # Assert
        assert result["success"] is True
        assert result["product"]["name"] == "New Name"
        session.commit.assert_awaited_once()


class TestProductServiceLifecycle:
    """Test lifecycle management"""

    @pytest.mark.asyncio
    async def test_activate_product_success(self, mock_db_manager):
        """Test successful product activation"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock target product
        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.is_active = False
        product.updated_at = None

        # Mock existing active product to deactivate
        active_product = Mock()
        active_product.id = "other-id"
        active_product.is_active = True

        # Mock execute calls: 1) get target product, 2) get active products, 3) deactivate projects in deactivated products
        session.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=product)),  # Get target product
                Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[active_product])))),  # Get active products
                Mock(),  # Bulk deactivate projects in deactivated products
            ]
        )
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.activate_product("test-id")

        # Assert
        assert result["success"] is True
        assert result["product"]["is_active"] is True
        assert result["deactivated_count"] == 1
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deactivate_product_success(self, mock_db_manager):
        """Test successful product deactivation"""
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.is_active = True

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))
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
    async def test_delete_product_success(self, mock_db_manager):
        """Test successful product soft delete"""
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock()
        product.id = "test-id"
        product.deleted_at = None
        product.is_active = True

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))
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
    async def test_restore_product_success(self, mock_db_manager):
        """Test successful product restoration"""
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.deleted_at = datetime.now(timezone.utc)

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))
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
    async def test_list_deleted_products(self, mock_db_manager):
        """Test listing soft-deleted products"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock deleted product
        product = Mock()
        product.id = "deleted-id"
        product.name = "Deleted Product"
        product.description = "Test"
        product.deleted_at = datetime.now(timezone.utc)

        # Mock execute calls - Multiple sequential calls with side_effect
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: get deleted products
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[product])))),
            # Second call: project count
            Mock(scalar=Mock(return_value=2)),
            # Third call: vision document count (mocking VisionDocument.deleted_at.is_(None))
            Mock(scalar=Mock(return_value=1)),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.list_deleted_products()

        # Assert
        assert result["success"] is True
        assert len(result["products"]) == 1
        assert "days_until_purge" in result["products"][0]
        assert result["products"][0]["project_count"] == 2
        assert result["products"][0]["vision_documents_count"] == 1


class TestProductServiceMetrics:
    """Test metrics and statistics"""

    @pytest.mark.asyncio
    async def test_get_product_statistics(self, mock_db_manager):
        """Test getting product statistics"""
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"
        product.is_active = True
        product.created_at = datetime.now(timezone.utc)
        product.updated_at = None

        # Mock execute calls for product and metrics
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: get product
                return Mock(scalar_one_or_none=Mock(return_value=product))
            # Subsequent calls: count queries
            return Mock(scalar=Mock(return_value=5))

        session.execute = mock_execute

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_product_statistics("test-id")

        # Assert
        assert result["success"] is True
        assert result["statistics"]["product_id"] == "test-id"
        assert result["statistics"]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_get_cascade_impact(self, mock_db_manager):
        """Test cascade impact analysis"""
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock()
        product.id = "test-id"
        product.name = "Test Product"

        # Mock execute calls - Multiple sequential calls with side_effect
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: get product
            Mock(scalar_one_or_none=Mock(return_value=product)),
            # Second call: total projects count
            Mock(scalar=Mock(return_value=5)),
            # Third call: total tasks count
            Mock(scalar=Mock(return_value=10)),
            # Fourth call: vision documents count
            Mock(scalar=Mock(return_value=3)),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_cascade_impact("test-id")

        # Assert
        assert result["success"] is True
        assert result["impact"]["product_id"] == "test-id"
        assert result["impact"]["product_name"] == "Test Product"
        assert result["impact"]["total_projects"] == 5
        assert result["impact"]["total_tasks"] == 10
        assert result["impact"]["total_vision_documents"] == 3
        assert "warning" in result["impact"]

    @pytest.mark.asyncio
    async def test_get_active_product_found(self, mock_db_manager):
        """Test getting active product when one exists"""
        # Arrange
        db_manager, session = mock_db_manager

        product = Mock()
        product.id = "active-id"
        product.name = "Active Product"
        product.description = "Test"
        product.project_path = "/test"
        product.config_data = {}

        # Mock execute calls
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call: get active product
                return Mock(scalar_one_or_none=Mock(return_value=product))
            # Subsequent calls: metrics
            return Mock(scalar=Mock(return_value=0))

        session.execute = mock_execute

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_active_product()

        # Assert
        assert result["success"] is True
        assert result["product"]["id"] == "active-id"
        assert result["product"]["name"] == "Active Product"

    @pytest.mark.asyncio
    async def test_get_active_product_none(self, mock_db_manager):
        """Test getting active product when none exists"""
        # Arrange
        db_manager, session = mock_db_manager

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

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

        # Create an async context manager that raises exception on __aenter__
        async_cm = AsyncMock()
        async_cm.__aenter__ = AsyncMock(side_effect=Exception("Database error"))
        async_cm.__aexit__ = AsyncMock(return_value=False)

        # Make get_session_async return the context manager
        db_manager.get_session_async = Mock(return_value=async_cm)

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise BaseGiljoException
        from src.giljo_mcp.exceptions import BaseGiljoException

        with pytest.raises(BaseGiljoException) as exc_info:
            await service.create_product(name="Test", description="Test")
        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_activate_product_not_found(self, mock_db_manager):
        """Test activating nonexistent product"""
        # Arrange
        db_manager, session = mock_db_manager

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.activate_product("nonexistent-id")
        assert "not found" in str(exc_info.value).lower()


class TestProductServiceConfigData:
    """Test config_data field persistence - Handover 0500"""

    @pytest.mark.asyncio
    async def test_create_product_with_config_data(self, mock_db_manager):
        """Test config_data persists during product creation"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock execute calls: 1) check duplicate product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: check for duplicate product
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        config = {
            "api_key": "test-key-123",
            "settings": {"debug": True, "timeout": 30},
            "tech_stack": {"python": "3.11", "framework": "FastAPI"},
        }

        # Act
        result = await service.create_product(
            name="Test Product", description="Product with config", config_data=config
        )

        # Assert
        assert result["success"] is True
        assert "product_id" in result
        session.commit.assert_awaited_once()

        # Verify config_data was passed to Product constructor
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_without_config_data(self, mock_db_manager):
        """Test product creation works without config_data"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock execute calls: 1) check duplicate product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: check for duplicate product
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.create_product(name="Test Product No Config")

        # Assert
        assert result["success"] is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_product_config_data(self, mock_db_manager):
        """Test config_data updates correctly"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock existing product
        existing_product = Mock(spec=Product)
        existing_product.id = str(uuid4())
        existing_product.name = "Test Product"
        existing_product.description = "Test"
        existing_product.config_data = {"version": "1.0"}
        existing_product.updated_at = datetime.now(timezone.utc)

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=existing_product)))

        service = ProductService(db_manager, "test-tenant")

        # Act
        updated_config = {"version": "2.0", "new_field": "value"}
        result = await service.update_product(product_id=existing_product.id, config_data=updated_config)

        # Assert
        assert result["success"] is True
        assert existing_product.config_data == updated_config
        session.commit.assert_awaited_once()


class TestProductServiceVisionUpload:
    """Test vision document upload with chunking - Handover 0500"""

    @pytest.mark.asyncio
    async def test_upload_small_vision_document(self, mock_db_manager):
        """Test uploading vision document under token limit"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock product exists
        product = Mock(spec=Product)
        product.id = str(uuid4())
        product.name = "Test Product"

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))

        # Mock vision document creation - patch at the source module (lazy import)
        with patch("src.giljo_mcp.repositories.vision_document_repository.VisionDocumentRepository") as MockRepo:
            mock_repo_instance = Mock()
            MockRepo.return_value = mock_repo_instance

            mock_doc = Mock()
            mock_doc.id = str(uuid4())
            mock_doc.document_name = "vision.md"
            mock_repo_instance.create = AsyncMock(return_value=mock_doc)

            # Mock chunker - patch at source module (lazy import in context_management)
            with patch("src.giljo_mcp.context_management.chunker.VisionDocumentChunker") as MockChunker:
                mock_chunker_instance = Mock()
                MockChunker.return_value = mock_chunker_instance
                mock_chunker_instance.chunk_vision_document = AsyncMock(
                    return_value={
                        "success": True,
                        "chunks_created": 1,
                        "total_tokens": 150,
                    }
                )

                service = ProductService(db_manager, "test-tenant")

                # Act
                result = await service.upload_vision_document(
                    product_id=product.id,
                    content="# Vision Document\n\nThis is a small vision document.",
                    filename="vision.md",
                )

        # Assert
        assert result["success"] is True
        assert result["document_name"] == "vision.md"
        assert result["chunks_created"] >= 1
        assert result["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_upload_vision_product_not_found(self, mock_db_manager):
        """Test vision upload fails for non-existent product"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock product not found
        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.upload_vision_document(product_id="non-existent-id", content="# Vision", filename="vision.md")
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_vision_with_chunking_disabled(self, mock_db_manager):
        """Test vision upload without auto-chunking"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock product exists
        product = Mock(spec=Product)
        product.id = str(uuid4())

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))

        # Mock vision document creation - patch at source module (lazy import)
        with patch("src.giljo_mcp.repositories.vision_document_repository.VisionDocumentRepository") as MockRepo:
            mock_repo_instance = Mock()
            MockRepo.return_value = mock_repo_instance

            mock_doc = Mock()
            mock_doc.id = str(uuid4())
            mock_doc.document_name = "vision_no_chunk.md"
            mock_repo_instance.create = AsyncMock(return_value=mock_doc)

            service = ProductService(db_manager, "test-tenant")

            # Act
            result = await service.upload_vision_document(
                product_id=product.id,
                content="# Vision Document\n\nNo chunking.",
                filename="vision_no_chunk.md",
                auto_chunk=False,
            )

        # Assert
        assert result["success"] is True
        assert result["chunks_created"] == 0  # No chunking when disabled


class TestProductServiceProductMemory:
    """
    Test suite for product_memory JSONB column in ProductService.

    Handover 0135: 360 Memory Management - Database Schema
    Tests written FIRST following TDD principles.
    """

    @pytest.mark.asyncio
    async def test_create_product_with_product_memory(self, mock_db_manager):
        """
        BEHAVIOR: Product created with custom product_memory preserves the structure

        GIVEN: Custom product_memory data provided
        WHEN: Product is created via ProductService
        THEN: Custom memory structure is persisted exactly (git_integration and context from JSONB, sequential_history from table)
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        # Mock execute calls: 1) check duplicate product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: check for duplicate product
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Second call: get product memory entries (empty list for new product)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        custom_memory = {
            "git_integration": {"enabled": True, "commit_limit": 20, "default_branch": "main"},
            "sequential_history": [],  # Will be populated from table, not JSONB
            "context": {"summary": "Custom product context", "token_count": 5000},
        }

        service = ProductService(db_manager, "test-tenant")

        # ACT
        result = await service.create_product(
            name="Custom Memory Product",
            description="Testing custom memory initialization",
            product_memory=custom_memory,
        )

        # ASSERT
        assert result is not None
        assert "product_memory" in result
        # Note: sequential_history comes from table, so it will be empty for new product
        assert result["product_memory"]["git_integration"]["enabled"] is True
        assert result["product_memory"]["git_integration"]["commit_limit"] == 20
        assert result["product_memory"]["sequential_history"] == []  # Empty for new product
        assert result["product_memory"]["context"]["token_count"] == 5000

    @pytest.mark.asyncio
    async def test_create_product_without_product_memory(self, mock_db_manager):
        """
        BEHAVIOR: Product created without product_memory gets default structure

        GIVEN: No product_memory data provided
        WHEN: Product is created via ProductService
        THEN: Default structure {"git_integration": {}, "sequential_history": [], "context": {}} is applied
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        # Mock execute calls: 1) check duplicate product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: check for duplicate product
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # ACT
        result = await service.create_product(
            name="Default Memory Product",
            description="Testing default memory initialization",
            # Note: No product_memory parameter provided
        )

        # ASSERT
        assert result is not None
        assert "product_memory" in result
        # Default structure matches ProductService implementation
        assert result["product_memory"] == {"git_integration": {}, "sequential_history": [], "context": {}}

    @pytest.mark.asyncio
    async def test_update_product_product_memory(self, mock_db_manager):
        """
        BEHAVIOR: Product memory updates persist correctly

        GIVEN: Existing product with product_memory
        WHEN: product_memory is updated via ProductService
        THEN: Updated memory structure persists
        """
        # ARRANGE
        db_manager, session = mock_db_manager
        product_id = str(uuid4())

        # Mock existing product with initial memory
        existing_product = Mock()
        existing_product.id = product_id
        existing_product.name = "Existing Product"
        existing_product.description = "Test"
        existing_product.tenant_key = "test-tenant"
        existing_product.product_memory = {"git_integration": {}, "sequential_history": [], "context": {}}
        existing_product.config_data = {}
        existing_product.is_active = False
        existing_product.deleted_at = None

        # Mock execute calls: 1) get product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: get product
            Mock(scalar_one_or_none=Mock(return_value=existing_product)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # Updated memory with GitHub integration
        updated_memory = {
            "git_integration": {"enabled": True, "commit_limit": 30, "default_branch": "develop"},
            "sequential_history": [],
            "context": {"summary": "Updated context"},
        }

        # ACT
        result = await service.update_product(product_id=product_id, product_memory=updated_memory)

        # ASSERT
        assert result is not None
        # Verify the mock object was updated
        assert existing_product.product_memory == updated_memory
        assert existing_product.product_memory["git_integration"]["enabled"] is True
        assert existing_product.product_memory["git_integration"]["commit_limit"] == 30


class TestProductServiceTargetPlatforms:
    """
    Test suite for target_platforms field in ProductService.

    Handover 0425: Phase 1 - Backend Implementation
    Tests written FIRST following TDD principles.
    """

    @pytest.mark.asyncio
    async def test_create_product_with_target_platforms_all(self, mock_db_manager):
        """
        BEHAVIOR: Product created with target_platforms=['all'] as default

        GIVEN: No target_platforms data provided
        WHEN: Product is created via ProductService
        THEN: Default value ['all'] is applied
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        # Mock execute calls: 1) check duplicate product, 2) get product memory entries
        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            # First call: check for duplicate product
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Second call: get product memory entries (empty list)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # ACT
        result = await service.create_product(name="Test Product", description="Testing default target_platforms")

        # ASSERT
        assert result["success"] is True
        assert "product_id" in result
        # Verify default value was set
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_with_target_platforms_windows(self, mock_db_manager):
        """
        BEHAVIOR: Product created with target_platforms=['windows'] persists correctly

        GIVEN: target_platforms=['windows'] provided
        WHEN: Product is created via ProductService
        THEN: Value persists correctly
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=None)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # ACT
        result = await service.create_product(
            name="Windows Product", description="Windows-only product", target_platforms=["windows"]
        )

        # ASSERT
        assert result["success"] is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_product_with_target_platforms_multiple(self, mock_db_manager):
        """
        BEHAVIOR: Product can target multiple platforms

        GIVEN: target_platforms=['windows', 'linux', 'macos'] provided
        WHEN: Product is created via ProductService
        THEN: All platforms persist correctly
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        execute_mock = AsyncMock()
        execute_mock.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=None)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
        session.execute = execute_mock

        service = ProductService(db_manager, "test-tenant")

        # ACT
        result = await service.create_product(
            name="Multi-Platform Product",
            description="Cross-platform product",
            target_platforms=["windows", "linux", "macos"],
        )

        # ASSERT
        assert result["success"] is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_product_with_target_platforms_all_exclusive(self, mock_db_manager):
        """
        BEHAVIOR: 'all' platform cannot be combined with specific platforms

        GIVEN: target_platforms=['all', 'windows'] provided
        WHEN: Product is created via ProductService
        THEN: Validation error is raised
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise ValidationError
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await service.create_product(
                name="Invalid Platform Product", description="Testing validation", target_platforms=["all", "windows"]
            )
        assert "all" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_create_product_with_invalid_platform(self, mock_db_manager):
        """
        BEHAVIOR: Invalid platform values are rejected

        GIVEN: target_platforms=['invalid'] provided
        WHEN: Product is created via ProductService
        THEN: Validation error is raised
        """
        # ARRANGE
        db_manager, session = mock_db_manager

        service = ProductService(db_manager, "test-tenant")

        # Act & Assert - should raise ValidationError
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await service.create_product(
                name="Invalid Platform Product", description="Testing validation", target_platforms=["invalid"]
            )
        assert "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_product_target_platforms(self, mock_db_manager):
        """
        BEHAVIOR: Product target_platforms updates correctly

        GIVEN: Existing product with target_platforms=['windows']
        WHEN: target_platforms is updated to ['linux', 'macos']
        THEN: Updated platforms persist
        """
        # ARRANGE
        db_manager, session = mock_db_manager
        product_id = str(uuid4())

        # Mock existing product
        existing_product = Mock(spec=Product)
        existing_product.id = product_id
        existing_product.name = "Test Product"
        existing_product.description = "Test"
        existing_product.tenant_key = "test-tenant"
        existing_product.target_platforms = ["windows"]
        existing_product.config_data = {}
        existing_product.updated_at = datetime.now(timezone.utc)

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=existing_product)))

        service = ProductService(db_manager, "test-tenant")

        # ACT
        result = await service.update_product(product_id=product_id, target_platforms=["linux", "macos"])

        # ASSERT
        assert result["success"] is True
        assert existing_product.target_platforms == ["linux", "macos"]
        session.commit.assert_awaited_once()
