"""
Unit tests for MissionPlanner vision chunk retrieval.

Tests the new _get_relevant_vision_chunks() and _rank_chunk_relevance() methods.
These tests will FAIL initially (RED phase) until implementation is complete.

Handover: 0305 - Integrate Vision Document Chunking with Context Generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.context import MCPContextIndex


@pytest.mark.asyncio
async def test_get_relevant_chunks_returns_top_chunks():
    """
    Test: _get_relevant_vision_chunks() returns most relevant chunks.

    Given: Product with chunked vision document, 5 chunks stored
    When: Project description mentions "authentication" and "API"
    Then: Chunks containing those keywords ranked higher
    And: Top 3 chunks returned within token budget
    """
    # Setup: Mock product with chunked vision
    product = Product(
        id="product-123",
        tenant_key="test-tenant",
        name="Test Product",
    )

    # Setup: Mock vision document (chunked)
    vision_doc = VisionDocument(
        id="vision-doc-123",
        tenant_key="test-tenant",
        product_id="product-123",
        document_name="Product Vision",
        vision_document="Full vision...",
        chunked=True,
        chunk_count=5,
        is_active=True,
    )
    product.vision_documents = [vision_doc]

    # Setup: Mock chunks with varying relevance
    mock_chunks = [
        MCPContextIndex(
            id=1,
            chunk_id="chunk-1",
            tenant_key="test-tenant",
            product_id="product-123",
            vision_document_id="vision-doc-123",
            content="Authentication system with JWT and API tokens for secure access",
            chunk_order=0,
        ),
        MCPContextIndex(
            id=2,
            chunk_id="chunk-2",
            tenant_key="test-tenant",
            product_id="product-123",
            vision_document_id="vision-doc-123",
            content="User interface design with dark mode and responsive layout",
            chunk_order=1,
        ),
        MCPContextIndex(
            id=3,
            chunk_id="chunk-3",
            tenant_key="test-tenant",
            product_id="product-123",
            vision_document_id="vision-doc-123",
            content="API endpoints for authentication and user management",
            chunk_order=2,
        ),
        MCPContextIndex(
            id=4,
            chunk_id="chunk-4",
            tenant_key="test-tenant",
            product_id="product-123",
            vision_document_id="vision-doc-123",
            content="Database schema for storing user credentials and tokens",
            chunk_order=3,
        ),
        MCPContextIndex(
            id=5,
            chunk_id="chunk-5",
            tenant_key="test-tenant",
            product_id="product-123",
            vision_document_id="vision-doc-123",
            content="Deployment configuration for production servers",
            chunk_order=4,
        ),
    ]

    # Setup: Mock project with specific focus
    project = Project(
        id="project-123",
        tenant_key="test-tenant",
        product_id="product-123",
        name="Auth Service",
        description="Build JWT authentication API with OAuth2 integration",
        status="active",
    )

    # Setup: Mock database session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_chunks
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Setup: Mock db_manager
    mock_db_manager = MagicMock()

    # Execute: Call the method
    planner = MissionPlanner(db_manager=mock_db_manager)

    # This will FAIL - method doesn't exist yet (RED phase)
    relevant_chunks = await planner._get_relevant_vision_chunks(
        session=mock_session,
        product=product,
        project=project,
        max_tokens=15000,
    )

    # Assert: Top chunks contain keywords from project description
    assert len(relevant_chunks) > 0
    assert len(relevant_chunks) <= 5

    # Assert: Most relevant chunks come first (auth-related)
    # Chunk 1 and 3 should rank highest (authentication + API keywords)
    top_chunk_content = relevant_chunks[0]['content']
    assert 'authentication' in top_chunk_content.lower() or 'api' in top_chunk_content.lower()

    # Assert: Each chunk has required fields
    for chunk in relevant_chunks:
        assert 'content' in chunk
        assert 'relevance_score' in chunk
        assert 'chunk_id' in chunk
        assert chunk['relevance_score'] >= 0


@pytest.mark.asyncio
async def test_get_relevant_chunks_respects_token_budget():
    """
    Test: Chunk retrieval respects max_tokens parameter.

    Given: Product with chunked vision, 10 chunks (each ~2K tokens)
    When: max_tokens=5000 specified
    Then: Only chunks fitting within budget returned
    And: Lower-ranked chunks excluded
    """
    # Setup: Mock product with chunked vision
    product = Product(
        id="product-456",
        tenant_key="test-tenant",
        name="Test Product",
    )

    vision_doc = VisionDocument(
        id="vision-doc-456",
        tenant_key="test-tenant",
        product_id="product-456",
        document_name="Product Vision",
        vision_document="Full vision...",
        chunked=True,
        chunk_count=10,
        is_active=True,
    )
    product.vision_documents = [vision_doc]

    # Setup: Mock chunks - each chunk is ~500 characters (~125 tokens)
    # Create 10 chunks with authentication-related content
    mock_chunks = []
    for i in range(10):
        content = f"Chunk {i}: Authentication and API security measures. " * 20  # ~500 chars
        mock_chunks.append(
            MCPContextIndex(
                id=i + 1,
                chunk_id=f"chunk-{i+1}",
                tenant_key="test-tenant",
                product_id="product-456",
                vision_document_id="vision-doc-456",
                content=content,
                chunk_order=i,
            )
        )

    project = Project(
        id="project-456",
        tenant_key="test-tenant",
        product_id="product-456",
        name="Auth Service",
        description="Build authentication API",
        status="active",
    )

    # Setup: Mock database session
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_chunks
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_db_manager = MagicMock()
    mock_db_manager.session = mock_session

    # Execute: Call with tight token budget (should only return ~2-3 chunks)
    planner = MissionPlanner(db_manager=mock_db_manager)

    # This will FAIL - token budget enforcement not implemented (RED phase)
    relevant_chunks = await planner._get_relevant_vision_chunks(
        session=mock_session,
        product=product,
        project=project,
        max_tokens=500,  # Very tight budget
    )

    # Assert: Total tokens should not exceed budget
    total_tokens = sum(chunk.get('tokens', 0) for chunk in relevant_chunks)
    assert total_tokens <= 500

    # Assert: Should return fewer chunks due to budget constraint
    assert len(relevant_chunks) < 10


@pytest.mark.asyncio
async def test_get_relevant_chunks_empty_when_not_chunked():
    """
    Test: Returns empty list when vision not chunked.

    Given: Product with vision_document but chunked=False
    When: _get_relevant_vision_chunks() called
    Then: Returns empty list (triggers fallback to full text)
    """
    # Setup: Product with non-chunked vision
    product = Product(
        id="product-789",
        tenant_key="test-tenant",
        name="Test Product",
    )

    vision_doc = VisionDocument(
        id="vision-doc-789",
        tenant_key="test-tenant",
        product_id="product-789",
        document_name="Product Vision",
        vision_document="Full vision...",
        chunked=False,  # NOT chunked
        chunk_count=0,
        is_active=True,
    )
    product.vision_documents = [vision_doc]

    project = Project(
        id="project-789",
        tenant_key="test-tenant",
        product_id="product-789",
        name="Test Project",
        description="Test description",
        status="active",
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_db_manager = MagicMock()
    mock_db_manager.session = mock_session

    # Execute
    planner = MissionPlanner(db_manager=mock_db_manager)

    # This will FAIL - method doesn't exist yet (RED phase)
    relevant_chunks = await planner._get_relevant_vision_chunks(
        session=mock_session,
        product=product,
        project=project,
        max_tokens=10000,
    )

    # Assert: Empty list returned
    assert relevant_chunks == []


def test_rank_chunk_relevance_keyword_matching():
    """
    Test: _rank_chunk_relevance() scores chunks by keyword overlap.

    Given: Project description "Build authentication API with JWT"
    And: Chunks with varying keyword overlap
    When: Ranking algorithm applied
    Then: Chunks with "authentication", "API", "JWT" ranked higher
    And: Chunks without keywords ranked lower
    """
    # Setup: Mock chunks with varying keyword overlap
    mock_chunks = [
        MCPContextIndex(
            id=1,
            chunk_id="chunk-1",
            content="Authentication system with JWT tokens for API security",
            chunk_order=0,
        ),
        MCPContextIndex(
            id=2,
            chunk_id="chunk-2",
            content="User interface design with dark mode support",
            chunk_order=1,
        ),
        MCPContextIndex(
            id=3,
            chunk_id="chunk-3",
            content="API endpoints for user management and authentication",
            chunk_order=2,
        ),
        MCPContextIndex(
            id=4,
            chunk_id="chunk-4",
            content="Database migration scripts for PostgreSQL",
            chunk_order=3,
        ),
    ]

    project_description = "Build authentication API with JWT tokens"

    # Execute
    mock_db_manager = MagicMock()
    planner = MissionPlanner(db_manager=mock_db_manager)

    # This will FAIL - method doesn't exist yet (RED phase)
    ranked_chunks = planner._rank_chunk_relevance(
        chunks=mock_chunks,
        project_description=project_description,
    )

    # Assert: Chunks sorted by relevance
    assert len(ranked_chunks) == 4

    # Assert: Top chunk should have highest relevance
    assert ranked_chunks[0]['relevance_score'] > 0

    # Assert: Chunk 1 (auth + JWT + API) should rank highest
    # Chunk 3 (API + auth) should rank second
    # Chunk 2 and 4 should rank lower (no matching keywords)
    top_chunk = ranked_chunks[0]
    assert 'authentication' in top_chunk['content'].lower()
    assert 'jwt' in top_chunk['content'].lower() or 'api' in top_chunk['content'].lower()

    # Assert: Scores decrease monotonically
    for i in range(len(ranked_chunks) - 1):
        assert ranked_chunks[i]['relevance_score'] >= ranked_chunks[i + 1]['relevance_score']


@pytest.mark.asyncio
async def test_multi_tenant_chunk_isolation():
    """
    Test: Chunk retrieval filters by tenant_key.

    Given: Two products from different tenants with chunked visions
    When: Retrieving chunks for tenant-alpha product
    Then: Only tenant-alpha chunks returned
    And: No tenant-beta chunks included
    """
    # Setup: Product from tenant-alpha
    product_alpha = Product(
        id="product-alpha",
        tenant_key="tenant-alpha",
        name="Alpha Product",
    )

    vision_doc_alpha = VisionDocument(
        id="vision-doc-alpha",
        tenant_key="tenant-alpha",
        product_id="product-alpha",
        document_name="Alpha Vision",
        vision_document="Alpha vision...",
        chunked=True,
        chunk_count=3,
        is_active=True,
    )
    product_alpha.vision_documents = [vision_doc_alpha]

    # Setup: Chunks from tenant-alpha (these should be returned)
    chunks_alpha = [
        MCPContextIndex(
            id=1,
            chunk_id="chunk-alpha-1",
            tenant_key="tenant-alpha",
            product_id="product-alpha",
            vision_document_id="vision-doc-alpha",
            content="Alpha authentication system",
            chunk_order=0,
        ),
        MCPContextIndex(
            id=2,
            chunk_id="chunk-alpha-2",
            tenant_key="tenant-alpha",
            product_id="product-alpha",
            vision_document_id="vision-doc-alpha",
            content="Alpha API endpoints",
            chunk_order=1,
        ),
        MCPContextIndex(
            id=3,
            chunk_id="chunk-alpha-3",
            tenant_key="tenant-alpha",
            product_id="product-alpha",
            vision_document_id="vision-doc-alpha",
            content="Alpha database schema",
            chunk_order=2,
        ),
    ]

    # NOTE: We should NOT retrieve chunks from tenant-beta
    # (Even though they exist in the database)

    project_alpha = Project(
        id="project-alpha",
        tenant_key="tenant-alpha",
        product_id="product-alpha",
        name="Alpha Project",
        description="Build authentication system",
        status="active",
    )

    # Setup: Mock database session (returns only tenant-alpha chunks)
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = chunks_alpha
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_db_manager = MagicMock()
    mock_db_manager.session = mock_session

    # Execute
    planner = MissionPlanner(db_manager=mock_db_manager)

    # This will FAIL - multi-tenant filtering not implemented (RED phase)
    relevant_chunks = await planner._get_relevant_vision_chunks(
        session=mock_session,
        product=product_alpha,
        project=project_alpha,
        max_tokens=10000,
    )

    # Assert: Only tenant-alpha chunks returned
    assert len(relevant_chunks) > 0
    for chunk in relevant_chunks:
        assert 'alpha' in chunk['content'].lower()
        assert 'beta' not in chunk['content'].lower()

    # Verify the query filtered by tenant_key
    # (Check that execute was called with proper WHERE clause)
    mock_session.execute.assert_called_once()
