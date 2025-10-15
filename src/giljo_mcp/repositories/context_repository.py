"""
Context repository for MCPContextIndex and MCPContextSummary operations.

Handover 0017: Provides agentic vision chunking and summarization with full-text search.
All operations enforce tenant isolation for security.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models import MCPContextIndex, MCPContextSummary
from .base import BaseRepository


class ContextRepository:
    """
    Repository for context indexing and summarization.

    Handles vision document chunking storage and retrieval with PostgreSQL full-text search.
    Supports both chunk-level operations and summary operations for token reduction.
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

    def create_chunk(self, session: Session, tenant_key: str,
                     product_id: str, content: str, keywords: List[str],
                     token_count: int, chunk_order: int,
                     summary: Optional[str] = None) -> MCPContextIndex:
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
            session, tenant_key,
            product_id=product_id,
            content=content,
            keywords=keywords,
            token_count=token_count,
            chunk_order=chunk_order,
            summary=summary
        )

    def search_chunks(self, session: Session, tenant_key: str,
                      product_id: str, query: str, limit: int = 10) -> List[MCPContextIndex]:
        """
        Search chunks by keywords using PostgreSQL full-text search.

        Uses pg_trgm extension for fuzzy matching on keywords array.

        Args:
            session: Database session
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

        result = session.execute(search_query, {
            'tenant_key': tenant_key,
            'product_id': product_id,
            'query_pattern': f'%{query}%',
            'exact_pattern': f'%{query}%',
            'limit': limit
        })

        # Convert results to MCPContextIndex objects
        chunks = []
        for row in result:
            chunk = session.query(MCPContextIndex).filter(
                MCPContextIndex.id == row.id
            ).first()
            if chunk:
                chunks.append(chunk)

        return chunks

    def get_chunks_by_product(self, session: Session, tenant_key: str,
                              product_id: str) -> List[MCPContextIndex]:
        """
        Get all chunks for a product ordered by chunk_order.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to retrieve chunks for

        Returns:
            List of MCPContextIndex instances ordered by chunk_order
        """
        return session.query(MCPContextIndex).filter(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.product_id == product_id
        ).order_by(MCPContextIndex.chunk_order).all()

    def get_chunk_by_id(self, session: Session, tenant_key: str,
                        chunk_id: str) -> Optional[MCPContextIndex]:
        """
        Get a specific chunk by chunk_id.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            chunk_id: Chunk ID to retrieve

        Returns:
            MCPContextIndex instance or None if not found
        """
        return session.query(MCPContextIndex).filter(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.chunk_id == chunk_id
        ).first()

    def delete_chunks_by_product(self, session: Session, tenant_key: str,
                                 product_id: str) -> int:
        """
        Delete all chunks for a product.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to delete chunks for

        Returns:
            Number of chunks deleted
        """
        count = session.query(MCPContextIndex).filter(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.product_id == product_id
        ).count()

        session.query(MCPContextIndex).filter(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.product_id == product_id
        ).delete()

        return count

    # MCPContextSummary operations

    def create_summary(self, session: Session, tenant_key: str,
                       product_id: str, full_content: str,
                       condensed_mission: str, full_tokens: int,
                       condensed_tokens: int) -> MCPContextSummary:
        """
        Create a context summary with token reduction calculation.

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
            session, tenant_key,
            product_id=product_id,
            full_content=full_content,
            condensed_mission=condensed_mission,
            full_token_count=full_tokens,
            condensed_token_count=condensed_tokens,
            reduction_percent=reduction_percent
        )

    def get_summaries_by_product(self, session: Session, tenant_key: str,
                                 product_id: str) -> List[MCPContextSummary]:
        """
        Get all summaries for a product.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            product_id: Product ID to retrieve summaries for

        Returns:
            List of MCPContextSummary instances
        """
        return session.query(MCPContextSummary).filter(
            MCPContextSummary.tenant_key == tenant_key,
            MCPContextSummary.product_id == product_id
        ).order_by(MCPContextSummary.created_at.desc()).all()

    def get_summary_by_id(self, session: Session, tenant_key: str,
                          context_id: str) -> Optional[MCPContextSummary]:
        """
        Get a specific summary by context_id.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            context_id: Context ID to retrieve

        Returns:
            MCPContextSummary instance or None if not found
        """
        return session.query(MCPContextSummary).filter(
            MCPContextSummary.tenant_key == tenant_key,
            MCPContextSummary.context_id == context_id
        ).first()

    def get_token_reduction_stats(self, session: Session, tenant_key: str,
                                  product_id: Optional[str] = None) -> dict:
        """
        Get token reduction statistics for a tenant or specific product.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            product_id: Optional product ID to filter by

        Returns:
            Dictionary with reduction statistics
        """
        query = session.query(MCPContextSummary).filter(
            MCPContextSummary.tenant_key == tenant_key
        )

        if product_id:
            query = query.filter(MCPContextSummary.product_id == product_id)

        summaries = query.all()

        if not summaries:
            return {
                'total_summaries': 0,
                'total_tokens_saved': 0,
                'average_reduction_percent': 0.0,
                'total_original_tokens': 0,
                'total_condensed_tokens': 0
            }

        total_original = sum(s.full_token_count or 0 for s in summaries)
        total_condensed = sum(s.condensed_token_count or 0 for s in summaries)
        total_saved = total_original - total_condensed
        avg_reduction = sum(s.reduction_percent or 0 for s in summaries) / len(summaries)

        return {
            'total_summaries': len(summaries),
            'total_tokens_saved': total_saved,
            'average_reduction_percent': round(avg_reduction, 2),
            'total_original_tokens': total_original,
            'total_condensed_tokens': total_condensed
        }