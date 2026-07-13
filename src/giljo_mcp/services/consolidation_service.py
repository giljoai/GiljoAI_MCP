# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Service for consolidating vision documents.

Performs aggregate-text + content-hash bookkeeping ONLY. The consolidated
``light`` / ``medium`` summary text is written by the AI agent through the
``update_product_context`` MCP tool, NOT here.

Contract:
- ``consolidate_vision_documents`` is async.
- Raises ``ResourceNotFoundError`` on missing product.
- Raises ``ValidationError(NO_CHANGES)`` when the aggregate hash has not
  changed and ``force=False`` -- callers use this signal to skip the
  auto-consolidation path after no-op uploads.
- ``consolidated_vision_hash`` and ``consolidated_at`` are updated when
  the hash differs; summary text columns are left untouched (the MCP tool
  owns those writes).

The returned ``ConsolidationResult.light`` / ``.medium`` reflect the
CURRENT product columns (whatever the agent last wrote), not freshly
generated summaries.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.products import Product
from giljo_mcp.repositories.project_repository import ProjectRepository
from giljo_mcp.schemas.service_responses import ConsolidationResult, SummaryLevel
from giljo_mcp.services.vision_hash import build_vision_aggregate
from giljo_mcp.utils.log_sanitizer import sanitize


logger = logging.getLogger(__name__)


class ConsolidatedVisionService:
    """Track the consolidated-vision aggregate hash and timestamp."""

    def __init__(self):
        self._repo = ProjectRepository()

    async def consolidate_vision_documents(
        self, product_id: str, session: AsyncSession, tenant_key: str, force: bool = False
    ) -> ConsolidationResult:
        """
        Refresh the consolidated-vision aggregate hash + timestamp.

        Args:
            product_id: Product UUID
            session: Database session
            tenant_key: Tenant isolation key
            force: Force update even if no aggregate-text changes detected

        Returns:
            ConsolidationResult with whatever summary text is currently on the
            product (agent-written via update_product_context) plus the fresh
            hash and the list of source-doc ids that contributed to the
            aggregate.

        Raises:
            ResourceNotFoundError: Product not found or tenant mismatch
            ValidationError: No aggregate-text changes detected (unless force=True)
        """
        with tenant_session_context(session, tenant_key):
            product = await self._repo.get_product_with_vision_docs(session, tenant_key, product_id)

        if not product:
            logger.warning("consolidate_vision_documents.product_not_found: product_id=%s", sanitize(product_id))
            raise ResourceNotFoundError(
                message="Product not found", error_code="PRODUCT_NOT_FOUND", context={"product_id": product_id}
            )

        aggregate_text, source_doc_ids, aggregate_hash = self._build_aggregate(product)

        if not force and product.consolidated_vision_hash == aggregate_hash:
            logger.info(
                "consolidate_vision_documents.no_changes: product_id=%s hash=%s", sanitize(product_id), aggregate_hash
            )
            raise ValidationError(
                message="No changes detected in vision documents",
                error_code="NO_CHANGES",
                context={"product_id": product_id, "hash": aggregate_hash},
            )

        product.consolidated_vision_hash = aggregate_hash
        product.consolidated_at = datetime.now(UTC)
        with tenant_session_context(session, tenant_key):
            await session.commit()

        logger.info(
            "consolidate_vision_documents.hash_updated: product_id=%s source_docs=%d aggregate_chars=%d",
            sanitize(product_id),
            len(source_doc_ids),
            len(aggregate_text),
        )

        return ConsolidationResult(
            light=SummaryLevel(
                summary=product.consolidated_vision_light or "",
                tokens=product.consolidated_vision_light_tokens or 0,
            ),
            medium=SummaryLevel(
                summary=product.consolidated_vision_medium or "",
                tokens=product.consolidated_vision_medium_tokens or 0,
            ),
            hash=aggregate_hash,
            source_docs=source_doc_ids,
        )

    def _build_aggregate(self, product: Product) -> tuple[str, list[str], str]:
        """Aggregate active vision documents with headers.

        Delegates to :func:`giljo_mcp.services.vision_hash.build_vision_aggregate`
        so the derived ``vision_inputs_hash`` and the persisted
        ``consolidated_vision_hash`` are computed by the same algorithm
        (BE-5122 review fix).
        """
        return build_vision_aggregate(product.vision_documents)
