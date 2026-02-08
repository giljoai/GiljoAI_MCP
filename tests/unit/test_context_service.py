"""
Unit tests for ContextService (Handover 0730b - Exception-based error handling)

Tests cover:
- Context index stub functionality
- Vision document stub functionality
- Product settings stub functionality
- Exception-based error handling (no dict wrappers)

Target: >80% line coverage

Note: Most methods are stubs that return data directly (no success wrappers).
"""

from unittest.mock import Mock

import pytest

from src.giljo_mcp.services.context_service import (
    ContextService,
    ContextIndex,
    VisionDocument,
    VisionIndex,
    ProductSettings,
)


class TestContextServiceStubs:
    """Test stub functionality"""

    @pytest.mark.asyncio
    async def test_get_context_index_returns_empty_stub(self):
        """Test that get_context_index returns empty index stub"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_context_index(product_id="prod-123")

        # Assert
        assert isinstance(result, ContextIndex)
        assert result.documents == []
        assert result.sections == []

    @pytest.mark.asyncio
    async def test_get_context_index_without_product_id(self):
        """Test get_context_index works without product_id"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_context_index()

        # Assert
        assert isinstance(result, ContextIndex)
        assert result.documents == []
        assert result.sections == []

    @pytest.mark.asyncio
    async def test_get_vision_returns_placeholder(self):
        """Test that get_vision returns placeholder content"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_vision(part=1, max_tokens=10000)

        # Assert
        assert isinstance(result, VisionDocument)
        assert result.part == 1
        assert result.total_parts == 1
        assert result.content == "Vision document placeholder"
        assert result.tokens == 100

    @pytest.mark.asyncio
    async def test_get_vision_with_different_part(self):
        """Test get_vision with different part number"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_vision(part=3, max_tokens=5000)

        # Assert
        assert isinstance(result, VisionDocument)
        assert result.part == 3

    @pytest.mark.asyncio
    async def test_get_vision_index_returns_empty_stub(self):
        """Test that get_vision_index returns empty index"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_vision_index()

        # Assert
        assert isinstance(result, VisionIndex)
        assert result.files == []
        assert result.chunks == []

    @pytest.mark.asyncio
    async def test_get_product_settings_returns_placeholder(self):
        """Test that get_product_settings returns placeholder settings"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_product_settings(product_id="prod-123")

        # Assert
        assert isinstance(result, ProductSettings)
        assert result.product_id == "prod-123"
        assert result.config == {}

    @pytest.mark.asyncio
    async def test_get_product_settings_without_product_id(self):
        """Test get_product_settings returns default when no product_id provided"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act
        result = await service.get_product_settings()

        # Assert
        assert isinstance(result, ProductSettings)
        assert result.product_id == "default"


class TestContextServiceBehavior:
    """Test service behavior and initialization"""

    def test_service_initializes_correctly(self):
        """Test that service initializes with required dependencies"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        # Act
        service = ContextService(db_manager, tenant_manager)

        # Assert
        assert service.db_manager == db_manager
        assert service.tenant_manager == tenant_manager
        assert service._logger is not None

    @pytest.mark.asyncio
    async def test_stub_methods_are_synchronous_safe(self):
        """Test that stub methods don't require database access"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act - Call all stub methods without database
        result1 = await service.get_context_index()
        result2 = await service.get_vision()
        result3 = await service.get_vision_index()
        result4 = await service.get_product_settings()

        # Assert - All should succeed without database calls
        assert isinstance(result1, ContextIndex)
        assert isinstance(result2, VisionDocument)
        assert isinstance(result3, VisionIndex)
        assert isinstance(result4, ProductSettings)

        # Verify no database calls were made
        db_manager.get_session_async.assert_not_called()


class TestContextServiceConsistency:
    """Test consistency of responses"""

    @pytest.mark.asyncio
    async def test_all_stub_methods_return_typed_objects(self):
        """Test that all stub methods return typed objects"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = ContextService(db_manager, tenant_manager)

        # Act & Assert - Each method returns appropriate type
        context_index = await service.get_context_index()
        assert isinstance(context_index, ContextIndex)

        vision = await service.get_vision()
        assert isinstance(vision, VisionDocument)

        vision_index = await service.get_vision_index()
        assert isinstance(vision_index, VisionIndex)

        settings = await service.get_product_settings()
        assert isinstance(settings, ProductSettings)
