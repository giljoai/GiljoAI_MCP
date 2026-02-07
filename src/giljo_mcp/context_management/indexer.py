"""
Context Indexer - Database storage and retrieval for chunked documents.

Handover 0018: Production-grade indexing using PostgreSQL full-text search.

Features:
- Database storage via ContextRepository
- PostgreSQL full-text search on keywords
- Multi-tenant isolation via tenant_key
- Batch storage operations
- Efficient chunk retrieval
"""

import logging
from typing import Any

from src.giljo_mcp.models import MCPContextIndex
from src.giljo_mcp.repositories.context_repository import ContextRepository


logger = logging.getLogger(__name__)


class ContextIndexer:
    """
    Context indexer using PostgreSQL full-text search.

    Stores and retrieves chunked vision documents with multi-tenant isolation.
    Leverages ContextRepository for database operations.
    """

    def __init__(self, db_manager):
        """
        Initialize ContextIndexer.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.context_repo = ContextRepository(db_manager)

        logger.info("ContextIndexer initialized")

    def store_chunk(self, tenant_key: str, product_id: str, chunk: dict[str, Any]) -> str:
        """
        Store a single chunk in the database.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID this chunk belongs to
            chunk: Chunk dictionary with content, tokens, keywords, summary, chunk_number

        Returns:
            Chunk ID of stored chunk
        """
        with self.db_manager.get_session() as session:
            created_chunk = self.context_repo.create_chunk(
                session=session,
                tenant_key=tenant_key,
                product_id=product_id,
                content=chunk["content"],
                keywords=chunk["keywords"],
                token_count=chunk["tokens"],
                chunk_order=chunk["chunk_number"],
                summary=chunk.get("summary"),
            )

            session.commit()

            logger.debug(f"Stored chunk {created_chunk.chunk_id} for product {product_id}")

            return created_chunk.chunk_id

    def store_chunks(self, tenant_key: str, product_id: str, chunks: list[dict[str, Any]]) -> list[str]:
        """
        Store multiple chunks in batch.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID these chunks belong to
            chunks: List of chunk dictionaries

        Returns:
            List of chunk IDs in same order as input chunks
        """
        if not chunks:
            return []

        chunk_ids = []

        with self.db_manager.get_session() as session:
            for chunk in chunks:
                created_chunk = self.context_repo.create_chunk(
                    session=session,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    content=chunk["content"],
                    keywords=chunk["keywords"],
                    token_count=chunk["tokens"],
                    chunk_order=chunk["chunk_number"],
                    summary=chunk.get("summary"),
                )

                chunk_ids.append(created_chunk.chunk_id)

            session.commit()

        logger.info(f"Stored {len(chunk_ids)} chunks for product {product_id}")

        return chunk_ids

    def search_chunks(self, tenant_key: str, product_id: str, query: str, limit: int = 10) -> list[MCPContextIndex]:
        """
        Search chunks by keywords using PostgreSQL full-text search.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID to search within
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of MCPContextIndex instances matching query
        """
        with self.db_manager.get_session() as session:
            results = self.context_repo.search_chunks(
                session=session, tenant_key=tenant_key, product_id=product_id, query=query, limit=limit
            )

            logger.debug(f"Search for '{query}' in product {product_id}: {len(results)} results")

            return results

    def get_chunks_by_product(self, tenant_key: str, product_id: str) -> list[MCPContextIndex]:
        """
        Get all chunks for a product ordered by chunk_order.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID to retrieve chunks for

        Returns:
            List of MCPContextIndex instances ordered by chunk_order
        """
        with self.db_manager.get_session() as session:
            chunks = self.context_repo.get_chunks_by_product(
                session=session, tenant_key=tenant_key, product_id=product_id
            )

            logger.debug(f"Retrieved {len(chunks)} chunks for product {product_id}")

            return chunks

    def get_chunk_by_id(self, tenant_key: str, chunk_id: str) -> MCPContextIndex | None:
        """
        Get a specific chunk by chunk_id.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            chunk_id: Chunk ID to retrieve

        Returns:
            MCPContextIndex instance or None if not found
        """
        with self.db_manager.get_session() as session:
            chunk = self.context_repo.get_chunk_by_id(session=session, tenant_key=tenant_key, chunk_id=chunk_id)

            if chunk:
                logger.debug(f"Retrieved chunk {chunk_id}")
            else:
                logger.debug(f"Chunk {chunk_id} not found")

            return chunk

    def delete_chunks_by_product(self, tenant_key: str, product_id: str) -> int:
        """
        Delete all chunks for a product.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID to delete chunks for

        Returns:
            Number of chunks deleted
        """
        with self.db_manager.get_session() as session:
            count = self.context_repo.delete_chunks_by_product(
                session=session, tenant_key=tenant_key, product_id=product_id
            )

            session.commit()

            logger.info(f"Deleted {count} chunks for product {product_id}")

            return count
