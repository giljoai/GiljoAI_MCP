"""Service for consolidating vision documents into unified summaries (Handover 0377).

Updated Handover 0730b: Migrated from dict wrappers to exception-based error handling.
Updated Handover 0731: Migrated from dict returns to typed ConsolidationResult.
"""

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.schemas.service_responses import ConsolidationResult, SummaryLevel


logger = logging.getLogger(__name__)


class ConsolidatedVisionService:
    """Generate consolidated summaries from multiple vision documents."""

    def __init__(self):
        from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

        self.summarizer = VisionDocumentSummarizer()

    async def consolidate_vision_documents(
        self, product_id: str, session: AsyncSession, tenant_key: str, force: bool = False
    ) -> ConsolidationResult:
        """
        Consolidate all active vision documents into light/medium summaries.

        Args:
            product_id: Product UUID
            session: Database session
            tenant_key: Tenant isolation key
            force: Force regeneration even if no changes detected

        Returns:
            ConsolidationResult with light/medium summaries, hash, and source_docs.

        Raises:
            ResourceNotFoundError: Product not found or tenant mismatch
            ValidationError: No changes detected (unless force=True)
        """
        # Fetch product with vision documents (defense-in-depth: tenant_key in WHERE clause)
        result = await session.execute(
            select(Product)
            .options(selectinload(Product.vision_documents))
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
        )
        product = result.scalar_one_or_none()

        if not product:
            logger.warning("consolidate_vision_documents.product_not_found: product_id=%s", product_id)
            raise ResourceNotFoundError(
                message="Product not found", error_code="PRODUCT_NOT_FOUND", context={"product_id": product_id}
            )

        # Build aggregate from all active vision documents
        aggregate_text, source_doc_ids, aggregate_hash = self._build_aggregate(product)

        # Check if content has changed (unless force=True)
        if not force and product.consolidated_vision_hash == aggregate_hash:
            logger.info("consolidate_vision_documents.no_changes: product_id=%s hash=%s", product_id, aggregate_hash)
            raise ValidationError(
                message="No changes detected in vision documents",
                error_code="NO_CHANGES",
                context={"product_id": product_id, "hash": aggregate_hash},
            )

        # Generate summaries
        logger.info(
            "consolidate_vision_documents.generating_summaries: product_id=%s aggregate_tokens=%d source_docs=%d",
            product_id,
            self.summarizer.estimate_tokens(aggregate_text),
            len(source_doc_ids),
        )

        summary_result = self.summarizer.summarize_multi_level(aggregate_text)

        # Update product fields (summary_result is typed SummarizeMultiLevelResult)
        product.consolidated_vision_light = summary_result.light.summary
        product.consolidated_vision_light_tokens = summary_result.light.tokens
        product.consolidated_vision_medium = summary_result.medium.summary
        product.consolidated_vision_medium_tokens = summary_result.medium.tokens
        product.consolidated_vision_hash = aggregate_hash
        product.consolidated_at = datetime.now(timezone.utc)

        # Commit changes
        await session.commit()

        logger.info(
            "consolidate_vision_documents.success: product_id=%s light_tokens=%d medium_tokens=%d",
            product_id,
            summary_result.light.tokens,
            summary_result.medium.tokens,
        )

        # Return typed ConsolidationResult (Handover 0731)
        return ConsolidationResult(
            light=SummaryLevel(
                summary=summary_result.light.summary,
                tokens=summary_result.light.tokens,
            ),
            medium=SummaryLevel(
                summary=summary_result.medium.summary,
                tokens=summary_result.medium.tokens,
            ),
            hash=aggregate_hash,
            source_docs=source_doc_ids,
        )

    def _build_aggregate(self, product: Product) -> tuple[str, list[str], str]:
        """
        Aggregate active vision documents with headers.

        Returns:
            (aggregate_text, source_doc_ids, aggregate_hash)
        """
        # Filter active documents
        active_docs = [doc for doc in product.vision_documents if doc.is_active]

        # Sort by display_order
        sorted_docs = sorted(active_docs, key=lambda d: d.display_order)

        # Build aggregate with headers
        parts = []
        source_doc_ids = []

        for doc in sorted_docs:
            # Add header and content
            parts.append(f"# {doc.document_name}\n\n{doc.vision_document}")
            source_doc_ids.append(doc.id if hasattr(doc, "id") else doc.document_name)

        aggregate_text = "\n\n".join(parts)

        # Calculate SHA-256 hash
        aggregate_hash = hashlib.sha256(aggregate_text.encode("utf-8")).hexdigest()

        return aggregate_text, source_doc_ids, aggregate_hash
