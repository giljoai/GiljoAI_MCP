"""
Unit tests for ContextIndexer.

Tests database storage and retrieval using PostgreSQL full-text search.
Multi-tenant isolation enforced via tenant_key.

TDD Approach: Tests written first, then implementation.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.giljo_mcp.context_management.indexer import ContextIndexer
from src.giljo_mcp.models import MCPContextIndex


class TestContextIndexer:
    """Test suite for ContextIndexer."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        mock_db = Mock()
        mock_session = Mock()
        # Set up context manager protocol for get_session()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_context_manager.__exit__.return_value = None
        mock_db.get_session.return_value = mock_context_manager
        return mock_db

    @pytest.fixture
    def mock_context_repo(self):
        """Create mock context repository."""
        with patch("src.giljo_mcp.context_management.indexer.ContextRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            yield mock_repo

    @pytest.fixture
    def indexer(self, mock_db_manager, mock_context_repo):
        """Create ContextIndexer with mocked dependencies."""
        return ContextIndexer(mock_db_manager)

    def test_initialization(self, indexer, mock_db_manager):
        """Test indexer initialization."""
        assert indexer.db_manager == mock_db_manager
        assert indexer.context_repo is not None

    def test_store_chunk(self, indexer, mock_context_repo):
        """Test storing a single chunk."""
        tenant_key = "tenant-123"
        product_id = "prod-456"
        chunk = {
            "content": "Test content for chunk",
            "tokens": 50,
            "keywords": ["test", "chunk"],
            "summary": "Test summary",
            "chunk_number": 1,
        }

        # Mock repository create_chunk
        mock_chunk = Mock(spec=MCPContextIndex)
        mock_chunk.chunk_id = "chunk-789"
        mock_context_repo.create_chunk.return_value = mock_chunk

        result = indexer.store_chunk(tenant_key, product_id, chunk)

        # Verify repository was called with correct parameters
        mock_context_repo.create_chunk.assert_called_once()
        call_args = mock_context_repo.create_chunk.call_args

        # Verify result
        assert result == "chunk-789"

    def test_store_chunks_batch(self, indexer, mock_context_repo):
        """Test storing multiple chunks in batch."""
        tenant_key = "tenant-123"
        product_id = "prod-456"
        chunks = [
            {
                "content": "Chunk 1 content",
                "tokens": 50,
                "keywords": ["chunk", "one"],
                "summary": "Summary 1",
                "chunk_number": 1,
            },
            {
                "content": "Chunk 2 content",
                "tokens": 45,
                "keywords": ["chunk", "two"],
                "summary": "Summary 2",
                "chunk_number": 2,
            },
        ]

        # Mock repository create_chunk to return different chunk IDs
        mock_chunks = [Mock(spec=MCPContextIndex, chunk_id="chunk-1"), Mock(spec=MCPContextIndex, chunk_id="chunk-2")]
        mock_context_repo.create_chunk.side_effect = mock_chunks

        result = indexer.store_chunks(tenant_key, product_id, chunks)

        # Verify repository was called twice
        assert mock_context_repo.create_chunk.call_count == 2

        # Verify result
        assert result == ["chunk-1", "chunk-2"]

    def test_store_chunks_empty_list(self, indexer, mock_context_repo):
        """Test storing empty list of chunks."""
        tenant_key = "tenant-123"
        product_id = "prod-456"
        chunks = []

        result = indexer.store_chunks(tenant_key, product_id, chunks)

        # Should not call repository
        mock_context_repo.create_chunk.assert_not_called()

        # Should return empty list
        assert result == []

    def test_search_chunks(self, indexer, mock_context_repo):
        """Test searching chunks by keywords."""
        tenant_key = "tenant-123"
        product_id = "prod-456"
        query = "database"

        # Mock repository search_chunks
        mock_chunks = [
            Mock(spec=MCPContextIndex, chunk_id="chunk-1", content="Database setup"),
            Mock(spec=MCPContextIndex, chunk_id="chunk-2", content="Database config"),
        ]
        mock_context_repo.search_chunks.return_value = mock_chunks

        result = indexer.search_chunks(tenant_key, product_id, query, limit=10)

        # Verify repository was called with correct parameters
        mock_context_repo.search_chunks.assert_called_once()
        call_args = mock_context_repo.search_chunks.call_args
        assert call_args[1]["query"] == query
        assert call_args[1]["limit"] == 10

        # Verify result
        assert len(result) == 2
        assert result[0].chunk_id == "chunk-1"

    def test_search_chunks_no_results(self, indexer, mock_context_repo):
        """Test searching chunks with no results."""
        tenant_key = "tenant-123"
        product_id = "prod-456"
        query = "nonexistent"

        # Mock repository search_chunks to return empty list
        mock_context_repo.search_chunks.return_value = []

        result = indexer.search_chunks(tenant_key, product_id, query, limit=10)

        # Verify result is empty
        assert result == []

    def test_get_chunks_by_product(self, indexer, mock_context_repo):
        """Test retrieving all chunks for a product."""
        tenant_key = "tenant-123"
        product_id = "prod-456"

        # Mock repository get_chunks_by_product
        mock_chunks = [
            Mock(spec=MCPContextIndex, chunk_id="chunk-1", chunk_order=1),
            Mock(spec=MCPContextIndex, chunk_id="chunk-2", chunk_order=2),
            Mock(spec=MCPContextIndex, chunk_id="chunk-3", chunk_order=3),
        ]
        mock_context_repo.get_chunks_by_product.return_value = mock_chunks

        result = indexer.get_chunks_by_product(tenant_key, product_id)

        # Verify repository was called
        mock_context_repo.get_chunks_by_product.assert_called_once()

        # Verify result
        assert len(result) == 3
        assert result[0].chunk_id == "chunk-1"

    def test_get_chunk_by_id(self, indexer, mock_context_repo):
        """Test retrieving a specific chunk by ID."""
        tenant_key = "tenant-123"
        chunk_id = "chunk-789"

        # Mock repository get_chunk_by_id
        mock_chunk = Mock(spec=MCPContextIndex, chunk_id=chunk_id)
        mock_context_repo.get_chunk_by_id.return_value = mock_chunk

        result = indexer.get_chunk_by_id(tenant_key, chunk_id)

        # Verify repository was called
        mock_context_repo.get_chunk_by_id.assert_called_once()

        # Verify result
        assert result.chunk_id == chunk_id

    def test_get_chunk_by_id_not_found(self, indexer, mock_context_repo):
        """Test retrieving non-existent chunk."""
        tenant_key = "tenant-123"
        chunk_id = "nonexistent"

        # Mock repository get_chunk_by_id to return None
        mock_context_repo.get_chunk_by_id.return_value = None

        result = indexer.get_chunk_by_id(tenant_key, chunk_id)

        # Verify result is None
        assert result is None

    def test_delete_chunks_by_product(self, indexer, mock_context_repo):
        """Test deleting all chunks for a product."""
        tenant_key = "tenant-123"
        product_id = "prod-456"

        # Mock repository delete_chunks_by_product to return count
        mock_context_repo.delete_chunks_by_product.return_value = 5

        result = indexer.delete_chunks_by_product(tenant_key, product_id)

        # Verify repository was called
        mock_context_repo.delete_chunks_by_product.assert_called_once()

        # Verify result
        assert result == 5

    def test_multi_tenant_isolation(self, indexer, mock_context_repo):
        """Test that tenant_key is always passed to repository methods."""
        tenant_key = "tenant-123"
        product_id = "prod-456"

        # Test store_chunk
        chunk = {"content": "Test", "tokens": 10, "keywords": [], "summary": "Test", "chunk_number": 1}
        mock_context_repo.create_chunk.return_value = Mock(chunk_id="test")
        indexer.store_chunk(tenant_key, product_id, chunk)

        # Verify tenant_key was passed
        call_args = mock_context_repo.create_chunk.call_args
        # tenant_key should be in keyword args
        assert call_args[1]["tenant_key"] == tenant_key

    def test_chunk_metadata_preserved(self, indexer, mock_context_repo):
        """Test that all chunk metadata is preserved during storage."""
        tenant_key = "tenant-123"
        product_id = "prod-456"
        chunk = {
            "content": "Full content here",
            "tokens": 75,
            "keywords": ["full", "content", "metadata"],
            "summary": "Full summary text",
            "chunk_number": 3,
        }

        mock_chunk = Mock(spec=MCPContextIndex, chunk_id="chunk-meta")
        mock_context_repo.create_chunk.return_value = mock_chunk

        indexer.store_chunk(tenant_key, product_id, chunk)

        # Verify all metadata was passed to repository
        call_args = mock_context_repo.create_chunk.call_args
        assert call_args[1]["content"] == chunk["content"]
        assert call_args[1]["token_count"] == chunk["tokens"]
        assert call_args[1]["keywords"] == chunk["keywords"]
        assert call_args[1]["summary"] == chunk["summary"]
        assert call_args[1]["chunk_order"] == chunk["chunk_number"]


class TestContextIndexerIntegration:
    """Integration tests for ContextIndexer with real database (if available)."""

    pass
