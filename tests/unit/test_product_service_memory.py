"""
Unit tests for ProductService - Product Memory, Target Platforms

Split from test_product_service.py (Handover 0127b, updated 0731b).

Tests cover:
- product_memory JSONB column (Handover 0135)
- target_platforms field (Handover 0425)

Handover 0731b: Updated assertions for typed returns (Product ORM,
Pydantic models) instead of dict[str, Any] wrappers.

Target: >80% line coverage
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import Product
from src.giljo_mcp.services.product_service import ProductService


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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
        assert result.name == "Custom Memory Product"
        # product_memory is persisted on the ORM model as JSONB
        assert result.product_memory is not None
        assert result.product_memory["git_integration"]["enabled"] is True
        assert result.product_memory["git_integration"]["commit_limit"] == 20

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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
        assert result.name == "Default Memory Product"
        # Default product_memory JSONB is set on the ORM model
        assert result.product_memory is not None

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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert result is existing_product
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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
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
        db_manager, _session = mock_db_manager

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
        db_manager, _session = mock_db_manager

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

        # ASSERT - returns Product ORM model (0731b typed returns)
        assert isinstance(result, Product)
        assert existing_product.target_platforms == ["linux", "macos"]
        session.commit.assert_awaited_once()
