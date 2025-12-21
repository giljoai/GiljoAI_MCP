"""
Orchestrator Succession Endpoints - Handover 0505

Handles manual orchestrator succession operations:
- POST /api/agent-jobs/{job_id}/trigger-succession - Manually trigger succession
- GET /api/agent-jobs/{job_id}/succession-status - Check succession status

Used by:
- "Hand Over" button in AgentCardEnhanced.vue
- /gil_handover slash command
- Auto-succession at 90% context threshold (from OrchestrationService)

All operations use OrchestrationService (no direct DB access).
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, User
from src.giljo_mcp.models.schemas import SuccessionRequest, SuccessionResponse, SuccessionStatusResponse
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

from .dependencies import get_orchestration_service


logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Orchestrator Succession Endpoints
# ============================================================================


@router.post(
    "/{job_id}/trigger-succession",
    response_model=SuccessionResponse,
    summary="Trigger orchestrator succession",
    description="Manually trigger orchestrator succession (create successor instance)",
    tags=["agent-jobs", "succession"]
)
async def trigger_succession(
    job_id: str,
    request: SuccessionRequest = SuccessionRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> SuccessionResponse:
    """
    Trigger manual orchestrator succession.

    Creates successor orchestrator instance with:
    - Incremented instance_number
    - Handover summary from current context
    - Thin-client launch prompt

    Used by:
    - "Hand Over" button in AgentCardEnhanced.vue
    - /gil_handover slash command

    Args:
        job_id: Current orchestrator job UUID
        request: SuccessionRequest with reason and optional notes
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)
        orchestration_service: Orchestration service (from dependency)

    Returns:
        SuccessionResponse with successor job and launch prompt

    Raises:
        HTTPException 400: Invalid job (not orchestrator, not found, or already has successor)
        HTTPException 500: Succession failed
    """
    logger.info(f"User {current_user.username} triggering succession for job {job_id}")

    try:
        # Trigger succession via OrchestrationService (handles all succession logic)
        succession_result = await orchestration_service.trigger_succession(
            job_id=job_id,
            reason=request.reason,
            tenant_key=current_user.tenant_key
        )

        # Extract results (dual-model aware)
        work_order_id = succession_result["job_id"]  # The work order (persists)
        successor_agent_id = succession_result.get("successor_agent_id")  # NEW executor
        successor_job_id = succession_result["successor_job_id"]  # Backwards compat (same as job_id in new model)
        instance_number = succession_result["successor_instance_number"]

        # Get successor for additional details (backwards compat: check both models)
        successor = None
        if successor_agent_id:
            # New dual-model path: look up by agent_id
            from src.giljo_mcp.models import AgentExecution
            stmt = select(AgentExecution).where(
                AgentExecution.agent_id == successor_agent_id,
                AgentExecution.tenant_key == current_user.tenant_key
            )
            result = await db.execute(stmt)
            successor = result.scalar_one_or_none()

        if not successor:
            # Fallback: old MCPAgentJob path
            stmt = select(MCPAgentJob).where(
                MCPAgentJob.job_id == successor_job_id,
                MCPAgentJob.tenant_key == current_user.tenant_key
            )
            result = await db.execute(stmt)
            successor = result.scalar_one_or_none()

        if not successor:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Successor created but could not be retrieved"
            )

        # Get current job for handover summary
        stmt = select(MCPAgentJob).where(
            MCPAgentJob.job_id == job_id,
            MCPAgentJob.tenant_key == current_user.tenant_key
        )
        result = await db.execute(stmt)
        current_job = result.scalar_one_or_none()

        # Generate handover summary from current job
        handover_summary_str = "Succession triggered - handover context available"
        if current_job and current_job.handover_summary:
            if isinstance(current_job.handover_summary, dict):
                handover_summary_str = json.dumps(current_job.handover_summary, indent=2)
            else:
                handover_summary_str = str(current_job.handover_summary)

        # Generate thin-client launch prompt for successor
        prompt_generator = ThinClientPromptGenerator(
            db=db,
            tenant_key=current_user.tenant_key
        )

        prompt_result = await prompt_generator.generate(
            project_id=successor.project_id,
            user_id=str(current_user.id),
            instance_number=instance_number
        )

        launch_prompt = prompt_result["prompt"]

        # Emit WebSocket event for UI updates
        try:
            from api.app import state  # Lazy import to avoid circular dependency
            if state.websocket_manager:
                await state.websocket_manager.broadcast_to_tenant(
                    tenant_key=current_user.tenant_key,
                    event_type="orchestrator:succession_triggered",
                    data={
                        "current_job_id": job_id,  # Original request parameter (could be agent_id or job_id)
                        "work_order_id": work_order_id,  # The work order (persists across succession)
                        "successor_agent_id": successor_agent_id,  # NEW executor agent_id
                        "successor_job_id": successor_job_id,  # Backwards compat
                        "instance_number": instance_number,
                        "reason": request.reason,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "triggered_by": current_user.username
                    }
                )
                logger.info(
                    f"WebSocket event 'orchestrator:succession_triggered' "
                    f"broadcasted for {job_id} -> {successor_job_id}"
                )
        except Exception as ws_error:
            logger.error(f"Failed to broadcast WebSocket event: {ws_error}", exc_info=True)

        return SuccessionResponse(
            current_job_id=job_id,
            successor_job_id=successor_job_id,
            successor_agent_id=successor_agent_id,  # NEW field for dual-model
            instance_number=instance_number,
            launch_prompt=launch_prompt,
            handover_summary=handover_summary_str,
            succession_reason=request.reason,
            created_at=successor.created_at
        )

    except ValueError as e:
        # Handle validation errors from OrchestrationService
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Failed to trigger succession for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Succession failed: {str(e)}"
        )


@router.get(
    "/{job_id}/succession-status",
    response_model=SuccessionStatusResponse,
    summary="Check succession status",
    description="Check if succession is needed based on context usage",
    tags=["agent-jobs", "succession"]
)
async def check_succession_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> SuccessionStatusResponse:
    """
    Check if orchestrator should trigger succession.

    Returns context usage metrics and succession recommendations.
    Succession is recommended at >= 90% context usage.

    Args:
        job_id: Orchestrator job UUID
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        SuccessionStatusResponse with usage metrics and recommendations

    Raises:
        HTTPException 404: Job not found
        HTTPException 400: Job is not an orchestrator
    """
    logger.debug(f"User {current_user.username} checking succession status for job {job_id}")

    try:
        # Get job with tenant isolation
        stmt = select(MCPAgentJob).where(
            MCPAgentJob.job_id == job_id,
            MCPAgentJob.tenant_key == current_user.tenant_key
        )
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Validate: must be orchestrator
        if job.agent_type != "orchestrator":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only check succession for orchestrators"
            )

        # Calculate context usage
        context_used = job.context_used or 0
        context_budget = job.context_budget or 200000  # Default Sonnet 4.5 budget

        context_usage_pct = 0.0
        if context_budget > 0:
            context_usage_pct = (context_used / context_budget) * 100

        # Recommend succession at >= 90% threshold
        needs_succession = context_usage_pct >= 90.0

        logger.info(
            f"Succession status for {job_id}: "
            f"{context_used}/{context_budget} ({context_usage_pct:.2f}%), "
            f"needs_succession={needs_succession}"
        )

        return SuccessionStatusResponse(
            job_id=job_id,
            needs_succession=needs_succession,
            context_used=context_used,
            context_budget=context_budget,
            context_usage_pct=round(context_usage_pct, 2),
            handover_to=job.handover_to,
            succession_reason=job.succession_reason,
            instance_number=job.instance_number or 1
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Failed to check succession status for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check succession status: {str(e)}"
        )
