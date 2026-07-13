# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Context repository for MCPContextIndex operations.

Provides agentic vision chunking storage and retrieval with full-text search.
All operations enforce tenant isolation for security.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import MCPContextIndex


class ContextRepository:
    """
    Repository for MCPContextIndex operations.

    Handles vision document chunking storage and retrieval with PostgreSQL full-text search.
    """

    def __init__(self, db_manager):
        self.db = db_manager

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
            List of matching MCPContextIndex instances in FTS rank order
        """
        # PostgreSQL full-text search on keywords array (pg_trgm similarity()).
        # Returns ranked ids only; the ORM rows are hydrated in a single
        # follow-up IN(...) query to avoid the historical N+1 (BE-6003).
        # BE-6130b: skip chunks whose parent vision doc is soft-deleted (trashed).
        # Soft-delete does NOT cascade, so the chunks survive — they must simply
        # stop being retrieved until the doc is restored. Legacy product-level
        # chunks (vision_document_id IS NULL) have no parent and are kept.
        search_query = text("""
            SELECT id FROM mcp_context_index
            WHERE tenant_key = :tenant_key
              AND product_id = :product_id
              AND (
                content ILIKE :query_pattern
                OR EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(keywords) AS keyword
                  WHERE keyword ILIKE :query_pattern
                )
              )
              AND (
                vision_document_id IS NULL
                OR NOT EXISTS (
                  SELECT 1 FROM vision_documents vd
                  WHERE vd.id = mcp_context_index.vision_document_id
                    AND vd.deleted_at IS NOT NULL
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

        ordered_ids = [row.id for row in result]
        if not ordered_ids:
            return []

        # Single hydration query, tenant-scoped. IN(...) does not preserve the
        # FTS rank order, so re-sort the ORM rows to match ordered_ids.
        stmt = select(MCPContextIndex).where(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.id.in_(ordered_ids),
        )
        chunk_result = await session.execute(stmt)
        by_id = {chunk.id: chunk for chunk in chunk_result.scalars()}

        return [by_id[chunk_id] for chunk_id in ordered_ids if chunk_id in by_id]

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
