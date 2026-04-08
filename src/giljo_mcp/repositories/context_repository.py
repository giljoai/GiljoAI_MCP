# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Context repository for MCPContextIndex operations.

Provides agentic vision chunking storage and retrieval with full-text search.
All operations enforce tenant isolation for security.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

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
