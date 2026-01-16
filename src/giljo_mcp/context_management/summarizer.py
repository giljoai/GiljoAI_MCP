"""
Context Summarizer - Context prioritization tracking and optimization.

Handover 0018: Production-grade summarization with token metrics.

Features:
- Token counting for original and condensed content
- Reduction percentage calculation
- Database storage via ContextRepository
- Multi-tenant isolation
"""

import logging
from typing import Dict, Optional

import tiktoken

from src.giljo_mcp.repositories.context_repository import ContextRepository


logger = logging.getLogger(__name__)


class ContextSummarizer:
    """
    Context summarizer with token tracking.

    Tracks context prioritization when condensing full context into missions.
    Simple implementation for Phase 1 - can be enhanced with LLM later.
    """

    def __init__(self, db_manager):
        """
        Initialize ContextSummarizer.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.context_repo = ContextRepository(db_manager)
        self.encoding = tiktoken.get_encoding("cl100k_base")

        logger.info("ContextSummarizer initialized")

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def create_summary(
        self, tenant_key: str, product_id: str, full_content: str, condensed_mission: str
    ) -> Dict[str, any]:
        """
        Create summary and track context prioritization.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Product ID
            full_content: Original full context
            condensed_mission: Condensed mission text

        Returns:
            Summary statistics dict
        """
        full_tokens = self.count_tokens(full_content)
        condensed_tokens = self.count_tokens(condensed_mission)

        with self.db_manager.get_session() as session:
            summary = self.context_repo.create_summary(
                session=session,
                tenant_key=tenant_key,
                product_id=product_id,
                full_content=full_content,
                condensed_mission=condensed_mission,
                full_tokens=full_tokens,
                condensed_tokens=condensed_tokens,
            )

            session.commit()

        reduction_percent = summary.reduction_percent
        tokens_saved = full_tokens - condensed_tokens

        logger.info(
            f"Created summary for product {product_id}: {reduction_percent:.1f}% reduction, {tokens_saved} tokens saved"
        )

        return {
            "context_id": summary.context_id,
            "full_tokens": full_tokens,
            "condensed_tokens": condensed_tokens,
            "reduction_percent": reduction_percent,
            "tokens_saved": tokens_saved,
        }

    def get_reduction_stats(self, tenant_key: str, product_id: Optional[str] = None) -> Dict[str, any]:
        """
        Get context prioritization statistics.

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Optional product ID filter

        Returns:
            Statistics dict
        """
        with self.db_manager.get_session() as session:
            stats = self.context_repo.get_token_reduction_stats(
                session=session, tenant_key=tenant_key, product_id=product_id
            )

        return stats
