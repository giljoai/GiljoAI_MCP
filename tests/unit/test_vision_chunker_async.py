"""
Unit tests for async vision document chunking refactoring.

Handover 0047: Tests async conversion of:
- ContextRepository.delete_chunks_by_vision_document()
- VisionDocumentRepository.mark_chunked()
- VisionDocumentChunker.chunk_vision_document()

TDD Approach: Tests written first, then async implementation.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
from src.giljo_mcp.models import VisionDocument
from src.giljo_mcp.repositories.context_repository import ContextRepository
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


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
    async def test_delete_chunks_by_vision_document_async_signature(self, context_repo):
        """Test that delete_chunks_by_vision_document is async."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(id="chunk1"), MagicMock(id="chunk2")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call should be awaitable
        tenant_key = "test-tenant"
        vision_doc_id = "test-doc-id"

        result = await context_repo.delete_chunks_by_vision_document(mock_session, tenant_key, vision_doc_id)

        # Should return count
        assert isinstance(result, int)
        assert result == 2

    @pytest.mark.asyncio
    async def test_delete_chunks_by_vision_document_no_chunks(self, context_repo):
        """Test deletion when no chunks exist."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await context_repo.delete_chunks_by_vision_document(mock_session, "test-tenant", "test-doc-id")

        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_chunks_by_vision_document_multiple_chunks(self, context_repo):
        """Test deletion of multiple chunks."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock multiple chunks
        chunks = [MagicMock(id=f"chunk{i}") for i in range(10)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chunks
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await context_repo.delete_chunks_by_vision_document(mock_session, "test-tenant", "test-doc-id")

        assert result == 10
        # Verify execute was called twice (select then delete)
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
    async def test_mark_chunked_async_signature(self, vision_repo):
        """Test that mark_chunked is async."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock document
        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.id = "test-doc-id"
        mock_doc.chunked = False
        mock_doc.chunk_count = 0
        mock_doc.total_tokens = None
        mock_doc.chunked_at = None
        mock_doc.vision_document = "Test content"

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Call should be awaitable
        await vision_repo.mark_chunked(mock_session, "test-doc-id", chunk_count=5, total_tokens=1000)

        # Verify document was updated
        assert mock_doc.chunked is True
        assert mock_doc.chunk_count == 5
        assert mock_doc.total_tokens == 1000
        assert mock_doc.chunked_at is not None

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

        await vision_repo.mark_chunked(mock_session, "test-doc-id", chunk_count=10, total_tokens=2500)

        after_time = datetime.now(timezone.utc)

        # Verify all fields updated
        assert mock_doc.chunked is True
        assert mock_doc.chunk_count == 10
        assert mock_doc.total_tokens == 2500
        assert before_time <= mock_doc.chunked_at <= after_time
        assert mock_doc.content_hash is not None

    @pytest.mark.asyncio
    async def test_mark_chunked_document_not_found(self, vision_repo):
        """Test mark_chunked when document doesn't exist."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock no document found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise, just skip update
        await vision_repo.mark_chunked(mock_session, "nonexistent-doc", chunk_count=5, total_tokens=1000)

        # Verify flush was not called
        mock_session.flush.assert_not_called()


class TestVisionDocumentChunkerAsync:
    """Test async conversion of VisionDocumentChunker.chunk_vision_document()."""

    @pytest.fixture
    def chunker(self):
        """Create chunker instance."""
        return VisionDocumentChunker()

    @pytest.mark.asyncio
    async def test_chunk_vision_document_async_signature(self, chunker):
        """Test that chunk_vision_document is async."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock vision document
        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.id = "test-doc-id"
        mock_doc.document_name = "Test Document"
        mock_doc.product_id = "test-product-id"
        mock_doc.storage_type = "inline"
        mock_doc.vision_document = "# Test\n\nThis is test content."
        mock_doc.vision_path = None

        # Mock repositories
        with (
            patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo,
            patch("src.giljo_mcp.context_management.chunker.ContextRepository") as MockContextRepo,
        ):
            mock_vision_repo = MockVisionRepo.return_value
            mock_vision_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_vision_repo.mark_chunked = AsyncMock()

            mock_context_repo = MockContextRepo.return_value
            mock_context_repo.delete_chunks_by_vision_document = AsyncMock(return_value=0)

            # Mock chunker's chunk_document method
            chunker.chunk_document = MagicMock(
                return_value=[
                    {"content": "chunk1", "keywords": ["test"], "tokens": 50},
                    {"content": "chunk2", "keywords": ["content"], "tokens": 50},
                ]
            )

            # Call should be awaitable
            result = await chunker.chunk_vision_document(mock_session, "test-tenant", "test-doc-id")

            # Verify result
            assert result["success"] is True
            assert result["document_id"] == "test-doc-id"
            assert result["chunks_created"] == 2
            assert result["total_tokens"] == 100

    @pytest.mark.asyncio
    async def test_chunk_vision_document_awaits_get_by_id(self, chunker):
        """Test that chunk_vision_document awaits vision_repo.get_by_id()."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo:
            mock_vision_repo = MockVisionRepo.return_value
            mock_vision_repo.get_by_id = AsyncMock(return_value=None)

            result = await chunker.chunk_vision_document(mock_session, "test-tenant", "nonexistent-doc")

            # Should fail with document not found
            assert result["success"] is False
            assert "not found" in result["error"]
            # Verify async method was called
            mock_vision_repo.get_by_id.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_chunk_vision_document_awaits_delete_chunks(self, chunker):
        """Test that chunk_vision_document awaits delete_chunks_by_vision_document()."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.storage_type = "inline"
        mock_doc.vision_document = "Test content"
        mock_doc.product_id = "test-product"

        with (
            patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo,
            patch("src.giljo_mcp.context_management.chunker.ContextRepository") as MockContextRepo,
        ):
            mock_vision_repo = MockVisionRepo.return_value
            mock_vision_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_vision_repo.mark_chunked = AsyncMock()

            mock_context_repo = MockContextRepo.return_value
            mock_context_repo.delete_chunks_by_vision_document = AsyncMock(return_value=5)

            chunker.chunk_document = MagicMock(return_value=[{"content": "chunk", "keywords": [], "tokens": 50}])

            result = await chunker.chunk_vision_document(mock_session, "test-tenant", "test-doc-id")

            # Verify async delete was called
            mock_context_repo.delete_chunks_by_vision_document.assert_awaited_once()
            assert result["old_chunks_deleted"] == 5

    @pytest.mark.asyncio
    async def test_chunk_vision_document_awaits_mark_chunked(self, chunker):
        """Test that chunk_vision_document awaits mark_chunked()."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.storage_type = "inline"
        mock_doc.vision_document = "Test content"
        mock_doc.product_id = "test-product"
        mock_doc.id = "test-doc-id"

        with (
            patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo,
            patch("src.giljo_mcp.context_management.chunker.ContextRepository") as MockContextRepo,
        ):
            mock_vision_repo = MockVisionRepo.return_value
            mock_vision_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_vision_repo.mark_chunked = AsyncMock()

            mock_context_repo = MockContextRepo.return_value
            mock_context_repo.delete_chunks_by_vision_document = AsyncMock(return_value=0)

            chunker.chunk_document = MagicMock(return_value=[{"content": "chunk", "keywords": [], "tokens": 50}])

            await chunker.chunk_vision_document(mock_session, "test-tenant", "test-doc-id")

            # Verify async mark_chunked was called
            mock_vision_repo.mark_chunked.assert_awaited_once_with(mock_session, "test-doc-id", 1, 50)

    @pytest.mark.asyncio
    async def test_chunk_vision_document_file_not_found(self, chunker):
        """Test chunk_vision_document handles missing file."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.storage_type = "file"
        mock_doc.vision_path = "nonexistent/path/file.md"
        mock_doc.vision_document = None

        with patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo:
            mock_vision_repo = MockVisionRepo.return_value
            mock_vision_repo.get_by_id = AsyncMock(return_value=mock_doc)

            result = await chunker.chunk_vision_document(mock_session, "test-tenant", "test-doc-id")

            # Should fail with file not found
            assert result["success"] is False
            assert "File not found" in result["error"]

    @pytest.mark.asyncio
    async def test_chunk_vision_document_empty_content(self, chunker):
        """Test chunk_vision_document handles empty content."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_doc = MagicMock(spec=VisionDocument)
        mock_doc.storage_type = "inline"
        mock_doc.vision_document = ""

        with (
            patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo,
            patch("src.giljo_mcp.context_management.chunker.ContextRepository") as MockContextRepo,
        ):
            mock_vision_repo = MockVisionRepo.return_value
            mock_vision_repo.get_by_id = AsyncMock(return_value=mock_doc)

            mock_context_repo = MockContextRepo.return_value
            mock_context_repo.delete_chunks_by_vision_document = AsyncMock(return_value=0)

            result = await chunker.chunk_vision_document(mock_session, "test-tenant", "test-doc-id")

            # Should fail with no content error
            assert result["success"] is False
            assert "no content" in result["error"]

    @pytest.mark.asyncio
    async def test_chunk_vision_document_path_normalization(self, chunker):
        """Test chunk_vision_document normalizes Windows paths."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Create temp file for test
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            # Simulate Windows backslash path
            windows_path = str(temp_path).replace("/", "\\")

            mock_doc = MagicMock(spec=VisionDocument)
            mock_doc.storage_type = "file"
            mock_doc.vision_path = windows_path
            mock_doc.vision_document = None
            mock_doc.product_id = "test-product"
            mock_doc.id = "test-doc-id"

            with (
                patch("src.giljo_mcp.context_management.chunker.VisionDocumentRepository") as MockVisionRepo,
                patch("src.giljo_mcp.context_management.chunker.ContextRepository") as MockContextRepo,
            ):
                mock_vision_repo = MockVisionRepo.return_value
                mock_vision_repo.get_by_id = AsyncMock(return_value=mock_doc)
                mock_vision_repo.mark_chunked = AsyncMock()

                mock_context_repo = MockContextRepo.return_value
                mock_context_repo.delete_chunks_by_vision_document = AsyncMock(return_value=0)

                chunker.chunk_document = MagicMock(return_value=[{"content": "chunk", "keywords": [], "tokens": 50}])

                result = await chunker.chunk_vision_document(mock_session, "test-tenant", "test-doc-id")

                # Should succeed (path was normalized)
                assert result["success"] is True
        finally:
            temp_path.unlink()
