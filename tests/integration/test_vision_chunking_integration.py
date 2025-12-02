"""
Integration smoke test for vision document chunking (Handover 0047).

Tests the full end-to-end flow:
- Create vision document in database
- Chunk document using real VisionDocumentChunker
- Verify chunks created correctly
- Verify async propagation through all layers

NOTE: These tests require PostgreSQL due to JSONB column types.
SQLite does not support JSONB, so these tests will fail with SQLite.

To run these tests:
1. Ensure PostgreSQL is running
2. Create test database: createdb giljo_mcp_test
3. Run: pytest tests/integration/test_vision_chunking_integration.py -v

For CI/CD: Use PostgreSQL container for integration tests.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
from src.giljo_mcp.models import Base, Product, VisionDocument
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


@pytest.fixture
async def test_db_session():
    """Create temporary PostgreSQL database for integration testing."""
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

    # Use PostgreSQL for integration testing
    engine = create_async_engine(PostgreSQLTestHelper.get_test_db_url(), echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture
async def test_product(test_db_session):
    """Create test product."""
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key="test-tenant",
        name="Integration Test Product",
        description="Product for integration testing",
    )
    test_db_session.add(product)
    await test_db_session.flush()
    return product


@pytest.mark.asyncio
async def test_vision_chunking_end_to_end_inline(test_db_session, test_product):
    """
    Integration test: Full chunking flow with inline storage.

    Tests:
    - VisionDocumentRepository.create()
    - VisionDocumentChunker.chunk_vision_document()
    - ContextRepository.delete_chunks_by_vision_document()
    - VisionDocumentRepository.mark_chunked()
    - Chunk creation and storage
    """
    vision_repo = VisionDocumentRepository(db_manager=None)
    chunker = VisionDocumentChunker()

    # Create vision document with inline content
    content = """
# Product Vision: AI-Powered Task Manager

## Overview
A revolutionary task management system that uses AI to prioritize tasks.

## Features
- Smart task prioritization using machine learning
- Natural language task creation
- Automatic deadline suggestions
- Integration with calendar systems

## Technical Requirements
- Backend: Python FastAPI
- Frontend: React
- Database: PostgreSQL
- AI: OpenAI GPT-4

## Success Criteria
- Process 1000 tasks per second
- 95% accuracy in task prioritization
- Sub-100ms response time for API calls
"""

    doc = await vision_repo.create(
        session=test_db_session,
        tenant_key="test-tenant",
        product_id=test_product.id,
        document_name="Product Vision",
        content=content,
        storage_type="inline",
        document_type="vision",
    )

    assert doc is not None
    assert doc.chunked is False
    assert doc.chunk_count == 0

    await test_db_session.commit()

    # Chunk the document
    result = await chunker.chunk_vision_document(test_db_session, "test-tenant", doc.id)

    # Verify chunking result
    assert result["success"] is True
    assert result["document_id"] == doc.id
    assert result["document_name"] == "Product Vision"
    assert result["chunks_created"] > 0
    assert result["total_tokens"] > 0
    assert result["old_chunks_deleted"] == 0

    await test_db_session.commit()

    # Verify chunks exist in database
    stmt = text("""
        SELECT COUNT(*) as count
        FROM mcp_context_index
        WHERE tenant_key = :tenant_key
        AND vision_document_id = :doc_id
    """)
    result_proxy = await test_db_session.execute(stmt, {"tenant_key": "test-tenant", "doc_id": doc.id})
    count_row = result_proxy.fetchone()
    chunk_count = count_row[0]

    assert chunk_count == result["chunks_created"]
    assert chunk_count > 0

    # Verify document marked as chunked
    await test_db_session.refresh(doc)
    assert doc.chunked is True
    assert doc.chunk_count == chunk_count
    assert doc.total_tokens == result["total_tokens"]
    assert doc.chunked_at is not None


@pytest.mark.asyncio
async def test_vision_rechunking_deletes_old_chunks(test_db_session, test_product):
    """
    Integration test: Re-chunking deletes old chunks.

    Verifies:
    - Re-chunking same document deletes previous chunks
    - New chunks replace old chunks
    - Chunk count updated correctly
    """
    vision_repo = VisionDocumentRepository(db_manager=None)
    chunker = VisionDocumentChunker()

    # Create and chunk document
    content_v1 = "# Version 1\nThis is the first version of the document."
    doc = await vision_repo.create(
        session=test_db_session,
        tenant_key="test-tenant",
        product_id=test_product.id,
        document_name="Versioned Doc",
        content=content_v1,
        storage_type="inline",
        document_type="vision",
    )
    await test_db_session.commit()

    # First chunking
    result1 = await chunker.chunk_vision_document(test_db_session, "test-tenant", doc.id)
    await test_db_session.commit()

    first_chunk_count = result1["chunks_created"]
    assert first_chunk_count > 0

    # Update document content (simulate edit)
    doc.vision_document = """
# Version 2
This is a much longer version of the document with more content.

## Additional Section
We've added more sections and more detailed information.

## Another Section
Even more content here to create more chunks.

## Technical Details
Lots of technical details that will require chunking.
"""
    await test_db_session.flush()
    await test_db_session.commit()

    # Re-chunk document
    result2 = await chunker.chunk_vision_document(test_db_session, "test-tenant", doc.id)
    await test_db_session.commit()

    # Verify old chunks deleted
    assert result2["old_chunks_deleted"] == first_chunk_count
    assert result2["chunks_created"] > 0

    # Verify only new chunks exist
    stmt = text("""
        SELECT COUNT(*) as count
        FROM mcp_context_index
        WHERE tenant_key = :tenant_key
        AND vision_document_id = :doc_id
    """)
    result_proxy = await test_db_session.execute(stmt, {"tenant_key": "test-tenant", "doc_id": doc.id})
    count_row = result_proxy.fetchone()
    current_chunk_count = count_row[0]

    assert current_chunk_count == result2["chunks_created"]

    # Verify document metadata updated
    await test_db_session.refresh(doc)
    assert doc.chunk_count == result2["chunks_created"]


@pytest.mark.asyncio
async def test_multi_tenant_isolation_during_chunking(test_db_session):
    """
    Integration test: Multi-tenant isolation in chunking.

    Verifies:
    - Documents from different tenants don't interfere
    - Chunks are properly isolated by tenant_key
    - Cannot chunk other tenant's documents
    """
    vision_repo = VisionDocumentRepository(db_manager=None)
    chunker = VisionDocumentChunker()

    # Create products for two tenants
    product1 = Product(id=str(uuid.uuid4()), tenant_key="tenant-alpha", name="Alpha Product")
    product2 = Product(id=str(uuid.uuid4()), tenant_key="tenant-beta", name="Beta Product")
    test_db_session.add_all([product1, product2])
    await test_db_session.flush()

    # Create documents for both tenants
    doc1 = await vision_repo.create(
        session=test_db_session,
        tenant_key="tenant-alpha",
        product_id=product1.id,
        document_name="Alpha Doc",
        content="# Alpha Content\nThis belongs to tenant alpha.",
        storage_type="inline",
        document_type="vision",
    )

    doc2 = await vision_repo.create(
        session=test_db_session,
        tenant_key="tenant-beta",
        product_id=product2.id,
        document_name="Beta Doc",
        content="# Beta Content\nThis belongs to tenant beta.",
        storage_type="inline",
        document_type="vision",
    )
    await test_db_session.commit()

    # Chunk both documents
    await chunker.chunk_vision_document(test_db_session, "tenant-alpha", doc1.id)
    await chunker.chunk_vision_document(test_db_session, "tenant-beta", doc2.id)
    await test_db_session.commit()

    # Verify chunks isolated by tenant
    stmt = text("""
        SELECT COUNT(*) as count
        FROM mcp_context_index
        WHERE tenant_key = :tenant_key
    """)

    # Alpha chunks
    result_alpha = await test_db_session.execute(stmt, {"tenant_key": "tenant-alpha"})
    alpha_count = result_alpha.fetchone()[0]
    assert alpha_count > 0

    # Beta chunks
    result_beta = await test_db_session.execute(stmt, {"tenant_key": "tenant-beta"})
    beta_count = result_beta.fetchone()[0]
    assert beta_count > 0

    # Try to chunk tenant-beta doc with tenant-alpha key (should fail)
    result = await chunker.chunk_vision_document(test_db_session, "tenant-alpha", doc2.id)
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_chunking_with_file_storage(test_db_session, test_product, tmp_path):
    """
    Integration test: Chunking with file storage.

    Verifies:
    - Chunker reads content from file path
    - File-based storage works correctly
    - Chunks created from file content
    """
    vision_repo = VisionDocumentRepository(db_manager=None)
    chunker = VisionDocumentChunker()

    # Create temporary file with content
    content = """
# File-Based Vision Document

## Feature Set
- Feature A: First feature
- Feature B: Second feature
- Feature C: Third feature

## Implementation Notes
This document is stored in a file, not inline.
"""

    vision_file = tmp_path / "vision_doc.md"
    vision_file.write_text(content, encoding="utf-8")

    # Create vision document with file storage
    doc = VisionDocument(
        tenant_key="test-tenant",
        product_id=test_product.id,
        document_name="File-Based Doc",
        vision_document=None,
        vision_path=str(vision_file),
        storage_type="file",
        document_type="vision",
        content_hash="placeholder",
        chunked=False,
        chunk_count=0,
    )
    test_db_session.add(doc)
    await test_db_session.flush()
    await test_db_session.commit()

    # Chunk the document
    result = await chunker.chunk_vision_document(test_db_session, "test-tenant", doc.id)

    # Verify chunking succeeded
    assert result["success"] is True
    assert result["chunks_created"] > 0

    # Verify chunks contain file content
    stmt = text("""
        SELECT content
        FROM mcp_context_index
        WHERE tenant_key = :tenant_key
        AND vision_document_id = :doc_id
        LIMIT 1
    """)
    result_proxy = await test_db_session.execute(stmt, {"tenant_key": "test-tenant", "doc_id": doc.id})
    chunk_content = result_proxy.fetchone()[0]

    assert "File-Based Vision Document" in chunk_content or "Feature" in chunk_content
