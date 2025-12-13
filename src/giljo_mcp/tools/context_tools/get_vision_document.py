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

import structlog
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
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
    - Summary style (with Sumy): summary_light, summary_moderate, full
    - Backward compat: moderate -> medium, heavy -> medium
    """
    # Backward compatibility mapping (Handover 0246b)
    if chunking == "moderate":
        chunking = "medium"
    elif chunking == "heavy":
        chunking = "medium"

    mapping = {
        # Standard style - token-based
        "none": 0,
        "light": 10000,
        "medium": 17500,
        "full": 24000,   # Safe margin below 25K Claude Code limit
        # Summary style - summary + chunks
        "summary_light": 2500,    # ~500 tokens (summary) + ~2000 tokens (light chunks)
        "summary_moderate": 5000, # ~500 tokens (summary) + ~4500 tokens (moderate chunks)
    }
    return mapping.get(chunking, 17500)


def get_max_chunks(chunking: str) -> int:
    """Map chunking depth to max chunk count.

    For summary_* depths, limits chunks to append after summary.
    For full, returns all chunks.
    """
    # Backward compatibility mapping (Handover 0246b)
    if chunking == "moderate":
        chunking = "medium"
    elif chunking == "heavy":
        chunking = "medium"

    mapping = {
        # Standard style - token-based
        "none": 0,
        "light": 2,
        "medium": 4,
        "full": 100,   # Effectively unlimited
        # Summary style - summary + chunks (chunk counts for the chunks portion only)
        "summary_light": 1,  # Just 1 chunk after summary (light)
        "summary_moderate": 2,  # 2 chunks after summary (moderate)
    }
    return mapping.get(chunking, 4)


async def get_vision_document(
    product_id: str,
    tenant_key: str,
    chunking: str = "medium",
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch vision document chunks for given product with depth control and pagination.

    Reuses chunking logic from mission_planner._get_relevant_vision_chunks().
    Queries mcp_context_index for pre-chunked vision documents.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        chunking: Depth level ("none", "light", "medium", "full")
        offset: Number of chunks to skip (for pagination)
        limit: Max chunks to return (None = use chunking default)
        db_manager: Database manager instance

    Returns:
        Dict with vision chunks and metadata:
        {
            "source": "vision_documents",
            "depth": "moderate",
            "data": [
                {"content": "...", "chunk_order": 1, "tokens": 1200},
                {"content": "...", "chunk_order": 2, "tokens": 950}
            ],
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "total_chunks": 12,
                "offset": 0,
                "limit": 4,
                "returned_chunks": 4,
                "has_more": true,
                "next_offset": 4,
                "estimated_tokens": 5000
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Pagination Example:
        # Fetch first batch
        batch1 = await get_vision_document(chunking='heavy', offset=0, limit=4)
        # Fetch next batch if has_more=True
        batch2 = await get_vision_document(chunking='heavy', offset=4, limit=4)

    Example:
        result = await get_vision_document(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            chunking="light",
            offset=0,
            limit=2
        )
    """
    logger.info(
        "fetching_vision_document_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=chunking,
        offset=offset,
        limit=limit
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
                "estimated_tokens": 0
            }
        }

    if db_manager is None:
        logger.error("db_manager is required", operation="get_vision_document")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch product to verify existence and get vision documents
        stmt = select(Product).options(selectinload(Product.vision_documents)).where(
            Product.id == product_id,
            Product.tenant_key == tenant_key
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found",
                product_id=product_id,
                tenant_key=tenant_key,
                operation="get_vision_document"
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
                    "estimated_tokens": 0,
                    "error": "product_not_found"
                }
            }

        # Check if product has chunked vision documents
        if not product.vision_documents:
            logger.debug(
                "no_vision_documents",
                product_id=product_id,
                operation="get_vision_document"
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
                    "estimated_tokens": 0
                }
            }

        # Get active chunked vision documents (reuse pattern from mission_planner)
        chunked_docs = [
            doc for doc in product.vision_documents
            if doc.is_active and doc.chunked and doc.chunk_count > 0
        ]

        if not chunked_docs:
            logger.debug(
                "no_chunked_documents",
                product_id=product_id,
                total_docs=len(product.vision_documents),
                operation="get_vision_document"
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
                    "estimated_tokens": 0
                }
            }

        # Get vision_document_ids for query
        vision_doc_ids = [doc.id for doc in chunked_docs]

        # Query chunks from mcp_context_index (reuse pattern from mission_planner)
        chunk_stmt = select(MCPContextIndex).where(
            MCPContextIndex.tenant_key == tenant_key,
            MCPContextIndex.vision_document_id.in_(vision_doc_ids)
        ).order_by(MCPContextIndex.chunk_order)

        chunk_result = await session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()

        if not all_chunks:
            logger.warning(
                "chunks_marked_but_not_found",
                product_id=product_id,
                vision_doc_ids=[str(vid) for vid in vision_doc_ids],
                operation="get_vision_document"
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
                    "estimated_tokens": 0,
                    "error": "chunks_not_found"
                }
            }

        # Apply depth filtering with pagination
        max_chunks = get_max_chunks(chunking) if limit is None else limit
        max_tokens = get_max_tokens(chunking)
        total_chunks = len(all_chunks)

        # Apply pagination: skip offset chunks, take up to limit chunks
        paginated_chunks = all_chunks[offset:offset + max_chunks] if offset < total_chunks else []

        # Handle summary_* depths: include summary from first chunked document
        summary_text = None
        if chunking.startswith('summary_'):
            # Get summary from first active chunked vision document
            for doc in chunked_docs:
                if doc.summary_text:
                    summary_text = doc.summary_text.strip()
                    break

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
                    operation="get_vision_document"
                )
                break

            selected_chunks.append({
                "content": chunk.content,
                "chunk_order": chunk.chunk_order,
                "tokens": chunk_tokens
            })
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
            max_tokens=max_tokens
        )

        # Build response data
        response_data = {"source": "vision_documents", "depth": chunking}
        
        # Include summary if available (for summary_* depths)
        if summary_text:
            response_data["summary"] = summary_text
            
        response_data["data"] = selected_chunks
        response_data["metadata"] = {
            "product_id": product_id,
            "tenant_key": tenant_key,
            "total_chunks": total_chunks,
            "offset": offset,
            "limit": max_chunks,
            "returned_chunks": len(selected_chunks),
            "has_more": has_more,
            "next_offset": next_offset,
            "estimated_tokens": total_tokens,
            "has_summary": bool(summary_text)
        }
        
        return response_data
