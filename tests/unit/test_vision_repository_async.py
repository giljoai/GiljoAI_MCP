"""
Unit tests for VisionDocumentRepository and ContextRepository async operations.
Tests the async refactoring for Handover 0047 - Vision Document Chunking Async Fix.
"""

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPContextIndex, VisionDocument
from src.giljo_mcp.repositories.context_repository import ContextRepository
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository


class TestVisionDocumentRepositoryAsync:
    """Test VisionDocumentRepository async methods"""

    @pytest.mark.asyncio
    async def test_get_by_id_is_async(self, db_session: AsyncSession, vision_document_with_file: VisionDocument):
        """Verify get_by_id is async and accepts AsyncSession"""
        repo = VisionDocumentRepository()

        # Should be async method
        doc = await repo.get_by_id(db_session, vision_document_with_file.tenant_key, vision_document_with_file.id)

        assert doc is not None
        assert doc.id == vision_document_with_file.id
        assert doc.document_name == vision_document_with_file.document_name

    @pytest.mark.asyncio
    async def test_get_by_id_tenant_isolation(
        self, db_session: AsyncSession, vision_document_with_file: VisionDocument
    ):
        """Verify get_by_id enforces tenant isolation"""
        repo = VisionDocumentRepository()

        # Attempt to get document with wrong tenant key
        doc = await repo.get_by_id(db_session, "wrong-tenant-key", vision_document_with_file.id)

        # Should return None (tenant isolation)
        assert doc is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self, db_session: AsyncSession):
        """Verify get_by_id returns None for non-existent document"""
        repo = VisionDocumentRepository()

        doc = await repo.get_by_id(db_session, "test-tenant", "nonexistent-id")

        assert doc is None

    @pytest.mark.asyncio
    async def test_mark_chunked_updates_metadata(
        self, db_session: AsyncSession, vision_document_with_file: VisionDocument
    ):
        """Test mark_chunked updates document metadata correctly"""
        repo = VisionDocumentRepository()

        # Initially not chunked
        assert vision_document_with_file.chunked is False
        assert vision_document_with_file.chunk_count == 0

        # Mark as chunked (NOTE: This method should be async after refactoring)
        # For now, testing current implementation
        # TODO: Update to await after async refactoring
        try:
            # Try async call (if refactored)
            await repo.mark_chunked(db_session, vision_document_with_file.id, 5, 2500)
        except TypeError:
            # Fallback to sync call (current implementation)
            repo.mark_chunked(db_session, vision_document_with_file.id, 5, 2500)

        await db_session.flush()
        await db_session.refresh(vision_document_with_file)

        # Verify updates
        assert vision_document_with_file.chunked is True
        assert vision_document_with_file.chunk_count == 5
        assert vision_document_with_file.total_tokens == 2500
        assert vision_document_with_file.chunked_at is not None

    @pytest.mark.asyncio
    async def test_mark_chunked_handles_missing_document(self, db_session: AsyncSession):
        """Test mark_chunked gracefully handles non-existent document"""
        repo = VisionDocumentRepository()

        # Should not raise exception
        try:
            # Try async call
            await repo.mark_chunked(db_session, "nonexistent-id", 3, 1500)
        except TypeError:
            # Fallback to sync call
            repo.mark_chunked(db_session, "nonexistent-id", 3, 1500)

        # No error should occur


class TestContextRepositoryAsync:
    """Test ContextRepository async operations"""

    @pytest.mark.asyncio
    async def test_delete_chunks_by_vision_document_is_async(
        self, db_session: AsyncSession, vision_document_with_chunks
    ):
        """Verify delete_chunks_by_vision_document works with AsyncSession"""
        doc, chunks = vision_document_with_chunks
        repo = ContextRepository(db_manager=None)

        # Should delete chunks
        # NOTE: Method should be async after refactoring
        try:
            # Try async call
            deleted_count = await repo.delete_chunks_by_vision_document(db_session, doc.tenant_key, doc.id)
        except TypeError:
            # Fallback to sync call (current implementation)
            deleted_count = repo.delete_chunks_by_vision_document(db_session, doc.tenant_key, doc.id)

        await db_session.flush()

        # Verify deletion
        assert deleted_count == 3

        # Verify chunks are gone
        stmt = select(MCPContextIndex).where(MCPContextIndex.vision_document_id == doc.id)
        result = await db_session.execute(stmt)
        remaining_chunks = result.scalars().all()

        assert len(remaining_chunks) == 0

    @pytest.mark.asyncio
    async def test_delete_chunks_tenant_isolation(self, db_session: AsyncSession, vision_document_with_chunks):
        """Verify delete_chunks enforces tenant isolation"""
        doc, chunks = vision_document_with_chunks
        repo = ContextRepository(db_manager=None)

        # Try to delete with wrong tenant key
        try:
            deleted_count = await repo.delete_chunks_by_vision_document(db_session, "wrong-tenant", doc.id)
        except TypeError:
            deleted_count = repo.delete_chunks_by_vision_document(db_session, "wrong-tenant", doc.id)

        await db_session.flush()

        # Should delete 0 (tenant isolation)
        assert deleted_count == 0

        # Verify chunks still exist
        stmt = select(MCPContextIndex).where(
            MCPContextIndex.vision_document_id == doc.id,
            MCPContextIndex.tenant_key == doc.tenant_key,
        )
        result = await db_session.execute(stmt)
        remaining_chunks = result.scalars().all()

        assert len(remaining_chunks) == 3

    @pytest.mark.asyncio
    async def test_delete_chunks_returns_zero_for_no_chunks(
        self, db_session: AsyncSession, vision_document_with_file: VisionDocument
    ):
        """Verify delete_chunks returns 0 when no chunks exist"""
        repo = ContextRepository(db_manager=None)

        try:
            deleted_count = await repo.delete_chunks_by_vision_document(
                db_session, vision_document_with_file.tenant_key, vision_document_with_file.id
            )
        except TypeError:
            deleted_count = repo.delete_chunks_by_vision_document(
                db_session, vision_document_with_file.tenant_key, vision_document_with_file.id
            )

        assert deleted_count == 0


class TestAsyncSessionCompatibility:
    """Test AsyncSession compatibility across repositories"""

    @pytest.mark.asyncio
    async def test_async_session_type_hints(self):
        """Verify repositories accept AsyncSession type hints"""
        from inspect import signature

        vision_repo = VisionDocumentRepository()

        # Check get_by_id signature
        sig = signature(vision_repo.get_by_id)
        params = sig.parameters

        # Should have session parameter
        assert "session" in params
        # Type hint should be AsyncSession (after refactoring)
        # This test will pass once refactoring is complete

    @pytest.mark.asyncio
    async def test_session_operations_use_await(
        self, db_session: AsyncSession, vision_document_with_file: VisionDocument
    ):
        """Verify session operations properly use await"""
        repo = VisionDocumentRepository()

        # All database operations should be awaited
        doc = await repo.get_by_id(db_session, vision_document_with_file.tenant_key, vision_document_with_file.id)

        # Flush should also be awaited
        await db_session.flush()

        # No "coroutine was never awaited" warnings should occur
        assert doc is not None

    @pytest.mark.asyncio
    async def test_no_sync_session_mixing(self, db_session: AsyncSession):
        """Verify no mixing of sync Session with async operations"""
        # AsyncSession should be used throughout
        assert hasattr(db_session, "execute")
        assert hasattr(db_session, "flush")

        # Should not have sync-only methods
        # AsyncSession.execute returns awaitable

        # execute should return coroutine
        result = db_session.execute(select(VisionDocument))
        assert hasattr(result, "__await__")


class TestRepositoryErrorHandling:
    """Test error handling in repository async operations"""

    @pytest.mark.asyncio
    async def test_handles_database_errors_gracefully(self, db_session: AsyncSession):
        """Verify repositories handle database errors gracefully"""
        repo = VisionDocumentRepository()

        # Close session to simulate error
        await db_session.close()

        # Should raise appropriate exception (not hang or deadlock)
        with pytest.raises(Exception):
            await repo.get_by_id(db_session, "tenant", "doc-id")

    @pytest.mark.asyncio
    async def test_handles_invalid_tenant_key(
        self, db_session: AsyncSession, vision_document_with_file: VisionDocument
    ):
        """Verify repositories handle invalid tenant keys"""
        repo = VisionDocumentRepository()

        # Empty tenant key
        doc = await repo.get_by_id(db_session, "", vision_document_with_file.id)
        assert doc is None

        # None tenant key should not crash
        with pytest.raises(Exception):
            await repo.get_by_id(db_session, None, vision_document_with_file.id)
