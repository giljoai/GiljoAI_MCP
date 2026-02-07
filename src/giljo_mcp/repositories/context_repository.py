"""
Context repository for MCPContextIndex and MCPContextSummary operations.

Handover 0017: Provides agentic vision chunking and summarization with full-text search.
All operations enforce tenant isolation for security.
"""

from typing import List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..models import MCPContextIndex, MCPContextSummary
from .base import BaseRepository


class ContextRepository:
    """
    Repository for context indexing and summarization.

    Handles vision document chunking storage and retrieval with PostgreSQL full-text search.
    Supports both chunk-level operations and summary operations for context prioritization.
    """

    def __init__(self, db_manager):
        """
        Initialize context repository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.context_index_repo = BaseRepository(MCPContextIndex, db_manager)
        self.context_summary_repo = BaseRepository(MCPContextSummary, db_manager)

    # MCPContextIndex operations

    def create_chunk(
        self,
        session: Session,
        tenant_key: str,
        product_id: str,
        content: str,
        keywords: List[str],
        token_count: int,
        chunk_order: int,
        summary: Optional[str] = None,
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
    ) -> List[MCPContextIndex]:
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
    ) -> List[MCPContextIndex]:
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

    async def get_chunk_by_id(self, session: AsyncSession, tenant_key: str, chunk_id: str) -> Optional[MCPContextIndex]:
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

    # MCPContextSummary operations

    def create_summary(
        self,
        session: Session,
        tenant_key: str,
        product_id: str,
        full_content: str,
        condensed_mission: str,
        full_tokens: int,
        condensed_tokens: int,
    ) -> MCPContextSummary:
        """
        Create a context summary with context prioritization calculation.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            product_id: Product this summary belongs to
            full_content: Original full context
            condensed_mission: Orchestrator-generated condensed mission
            full_tokens: Original token count
            condensed_tokens: Condensed token count

        Returns:
            Created MCPContextSummary instance
        """
        reduction_percent = ((full_tokens - condensed_tokens) / full_tokens) * 100 if full_tokens > 0 else 0.0

        return self.context_summary_repo.create(
            session,
            tenant_key,
            product_id=product_id,
            full_content=full_content,
            condensed_mission=condensed_mission,
            full_token_count=full_tokens,
            condensed_token_count=condensed_tokens,
            reduction_percent=reduction_percent,
        )

    async def get_summaries_by_product(
        self, session: AsyncSession, tenant_key: str, product_id: str
    ) -> List[MCPContextSummary]:
        """
        Get all summaries for a product.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to retrieve summaries for

        Returns:
            List of MCPContextSummary instances
        """
        result = await session.execute(
            select(MCPContextSummary)
            .where(MCPContextSummary.tenant_key == tenant_key, MCPContextSummary.product_id == product_id)
            .order_by(MCPContextSummary.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_summary_by_id(
        self, session: AsyncSession, tenant_key: str, context_id: str
    ) -> Optional[MCPContextSummary]:
        """
        Get a specific summary by context_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            context_id: Context ID to retrieve

        Returns:
            MCPContextSummary instance or None if not found
        """
        result = await session.execute(
            select(MCPContextSummary).where(
                MCPContextSummary.tenant_key == tenant_key, MCPContextSummary.context_id == context_id
            )
        )
        return result.scalar_one_or_none()

    async def get_token_reduction_stats(
        self, session: AsyncSession, tenant_key: str, product_id: Optional[str] = None
    ) -> dict:
        """
        Get context prioritization statistics for a tenant or specific product.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product ID to filter by

        Returns:
            Dictionary with reduction statistics
        """
        stmt = select(MCPContextSummary).where(MCPContextSummary.tenant_key == tenant_key)

        if product_id:
            stmt = stmt.where(MCPContextSummary.product_id == product_id)

        result = await session.execute(stmt)
        summaries = list(result.scalars().all())

        if not summaries:
            return {
                "total_summaries": 0,
                "total_tokens_saved": 0,
                "average_reduction_percent": 0.0,
                "total_original_tokens": 0,
                "total_condensed_tokens": 0,
            }

        total_original = sum(s.full_token_count or 0 for s in summaries)
        total_condensed = sum(s.condensed_token_count or 0 for s in summaries)
        total_saved = total_original - total_condensed
        avg_reduction = sum(s.reduction_percent or 0 for s in summaries) / len(summaries)

        return {
            "total_summaries": len(summaries),
            "total_tokens_saved": total_saved,
            "average_reduction_percent": round(avg_reduction, 2),
            "total_original_tokens": total_original,
            "total_condensed_tokens": total_condensed,
        }
