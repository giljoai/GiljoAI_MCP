"""
Context repository for MCPContextIndex operations.

Provides agentic vision chunking storage and retrieval with full-text search.
All operations enforce tenant isolation for security.
"""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.giljo_mcp.models import MCPContextIndex

from .base import BaseRepository


class ContextRepository:
    """
    Repository for MCPContextIndex operations.

    Handles vision document chunking storage and retrieval with PostgreSQL full-text search.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self.context_index_repo = BaseRepository(MCPContextIndex, db_manager)

    # MCPContextIndex operations

    def create_chunk(
        self,
        session: Session,
        tenant_key: str,
        product_id: str,
        content: str,
        keywords: list[str],
        token_count: int,
        chunk_order: int,
        summary: str | None = None,
    ) -> MCPContextIndex:
        """
        Create a context chunk.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            product_id: Product this chunk belongs to
            content: Chunk content
            keywords: List of keywords for search
            token_count: Estimated token count
            chunk_order: Sequential order of chunk
            summary: Optional LLM-generated summary

        Returns:
            Created MCPContextIndex instance
        """
        return self.context_index_repo.create(
            session,
            tenant_key,
            product_id=product_id,
            content=content,
            keywords=keywords,
            token_count=token_count,
            chunk_order=chunk_order,
            summary=summary,
        )

    async def search_chunks(
        self, session: AsyncSession, tenant_key: str, product_id: str, query: str, limit: int = 10
    ) -> list[MCPContextIndex]:
        """
        Search chunks by keywords using PostgreSQL full-text search.

        Uses pg_trgm extension for fuzzy matching on keywords array.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product to search within
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching MCPContextIndex instances
        """
        # PostgreSQL full-text search on keywords array
        # Uses similarity() function from pg_trgm extension
        search_query = text("""
            SELECT * FROM mcp_context_index
            WHERE tenant_key = :tenant_key
              AND product_id = :product_id
              AND (
                content ILIKE :query_pattern
                OR EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(keywords) AS keyword
                  WHERE keyword ILIKE :query_pattern
                )
              )
            ORDER BY
              CASE WHEN content ILIKE :exact_pattern THEN 1 ELSE 2 END,
              chunk_order
            LIMIT :limit
        """)

        result = await session.execute(
            search_query,
            {
                "tenant_key": tenant_key,
                "product_id": product_id,
                "query_pattern": f"%{query}%",
                "exact_pattern": f"%{query}%",
                "limit": limit,
            },
        )

        # Convert results to MCPContextIndex objects
        chunks = []
        for row in result:
            stmt = select(MCPContextIndex).where(MCPContextIndex.id == row.id)
            chunk_result = await session.execute(stmt)
            chunk = chunk_result.scalar_one_or_none()
            if chunk:
                chunks.append(chunk)

        return chunks

    async def get_chunks_by_product(
        self, session: AsyncSession, tenant_key: str, product_id: str
    ) -> list[MCPContextIndex]:
        """
        Get all chunks for a product ordered by chunk_order.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to retrieve chunks for

        Returns:
            List of MCPContextIndex instances ordered by chunk_order
        """
        result = await session.execute(
            select(MCPContextIndex)
            .where(MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.product_id == product_id)
            .order_by(MCPContextIndex.chunk_order)
        )
        return list(result.scalars().all())

    async def get_chunk_by_id(self, session: AsyncSession, tenant_key: str, chunk_id: str) -> MCPContextIndex | None:
        """
        Get a specific chunk by chunk_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            chunk_id: Chunk ID to retrieve

        Returns:
            MCPContextIndex instance or None if not found
        """
        result = await session.execute(
            select(MCPContextIndex).where(
                MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.chunk_id == chunk_id
            )
        )
        return result.scalar_one_or_none()

    async def delete_chunks_by_product(self, session: AsyncSession, tenant_key: str, product_id: str) -> int:
        """
        Delete all chunks for a product.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to delete chunks for

        Returns:
            Number of chunks deleted
        """
        from sqlalchemy import delete

        # Count first
        count_result = await session.execute(
            select(func.count())
            .select_from(MCPContextIndex)
            .where(MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.product_id == product_id)
        )
        count = count_result.scalar()

        # Then delete
        await session.execute(
            delete(MCPContextIndex).where(
                MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.product_id == product_id
            )
        )

        return count

    async def delete_chunks_by_vision_document(
        self, session: AsyncSession, tenant_key: str, vision_document_id: str
    ) -> int:
        """
        Delete all chunks for a specific vision document.

        Handover 0043 Phase 2: Selective deletion for multi-vision document support.
        Allows re-chunking of individual documents without affecting others.

        Handover 0047: Converted to async for proper async/await propagation.

        Args:
            session: Async database session
            tenant_key: Tenant key for multi-tenant isolation
            vision_document_id: Vision document ID to delete chunks for

        Returns:
            Number of chunks deleted
        """
        from sqlalchemy import delete, select

        # Count chunks before deletion
        stmt = select(MCPContextIndex).where(
            MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.vision_document_id == vision_document_id
        )
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        count = len(chunks)

        # Delete chunks
        delete_stmt = delete(MCPContextIndex).where(
            MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.vision_document_id == vision_document_id
        )
        await session.execute(delete_stmt)

        return count
