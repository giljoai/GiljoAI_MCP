"""
Dynamic Context Loader - Role-based chunk selection and loading.

Handover 0018: Production-grade context loading with relevance scoring.

Features:
- Role-based chunk filtering
- Relevance scoring
- Token budget management
- Multi-tenant isolation
"""

import logging
from typing import Dict, List, Optional

from src.giljo_mcp.context_management.indexer import ContextIndexer


logger = logging.getLogger(__name__)


# Agent role patterns for chunk selection
ROLE_PATTERNS = {
    "architect": ["architecture", "design", "structure", "pattern"],
    "implementer": ["implementation", "code", "function", "class"],
    "tester": ["testing", "test", "quality", "validation"],
    "analyzer": ["analysis", "requirements", "specification"],
    "orchestrator": ["mission", "vision", "goal", "objective"],
}


class DynamicContextLoader:
    """
    Dynamic context loader with role-based selection.

    Loads relevant chunks based on agent role and query.
    Manages token budget to stay within limits.
    """

    def __init__(self, db_manager):
        """
        Initialize DynamicContextLoader.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.indexer = ContextIndexer(db_manager)

        logger.info("DynamicContextLoader initialized")

    def calculate_relevance_score(self, chunk, query: str, role: Optional[str] = None) -> float:
        """
        Calculate relevance score for a chunk.

        Args:
            chunk: MCPContextIndex instance
            query: Search query
            role: Optional agent role

        Returns:
            Relevance score (0-1)
        """
        score = 0.0

        # Query match in keywords (40% weight)
        query_lower = query.lower()
        keywords_lower = [k.lower() for k in (chunk.keywords or [])]
        if any(query_lower in k or k in query_lower for k in keywords_lower):
            score += 0.4

        # Role pattern match (30% weight)
        if role and role.lower() in ROLE_PATTERNS:
            role_keywords = ROLE_PATTERNS[role.lower()]
            if any(rk in keywords_lower for rk in role_keywords):
                score += 0.3

        # Content match (30% weight)
        if query_lower in (chunk.content or "").lower():
            score += 0.3

        return min(score, 1.0)

    def load_relevant_chunks(
        self,
        tenant_key: str,
        product_id: str,
        query: str,
        role: Optional[str] = None,
        max_tokens: int = 10000,
        limit: int = 20,
    ) -> List[Dict[str, any]]:
        """
        Load relevant chunks with role-based filtering.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID
            query: Search query
            role: Optional agent role for filtering
            max_tokens: Maximum tokens to load
            limit: Maximum chunks to consider

        Returns:
            List of chunk dicts with relevance scores
        """
        # Search for chunks
        raw_chunks = self.indexer.search_chunks(tenant_key=tenant_key, product_id=product_id, query=query, limit=limit)

        # Score and sort chunks
        scored_chunks = []
        for chunk in raw_chunks:
            score = self.calculate_relevance_score(chunk, query, role)
            scored_chunks.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "tokens": chunk.token_count or 0,
                    "keywords": chunk.keywords,
                    "summary": chunk.summary,
                    "relevance_score": score,
                    "chunk_order": chunk.chunk_order,
                }
            )

        # Sort by relevance score (descending)
        scored_chunks.sort(key=lambda c: c["relevance_score"], reverse=True)

        # Select chunks within token budget
        selected_chunks = []
        total_tokens = 0

        for chunk in scored_chunks:
            chunk_tokens = chunk["tokens"]
            if total_tokens + chunk_tokens <= max_tokens:
                selected_chunks.append(chunk)
                total_tokens += chunk_tokens
            else:
                break

        logger.info(
            f"Loaded {len(selected_chunks)} chunks ({total_tokens} tokens) for query '{query}' with role '{role}'"
        )

        return selected_chunks
