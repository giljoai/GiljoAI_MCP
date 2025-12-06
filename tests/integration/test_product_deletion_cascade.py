#!/usr/bin/env python3
"""
Integration tests for product deletion with CASCADE constraints.

Tests that products can be deleted when they have:
- Related projects
- Related tasks
- Vision documents
- Context index chunks
- Condensed context records

This test reveals the bug where foreign key constraints lack CASCADE
and prevent product deletion from succeeding.
"""

import asyncio
import sys
from pathlib import Path

import pytest
from sqlalchemy import select


# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import (
    MCPContextIndex,
    Product,
    Project,
    Task,
    VisionDocument,
)
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_manager():
    """Create test database manager"""
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False), is_async=True)
    await db_manager.create_tables_async()
    yield db_manager
    await db_manager.close_async()


@pytest.fixture
async def tenant_key():
    """Test tenant key"""
    return "tk_test_cascade_delete"


@pytest.fixture
async def test_product_with_relations(db_manager, tenant_key):
    """
    Create a product with all related data:
    - Projects
    - Tasks
    - Vision documents
    - Context index chunks
    """
    async with db_manager.get_session_async() as db:
        # Create product
        product = Product(
            name="Test Product for Deletion", description="Has many related records", tenant_key=tenant_key
        )
        db.add(product)
        await db.flush()  # Get product.id

        # Create projects
        project1 = Project(
            name="Project 1",
            mission="Test mission 1",
            alias="ABC123",
            product_id=product.id,
            tenant_key=tenant_key,
            status="active",
        )
        project2 = Project(
            name="Project 2",
            mission="Test mission 2",
            alias="DEF456",
            product_id=product.id,
            tenant_key=tenant_key,
            status="completed",
        )
        db.add_all([project1, project2])
        await db.flush()

        # Create tasks
        task1 = Task(
            title="Task 1",
            description="Pending task",
            product_id=product.id,
            project_id=project1.id,
            tenant_key=tenant_key,
            status="waiting",
        )
        task2 = Task(
            title="Task 2",
            description="Completed task",
            product_id=product.id,
            project_id=project2.id,
            tenant_key=tenant_key,
            status="completed",
        )
        db.add_all([task1, task2])
        await db.flush()

        # Create vision document
        vision_doc = VisionDocument(
            product_id=product.id,
            tenant_key=tenant_key,
            filename="vision.md",
            document_type="file",
            content="# Vision Document\n\nTest content",
            display_order=1,
            chunked=True,
        )
        db.add(vision_doc)
        await db.flush()

        # Create context index chunks
        chunk1 = MCPContextIndex(
            product_id=product.id,
            vision_document_id=vision_doc.id,
            tenant_key=tenant_key,
            content="Chunk 1 content",
            keywords=["test", "chunk"],
            chunk_order=1,
            token_count=50,
        )
        chunk2 = MCPContextIndex(
            product_id=product.id,
            vision_document_id=vision_doc.id,
            tenant_key=tenant_key,
            content="Chunk 2 content",
            keywords=["test", "another"],
            chunk_order=2,
            token_count=45,
        )
        db.add_all([chunk1, chunk2])

        await db.commit()

        # Return product ID for tests
        return product.id


@pytest.mark.asyncio
async def test_product_deletion_with_projects(db_manager, tenant_key, test_product_with_relations):
    """
    Test that deleting a product also deletes related projects.

    Expected behavior: CASCADE should delete projects automatically.
    Actual behavior (bug): Deletion fails because projects.product_id lacks CASCADE.
    """
    product_id = test_product_with_relations

    async with db_manager.get_session_async() as db:
        # Verify product exists with related projects
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        assert product is not None, "Product should exist"

        # Count related projects
        stmt = select(Project).where(Project.product_id == product_id)
        result = await db.execute(stmt)
        projects = result.scalars().all()
        assert len(projects) == 2, "Should have 2 projects"

        # Attempt to delete product
        db.delete(product)

        # This SHOULD succeed with CASCADE, but WILL FAIL without it
        try:
            await db.commit()
            deletion_succeeded = True
        except Exception as e:
            deletion_succeeded = False
            error_message = str(e)
            await db.rollback()

        # Assert deletion succeeded
        assert deletion_succeeded, f"Product deletion failed: {error_message if not deletion_succeeded else ''}"

    # Verify product is actually deleted
    async with db_manager.get_session_async() as db:
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        assert product is None, "Product should be deleted"

        # Verify projects are also deleted (CASCADE)
        stmt = select(Project).where(Project.product_id == product_id)
        result = await db.execute(stmt)
        projects = result.scalars().all()
        assert len(projects) == 0, "Projects should be cascade-deleted"


@pytest.mark.asyncio
async def test_product_deletion_with_tasks(db_manager, tenant_key, test_product_with_relations):
    """
    Test that deleting a product also deletes related tasks.

    Expected behavior: CASCADE should delete tasks automatically.
    Actual behavior (bug): Deletion fails because tasks.product_id lacks CASCADE.
    """
    product_id = test_product_with_relations

    async with db_manager.get_session_async() as db:
        # Count related tasks
        stmt = select(Task).where(Task.product_id == product_id)
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        assert len(tasks) == 2, "Should have 2 tasks"

        # Get product
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        # Delete product
        db.delete(product)

        try:
            await db.commit()
            deletion_succeeded = True
        except Exception:
            deletion_succeeded = False
            await db.rollback()

        assert deletion_succeeded, "Product deletion should succeed with CASCADE"

    # Verify tasks are deleted
    async with db_manager.get_session_async() as db:
        stmt = select(Task).where(Task.product_id == product_id)
        result = await db.execute(stmt)
        tasks = result.scalars().all()
        assert len(tasks) == 0, "Tasks should be cascade-deleted"


@pytest.mark.asyncio
async def test_product_deletion_with_context_chunks(db_manager, tenant_key, test_product_with_relations):
    """
    Test that deleting a product also deletes MCP context index chunks.

    Expected behavior: CASCADE should delete chunks automatically.
    Actual behavior (bug): Deletion fails because mcp_context_index.product_id lacks CASCADE.
    """
    product_id = test_product_with_relations

    async with db_manager.get_session_async() as db:
        # Count related chunks
        stmt = select(MCPContextIndex).where(MCPContextIndex.product_id == product_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        assert len(chunks) == 2, "Should have 2 context chunks"

        # Delete product
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        db.delete(product)

        try:
            await db.commit()
            deletion_succeeded = True
        except Exception:
            deletion_succeeded = False
            await db.rollback()

        assert deletion_succeeded, "Product deletion should succeed with CASCADE"

    # Verify chunks are deleted
    async with db_manager.get_session_async() as db:
        stmt = select(MCPContextIndex).where(MCPContextIndex.product_id == product_id)
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        assert len(chunks) == 0, "Context chunks should be cascade-deleted"


@pytest.mark.asyncio
async def test_product_deletion_complete_cleanup(db_manager, tenant_key, test_product_with_relations):
    """
    Integration test: Verify complete cleanup of all product-related data.

    This is the real-world scenario where a user deletes a product from the UI
    and expects all related data to be removed.
    """
    product_id = test_product_with_relations

    async with db_manager.get_session_async() as db:
        # Get product
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        assert product is not None

        # Delete product (simulating API endpoint behavior)
        db.delete(product)

        # This should succeed and cascade to all related tables
        try:
            await db.commit()
            deletion_succeeded = True
            error_message = None
        except Exception as e:
            deletion_succeeded = False
            error_message = str(e)
            await db.rollback()

        # CRITICAL: Deletion must succeed
        assert deletion_succeeded, f"Product deletion failed: {error_message}"

    # Verify complete cleanup
    async with db_manager.get_session_async() as db:
        # Product should be gone
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        assert result.scalar_one_or_none() is None, "Product should be deleted"

        # Projects should be gone
        stmt = select(Project).where(Project.product_id == product_id)
        result = await db.execute(stmt)
        assert len(result.scalars().all()) == 0, "Projects should be deleted"

        # Tasks should be gone
        stmt = select(Task).where(Task.product_id == product_id)
        result = await db.execute(stmt)
        assert len(result.scalars().all()) == 0, "Tasks should be deleted"

        # Vision documents should be gone (already has CASCADE)
        stmt = select(VisionDocument).where(VisionDocument.product_id == product_id)
        result = await db.execute(stmt)
        assert len(result.scalars().all()) == 0, "Vision documents should be deleted"

        # Context chunks should be gone
        stmt = select(MCPContextIndex).where(MCPContextIndex.product_id == product_id)
        result = await db.execute(stmt)
        assert len(result.scalars().all()) == 0, "Context chunks should be deleted"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
