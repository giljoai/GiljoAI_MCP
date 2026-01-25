"""
Simple Handover Endpoint - Handover 0461c

Replaces complex Agent ID Swap succession with 360 Memory-based session continuity.

This endpoint:
1. Writes session context to 360 Memory (session_handover entry)
2. Resets context_used counter to 0
3. Returns a continuation prompt that instructs reading 360 Memory
4. Emits WebSocket event for UI updates

No more Agent ID Swap. No new AgentExecution rows. Just simple context reset.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/{job_id}/simple-handover",
    summary="Simple session handover via 360 Memory",
    description="Write session context to 360 Memory and return continuation prompt",
    tags=["agent-jobs", "handover"],
)
async def simple_handover(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Simple handover: Write session to 360 Memory and reset context.

    Does NOT create new AgentExecution rows. Instead:
    1. Gathers current session context
    2. Writes session_handover entry to 360 Memory
    3. Resets context_used to 0
    4. Returns continuation prompt that reads 360 Memory

    Args:
        job_id: Orchestrator job_id or agent_id
        current_user: Authenticated user
        db: Database session

    Returns:
        {
            "success": True,
            "continuation_prompt": "...",
            "memory_entry_id": "...",
            "context_reset": True
        }
    """
    try:
        # Find execution (job_id could be agent_id)
        stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.agent_id == job_id,
                AgentExecution.tenant_key == current_user.tenant_key,
            )
            .order_by(AgentExecution.instance_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        execution = result.scalars().first()

        # Fallback to job_id
        if not execution:
            stmt = (
                select(AgentExecution)
                .where(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == current_user.tenant_key,
                )
                .order_by(AgentExecution.instance_number.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            execution = result.scalars().first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        if execution.agent_display_name != "orchestrator":
            raise HTTPException(status_code=400, detail="Only orchestrators can use handover")

        # Get job for project_id
        stmt = select(AgentJob).where(AgentJob.job_id == execution.job_id)
        result = await db.execute(stmt)
        job = result.scalars().first()

        if not job:
            raise HTTPException(status_code=500, detail="Job not found")

        # Build session context for 360 Memory
        session_context = {
            "context_used": execution.context_used,
            "context_budget": execution.context_budget,
            "progress": execution.progress,
            "current_task": execution.current_task,
            "agent_id": execution.agent_id,
            "job_id": execution.job_id,
        }

        # Calculate context usage percentage (avoid division by zero)
        context_percent = (
            int((execution.context_used / execution.context_budget) * 100)
            if execution.context_budget > 0
            else 0
        )

        # Write to 360 Memory
        from src.giljo_mcp.tools.write_360_memory import write_360_memory
        from api.app import app

        # Get database manager from app state (Handover 0461c fix)
        db_manager = getattr(app.state, "db_manager", None)
        if db_manager is None:
            raise HTTPException(
                status_code=500,
                detail="Database manager not initialized"
            )

        memory_result = await write_360_memory(
            project_id=str(job.project_id),
            tenant_key=current_user.tenant_key,
            summary=f"Session handover at {execution.context_used}/{execution.context_budget} tokens ({context_percent}% context used). Progress: {execution.progress}%. Current task: {execution.current_task or 'N/A'}.",
            key_outcomes=[
                f"Progress: {execution.progress}%",
                f"Current task: {execution.current_task or 'N/A'}",
                f"Context usage: {context_percent}%",
            ],
            decisions_made=["Session handover triggered by user"],
            entry_type="session_handover",
            author_job_id=execution.job_id,
            db_manager=db_manager,
            session=db,
        )

        # Check if memory write succeeded
        if not memory_result.get("success"):
            logger.error(f"Failed to write 360 memory: {memory_result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to write 360 memory: {memory_result.get('error')}",
            )

        # Reset context_used
        old_context = execution.context_used
        execution.context_used = 0
        await db.commit()

        # Generate continuation prompt
        # Note: ThinClientPromptGenerator doesn't support continuation_mode parameter,
        # so we build a simple prompt manually that instructs reading 360 Memory
        continuation_prompt = _build_continuation_prompt(
            project_id=str(job.project_id),
            agent_id=execution.agent_id,
            job_id=execution.job_id,
        )

        # Emit WebSocket event
        try:
            from api.app import app

            websocket_manager = getattr(app.state, "websocket_manager", None)
            if websocket_manager:
                await websocket_manager.broadcast_to_tenant(
                    tenant_key=current_user.tenant_key,
                    event_type="orchestrator:context_reset",
                    data={
                        "agent_id": execution.agent_id,
                        "job_id": execution.job_id,
                        "project_id": str(job.project_id),
                        "old_context_used": old_context,
                        "new_context_used": 0,
                        "memory_entry_created": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception as ws_error:
            logger.warning(f"WebSocket broadcast failed: {ws_error}")

        return {
            "success": True,
            "continuation_prompt": continuation_prompt,
            "memory_entry_id": memory_result.get("entry_id"),
            "context_reset": True,
            "old_context_used": old_context,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Simple handover failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_continuation_prompt(
    project_id: str,
    agent_id: str,
    job_id: str,
) -> str:
    """
    Build a continuation prompt that instructs reading 360 Memory.

    This is a simplified prompt that tells the orchestrator to:
    1. Verify MCP connection
    2. Read 360 Memory for session context
    3. Check messages and workflow status
    4. Continue work

    Args:
        project_id: Project UUID
        agent_id: Agent ID (WHO - executor ID for MCP calls)
        job_id: Job ID (WHAT - work order ID)

    Returns:
        Continuation prompt string
    """
    # Note: We use the MCP server URL pattern from config
    # In production, this would be dynamically determined
    mcp_url = "http://localhost:7272/mcp"

    prompt = f"""I am Orchestrator for Project (CONTINUATION SESSION).

A previous session ran out of context. I am continuing the work.

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {job_id}
  THE Project ID: {project_id}

MCP Server: {mcp_url}
Note: tenant_key is auto-injected by server from your API key session

FIRST ACTIONS (DO NOT RE-STAGE):

1. Verify MCP: mcp__giljo-mcp__health_check()
   → Expected: {{"status": "healthy"}}

2. Read 360 Memory for session context:
   mcp__giljo-mcp__fetch_context(
       product_id="<fetch from project>",
       categories=["memory_360"]
   )
   → Look for "session_handover" entry with session context
   → Contains: previous context_used, progress, current_task

3. Check messages from agents:
   mcp__giljo-mcp__receive_messages(agent_id="{agent_id}")

4. Check workflow status:
   mcp__giljo-mcp__get_workflow_status(project_id="{project_id}")

CRITICAL RULES:
- Do NOT call get_orchestrator_instructions() to re-stage
- Do NOT re-write the project mission
- Read 360 Memory session_handover for context from previous session
- You are CONTINUING work, not starting from scratch

When ready, coordinate agents based on current status.
"""
    return prompt
