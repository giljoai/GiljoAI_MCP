"""
Slash command handler for /gil_handover
Triggers orchestrator succession (Handover 0080a)
"""

import logging
import os
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.agent_identity import AgentJob, AgentExecution
from ..orchestrator_succession import OrchestratorSuccessionManager


logger = logging.getLogger(__name__)


async def handle_gil_handover(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: Optional[str] = None,
    orchestrator_job_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Handle /gil_handover slash command

    Args:
        db_session: Database session instance
        tenant_key: Current tenant key
        project_id: Optional project ID (auto-detected if not provided)
        orchestrator_job_id: Optional explicit orchestrator job ID

    Returns:
        {
            "success": bool,
            "message": str,
            "successor_id": str,
            "launch_prompt": str,
            "handover_summary": dict
        }
    """
    succession_mgr = OrchestratorSuccessionManager(db_session, tenant_key)

    # Get current orchestrator execution (AgentExecution)
    if not orchestrator_job_id:
        orchestrator = await _get_active_orchestrator(db_session, tenant_key, project_id)
    else:
        orchestrator = await _get_active_orchestrator(
            db_session, tenant_key, project_id, job_id=orchestrator_job_id
        )

    if not orchestrator:
        return {
            "success": False,
            "message": "❌ No active orchestrator found. Only orchestrators can trigger succession.",
            "error": "NO_ORCHESTRATOR",
        }

    # Check if already handed over
    if orchestrator.status == "complete" and orchestrator.handover_to:
        return {
            "success": False,
            "message": f"❌ This orchestrator has already been handed over to Instance {orchestrator.instance_number + 1}.",
            "error": "ALREADY_HANDED_OVER",
        }

    # Check if successor already exists
    if orchestrator.handover_to:
        return {
            "success": False,
            "message": f"❌ Successor already created. Launch Instance {orchestrator.instance_number + 1} instead.",
            "error": "SUCCESSOR_EXISTS",
        }

    try:
        # Generate handover summary for current execution
        handover_summary = succession_mgr.generate_handover_summary(orchestrator)

        # Create successor execution
        successor = await succession_mgr.create_successor(
            current_execution=orchestrator,
            reason="manual",  # User-triggered via slash command
        )

        # Mark orchestrator as complete with handover
        succession_mgr.complete_handover(
            execution=orchestrator, successor=successor, handover_summary=handover_summary
        )

        await db_session.commit()

        # Generate launch prompt (job_id persists across succession)
        launch_prompt = _generate_launch_prompt(
            server_url=os.getenv("GILJO_MCP_SERVER_URL", "http://localhost:7272"),
            job_id=successor.job_id,
            project_id=orchestrator.job.project_id if isinstance(orchestrator.job, AgentJob) else None,
            handover_summary=handover_summary,
        )

        return {
            "success": True,
            "message": f"✅ Successor orchestrator created (Instance {successor.instance_number})",
            "successor_id": successor.job_id,
            "launch_prompt": launch_prompt,
            "handover_summary": handover_summary,
        }

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Failed to create successor orchestrator: {e}", exc_info=True)
        return {
            "success": False,
            "message": "❌ Failed to create successor. Please try again.",
            "error": "DATABASE_ERROR",
            "details": str(e),
        }


async def _get_active_orchestrator(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: Optional[str],
    job_id: Optional[str] = None,
) -> Optional[AgentExecution]:
    """
    Get active orchestrator execution for project/tenant.

    Returns the AgentExecution representing the current orchestrator
    (agent_display_name='orchestrator', status='working'). Optionally filters
    by job_id and/or project_id.
    """
    stmt = select(AgentExecution).where(
        and_(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.agent_display_name == "orchestrator",
            AgentExecution.status == "working",
        )
    )

    if job_id:
        stmt = stmt.where(AgentExecution.job_id == job_id)

    if project_id:
        stmt = stmt.join(AgentJob, AgentExecution.job_id == AgentJob.job_id).where(
            AgentJob.project_id == project_id
        )

    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


def _generate_launch_prompt(server_url: str, job_id: str, project_id: str, handover_summary: dict[str, Any]) -> str:
    """Generate formatted launch prompt for successor"""
    active_agents = handover_summary.get("active_agents", [])
    active_agents_count = len(active_agents)

    return f"""
export GILJO_MCP_SERVER_URL={server_url}
export GILJO_AGENT_JOB_ID={job_id}
export GILJO_PROJECT_ID={project_id}

# Handover Summary:
# Project: {handover_summary.get("project_name", "Unknown")} ({handover_summary.get("project_status", 0)}% complete)
# Active Agents: {active_agents_count} agent{"s" if active_agents_count != 1 else ""}
# Next Steps: {handover_summary.get("next_steps", "Continue project work")}

## FIRST ACTION (MANDATORY)
Verify MCP connection before proceeding:
```python
mcp__giljo-mcp__health_check()
```
Expected: {{"status": "healthy"}} - If failed, STOP and report error

## Before Decommissioning

IMPORTANT: Before marking yourself complete, call write_360_memory() with:
- project_id: {project_id}
- summary: Brief summary of your progress during this session
- key_outcomes: What you accomplished before handover
- decisions_made: Key decisions for successor to know
- entry_type: "handover_closeout"
- author_job_id: {job_id}

Then mark yourself complete via complete_job().

codex mcp add giljo-orchestrator
""".strip()
