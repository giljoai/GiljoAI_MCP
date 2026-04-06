"""MCP tool for fetching vision document chunks with depth control.

Reuses logic from:
- mission_planner._get_relevant_vision_chunks() (lines 695-832)
- tools/chunking.py EnhancedChunker class

Token Budget by Depth (Handover 0246b, updated 0493):
- "none": 0 tokens (empty response)
- "light": consolidated summary, paginated at 24K tokens (VISION_DELIVERY_BUDGET)
- "medium": consolidated summary, paginated at 24K tokens (VISION_DELIVERY_BUDGET)
- "full": all chunks, paginated at 24K tokens (VISION_DELIVERY_BUDGET)

Backward Compatibility:
- "moderate" maps to "medium"
- "heavy" maps to "medium"
"""

from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.context import MCPContextIndex
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from src.giljo_mcp.tools.chunking import VISION_DELIVERY_BUDGET, EnhancedChunker


DEPTH_RATIO_MAP: dict[str, Decimal] = {
    "light": Decimal("0.33"),
    "medium": Decimal("0.66"),
}


logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    import json

    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


def get_max_tokens(chunking: str) -> int:
    """Max per-call token budget. Only called for 'full' depth (light/medium
    are routed to _get_summary_response() before reaching the chunk loop)."""
    if chunking == "none":
        return 0
    return VISION_DELIVERY_BUDGET


def get_max_chunks(chunking: str) -> int:
    """Max chunk count per call. Only called for 'full' depth."""
    if chunking == "none":
        return 0
    return 100


async def _build_aggregated_summary(
    product: Product,
    summaries: list,
) -> tuple[str, int]:
    """
    Build aggregated summary text from per-document summaries.

    Picks the best summary per document_id (first one, since results are
    ordered AI-first by the repository). For multiple documents, produces
    markdown headers with document names.

    Args:
        product: Product instance (used to look up document names)
        summaries: List of VisionDocumentSummary rows, ordered by
                   document_id then AI-preferred source

    Returns:
        Tuple of (aggregated_summary_text, total_tokens)
    """
    doc_name_map: dict[str, str] = {str(doc.id): doc.document_name for doc in (product.vision_documents or [])}

    best_per_doc: dict[str, tuple[str, int]] = {}
    for s in summaries:
        if s.document_id not in best_per_doc:
            best_per_doc[s.document_id] = (s.summary, s.tokens_summary)

    if len(best_per_doc) == 1:
        doc_id = next(iter(best_per_doc))
        text, tokens = best_per_doc[doc_id]
        return text, tokens

    parts: list[str] = []
    total_tokens = 0
    for doc_id, (text, tokens) in best_per_doc.items():
        doc_name = doc_name_map.get(doc_id, doc_id)
        parts.append(f"# {doc_name}\n{text}")
        total_tokens += tokens

    return "\n\n".join(parts), total_tokens


async def _get_summary_response(
    product: Product,
    depth: str,
    product_id: str,
    tenant_key: str,
    offset: int = 0,
    session: Optional[AsyncSession] = None,
    db_manager: Optional[DatabaseManager] = None,
) -> dict[str, Any]:
    """
    Retrieve summary response, preferring per-document summaries (Handover 0842b).

    Priority:
    1. Read from vision_document_summaries table (AI-preferred per document)
    2. Fall back to Product.consolidated_vision_* columns (Handover 0377)

    Handover 0493: Adds pagination when summary exceeds VISION_DELIVERY_BUDGET.
    If the summary fits within budget, returns as single response (no regression).

    Args:
        product: Product instance with consolidated vision columns
        depth: Depth level ("light" or "medium")
        product_id: Product UUID
        tenant_key: Tenant key
        offset: Character offset for pagination (0 = start)
        session: Async database session (for querying summaries table)
        db_manager: Database manager (used to create VisionDocumentRepository)

    Returns:
        Dict with summary content, paginated if needed
    """
    if depth not in DEPTH_RATIO_MAP:
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

    compression = "33%" if depth == "light" else "66%"
    ratio = DEPTH_RATIO_MAP[depth]

    # ---- Handover 0842b: Try per-document summaries table first ----
    summary_text: Optional[str] = None
    summary_tokens: Optional[int] = None

    if session is not None and db_manager is not None:
        repo = VisionDocumentRepository(db_manager)
        product_summaries = await repo.get_product_summaries(
            session=session,
            tenant_key=tenant_key,
            product_id=product_id,
            ratio=ratio,
        )
        if product_summaries:
            summary_text, summary_tokens = await _build_aggregated_summary(product, product_summaries)
            logger.info(
                "per_document_summaries_fetched",
                product_id=product_id,
                depth=depth,
                num_summaries=len(product_summaries),
                tokens=summary_tokens,
                compression=compression,
            )

    # ---- Fallback: Product consolidated columns (Handover 0377) ----
    if summary_text is None:
        if depth == "light":
            summary_text = product.consolidated_vision_light
            summary_tokens = product.consolidated_vision_light_tokens
        else:
            summary_text = product.consolidated_vision_medium
            summary_tokens = product.consolidated_vision_medium_tokens

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

    # Handover 0493: Check if summary exceeds delivery budget and paginate if needed
    token_count = summary_tokens or estimate_tokens(summary_text)

    if token_count <= VISION_DELIVERY_BUDGET:
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

    # Summary exceeds budget - chunk and paginate
    chunker = EnhancedChunker(max_tokens=VISION_DELIVERY_BUDGET)
    chunks = chunker.chunk_content(summary_text)
    total_chunks = len(chunks)

    if offset >= total_chunks:
        return {
            "source": "vision_documents",
            "depth": depth,
            "data": {"summary": "", "tokens": 0, "compression": compression},
            "pagination": {
                "total_chunks": total_chunks,
                "offset": offset,
                "limit": 1,
                "has_more": False,
                "next_offset": None,
            },
        }

    selected_chunk = chunks[offset]
    chunk_text = selected_chunk.get("content", "")
    chunk_tokens = estimate_tokens(chunk_text)
    has_more = (offset + 1) < total_chunks
    next_offset = offset + 1 if has_more else None

    logger.info(
        "consolidated_vision_summary_paginated",
        product_id=product_id,
        depth=depth,
        total_tokens=token_count,
        chunk_tokens=chunk_tokens,
        chunk_index=offset,
        total_chunks=total_chunks,
        has_more=has_more,
        compression=compression,
    )

    return {
        "source": "vision_documents",
        "depth": depth,
        "data": {
            "summary": chunk_text,
            "tokens": chunk_tokens,
            "compression": compression,
            "consolidated_at": str(product.consolidated_at) if product.consolidated_at else None,
            "source_hash": product.consolidated_vision_hash,
        },
        "pagination": {
            "total_chunks": total_chunks,
            "offset": offset,
            "limit": 1,
            "has_more": has_more,
            "next_offset": next_offset,
        },
    }


async def get_vision_document(
    product_id: str,
    tenant_key: str,
    chunking: str = "medium",
    offset: int = 0,
    limit: Optional[int] = None,
    db_manager: Optional[DatabaseManager] = None,
    _test_session: Optional[AsyncSession] = None,
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
        _test_session: Injected session for test isolation (internal use only)

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

    if db_manager is None and _test_session is None:
        logger.error("db_manager is required", operation="get_vision_document")
        raise ValueError("db_manager parameter is required")

    return await _get_vision_document_with_session(
        product_id=product_id,
        tenant_key=tenant_key,
        chunking=chunking,
        offset=offset,
        limit=limit,
        db_manager=db_manager,
        session=_test_session,
    )


async def _get_vision_document_with_session(
    product_id: str,
    tenant_key: str,
    chunking: str,
    offset: int,
    limit: Optional[int],
    db_manager: Optional[DatabaseManager],
    session: Optional[AsyncSession] = None,
) -> dict[str, Any]:
    """Inner implementation that operates on a given or new session."""
    if session is not None:
        return await _execute_vision_query(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            chunking=chunking,
            offset=offset,
            limit=limit,
            db_manager=db_manager,
        )

    async with db_manager.get_session_async() as new_session:
        return await _execute_vision_query(
            session=new_session,
            product_id=product_id,
            tenant_key=tenant_key,
            chunking=chunking,
            offset=offset,
            limit=limit,
            db_manager=db_manager,
        )


async def _fetch_active_vision_docs(
    session: AsyncSession,
    product_id: str,
    tenant_key: str,
    chunking: str,
    offset: int,
    limit: Optional[int],
    db_manager: Optional[DatabaseManager],
) -> tuple[Optional[list], Optional[dict[str, Any]]]:
    """Fetch product, validate vision documents, and dispatch light/medium to summary.

    Applies the guard-clause chain: product existence, presence of vision
    documents, and active-document filter. For light/medium depth, calls
    _get_summary_response directly and returns the result as the early-return
    value.

    Args:
        session: Active async database session.
        product_id: Product UUID (filtered by tenant_key for isolation).
        tenant_key: Tenant isolation key.
        chunking: Depth level — "light" and "medium" are handled here;
                  "full" is passed back to the caller.
        offset: Pagination offset forwarded to _get_summary_response.
        limit: Pagination limit stored in error metadata.
        db_manager: Database manager forwarded to _get_summary_response.

    Returns:
        (active_docs, None) when depth is "full" and active docs exist.
        (None, response_dict) for all early-return paths (errors, light/medium).
    """
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
        return None, {
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

    if not product.vision_documents:
        logger.debug("no_vision_documents", product_id=product_id, operation="get_vision_document")
        return None, {
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

    active_docs = [doc for doc in product.vision_documents if doc.is_active]
    if not active_docs:
        logger.debug("no_active_vision_documents", product_id=product_id, operation="get_vision_document")
        return None, {
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

    # Handover 0377/0493/0842b: Prefer per-document summaries, fall back to consolidated
    if chunking in ("light", "medium"):
        response = await _get_summary_response(
            product=product,
            depth=chunking,
            product_id=product_id,
            tenant_key=tenant_key,
            offset=offset,
            session=session,
            db_manager=db_manager,
        )
        return None, response

    return active_docs, None


def _select_chunks_by_token_budget(
    all_chunks: list,
    offset: int,
    max_chunks: int,
    max_tokens: int,
) -> list[dict[str, Any]]:
    """Select chunks from a paginated window that fit within the token budget.

    Iterates over all_chunks[offset : offset + max_chunks], accumulating
    chunks until adding the next one would exceed max_tokens.

    Handover 0493: Uses chunk.token_count (tiktoken) when available; falls
    back to estimate_tokens(chunk.content) for legacy rows.

    Args:
        all_chunks: Full ordered list of MCPContextIndex rows.
        offset: Number of leading chunks to skip.
        max_chunks: Maximum number of chunks to consider from the window.
        max_tokens: Hard token ceiling for the selected set.

    Returns:
        List of dicts with keys ``content``, ``chunk_order``, and ``tokens``.
    """
    total_chunks = len(all_chunks)
    paginated_chunks = all_chunks[offset : offset + max_chunks] if offset < total_chunks else []

    selected_chunks: list[dict[str, Any]] = []
    total_tokens = 0

    for chunk in paginated_chunks:
        chunk_tokens = chunk.token_count if chunk.token_count else estimate_tokens(chunk.content)

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

    return selected_chunks


async def _execute_vision_query(
    session: AsyncSession,
    product_id: str,
    tenant_key: str,
    chunking: str,
    offset: int,
    limit: Optional[int],
    db_manager: Optional[DatabaseManager],
) -> dict[str, Any]:
    """Execute the actual vision document query within a session context."""
    active_docs, early_response = await _fetch_active_vision_docs(
        session=session,
        product_id=product_id,
        tenant_key=tenant_key,
        chunking=chunking,
        offset=offset,
        limit=limit,
        db_manager=db_manager,
    )
    if early_response is not None:
        return early_response

    # For "full" depth, use chunk-based pagination (existing logic below)

    # Get active chunked vision documents (reuse pattern from mission_planner)
    chunked_docs = [doc for doc in active_docs if doc.chunked and doc.chunk_count > 0]

    if not chunked_docs:
        logger.debug(
            "no_chunked_documents",
            product_id=product_id,
            total_docs=len(active_docs),
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

    # Query chunks from mcp_context_index (reuse pattern from mission_planner)
    vision_doc_ids = [doc.id for doc in chunked_docs]
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

    max_chunks = get_max_chunks(chunking) if limit is None else limit
    max_tokens = get_max_tokens(chunking)
    total_chunks = len(all_chunks)

    selected_chunks = _select_chunks_by_token_budget(
        all_chunks=all_chunks,
        offset=offset,
        max_chunks=max_chunks,
        max_tokens=max_tokens,
    )

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
        total_tokens=sum(c["tokens"] for c in selected_chunks),
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
