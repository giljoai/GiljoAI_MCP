"""
Unit tests for async vision document chunking refactoring (Handover 0047).

Tests async conversion of:
- ContextRepository.delete_chunks_by_vision_document()
- VisionDocumentRepository.mark_chunked()
- VisionDocumentChunker.chunk_vision_document()
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.repositories.context_repository import ContextRepository
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
from src.giljo_mcp.models import MCPContextIndex, VisionDocument


class TestContextRepositoryAsync:
    """Test async conversion of ContextRepository methods."""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        return MagicMock()

    @pytest.fixture
    def context_repo(self, mock_db_manager):
        """Create context repository instance."""
        return ContextRepository(mock_db_manager)

    @pytest.mark.asyncio
    async def test_delete_chunks_by_vision_document_returns_count(self, context_repo):
        """Test that delete_chunks_by_vision_document returns correct count."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(id="chunk1"),
            MagicMock(id="chunk2")
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call method
        result = await context_repo.delete_chunks_by_vision_document(
            mock_session, "test-tenant", "test-doc-id"
        )

        # Should return count
        assert isinstance(result, int)
        assert result == 2
        # Verify execute was called (select then delete)
        assert mock_session.execute.call_count == 2


class TestVisionDocumentRepositoryAsync:
    """Test async conversion of VisionDocumentRepository methods."""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        return MagicMock()

    @pytest.fixture
    def vision_repo(self, mock_db_manager):
        """Create vision document repository instance."""
        return VisionDocumentRepository(mock_db_manager)

    @pytest.mark.asyncio
    async def test_mark_chunked_updates_fields(self, vision_repo):
        """Test mark_chunked updates all required fields."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.vision_document = "Test content for hashing"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_session.execute = AsyncMock(return_value=mock_result)

        before_time = datetime.now(timezone.utc)

        await vision_repo.mark_chunked(
            mock_session, "test-doc-id", chunk_count=10, total_tokens=2500
        )

        after_time = datetime.now(timezone.utc)

        # Verify all fields updated
        assert mock_doc.chunked is True
        assert mock_doc.chunk_count == 10
        assert mock_doc.total_tokens == 2500
        assert before_time <= mock_doc.chunked_at <= after_time
        assert mock_doc.content_hash is not None
        # Verify flush was called
        mock_session.flush.assert_awaited_once()


class TestVisionDocumentChunkerAsync:
    """Test async conversion of VisionDocumentChunker.chunk_vision_document()."""

    @pytest.fixture
    def chunker(self):
        """Create chunker instance."""
        return VisionDocumentChunker()

    @pytest.mark.asyncio
    async def test_chunk_vision_document_is_awaitable(self, chunker):
        """Test that chunk_vision_document is async and awaitable."""
        import inspect

        # Verify method is async
        assert inspect.iscoroutinefunction(chunker.chunk_vision_document)

    @pytest.mark.asyncio
    async def test_chunk_vision_document_with_mocked_repos(self, chunker):
        """Test chunk_vision_document awaits all async calls."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock vision document
        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.id = "test-doc-id"
        mock_doc.document_name = "Test Document"
        mock_doc.product_id = "test-product-id"
        mock_doc.storage_type = "inline"
        mock_doc.vision_document = "Test content for chunking"
        mock_doc.vision_path = None

        # Patch repository classes where chunker imports them from
        # chunker.py uses: from ..repositories.vision_document_repository import VisionDocumentRepository
        with patch('src.giljo_mcp.repositories.vision_document_repository.VisionDocumentRepository') as MockVisionRepo, \
             patch('src.giljo_mcp.repositories.context_repository.ContextRepository') as MockContextRepo:

            mock_vision_repo_instance = MockVisionRepo.return_value
            mock_vision_repo_instance.get_by_id = AsyncMock(return_value=mock_doc)
            mock_vision_repo_instance.mark_chunked = AsyncMock()

            mock_context_repo_instance = MockContextRepo.return_value
            mock_context_repo_instance.delete_chunks_by_vision_document = AsyncMock(return_value=0)

            # Mock chunk_document method
            chunker.chunk_document = MagicMock(return_value=[
                {"content": "chunk1", "keywords": ["test"], "tokens": 50},
                {"content": "chunk2", "keywords": ["content"], "tokens": 50}
            ])

            # Call async method
            result = await chunker.chunk_vision_document(
                mock_session, "test-tenant", "test-doc-id"
            )

            # Verify result
            assert result["success"] is True
            assert result["document_id"] == "test-doc-id"
            assert result["chunks_created"] == 2
            assert result["total_tokens"] == 100

            # Verify async methods were awaited
            mock_vision_repo_instance.get_by_id.assert_awaited_once_with(
                mock_session, "test-tenant", "test-doc-id"
            )
            mock_context_repo_instance.delete_chunks_by_vision_document.assert_awaited_once_with(
                mock_session, "test-tenant", "test-doc-id"
            )
            mock_session.flush.assert_awaited_once()
            mock_vision_repo_instance.mark_chunked.assert_awaited_once_with(
                mock_session, "test-doc-id", 2, 100
            )

    @pytest.mark.asyncio
    async def test_chunk_vision_document_handles_missing_document(self, chunker):
        """Test chunk_vision_document handles missing document gracefully."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Patch repository to return None (document not found)
        with patch('src.giljo_mcp.repositories.vision_document_repository.VisionDocumentRepository') as MockVisionRepo:
            mock_vision_repo_instance = MockVisionRepo.return_value
            mock_vision_repo_instance.get_by_id = AsyncMock(return_value=None)

            # Call async method
            result = await chunker.chunk_vision_document(
                mock_session, "test-tenant", "nonexistent-doc-id"
            )

            # Verify error response
            assert result["success"] is False
            assert "error" in result
            assert "not found" in result["error"].lower()

            # Verify get_by_id was awaited
            mock_vision_repo_instance.get_by_id.assert_awaited_once_with(
                mock_session, "test-tenant", "nonexistent-doc-id"
            )
