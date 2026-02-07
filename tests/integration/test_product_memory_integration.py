"""
Integration tests for product_memory column across services.

Handover 0135: 360 Memory Management - Database Schema
Full lifecycle test from creation to update to JSONB queries.
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.services.product_service import ProductService


@pytest.mark.asyncio
async def test_product_memory_lifecycle(db_session, tenant_key):
    """
    INTEGRATION: Full lifecycle test of product_memory from creation to update

    GIVEN: A product is created via ProductService
    WHEN: Memory data is added, updated, and queried
    THEN: All operations work correctly with proper structure

    This test validates:
    1. Product creation with default memory structure
    2. GitHub integration settings update
    3. Learning entry append
    4. Context summary update
    5. JSONB path queries work correctly
    6. Multi-tenant isolation is preserved
    """
    # ARRANGE
    from giljo_mcp.database.session import DatabaseManager

    db_manager = DatabaseManager()
    product_service = ProductService(db_manager, tenant_key)

    # ACT - Create product with default memory
    product_data = await product_service.create_product(
        name="Integration Test Product", description="Testing full memory lifecycle"
    )

    # ASSERT - Product created with default structure
    assert product_data["success"] is True
    product_id = product_data["product_id"]
    assert product_data["product_memory"] == {"github": {}, "learnings": [], "context": {}}

    # ACT - Add GitHub integration settings
    updated_memory = {
        "github": {
            "enabled": True,
            "repo_url": "https://github.com/test/integration",
            "auto_commit": True,
            "last_sync": "2025-11-16T10:30:00Z",
        },
        "learnings": [],
        "context": {},
    }

    update_result = await product_service.update_product(product_id=product_id, product_memory=updated_memory)

    # ASSERT - GitHub settings persisted
    assert update_result["success"] is True

    # Query product directly from database to verify persistence
    stmt = select(Product).where(Product.id == product_id)
    result = await db_session.execute(stmt)
    product = result.scalar_one()

    assert product.product_memory["github"]["enabled"] is True
    assert product.product_memory["github"]["repo_url"] == "https://github.com/test/integration"

    # ACT - Add learning entry
    learning_entry = {
        "timestamp": "2025-11-16T11:00:00Z",
        "project_id": "proj_integration_001",
        "summary": "Learned to use JSONB for flexible schema",
        "tags": ["database", "postgresql", "jsonb"],
    }

    product.product_memory["learnings"].append(learning_entry)
    await db_session.commit()
    await db_session.refresh(product)

    # ASSERT - Learning entry persisted
    assert len(product.product_memory["learnings"]) == 1
    assert product.product_memory["learnings"][0]["summary"] == "Learned to use JSONB for flexible schema"
    assert product.product_memory["learnings"][0]["tags"] == ["database", "postgresql", "jsonb"]

    # ACT - Update context summary
    product.product_memory["context"] = {
        "last_updated": "2025-11-16T11:00:00Z",
        "token_count": 25000,
        "summary": "Integration testing framework for GiljoAI MCP",
    }
    await db_session.commit()
    await db_session.refresh(product)

    # ASSERT - Context summary persisted
    assert product.product_memory["context"]["token_count"] == 25000
    assert product.product_memory["context"]["summary"] == "Integration testing framework for GiljoAI MCP"

    # ACT - JSONB path query (GitHub enabled products)
    query = select(Product).where(
        Product.tenant_key == tenant_key, Product.product_memory["github"]["enabled"].astext == "true"
    )
    result = await db_session.execute(query)
    github_products = result.scalars().all()

    # ASSERT - Query returns correct product
    assert len(github_products) == 1
    assert github_products[0].id == product_id

    # ACT - Verify multi-tenant isolation
    # Create product for different tenant
    other_tenant_product = Product(
        name="Other Tenant Product",
        description="Different tenant",
        tenant_key="other_tenant",
        product_memory={"github": {"enabled": True}, "learnings": [], "context": {}},
    )
    db_session.add(other_tenant_product)
    await db_session.commit()

    # Query with original tenant key
    isolated_query = select(Product).where(
        Product.tenant_key == tenant_key, Product.product_memory["github"]["enabled"].astext == "true"
    )
    isolated_result = await db_session.execute(isolated_query)
    isolated_products = isolated_result.scalars().all()

    # ASSERT - Only original tenant's product returned
    assert len(isolated_products) == 1
    assert isolated_products[0].id == product_id
    assert isolated_products[0].tenant_key == tenant_key


@pytest.mark.asyncio
async def test_product_memory_helper_methods(db_session, tenant_key):
    """
    INTEGRATION: Test Product model helper methods for product_memory

    GIVEN: A product with populated product_memory
    WHEN: Using has_product_memory and get_memory_field
    THEN: Helper methods work correctly
    """
    # ARRANGE
    product = Product(
        name="Helper Methods Test",
        description="Testing helper methods",
        tenant_key=tenant_key,
        product_memory={
            "github": {"enabled": True, "repo_url": "https://github.com/test/helpers"},
            "learnings": [{"summary": "First learning", "tags": ["test"]}],
            "context": {"summary": "Helper test context"},
        },
    )
    db_session.add(product)
    await db_session.commit()

    # ACT & ASSERT - has_product_memory
    assert product.has_product_memory is True

    # ACT & ASSERT - get_memory_field
    assert product.get_memory_field("github.enabled") is True
    assert product.get_memory_field("github.repo_url") == "https://github.com/test/helpers"
    assert product.get_memory_field("github.nonexistent", "default") == "default"
    assert product.get_memory_field("context.summary") == "Helper test context"
    assert len(product.get_memory_field("learnings", [])) == 1

    # Test empty memory
    empty_product = Product(
        name="Empty Memory Test",
        description="Testing empty memory",
        tenant_key=tenant_key,
        product_memory={"github": {}, "learnings": [], "context": {}},
    )
    db_session.add(empty_product)
    await db_session.commit()

    assert empty_product.has_product_memory is False
