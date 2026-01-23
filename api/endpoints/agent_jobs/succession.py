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
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.schemas import (
    InitiateHandoverResponse,
    SuccessionRequest,
    SuccessionResponse,
    SuccessionStatusResponse,
)
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

        # Extract results (dual-model aware - Handover 0381: clean contract)
        # Agent ID Swap: decommissioned_agent_id is the old orchestrator's new ID
        work_order_id = succession_result["job_id"]  # The work order (persists across succession)
        successor_agent_id = succession_result.get("successor_agent_id")  # Takes over original agent_id
        decommissioned_agent_id = succession_result.get("decommissioned_agent_id")  # Old orch's new ID
        instance_number = succession_result["successor_instance_number"]

        # Get successor for additional details (backwards compat: check both models)
        # NOTE: Same agent_id can have multiple instances (Handover 0429), so we must
        # filter by the specific instance_number returned from the service
        successor = None
        if successor_agent_id:
            # New dual-model path: look up by agent_id AND instance_number (exact match)
            # Use joinedload for job relationship (needed for response at line 217)
            from sqlalchemy.orm import joinedload
            from src.giljo_mcp.models import AgentExecution
            stmt = select(AgentExecution).options(
                joinedload(AgentExecution.job)
            ).where(
                AgentExecution.agent_id == successor_agent_id,
                AgentExecution.tenant_key == current_user.tenant_key,
                AgentExecution.instance_number == instance_number  # Exact match
            )
            result = await db.execute(stmt)
            successor = result.scalars().first()

        # Note: Removed MCPAgentJob fallback - only use AgentExecution

        if not successor:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Successor created but could not be retrieved"
            )

        # Get current execution for handover summary (job_id param could be agent_id)
        # NOTE: Same agent_id can have multiple instances (Handover 0429), so we must
        # order by instance_number DESC and limit to 1 to get the latest instance.
        # However, after succession, the current execution is instance N-1, so we want
        # the second-latest (or filter by instance_number = successor.instance_number - 1)
        current_instance_number = instance_number - 1
        stmt = select(AgentExecution).where(
            AgentExecution.agent_id == job_id,
            AgentExecution.tenant_key == current_user.tenant_key,
            AgentExecution.instance_number == current_instance_number
        )
        result = await db.execute(stmt)
        current_execution = result.scalars().first()

        # Fallback: try job_id if not found by agent_id
        if not current_execution:
            stmt = select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == current_user.tenant_key,
                AgentExecution.instance_number == current_instance_number
            )
            result = await db.execute(stmt)
            current_execution = result.scalars().first()

        # Final fallback: if still not found, get by job_id with latest completed status
        if not current_execution:
            stmt = select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == current_user.tenant_key,
                AgentExecution.status == "complete"
            ).order_by(AgentExecution.instance_number.desc()).limit(1)
            result = await db.execute(stmt)
            current_execution = result.scalars().first()

        # Generate handover summary from current execution
        handover_summary_str = "Succession triggered - handover context available"
        if current_execution and current_execution.handover_summary:
            if isinstance(current_execution.handover_summary, dict):
                handover_summary_str = json.dumps(current_execution.handover_summary, indent=2)
            else:
                handover_summary_str = str(current_execution.handover_summary)

        # Generate thin-client launch prompt for successor
        prompt_generator = ThinClientPromptGenerator(
            db=db,
            tenant_key=current_user.tenant_key
        )

        prompt_result = await prompt_generator.generate(
            project_id=successor.job.project_id,  # project_id is on AgentJob, not AgentExecution
            user_id=str(current_user.id),
            instance_number=instance_number
        )

        launch_prompt = prompt_result["thin_prompt"]  # Key is "thin_prompt", not "prompt"

        # Get current agent_id for response (Handover 0381: clean contract)
        current_agent_id = current_execution.agent_id if current_execution else job_id

        # Emit WebSocket event for UI updates (Handover 0381: clean contract)
        # Agent ID Swap: Include decommissioned_agent_id for UI reference
        try:
            from api.app import state  # Lazy import to avoid circular dependency
            if state.websocket_manager:
                await state.websocket_manager.broadcast_to_tenant(
                    tenant_key=current_user.tenant_key,
                    event_type="orchestrator:succession_triggered",
                    data={
                        "current_agent_id": decommissioned_agent_id or str(current_agent_id),  # Decommissioned ID
                        "decommissioned_agent_id": decommissioned_agent_id,  # Explicit field
                        "job_id": work_order_id,  # Work order (persists across succession)
                        "successor_agent_id": successor_agent_id,  # Takes over original ID
                        "instance_number": instance_number,
                        "reason": request.reason,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "triggered_by": current_user.username
                    }
                )
                logger.info(
                    f"WebSocket event 'orchestrator:succession_triggered' "
                    f"broadcasted: {decommissioned_agent_id} (decommissioned) -> {successor_agent_id}"
                )
        except Exception as ws_error:
            logger.error(f"Failed to broadcast WebSocket event: {ws_error}", exc_info=True)

        # Agent ID Swap: current_agent_id is now the decommissioned ID
        # For backward compatibility, use decommissioned_agent_id if available
        current_agent_id_value = decommissioned_agent_id or str(current_agent_id)

        return SuccessionResponse(
            current_agent_id=current_agent_id_value,
            job_id=work_order_id,
            successor_agent_id=successor_agent_id,
            instance_number=instance_number,
            launch_prompt=launch_prompt,
            handover_summary=handover_summary_str,
            succession_reason=request.reason,
            created_at=successor.started_at or successor.job.created_at,
            decommissioned_agent_id=decommissioned_agent_id,
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
        # Get execution with tenant isolation (job_id could be agent_id)
        # NOTE: Same agent_id can have multiple instances (Handover 0429), so we must
        # order by instance_number DESC and limit to 1 to get the latest instance
        stmt = select(AgentExecution).where(
            AgentExecution.agent_id == job_id,
            AgentExecution.tenant_key == current_user.tenant_key
        ).order_by(AgentExecution.instance_number.desc()).limit(1)
        result = await db.execute(stmt)
        execution = result.scalars().first()

        # Fallback: try job_id (get latest instance for this work order)
        if not execution:
            stmt = select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == current_user.tenant_key
            ).order_by(AgentExecution.instance_number.desc()).limit(1)
            result = await db.execute(stmt)
            execution = result.scalars().first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Validate: must be orchestrator
        if execution.agent_display_name != "orchestrator":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only check succession for orchestrators"
            )

        # Calculate context usage
        context_used = execution.context_used or 0
        context_budget = execution.context_budget or 200000  # Default Sonnet 4.5 budget

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
            job_id=execution.job_id,
            needs_succession=needs_succession,
            context_used=context_used,
            context_budget=context_budget,
            context_usage_pct=round(context_usage_pct, 2),
            handover_to=execution.succeeded_by,
            succession_reason=execution.succession_reason,
            instance_number=execution.instance_number
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


@router.post(
    "/{job_id}/initiate-handover",
    response_model=InitiateHandoverResponse,
    summary="Initiate orchestrator handover",
    description="Returns prompt for retiring orchestrator to spawn its successor",
    tags=["agent-jobs", "succession"]
)
async def initiate_handover(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> InitiateHandoverResponse:
    """
    Initiate orchestrator handover (Handover 0506).

    Returns a prompt that the user pastes into the CURRENT orchestrator terminal.
    The prompt instructs the retiring orchestrator to:
    1. Gather its context (mission status, work progress, active agents)
    2. Spawn a successor orchestrator with rich handover mission
    3. Mark itself as handed_over

    The RETIRING orchestrator has the context - it spawns the successor.

    Args:
        job_id: Current orchestrator's job_id or agent_id
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        InitiateHandoverResponse with prompt and job details

    Raises:
        HTTPException 404: Job not found
        HTTPException 400: Job is not an orchestrator or not in active status
    """
    logger.info(f"User {current_user.username} initiating handover for job {job_id}")

    try:
        # Get execution (job_id could be agent_id)
        # NOTE: Same agent_id can have multiple instances (Handover 0429), so we must
        # order by instance_number DESC to get the latest active instance
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        stmt = select(AgentExecution).options(
            joinedload(AgentExecution.job)
        ).where(
            AgentExecution.agent_id == job_id,
            AgentExecution.tenant_key == current_user.tenant_key
        ).order_by(AgentExecution.instance_number.desc()).limit(1)
        result = await db.execute(stmt)
        execution = result.scalars().first()

        # Fallback: try job_id (get latest instance for this work order)
        if not execution:
            stmt = select(AgentExecution).options(
                joinedload(AgentExecution.job)
            ).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == current_user.tenant_key
            ).order_by(AgentExecution.instance_number.desc()).limit(1)
            result = await db.execute(stmt)
            execution = result.scalars().first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Validate: must be orchestrator
        if execution.agent_display_name != "orchestrator":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only initiate handover for orchestrators"
            )

        # Validate: must be in active status
        if execution.status not in ["waiting", "working", "blocked"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot initiate handover for orchestrator in '{execution.status}' status"
            )

        # Get project_id from the job
        project_id = execution.job.project_id if execution.job else None
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not determine project_id for orchestrator"
            )

        # Build handover prompt for the retiring orchestrator
        instance = execution.instance_number or 1
        tenant_key = current_user.tenant_key

        prompt = f"""=== HANDOVER REQUESTED ===

The user has requested you hand over to a successor orchestrator.

YOU must spawn the successor because YOU have the richest context.

## Step 1: Gather Your Context

Think about:
- What is the current mission status?
- What work is complete, in-progress, or blocked?
- Who are the active agents and what are they doing?
- What decisions are pending?
- What should the successor do next?

## Step 2: Spawn Successor Orchestrator

Call spawn_agent_job with a RICH mission:

mcp__giljo-mcp__spawn_agent_job(
    agent_display_name="orchestrator",
    agent_name="Orchestrator",
    mission='''
## HANDOVER CONTEXT

You are taking over from Orchestrator Instance {instance}.

### Mission Status
[Describe current overall status]

### Completed Work
- [List completed items]

### In-Progress Work
- [List in-progress items with status]

### Active Agents
- agent_name (agent_id): [what they're doing]

### Pending Decisions
- [List decisions needing user input]

### Recommended Next Steps
1. [First priority]
2. [Second priority]

### User Notes
[Any notes from user conversations]

## TOOLS TO USE

1. get_agent_mission(job_id, tenant_key) - Read this mission
2. get_team_agents(job_id, tenant_key) - List agents for any job
3. get_orchestrator_instructions(job_id, tenant_key) - Get product/project context
4. get_workflow_status(project_id, tenant_key) - Check agent counts

## FIRST ACTIONS

1. Call acknowledge_job() to mark yourself as working
2. Review the handover context above
3. Call get_team_agents() to see current agent states
4. ASK THE USER how they want to proceed
''',
    project_id="{project_id}",
    tenant_key="{tenant_key}",
    parent_agent_id="{execution.agent_id}"
)

## Step 3: Output the Result

After spawning, OUTPUT the launch prompt that was returned, so user can paste it in a new terminal.

Then mark yourself as complete:

mcp__giljo-mcp__complete_job(
    job_id="{execution.job_id}",
    tenant_key="{tenant_key}",
    result={{"handover": "complete", "successor_spawned": true}}
)
"""

        logger.info(
            f"Generated handover prompt for orchestrator {execution.agent_id} "
            f"(job: {execution.job_id}, instance: {instance})"
        )

        return InitiateHandoverResponse(
            prompt=prompt,
            job_id=execution.job_id,
            agent_id=execution.agent_id,
            project_id=project_id,
            instance_number=instance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to initiate handover for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate handover: {str(e)}"
        )
