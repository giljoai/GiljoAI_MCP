"""
Agent management API endpoints for Handover 0017.

Provides endpoints for vision document chunking, agent job management, and context search.
All operations enforce tenant isolation for security.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.dependencies import get_tenant_key
from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from src.giljo_mcp.repositories.context_repository import ContextRepository
from src.giljo_mcp.tools.chunking import EnhancedChunker


router = APIRouter(prefix="/api", tags=["Agent Management"])


# Pydantic models for request/response


class VisionUploadRequest(BaseModel):
    product_id: str = Field(..., description="Product ID to upload vision for")
    content: str = Field(..., description="Vision document content")


class VisionUploadResponse(BaseModel):
    message: str
    product_id: str
    chunks_created: int
    total_tokens: int
    chunked: bool


class ContextChunkResponse(BaseModel):
    chunk_id: str
    content: str
    keywords: List[str]
    token_count: int
    chunk_order: int
    summary: Optional[str]
    created_at: datetime


class ContextSearchRequest(BaseModel):
    product_id: str = Field(..., description="Product ID to search within")
    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum results to return")


class AgentJobCreate(BaseModel):
    agent_display_name: str = Field(..., description="Human-readable display name for UI")
    mission: str = Field(..., description="Agent mission/instructions")
    spawned_by: Optional[str] = Field(None, description="Agent ID that spawned this job")
    context_chunks: List[str] = Field(default_factory=list, description="Context chunk IDs")


class AgentJobResponse(BaseModel):
    job_id: str
    agent_display_name: str
    mission: str
    status: str
    spawned_by: Optional[str]
    template_id: Optional[str] = None  # Handover 0244a: Link to source template
    context_chunks: List[str]
    messages: List[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class AgentJobStatusUpdate(BaseModel):
    status: str = Field(..., description="New status (pending, active, completed, failed)")


class AgentJobMessage(BaseModel):
    message: Dict[str, Any] = Field(..., description="Message object to add")


class TokenReductionStats(BaseModel):
    total_summaries: int
    total_tokens_saved: int
    average_reduction_percent: float
    total_original_tokens: int
    total_condensed_tokens: int


# Handover 0503: Removed duplicate vision upload endpoint
# Vision uploads now handled by api/endpoints/products/vision.py
# Use POST /api/v1/products/{product_id}/vision instead

@router.get("/agent-jobs/active", response_model=List[AgentJobResponse])
async def get_active_agent_jobs(
    agent_display_name: Optional[str] = Query(None, description="Filter by agent display name"),
    tenant_key: str = Depends(get_tenant_key),
):
    """List all active agent jobs for tenant."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        job_repo = AgentJobRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            jobs = job_repo.get_active_jobs(db, tenant_key, agent_display_name)

            # Note: AgentJobResponse expects messages field, but we're migrating to counters (0387f)
            # This endpoint uses AgentJobRepository which returns AgentJob, not AgentExecution
            # AgentJob doesn't have counter fields - need to query AgentExecution for counters
            # For now, return empty list as messages field will be deprecated
            return [
                AgentJobResponse(
                    job_id=job.job_id,
                    agent_display_name=job.job_type,
                    mission=job.mission,
                    status=job.status,
                    spawned_by=job.spawned_by,
                    template_id=job.template_id,  # Handover 0244a
                    context_chunks=job.context_chunks or [],
                    messages=[],  # Handover 0387f: JSONB messages deprecated, use counter fields
                    created_at=job.created_at,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                )
                for job in jobs
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-jobs", response_model=AgentJobResponse)
async def create_agent_job(job_data: AgentJobCreate, tenant_key: str = Depends(get_tenant_key)):
    """Create a new agent job."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        job_repo = AgentJobRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            job = job_repo.create_job(
                db,
                tenant_key,
                agent_display_name=job_data.agent_display_name,
                mission=job_data.mission,
                spawned_by=job_data.spawned_by,
                context_chunks=job_data.context_chunks,
            )

            await db.commit()

            # Broadcast job creation via WebSocket
            if state.websocket_manager:
                await state.websocket_manager.broadcast_job_created(
                    job_id=job.job_id,
                    agent_display_name=job.job_type,
                    tenant_key=tenant_key,
                    project_id=str(job.project_id) if getattr(job, "project_id", None) else None,
                    agent_name=getattr(job, "agent_name", None),
                    status=job.status,
                    spawned_by=job.spawned_by,
                    mission_preview=job.mission[:100] if job.mission else None,
                    created_at=job.created_at,
                )

            return AgentJobResponse(
                job_id=job.job_id,
                agent_display_name=job.job_type,
                mission=job.mission,
                status=job.status,
                spawned_by=job.spawned_by,
                template_id=job.template_id,  # Handover 0244a
                context_chunks=job.context_chunks or [],
                messages=[],  # Handover 0387f: JSONB messages deprecated, use counter fields
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agent-jobs/{job_id}/status", response_model=dict)
async def update_agent_job_status(
    job_id: str, status_update: AgentJobStatusUpdate, tenant_key: str = Depends(get_tenant_key)
):
    """Update agent job status."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        job_repo = AgentJobRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            # Get current job to capture old status
            job = job_repo.get_job_by_job_id(db, tenant_key, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Agent job not found")

            old_status = job.status

            # Update status
            success = job_repo.update_status(db, tenant_key, job_id, status_update.status)

            if not success:
                raise HTTPException(status_code=404, detail="Agent job not found")

            # Calculate duration for completed/failed jobs
            duration_seconds = None
            if status_update.status in ["completed", "failed"] and job.started_at:
                from datetime import datetime, timezone

                completed_at = job.completed_at or datetime.now(timezone.utc)
                duration_seconds = (completed_at - job.started_at).total_seconds()

            await db.commit()

            # Broadcast status update via WebSocket
            # Handover 0463: Include project_id for frontend project-aware filtering
            if state.websocket_manager:
                await state.websocket_manager.broadcast_job_status_update(
                    job_id=job_id,
                    agent_display_name=job.job_type,
                    tenant_key=tenant_key,
                    old_status=old_status,
                    new_status=status_update.status,
                    duration_seconds=duration_seconds,
                    project_id=job.project_id,
                )

            return {"message": f"Job status updated to {status_update.status}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-jobs/{job_id}/acknowledge", response_model=dict)
async def acknowledge_job_message(job_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Acknowledge receipt of a job message."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        job_repo = AgentJobRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            # Get job before acknowledgment
            job = job_repo.get_job_by_job_id(db, tenant_key, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Agent job not found")

            old_status = job.status

            success = job_repo.acknowledge_job(db, tenant_key, job_id)

            if not success:
                raise HTTPException(status_code=404, detail="Agent job not found")

            await db.commit()

            # Broadcast acknowledgment via WebSocket (transitions to 'active')
            # Handover 0463: Include project_id for frontend project-aware filtering
            if state.websocket_manager and old_status == "pending":
                await state.websocket_manager.broadcast_job_status_update(
                    job_id=job_id,
                    agent_display_name=job.job_type,
                    tenant_key=tenant_key,
                    old_status=old_status,
                    new_status="active",  # Acknowledgment implies active status
                    project_id=job.project_id,
                )

            return {"message": "Job acknowledged successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-jobs/{job_id}/messages", response_model=dict)
async def add_job_message(job_id: str, message_data: AgentJobMessage, tenant_key: str = Depends(get_tenant_key)):
    """Add a message to an agent job."""
    from uuid import uuid4

    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        job_repo = AgentJobRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            # Get job for broadcasting
            job = await job_repo.get_job_by_job_id(db, tenant_key, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Agent job not found")

            success = await job_repo.add_message(db, tenant_key, job_id, message_data.message)

            if not success:
                raise HTTPException(status_code=404, detail="Agent job not found")

            await db.commit()

            # Broadcast message via WebSocket
            if state.websocket_manager:
                message_content = message_data.message.get("content", "")
                content_preview = (
                    message_content[:100] if isinstance(message_content, str) else str(message_content)[:100]
                )

                await state.websocket_manager.broadcast_job_message(
                    job_id=job_id,
                    message_id=message_data.message.get("message_id", str(uuid4())),
                    from_agent=message_data.message.get("from_agent", job.job_type),
                    tenant_key=tenant_key,
                    to_agent=message_data.message.get("to_agent"),
                    message_type=message_data.message.get("type", "status"),
                    content_preview=content_preview,
                )

            return {"message": "Message added to job successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/search", response_model=List[ContextChunkResponse])
async def search_context(search_data: ContextSearchRequest, tenant_key: str = Depends(get_tenant_key)):
    """Full-text search on vision chunks."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        context_repo = ContextRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            # Verify product exists and belongs to tenant
            stmt = select(Product).where(Product.id == search_data.product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Search chunks
            chunks = context_repo.search_chunks(
                db, tenant_key, search_data.product_id, search_data.query, search_data.limit
            )

            return [
                ContextChunkResponse(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    keywords=chunk.keywords or [],
                    token_count=chunk.token_count or 0,
                    chunk_order=chunk.chunk_order or 0,
                    summary=chunk.summary,
                    created_at=chunk.created_at,
                )
                for chunk in chunks
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/product/{product_id}/chunks", response_model=List[ContextChunkResponse])
async def get_product_chunks(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Get all context chunks for a product."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        context_repo = ContextRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            # Verify product exists and belongs to tenant
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Get all chunks for product
            chunks = context_repo.get_chunks_by_product(db, tenant_key, product_id)

            return [
                ContextChunkResponse(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    keywords=chunk.keywords or [],
                    token_count=chunk.token_count or 0,
                    chunk_order=chunk.chunk_order or 0,
                    summary=chunk.summary,
                    created_at=chunk.created_at,
                )
                for chunk in chunks
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/stats/{product_id}", response_model=TokenReductionStats)
async def get_token_reduction_stats(product_id: str, tenant_key: str = Depends(get_tenant_key)):
    """Get context prioritization statistics for a product."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        context_repo = ContextRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            # Verify product exists and belongs to tenant
            stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            # Get stats
            stats = context_repo.get_token_reduction_stats(db, tenant_key, product_id)

            return TokenReductionStats(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-jobs/stats", response_model=dict)
async def get_agent_job_statistics(
    agent_display_name: Optional[str] = Query(None, description="Filter by agent display name"),
    tenant_key: str = Depends(get_tenant_key),
):
    """Get agent job statistics for tenant."""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        job_repo = AgentJobRepository(state.db_manager)

        async with state.db_manager.get_session_async() as db:
            stats = job_repo.get_job_statistics(db, tenant_key, agent_display_name)
            return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
