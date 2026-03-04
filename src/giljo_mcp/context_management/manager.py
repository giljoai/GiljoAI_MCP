"""
Context Management System - Main orchestration interface.

Handover 0018: Production-grade context management orchestration.

Features:
- Complete workflow: chunk → index → load → summarize
- Multi-tenant isolation
- Context prioritization tracking
- Production-grade error handling
"""

import logging
from typing import Any

from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
from src.giljo_mcp.context_management.indexer import ContextIndexer
from src.giljo_mcp.context_management.loader import DynamicContextLoader
from src.giljo_mcp.context_management.summarizer import ContextSummarizer
from src.giljo_mcp.tools.chunking import VISION_DELIVERY_BUDGET


logger = logging.getLogger(__name__)


class ContextManagementSystem:
    """
    Main context management system orchestrator.

    Coordinates all context management components for complete
    vision document workflow with context prioritization tracking.
    """

    def __init__(self, db_manager, target_chunk_size: int = VISION_DELIVERY_BUDGET):
        """
        Initialize ContextManagementSystem.

        Args:
            db_manager: Database manager instance
            target_chunk_size: Target tokens per chunk
        """
        self.db_manager = db_manager
        self.chunker = VisionDocumentChunker(target_chunk_size=target_chunk_size)
        self.indexer = ContextIndexer(db_manager)
        self.loader = DynamicContextLoader(db_manager)
        self.summarizer = ContextSummarizer(db_manager)

        logger.info(f"ContextManagementSystem initialized with chunk size {target_chunk_size}")

    def process_vision_document(self, tenant_key: str, product_id: str, content: str) -> dict[str, Any]:
        """
        Complete workflow: chunk and index vision document.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID
            content: Vision document content

        Returns:
            Processing results dict
        """
        # Chunk the document
        chunks = self.chunker.chunk_document(content, product_id=product_id)

        if not chunks:
            logger.warning(f"No chunks created for product {product_id}")
            from giljo_mcp.exceptions import ContextError

            raise ContextError("No content to chunk")

        # Store chunks in database
        chunk_ids = self.indexer.store_chunks(tenant_key, product_id, chunks)

        total_tokens = sum(c["tokens"] for c in chunks)

        logger.info(f"Processed vision document for product {product_id}: {len(chunks)} chunks, {total_tokens} tokens")

        return {
            "chunks_created": len(chunks),
            "chunk_ids": chunk_ids,
            "total_tokens": total_tokens,
            "chunks": chunks,
        }

    def load_context_for_agent(
        self, tenant_key: str, product_id: str, query: str, role: str | None = None, max_tokens: int = 10000
    ) -> dict[str, Any]:
        """
        Load relevant context chunks for an agent.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID
            query: Search query
            role: Optional agent role
            max_tokens: Maximum tokens to load

        Returns:
            Loaded context dict
        """
        chunks = self.loader.load_relevant_chunks(
            tenant_key=tenant_key, product_id=product_id, query=query, role=role, max_tokens=max_tokens
        )

        total_tokens = sum(c["tokens"] for c in chunks)
        avg_relevance = sum(c["relevance_score"] for c in chunks) / len(chunks) if chunks else 0

        return {
            "chunks": chunks,
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "average_relevance": avg_relevance,
        }

    def get_token_reduction_stats(self, tenant_key: str, product_id: str | None = None) -> dict[str, Any]:
        """
        Get context prioritization statistics.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Optional product ID filter

        Returns:
            Statistics dict
        """
        return self.summarizer.get_reduction_stats(tenant_key=tenant_key, product_id=product_id)

    def get_all_chunks(self, tenant_key: str, product_id: str) -> list[Any]:
        """
        Get all chunks for a product.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID

        Returns:
            List of MCPContextIndex instances
        """
        return self.indexer.get_chunks_by_product(tenant_key, product_id)
