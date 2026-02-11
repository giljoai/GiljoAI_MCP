"""
Context and vision management API endpoints

Handover 0018: Context Management System API
Provides endpoints for vision document chunking, indexing, and dynamic context loading.

Handover 0347e: 4-level vision depth validation
Validates vision_documents depth values (optional, light, medium, full).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import get_tenant_key


router = APIRouter()

# Handover 0347e: Valid vision depth values for 4-level system
VALID_VISION_DEPTH_VALUES = ["optional", "light", "medium", "full"]


class ContextIndexResponse(BaseModel):
    product_id: str
    index: dict[str, Any]
    document_count: int
    total_sections: int


class VisionResponse(BaseModel):
    part: int
    total_parts: int
    content: str
    tokens: int


class ChunkVisionRequest(BaseModel):
    force_rechunk: bool = Field(default=False, description="Force rechunking even if already chunked")


class ChunkVisionResponse(BaseModel):
    success: bool
    product_id: str
    chunks_created: int
    total_tokens: int
    original_size: int
    reduction_percentage: float | None = None
    message: str | None = None


class ContextChunk(BaseModel):
    chunk_id: str
    content: str
    tokens: int
    chunk_number: int
    relevance_score: float | None = None


class SearchContextResponse(BaseModel):
    query: str
    chunks: list[ContextChunk]
    total_chunks: int
    total_tokens: int


class LoadContextRequest(BaseModel):
    agent_display_name: str = Field(..., description="Human-readable display name for UI")
    mission: str = Field(..., description="Mission or query for context selection")
    product_id: str = Field(..., description="Product ID")
    max_tokens: int = Field(10000, description="Maximum tokens to load")


class LoadContextResponse(BaseModel):
    agent_display_name: str
    chunks: list[ContextChunk]
    total_chunks: int
    total_tokens: int
    average_relevance: float
    reduction_percentage: float | None = None


class TokenStatsResponse(BaseModel):
    product_id: str
    original_tokens: int
    condensed_tokens: int
    reduction_percentage: float
    chunks_count: int


class HealthCheckResponse(BaseModel):
    status: str
    chunk_count: int
    search_performance_ms: float | None = None
    message: str | None = None


@router.get("/index", response_model=ContextIndexResponse)
async def get_context_index(product_id: str | None = Query(None, description="Product ID")):
    """Get the context index for intelligent querying"""
    from src.giljo_mcp.tools.context import get_context_index

    # Tool raises exceptions on error
    index = await get_context_index(product_id=product_id)

    return ContextIndexResponse(
        product_id=product_id or "default",
        index=index,
        document_count=len(index.get("documents", [])),
        total_sections=sum(len(doc.get("sections", [])) for doc in index.get("documents", [])),
    )


@router.get("/vision", response_model=VisionResponse)
async def get_vision(
    part: int = Query(1, description="Part number to retrieve"),
    max_tokens: int = Query(20000, description="Maximum tokens per part"),
):
    """Get the vision document (chunked if large)"""
    from src.giljo_mcp.tools.context import get_vision

    # Tool raises exceptions on error
    result = await get_vision(part=part, max_tokens=max_tokens)

    return VisionResponse(
        part=part,
        total_parts=result.get("total_parts", 1),
        content=result.get("content", ""),
        tokens=result.get("tokens", 0),
    )


@router.get("/vision/index", response_model=dict[str, Any])
async def get_vision_index():
    """Get the vision document index"""
    from src.giljo_mcp.tools.context import get_vision_index

    # Tool raises exceptions on error
    return await get_vision_index()


@router.get("/settings", response_model=dict[str, Any])
async def get_product_settings(product_id: str | None = Query(None, description="Product ID")):
    """Get all product settings for analysis"""
    from src.giljo_mcp.tools.context import get_product_settings

    # Tool raises exceptions on error
    return await get_product_settings(product_id=product_id)


@router.post("/products/{product_id}/chunk-vision", response_model=ChunkVisionResponse)
async def chunk_vision_document(
    product_id: str,
    request: ChunkVisionRequest,
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Chunk and index a product's vision document.

    This endpoint processes the vision document stored in the Product model,
    chunks it using tiktoken-based accurate token counting, and stores the
    chunks in the context index for efficient retrieval.

    Multi-tenant isolation enforced via tenant_key.
    """
    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.context_management import ContextManagementSystem
    from src.giljo_mcp.models import Product

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    async with state.db_manager.get_session_async() as db:
        stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        content = None
        original_size = 0
        vision_doc_id = None

        # Get content from VisionDocument relationship
        if product.primary_vision_text:
            content = product.primary_vision_text
            original_size = len(content)
            # Get the vision document ID for later update
            if product.vision_documents:
                vision_doc_id = product.vision_documents[0].id
        elif product.primary_vision_path:
            from pathlib import Path

            import aiofiles

            vision_path = Path(product.primary_vision_path)
            if not vision_path.exists():
                raise HTTPException(status_code=404, detail="Vision document file not found")

            async with aiofiles.open(vision_path, encoding="utf-8") as f:
                content = await f.read()
                original_size = len(content)
            # Get the vision document ID for later update
            if product.vision_documents:
                vision_doc_id = product.vision_documents[0].id
        else:
            raise HTTPException(status_code=404, detail="No vision document available for this product")

        if product.vision_is_chunked and not request.force_rechunk:
            return ChunkVisionResponse(
                success=False,
                product_id=product_id,
                chunks_created=0,
                total_tokens=0,
                original_size=original_size,
                message="Vision document already chunked. Use force_rechunk=true to rechunk.",
            )

        cms = ContextManagementSystem(state.db_manager)
        result = cms.process_vision_document(tenant_key, product_id, content)

        # Mark vision document as chunked
        if vision_doc_id:
            from src.giljo_mcp.models.products import VisionDocument

            stmt = select(VisionDocument).where(VisionDocument.id == vision_doc_id)
            vision_result = await db.execute(stmt)
            vision_doc = vision_result.scalar_one_or_none()
            if vision_doc:
                vision_doc.chunked = True
                vision_doc.chunk_count = result["chunks_created"]
        await db.commit()

        return ChunkVisionResponse(
            success=True,
            product_id=product_id,
            chunks_created=result["chunks_created"],
            total_tokens=result["total_tokens"],
            original_size=original_size,
            reduction_percentage=None,
            message="Vision document chunked and indexed successfully",
        )


@router.get("/search", response_model=SearchContextResponse)
async def search_context(
    query: str = Query(..., description="Search query"),
    product_id: str | None = Query(None, description="Filter by product ID"),
    limit: int = Query(10, description="Maximum chunks to return"),
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Search context index by keywords.

    Uses PostgreSQL full-text search to find relevant chunks based on the query.
    Returns chunks sorted by relevance score.

    Multi-tenant isolation enforced via tenant_key.
    """
    from api.app import state
    from src.giljo_mcp.context_management import ContextManagementSystem

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    cms = ContextManagementSystem(state.db_manager)

    if product_id:
        chunks = cms.loader.load_relevant_chunks(
            tenant_key=tenant_key, product_id=product_id, query=query, max_tokens=100000
        )[:limit]
    else:
        chunks = cms.indexer.search_chunks(tenant_key, query, limit)

    total_tokens = sum(c.get("tokens", 0) for c in chunks)

    context_chunks = [
        ContextChunk(
            chunk_id=str(c.get("id", c.get("chunk_id", ""))),
            content=c.get("content", ""),
            tokens=c.get("tokens", 0),
            chunk_number=c.get("chunk_number", 0),
            relevance_score=c.get("relevance_score"),
        )
        for c in chunks
    ]

    return SearchContextResponse(
        query=query, chunks=context_chunks, total_chunks=len(context_chunks), total_tokens=total_tokens
    )


@router.post("/load-for-agent", response_model=LoadContextResponse)
async def load_context_for_agent(
    request: LoadContextRequest,
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Load context for specific agent.

    Selects relevant chunks based on agent role and mission.
    Uses role-based weighting to prioritize chunks relevant to the agent type.

    Multi-tenant isolation enforced via tenant_key.
    """
    from api.app import state
    from src.giljo_mcp.context_management import ContextManagementSystem

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    cms = ContextManagementSystem(state.db_manager)

    result = cms.load_context_for_agent(
        tenant_key=tenant_key,
        product_id=request.product_id,
        query=request.mission,
        role=request.agent_display_name,
        max_tokens=request.max_tokens,
    )

    context_chunks = [
        ContextChunk(
            chunk_id=str(c.get("id", c.get("chunk_id", ""))),
            content=c.get("content", ""),
            tokens=c.get("tokens", 0),
            chunk_number=c.get("chunk_number", 0),
            relevance_score=c.get("relevance_score"),
        )
        for c in result["chunks"]
    ]

    return LoadContextResponse(
        agent_display_name=request.agent_display_name,
        chunks=context_chunks,
        total_chunks=result["total_chunks"],
        total_tokens=result["total_tokens"],
        average_relevance=result["average_relevance"],
        reduction_percentage=None,
    )


@router.get("/products/{product_id}/token-stats", response_model=TokenStatsResponse)
async def get_token_stats(
    product_id: str,
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Get context prioritization statistics for a product.

    Returns original tokens, condensed tokens (if summarized),
    and reduction percentage.

    Multi-tenant isolation enforced via tenant_key.
    """
    from api.app import state
    from src.giljo_mcp.context_management import ContextManagementSystem

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    cms = ContextManagementSystem(state.db_manager)

    stats = cms.get_token_reduction_stats(tenant_key, product_id)

    if not stats:
        chunks = cms.get_all_chunks(tenant_key, product_id)
        if not chunks:
            raise HTTPException(status_code=404, detail="No chunks found for this product")

        total_tokens = sum(c.tokens for c in chunks)
        return TokenStatsResponse(
            product_id=product_id,
            original_tokens=total_tokens,
            condensed_tokens=total_tokens,
            reduction_percentage=0.0,
            chunks_count=len(chunks),
        )

    return TokenStatsResponse(
        product_id=product_id,
        original_tokens=stats.get("original_tokens", 0),
        condensed_tokens=stats.get("condensed_tokens", 0),
        reduction_percentage=stats.get("reduction_percentage", 0.0),
        chunks_count=stats.get("chunks_count", 0),
    )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    tenant_key: str = Depends(get_tenant_key),
):
    """
    Health check for context management system.

    Returns system status, chunk count, and search performance.
    """
    import time

    from sqlalchemy import func, select

    from api.app import state
    from src.giljo_mcp.models import MCPContextIndex

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            stmt = select(func.count()).select_from(MCPContextIndex).where(MCPContextIndex.tenant_key == tenant_key)
            result = await db.execute(stmt)
            chunk_count = result.scalar()

            start_time = time.time()
            search_stmt = select(MCPContextIndex).where(MCPContextIndex.tenant_key == tenant_key).limit(1)
            await db.execute(search_stmt)
            search_time_ms = (time.time() - start_time) * 1000

            return HealthCheckResponse(
                status="healthy",
                chunk_count=chunk_count or 0,
                search_performance_ms=round(search_time_ms, 2),
                message="Context management system operational",
            )

    except (ValueError, KeyError, RuntimeError) as e:
        return HealthCheckResponse(
            status="degraded", chunk_count=0, search_performance_ms=None, message=f"Error: {e!s}"
        )
