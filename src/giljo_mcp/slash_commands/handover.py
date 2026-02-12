"""
Slash command handler for /gil_handover
Simple session handover via 360 Memory (Handover 0461c)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.thin_prompt_generator import build_continuation_prompt


logger = logging.getLogger(__name__)


async def handle_gil_handover(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: Optional[str] = None,
    orchestrator_job_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Handle /gil_handover slash command

    Simple handover: Write session to 360 Memory and reset context.
    Does NOT create new AgentExecution rows.

    Args:
        db_session: Database session instance
        tenant_key: Current tenant key
        project_id: Optional project ID (auto-detected if not provided)
        orchestrator_job_id: Optional explicit orchestrator job ID

    Returns:
        {
            "success": bool,
            "message": str,
            "launch_prompt": str,  # Continuation prompt
            "memory_entry_id": str,
            "context_reset": bool
        }
    """
    # Find execution (job_id could be agent_id)
    if orchestrator_job_id:
        # Try agent_id first
        stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.agent_id == orchestrator_job_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        result = await db_session.execute(stmt)
        execution = result.scalars().first()

        # Fallback to job_id
        if not execution:
            stmt = (
                select(AgentExecution)
                .where(
                    AgentExecution.job_id == orchestrator_job_id,
                    AgentExecution.tenant_key == tenant_key,
                )
                .order_by(AgentExecution.started_at.desc())
                .limit(1)
            )
            result = await db_session.execute(stmt)
            execution = result.scalars().first()
    else:
        # Auto-detect active orchestrator for project
        execution = await _get_active_orchestrator(db_session, tenant_key, project_id)

    if not execution:
        return {
            "success": False,
            "message": "❌ No active orchestrator found. Only orchestrators can trigger handover.",
            "error": "NO_ORCHESTRATOR",
        }

    if execution.agent_display_name != "orchestrator":
        return {
            "success": False,
            "message": "❌ Only orchestrators can use handover.",
            "error": "NOT_ORCHESTRATOR",
        }

    # Get job for project_id
    stmt = select(AgentJob).where(AgentJob.job_id == execution.job_id)
    result = await db_session.execute(stmt)
    job = result.scalars().first()

    if not job:
        return {
            "success": False,
            "message": "❌ Job not found.",
            "error": "JOB_NOT_FOUND",
        }

    try:
        # Calculate context usage percentage (avoid division by zero)
        context_percent = (
            int((execution.context_used / execution.context_budget) * 100) if execution.context_budget > 0 else 0
        )

        # Write to 360 Memory
        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tools.write_360_memory import write_360_memory

        db_manager = DatabaseManager()

        memory_result = await write_360_memory(
            project_id=str(job.project_id),
            tenant_key=tenant_key,
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
            session=db_session,
        )

        # Check if memory write succeeded
        if not memory_result.get("success"):
            logger.error(f"Failed to write 360 memory: {memory_result.get('error')}")
            return {
                "success": False,
                "message": "❌ Failed to write 360 memory.",
                "error": "MEMORY_WRITE_FAILED",
                "details": memory_result.get("error"),
            }

        # Reset context_used
        old_context = execution.context_used
        execution.context_used = 0
        await db_session.commit()

        # Generate continuation prompt (canonical builder from ThinClientPromptGenerator)
        continuation_prompt = build_continuation_prompt(
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
                    tenant_key=tenant_key,
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
        except (RuntimeError, ValueError) as ws_error:
            logger.warning(f"WebSocket broadcast failed: {ws_error}")

        return {
            "success": True,
            "message": f"✅ Session handed over. Context reset from {old_context} to 0 tokens.",
            "launch_prompt": continuation_prompt,
            "memory_entry_id": memory_result.get("entry_id"),
            "context_reset": True,
        }

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Failed to execute handover: {e}", exc_info=True)
        return {
            "success": False,
            "message": "❌ Failed to execute handover. Please try again.",
            "error": "DATABASE_ERROR",
            "details": str(e),
        }


async def _get_active_orchestrator(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: Optional[str],
) -> Optional[AgentExecution]:
    """
    Get active orchestrator execution for project/tenant.

    Returns the AgentExecution representing the current orchestrator
    (agent_display_name='orchestrator', status='working').
    """
    stmt = select(AgentExecution).where(
        AgentExecution.tenant_key == tenant_key,
        AgentExecution.agent_display_name == "orchestrator",
        AgentExecution.status == "working",
    )

    if project_id:
        stmt = stmt.join(AgentJob, AgentExecution.job_id == AgentJob.job_id).where(AgentJob.project_id == project_id)

    stmt = stmt.order_by(AgentExecution.started_at.desc()).limit(1)

    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()
