"""
Unit tests for product_memory initialization and backward compatibility.

Handover 0136: 360 Memory Management - Product Memory Initialization
Tests written FIRST following TDD principles.

Tests ensure:
1. New products auto-initialize product_memory
2. Existing products with NULL/incomplete memory get fixed on retrieval
3. Partial memory structures are completed (e.g., only has "github" key)
4. Valid memory structures are unchanged
"""

import uuid

import pytest

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.services.product_service import ProductService


class TestProductMemoryInitialization:
    """Test suite for product_memory initialization logic."""

    @pytest.mark.asyncio
    async def test_new_product_auto_initializes_memory(self, db_session):
        """
        BEHAVIOR: New products automatically get product_memory initialized

        GIVEN: ProductService.create_product() is called without explicit product_memory
        WHEN: Product is created and retrieved
        THEN: product_memory contains default structure {"github": {}, "learnings": [], "context": {}}
        """
        # ARRANGE
        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_auto_init"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # ACT
            unique_name = f"Auto-Init Product {uuid.uuid4().hex[:8]}"
            result = await product_service.create_product(
                name=unique_name,
                description="Testing automatic memory initialization",
                # NOTE: product_memory NOT provided - should auto-initialize
            )

            # ASSERT
            if not result["success"]:
                print(f"ERROR: {result.get('error', 'Unknown error')}")
            assert result["success"] is True
            assert "product_memory" in result
            assert result["product_memory"] == {"github": {}, "learnings": [], "context": {}}
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_existing_product_with_null_memory_gets_initialized(self, db_session):
        """
        BEHAVIOR: Product with NULL product_memory gets initialized on retrieval

        GIVEN: A product exists with product_memory = NULL (shouldn't happen, but defensive)
        WHEN: Product is retrieved via get_product()
        THEN: product_memory is initialized to default structure
        """
        # ARRANGE
        from sqlalchemy import update

        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_null_memory"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # Create a product normally
            result = await product_service.create_product(
                name="Null Memory Product " + uuid.uuid4().hex[:8], description="Testing NULL memory handling"
            )
            product_id = result["product_id"]

            # Force product_memory to NULL (simulate edge case)
            async with db_manager.get_session_async() as session:
                stmt = update(Product).where(Product.id == product_id).values(product_memory=None)
                await session.execute(stmt)
                await session.commit()

            # ACT - Retrieve product (should initialize memory)
            retrieved = await product_service.get_product(product_id)

            # ASSERT
            assert retrieved["success"] is True
            assert "product" in retrieved
            product_data = retrieved["product"]

            # NOTE: This test will FAIL until we implement _ensure_product_memory_initialized()
            # Expected behavior: NULL memory should be replaced with default structure
            assert "product_memory" in product_data
            assert product_data["product_memory"] == {"github": {}, "learnings": [], "context": {}}
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_existing_product_with_empty_dict_gets_initialized(self, db_session):
        """
        BEHAVIOR: Product with empty {} product_memory gets proper structure

        GIVEN: A product exists with product_memory = {}
        WHEN: Product is retrieved via get_product()
        THEN: product_memory is updated to include all required keys
        """
        # ARRANGE
        from sqlalchemy import update

        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_empty_memory"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # Create a product
            result = await product_service.create_product(
                name="Empty Memory Product " + uuid.uuid4().hex[:8], description="Testing empty dict memory handling"
            )
            product_id = result["product_id"]

            # Force product_memory to empty dict
            async with db_manager.get_session_async() as session:
                stmt = update(Product).where(Product.id == product_id).values(product_memory={})
                await session.execute(stmt)
                await session.commit()

            # ACT - Retrieve product
            retrieved = await product_service.get_product(product_id)

            # ASSERT
            assert retrieved["success"] is True
            product_data = retrieved["product"]

            # NOTE: This test will FAIL until we implement _ensure_product_memory_initialized()
            assert product_data["product_memory"] == {"github": {}, "learnings": [], "context": {}}
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_product_with_partial_memory_gets_completed(self, db_session):
        """
        BEHAVIOR: Product with partial memory (only "github") gets missing keys added

        GIVEN: A product exists with product_memory = {"github": {"enabled": true}}
        WHEN: Product is retrieved via get_product()
        THEN: Missing "learnings" and "context" keys are added, "github" is preserved
        """
        # ARRANGE
        from sqlalchemy import update

        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_partial_memory"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # Create a product
            result = await product_service.create_product(
                name="Partial Memory Product " + uuid.uuid4().hex[:8], description="Testing partial memory completion"
            )
            product_id = result["product_id"]

            # Set partial memory (only github key)
            partial_memory = {"github": {"enabled": True, "repo": "test/repo"}}
            async with db_manager.get_session_async() as session:
                stmt = update(Product).where(Product.id == product_id).values(product_memory=partial_memory)
                await session.execute(stmt)
                await session.commit()

            # ACT - Retrieve product
            retrieved = await product_service.get_product(product_id)

            # ASSERT
            assert retrieved["success"] is True
            product_data = retrieved["product"]

            # NOTE: This test will FAIL until we implement _ensure_product_memory_initialized()
            # Should have all keys, with github preserved
            memory = product_data["product_memory"]
            assert "github" in memory
            assert "learnings" in memory
            assert "context" in memory

            # Existing data should be preserved
            assert memory["github"]["enabled"] is True
            assert memory["github"]["repo"] == "test/repo"

            # Missing keys should be added with defaults
            assert memory["learnings"] == []
            assert memory["context"] == {}
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_product_with_valid_memory_unchanged(self, db_session):
        """
        BEHAVIOR: Product with valid memory structure is unchanged

        GIVEN: A product exists with complete, valid product_memory
        WHEN: Product is retrieved via get_product()
        THEN: product_memory is returned exactly as stored (no modifications)
        """
        # ARRANGE
        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_valid_memory"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # Create product with valid memory
            valid_memory = {
                "github": {"enabled": True, "repo_url": "https://github.com/test/repo", "auto_commit": False},
                "learnings": [
                    {
                        "timestamp": "2025-11-16T10:00:00Z",
                        "project_id": "proj_001",
                        "summary": "Test learning",
                        "tags": ["test"],
                    }
                ],
                "context": {"last_updated": "2025-11-16T10:00:00Z", "token_count": 15000, "summary": "Test summary"},
            }

            result = await product_service.create_product(
                name="Valid Memory Product " + uuid.uuid4().hex[:8],
                description="Testing valid memory preservation",
                product_memory=valid_memory,
            )
            product_id = result["product_id"]

            # ACT - Retrieve product
            retrieved = await product_service.get_product(product_id)

            # ASSERT
            assert retrieved["success"] is True
            product_data = retrieved["product"]

            # Memory should be identical to what was stored
            assert product_data["product_memory"] == valid_memory
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_list_products_initializes_all_products(self, db_session):
        """
        BEHAVIOR: list_products() initializes memory for all returned products

        GIVEN: Multiple products with varying memory states (NULL, partial, valid)
        WHEN: Products are listed via list_products()
        THEN: All products have properly initialized product_memory
        """
        # ARRANGE
        from sqlalchemy import update

        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_list_init"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # Create three products
            product_ids = []
            for i in range(3):
                result = await product_service.create_product(
                    name=f"List Product {i} " + uuid.uuid4().hex[:8], description=f"Product {i}"
                )
                product_ids.append(result["product_id"])

            # Force different memory states
            async with db_manager.get_session_async() as session:
                # Product 0: NULL
                await session.execute(update(Product).where(Product.id == product_ids[0]).values(product_memory=None))
                # Product 1: Empty dict
                await session.execute(update(Product).where(Product.id == product_ids[1]).values(product_memory={}))
                # Product 2: Valid (no change needed)
                await session.commit()

            # ACT - List all products
            result = await product_service.list_products(include_inactive=True)

            # ASSERT
            assert result["success"] is True
            products = result["products"]
            assert len(products) >= 3  # At least our 3 test products

            # NOTE: This test will FAIL until we implement _ensure_product_memory_initialized()
            # All products should have valid memory
            test_products = [p for p in products if p["id"] in product_ids]
            for product in test_products:
                assert "product_memory" in product
                memory = product["product_memory"]
                assert "github" in memory
                assert "learnings" in memory
                assert "context" in memory
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_initialization_is_idempotent(self, db_session):
        """
        BEHAVIOR: Initialization is idempotent (safe to call multiple times)

        GIVEN: A product with NULL memory
        WHEN: Product is retrieved multiple times
        THEN: Memory is initialized once and remains consistent
        """
        # ARRANGE
        from sqlalchemy import update

        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = "test_idempotent"

        try:
            product_service = ProductService(db_manager=db_manager, tenant_key=tenant_key)

            # Create product
            result = await product_service.create_product(
                name="Idempotent Test Product " + uuid.uuid4().hex[:8], description="Testing idempotent initialization"
            )
            product_id = result["product_id"]

            # Force NULL memory
            async with db_manager.get_session_async() as session:
                await session.execute(update(Product).where(Product.id == product_id).values(product_memory=None))
                await session.commit()

            # ACT - Retrieve product multiple times
            result1 = await product_service.get_product(product_id)
            result2 = await product_service.get_product(product_id)
            result3 = await product_service.get_product(product_id)

            # ASSERT - All retrievals should return identical memory
            # NOTE: This test will FAIL until we implement _ensure_product_memory_initialized()
            memory1 = result1["product"]["product_memory"]
            memory2 = result2["product"]["product_memory"]
            memory3 = result3["product"]["product_memory"]

            assert memory1 == memory2 == memory3
            assert memory1 == {"github": {}, "learnings": [], "context": {}}
        finally:
            await db_manager.close_async()
