"""Service for consolidating vision documents into unified summaries (Handover 0377).

Updated Handover 0730b: Migrated from dict wrappers to exception-based error handling.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer


logger = logging.getLogger(__name__)


class ConsolidatedVisionService:
    """Generate consolidated summaries from multiple vision documents."""

    def __init__(self):
        self.summarizer = VisionDocumentSummarizer()

    async def consolidate_vision_documents(
        self, product_id: str, session: AsyncSession, tenant_key: str, force: bool = False
    ) -> dict[str, Any]:
        """
        Consolidate all active vision documents into light/medium summaries.

        Args:
            product_id: Product UUID
            session: Database session
            tenant_key: Tenant isolation key
            force: Force regeneration even if no changes detected

        Returns:
            {
                "light": {"summary": "...", "tokens": int},
                "medium": {"summary": "...", "tokens": int},
                "hash": "...",
                "source_docs": ["doc_id1", "doc_id2", ...]
            }

        Raises:
            ResourceNotFoundError: Product not found or tenant mismatch
            ValidationError: No changes detected (unless force=True)
        """
        # Fetch product with vision documents (eagerly load relationship to avoid lazy loading issues)
        result = await session.execute(
            select(Product).options(selectinload(Product.vision_documents)).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            logger.warning("consolidate_vision_documents.product_not_found", product_id=product_id)
            raise ResourceNotFoundError(
                message="Product not found", error_code="PRODUCT_NOT_FOUND", context={"product_id": product_id}
            )

        # Multi-tenant isolation check
        if product.tenant_key != tenant_key:
            logger.warning(
                "consolidate_vision_documents.tenant_mismatch",
                product_id=product_id,
                expected_tenant=tenant_key,
                actual_tenant=product.tenant_key,
            )
            # Don't leak tenant info - raise same error as not found
            raise ResourceNotFoundError(
                message="Product not found", error_code="PRODUCT_NOT_FOUND", context={"product_id": product_id}
            )

        # Build aggregate from all active vision documents
        aggregate_text, source_doc_ids, aggregate_hash = self._build_aggregate(product)

        # Check if content has changed (unless force=True)
        if not force and product.consolidated_vision_hash == aggregate_hash:
            logger.info("consolidate_vision_documents.no_changes", product_id=product_id, hash=aggregate_hash)
            raise ValidationError(
                message="No changes detected in vision documents",
                error_code="NO_CHANGES",
                context={"product_id": product_id, "hash": aggregate_hash},
            )

        # Generate summaries
        logger.info(
            "consolidate_vision_documents.generating_summaries",
            product_id=product_id,
            aggregate_tokens=self.summarizer.estimate_tokens(aggregate_text),
            source_docs=len(source_doc_ids),
        )

        summary_result = self.summarizer.summarize_multi_level(aggregate_text)

        # Update product fields
        product.consolidated_vision_light = summary_result["light"]["summary"]
        product.consolidated_vision_light_tokens = summary_result["light"]["tokens"]
        product.consolidated_vision_medium = summary_result["medium"]["summary"]
        product.consolidated_vision_medium_tokens = summary_result["medium"]["tokens"]
        product.consolidated_vision_hash = aggregate_hash
        product.consolidated_at = datetime.now(timezone.utc)

        # Commit changes
        await session.commit()

        logger.info(
            "consolidate_vision_documents.success",
            product_id=product_id,
            light_tokens=summary_result["light"]["tokens"],
            medium_tokens=summary_result["medium"]["tokens"],
            processing_time_ms=summary_result["processing_time_ms"],
        )

        # Return ConsolidationResult (exception-based - no "success" wrapper)
        return {
            "light": {"summary": summary_result["light"]["summary"], "tokens": summary_result["light"]["tokens"]},
            "medium": {"summary": summary_result["medium"]["summary"], "tokens": summary_result["medium"]["tokens"]},
            "hash": aggregate_hash,
            "source_docs": source_doc_ids,
        }

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
