"""MCP tool for fetching vision document chunks with depth control.

Reuses logic from:
- mission_planner._get_relevant_vision_chunks() (lines 695-832)
- tools/chunking.py EnhancedChunker class

Token Budget by Depth (Handover 0246b):
- "none": 0 tokens (empty response)
- "light": ~10K tokens (first 2 chunks)
- "medium": ~17.5K tokens (first 4 chunks)
- "full": ~30K tokens (all chunks)

Backward Compatibility:
- "moderate" maps to "medium"
- "heavy" maps to "medium"
"""

from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.context import MCPContextIndex


logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    import json

    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


def get_max_tokens(chunking: str) -> int:
    """Map chunking depth to max token budget.

    Handles both new-style depth values and summary-based values:
    - Standard style: light, medium, full
    - Summary style (with Sumy): summary_light, summary_medium, full
    - Backward compat: moderate -> medium, heavy -> medium
    """
    # Backward compatibility mapping (Handover 0246b)
    if chunking in {"moderate", "heavy"}:
        chunking = "medium"

    mapping = {
        # Standard style - token-based
        "none": 0,
        "light": 10000,
        "medium": 17500,
        "full": 24000,  # Safe margin below 25K Claude Code limit
        # Summary style - summary + chunks
        "summary_light": 2500,  # ~500 tokens (summary) + ~2000 tokens (light chunks)
        "summary_medium": 5000,  # ~500 tokens (summary) + ~4500 tokens (medium chunks)
    }
    return mapping.get(chunking, 17500)


def get_max_chunks(chunking: str) -> int:
    """Map chunking depth to max chunk count.

    For summary_* depths, limits chunks to append after summary.
    For full, returns all chunks.
    """
    # Backward compatibility mapping (Handover 0246b)
    if chunking in {"moderate", "heavy"}:
        chunking = "medium"

    mapping = {
        # Standard style - token-based
        "none": 0,
        "light": 2,
        "medium": 4,
        "full": 100,  # Effectively unlimited
        # Summary style - summary + chunks (chunk counts for the chunks portion only)
        "summary_light": 1,  # Just 1 chunk after summary (light)
        "summary_medium": 2,  # 2 chunks after summary (medium)
    }
    return mapping.get(chunking, 4)


async def _get_summary_response(
    product: Product,
    depth: str,
    product_id: str,
    tenant_key: str,  # noqa: ARG001
) -> dict[str, Any]:
    """
    Helper function to retrieve CONSOLIDATED summary response (Handover 0377).

    Args:
        product: Product instance with consolidated vision columns
        depth: Depth level ("light" or "medium")
        product_id: Product UUID
        tenant_key: Tenant key

    Returns:
        Dict with consolidated summary content (no pagination)
    """
    # Handover 0377: Use Product's consolidated columns
    if depth == "light":
        summary_text = product.consolidated_vision_light
        token_count = product.consolidated_vision_light_tokens
        compression = "33%"
    elif depth == "medium":
        summary_text = product.consolidated_vision_medium
        token_count = product.consolidated_vision_medium_tokens
        compression = "66%"
    else:
        logger.warning(
            "invalid_depth_for_summary",
            product_id=product_id,
            depth=depth,
            operation="get_vision_document",
        )
        return {
            "source": "vision_documents",
            "depth": depth,
            "data": {"error": "invalid_depth", "message": f"Invalid depth '{depth}' for summary response"},
            "pagination": None,
        }

    if not summary_text:
        logger.warning(
            "consolidated_summary_not_available",
            product_id=product_id,
            depth=depth,
            consolidated_at=product.consolidated_at,
            operation="get_vision_document",
        )
        return {
            "source": "vision_documents",
            "depth": depth,
            "data": {
                "error": "summary_not_available",
                "message": f"No consolidated {depth} summary available. Run consolidation first.",
            },
            "pagination": None,
        }

    logger.info(
        "consolidated_vision_summary_fetched",
        product_id=product_id,
        depth=depth,
        tokens=token_count,
        compression=compression,
        consolidated_at=str(product.consolidated_at) if product.consolidated_at else None,
        consolidated_hash=product.consolidated_vision_hash[:8] if product.consolidated_vision_hash else None,
    )

    return {
        "source": "vision_documents",
        "depth": depth,
        "data": {
            "summary": summary_text,
            "tokens": token_count,
            "compression": compression,
            "consolidated_at": str(product.consolidated_at) if product.consolidated_at else None,
            "source_hash": product.consolidated_vision_hash,
        },
        "pagination": None,
    }


async def get_vision_document(
    product_id: str,
    tenant_key: str,
    chunking: str = "medium",
    offset: int = 0,
    limit: Optional[int] = None,
    db_manager: Optional[DatabaseManager] = None,
) -> dict[str, Any]:
    """
    Fetch vision document with depth-based source selection (Handover 0352).

    Depth-Based Source Selection:
    - "light": Returns VisionDocument.summary_light (single response, ~33% compression)
    - "medium": Returns VisionDocument.summary_medium (single response, ~66% compression)
    - "full": Returns MCPContextIndex chunks (paginated, ≤25K tokens per call)
    - "none": Returns empty response

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        chunking: Depth level ("none", "light", "medium", "full")
        offset: Number of chunks to skip (for pagination, full depth only)
        limit: Max chunks to return (for pagination, full depth only)
        db_manager: Database manager instance

    Returns:
        For light/medium depth:
        {
            "source": "vision_documents",
            "depth": "light",
            "data": {
                "summary": "Light summary content",
                "tokens": 5000,
                "compression": "33%"
            },
            "pagination": None
        }

        For full depth:
        {
            "source": "vision_documents",
            "depth": "full",
            "data": [
                {"content": "...", "chunk_order": 1, "tokens": 1200},
                {"content": "...", "chunk_order": 2, "tokens": 950}
            ],
            "pagination": {
                "total_chunks": 12,
                "offset": 0,
                "limit": 3,
                "has_more": true,
                "next_offset": 3
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Example:
        # Light summary (no pagination)
        result = await get_vision_document(
            product_id="uuid",
            tenant_key="tenant_abc",
            chunking="light"
        )

        # Full chunks with pagination
        result = await get_vision_document(
            product_id="uuid",
            tenant_key="tenant_abc",
            chunking="full",
            offset=0,
            limit=3
        )
    """
    logger.info(
        "fetching_vision_document_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=chunking,
        offset=offset,
        limit=limit,
    )

    # Handle "none" depth early
    if chunking == "none":
        return {
            "source": "vision_documents",
            "depth": chunking,
            "data": [],
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "total_chunks": 0,
                "offset": offset,
                "limit": 0,
                "returned_chunks": 0,
                "has_more": False,
                "next_offset": None,
            },
        }

    if db_manager is None:
        logger.error("db_manager is required", operation="get_vision_document")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch product to verify existence and get vision documents
        stmt = (
            select(Product)
            .options(selectinload(Product.vision_documents))
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_vision_document"
            )
            return {
                "source": "vision_documents",
                "depth": chunking,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_chunks": 0,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_chunks": 0,
                    "has_more": False,
                    "next_offset": None,
                    "error": "product_not_found",
                },
            }

        # Check if product has vision documents
        if not product.vision_documents:
            logger.debug("no_vision_documents", product_id=product_id, operation="get_vision_document")
            return {
                "source": "vision_documents",
                "depth": chunking,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_chunks": 0,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_chunks": 0,
                    "has_more": False,
                    "next_offset": None,
                },
            }

        # Get active vision documents
        active_docs = [doc for doc in product.vision_documents if doc.is_active]
        if not active_docs:
            logger.debug("no_active_vision_documents", product_id=product_id, operation="get_vision_document")
            return {
                "source": "vision_documents",
                "depth": chunking,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_chunks": 0,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_chunks": 0,
                    "has_more": False,
                    "next_offset": None,
                },
            }

        # Handover 0377: Use Product's consolidated vision columns for light/medium depths
        if chunking == "light":
            return await _get_summary_response(
                product=product,
                depth="light",
                product_id=product_id,
                tenant_key=tenant_key,
            )

        if chunking == "medium":
            return await _get_summary_response(
                product=product,
                depth="medium",
                product_id=product_id,
                tenant_key=tenant_key,
            )

        # For "full" depth, use chunk-based pagination (existing logic below)

        # Get active chunked vision documents (reuse pattern from mission_planner)
        chunked_docs = [
            doc for doc in product.vision_documents if doc.is_active and doc.chunked and doc.chunk_count > 0
        ]

        if not chunked_docs:
            logger.debug(
                "no_chunked_documents",
                product_id=product_id,
                total_docs=len(product.vision_documents),
                operation="get_vision_document",
            )
            return {
                "source": "vision_documents",
                "depth": chunking,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_chunks": 0,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_chunks": 0,
                    "has_more": False,
                    "next_offset": None,
                },
            }

        # Get vision_document_ids for query
        vision_doc_ids = [doc.id for doc in chunked_docs]

        # Query chunks from mcp_context_index (reuse pattern from mission_planner)
        chunk_stmt = (
            select(MCPContextIndex)
            .where(MCPContextIndex.tenant_key == tenant_key, MCPContextIndex.vision_document_id.in_(vision_doc_ids))
            .order_by(MCPContextIndex.chunk_order)
        )

        chunk_result = await session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()

        if not all_chunks:
            logger.warning(
                "chunks_marked_but_not_found",
                product_id=product_id,
                vision_doc_ids=[str(vid) for vid in vision_doc_ids],
                operation="get_vision_document",
            )
            return {
                "source": "vision_documents",
                "depth": chunking,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_chunks": 0,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_chunks": 0,
                    "has_more": False,
                    "next_offset": None,
                    "error": "chunks_not_found",
                },
            }

        # Apply depth filtering with pagination (full depth only)
        max_chunks = get_max_chunks(chunking) if limit is None else limit
        max_tokens = get_max_tokens(chunking)
        total_chunks = len(all_chunks)

        # Apply pagination: skip offset chunks, take up to limit chunks
        paginated_chunks = all_chunks[offset : offset + max_chunks] if offset < total_chunks else []

        selected_chunks = []
        total_tokens = 0

        # Select chunks within budget
        for chunk in paginated_chunks:
            chunk_tokens = estimate_tokens(chunk.content)

            if total_tokens + chunk_tokens > max_tokens:
                logger.debug(
                    "token_budget_reached",
                    total_tokens=total_tokens,
                    max_tokens=max_tokens,
                    chunks_selected=len(selected_chunks),
                    operation="get_vision_document",
                )
                break

            selected_chunks.append({"content": chunk.content, "chunk_order": chunk.chunk_order, "tokens": chunk_tokens})
            total_tokens += chunk_tokens

        # Calculate pagination metadata
        has_more = (offset + len(selected_chunks)) < total_chunks
        next_offset = offset + len(selected_chunks) if has_more else None

        logger.info(
            "vision_chunks_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            depth=chunking,
            offset=offset,
            limit=max_chunks,
            returned_chunks=len(selected_chunks),
            total_chunks=total_chunks,
            has_more=has_more,
            total_tokens=total_tokens,
            max_tokens=max_tokens,
        )

        # Build response data (Handover 0352: consistent format)
        return {
            "source": "vision_documents",
            "depth": chunking,
            "data": selected_chunks,
            "pagination": {
                "total_chunks": total_chunks,
                "offset": offset,
                "limit": max_chunks,
                "has_more": has_more,
                "next_offset": next_offset,
            },
        }
