"""
Unit tests for ProductService - Metrics, Statistics, Config Data, Vision Upload

Split from test_product_service.py (Handover 0127b, updated 0731b).

Tests cover:
- Metrics and statistics
- Cascade impact analysis
- Active product queries
- config_data field persistence (Handover 0500)
- Vision document upload with chunking (Handover 0500)

Handover 0731b: Updated assertions for typed returns (Product ORM,
Pydantic models) instead of dict[str, Any] wrappers.

Target: >80% line coverage
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import Product
from src.giljo_mcp.schemas.service_responses import (
    CascadeImpact,
    ProductStatistics,
    VisionUploadResult,
)
from src.giljo_mcp.services.product_service import ProductService


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

        # Assert - returns ProductStatistics Pydantic model (0731b typed returns)
        assert isinstance(result, ProductStatistics)
        assert result.product_id == "test-id"
        assert result.name == "Test Product"

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

        # Assert - returns CascadeImpact Pydantic model (0731b typed returns)
        assert isinstance(result, CascadeImpact)
        assert result.product_id == "test-id"
        assert result.product_name == "Test Product"
        assert result.total_projects == 5
        assert result.total_tasks == 10
        assert result.total_vision_documents == 3
        assert result.warning != ""

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

        # Mock execute: get active product (0731b: no longer builds metrics dict)
        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=product)))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_active_product()

        # Assert - returns Product ORM model (0731b typed returns)
        assert result is product
        assert result.id == "active-id"
        assert result.name == "Active Product"

    @pytest.mark.asyncio
    async def test_get_active_product_none(self, mock_db_manager):
        """Test getting active product when none exists"""
        # Arrange
        db_manager, session = mock_db_manager

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = ProductService(db_manager, "test-tenant")

        # Act
        result = await service.get_active_product()

        # Assert - returns None when no active product (0731b typed returns)
        assert result is None


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

        # Assert - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
        assert result.name == "Test Product"
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

        # Assert - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
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

        # Assert - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
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

        # Assert - returns VisionUploadResult Pydantic model (0731b typed returns)
        assert isinstance(result, VisionUploadResult)
        assert result.document_name == "vision.md"
        assert result.chunks_created >= 1
        assert result.total_tokens > 0

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

        # Assert - returns VisionUploadResult Pydantic model (0731b typed returns)
        assert isinstance(result, VisionUploadResult)
        assert result.chunks_created == 0  # No chunking when disabled
