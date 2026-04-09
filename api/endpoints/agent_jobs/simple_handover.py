# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Simple Handover Endpoint - Handover 0461c (Updated: Two-Stage Retirement Flow)

Two-stage orchestrator session refresh:
1. Returns retirement_prompt (old orchestrator writes 360 Memory with rich context)
2. Returns continuation_prompt (new terminal picks up where old left off)

The OLD orchestrator writes 360 Memory via MCP tools (not this endpoint),
because only the orchestrator has the actual session context (decisions, progress, blockers).

No more Agent ID Swap. No new AgentExecution rows. Same UUID, same card.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.thin_prompt_generator import build_continuation_prompt, build_retirement_prompt

logger = logging.getLogger(__name__)
router = APIRouter()


class SimpleHandoverResponse(BaseModel):
    """Response model for simple session handover."""

    success: bool = Field(..., description="Whether handover succeeded")
    retirement_prompt: str = Field(..., description="Prompt for old orchestrator to write 360 Memory")
    continuation_prompt: str = Field(..., description="Prompt for new terminal to continue work")
    context_reset: bool = Field(..., description="Whether context was reset")


@router.post(
    "/{job_id}/simple-handover",
    response_model=SimpleHandoverResponse,
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
    Two-stage session handover: Returns retirement + continuation prompts.

    Stage 1 (retirement_prompt): User pastes in OLD terminal -> orchestrator writes
    rich 360 Memory via MCP tools (captures actual session context, not just DB stats).

    Stage 2 (continuation_prompt): User pastes in NEW terminal -> orchestrator reads
    360 Memory and continues work with same UUID/identity.

    Does NOT write 360 Memory server-side (the orchestrator does that with full context).
    Does NOT create new AgentExecution rows. Same UUID, same card.

    Args:
        job_id: Orchestrator job_id or agent_id
        current_user: Authenticated user
        db: Database session

    Returns:
        {
            "success": True,
            "retirement_prompt": "...",
            "continuation_prompt": "...",
            "context_reset": True
        }
    """
    # Find execution (job_id could be agent_id)
    stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.agent_id == job_id,
            AgentExecution.tenant_key == current_user.tenant_key,
        )
        .order_by(AgentExecution.started_at.desc())
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
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        execution = result.scalars().first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.agent_display_name != "orchestrator":
        raise HTTPException(status_code=400, detail="Only orchestrators can use handover")

    # Get job for project_id (tenant-scoped for defense-in-depth)
    stmt = select(AgentJob).where(
        AgentJob.job_id == execution.job_id,
        AgentJob.tenant_key == current_user.tenant_key,
    )
    result = await db.execute(stmt)
    job = result.scalars().first()

    if not job:
        raise HTTPException(status_code=500, detail="Job not found")

    # Load project + product for git closeout commit gating
    project_stmt = (
        select(Project)
        .options(joinedload(Project.product), joinedload(Project.project_type))
        .where(Project.id == job.project_id, Project.tenant_key == current_user.tenant_key)
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    git_enabled = False
    project_taxonomy = ""
    if project and project.product and getattr(project.product, "product_memory", None):
        git_config = project.product.product_memory.get("git_integration", {})
        # Require BOTH: git integration enabled AND git_history toggle enabled
        # Handover 0840d: Check git_history toggle from user_field_priorities table
        from sqlalchemy import select as sa_select

        from src.giljo_mcp.models.auth import UserFieldPriority

        prio_result = await db.execute(
            sa_select(UserFieldPriority).where(
                UserFieldPriority.user_id == current_user.id,
                UserFieldPriority.tenant_key == current_user.tenant_key,
                UserFieldPriority.category == "git_history",
            )
        )
        prio_row = prio_result.scalar_one_or_none()
        git_history_enabled = prio_row.enabled if prio_row else False
        git_enabled = git_config.get("enabled", False) and git_history_enabled
        project_taxonomy = project.taxonomy_alias

    await db.commit()

    # Generate retirement prompt (old orchestrator writes 360 Memory)
    retirement_prompt = build_retirement_prompt(
        project_id=str(job.project_id),
        agent_id=execution.agent_id,
        job_id=execution.job_id,
        project_name=project.name if project else None,
        git_enabled=git_enabled,
        project_taxonomy=project_taxonomy,
    )

    # Generate continuation prompt (new terminal reads 360 Memory)
    continuation_prompt = build_continuation_prompt(
        project_id=str(job.project_id),
        agent_id=execution.agent_id,
        job_id=execution.job_id,
        project_name=project.name if project else None,
        product_id=str(project.product_id) if project and project.product_id else None,
    )

    # Emit WebSocket event
    try:
        from api.app import app

        websocket_manager = getattr(app.state, "websocket_manager", None)
        if websocket_manager:
            await websocket_manager.broadcast_to_tenant(
                tenant_key=current_user.tenant_key,
                event_type="orchestrator:handover_initiated",
                data={
                    "agent_id": execution.agent_id,
                    "job_id": execution.job_id,
                    "project_id": str(job.project_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
        logger.warning(f"WebSocket broadcast failed: {ws_error}")

    return SimpleHandoverResponse(
        success=True,
        retirement_prompt=retirement_prompt,
        continuation_prompt=continuation_prompt,
        context_reset=True,
    )
