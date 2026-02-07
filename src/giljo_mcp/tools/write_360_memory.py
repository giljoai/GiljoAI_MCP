"""
Write 360 Memory Tool (Handover 0412, updated 0390c, 0431)

Allows agents to write 360 memory entries during handovers or project completion.
Similar to close_project_and_update_memory but more flexible for agent usage.

Phase 2 (0390c): Updated to write to product_memory_entries table instead of JSONB array.

Handover 0431: Added pre-closeout verification protocol.
- Blocks closeout when agents have unfinished work
- Checks: status, unread messages, incomplete todos
- Returns CLOSEOUT_BLOCKED with actionable blocker details
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from inspect import iscoroutine
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

logger = logging.getLogger(__name__)

# Field length constraints
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100

# Statuses to skip during verification (they don't block closeout)
SKIP_STATUSES = {"decommissioned", "cancelled", "failed"}

async def _check_closeout_readiness(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
    orchestrator_job_id: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Verify all agents are ready for project closeout (Handover 0431).

    Checks:
    1. All agents have status == 'complete' (excluding orchestrator, decommissioned, cancelled)
    2. All agents have messages_waiting_count == 0
    3. All agents have all AgentTodoItem.status == 'completed'
    4. Orchestrator's own todos are completed (if orchestrator_job_id provided)

    Args:
        session: Active database session
        project_id: Project UUID being closed
        tenant_key: Tenant isolation key
        orchestrator_job_id: Job ID of orchestrator calling closeout (for todo check)

    Returns:
        Tuple of (is_ready, result_data) where:
        - is_ready: True if all checks pass, False if blockers found
        - result_data: Contains blockers list and summary if blocked,
                       or verified dict if ready
    """
    blockers: list[dict[str, Any]] = []
    summary = {
        "agents_checked": 0,
        "still_working": 0,
        "agents_with_unread": 0,
        "agents_with_incomplete_todos": 0,
        "orchestrator_incomplete_todos": 0,
    }

    # Get all agent executions for this project (excluding orchestrator)
    # Join with jobs to get project_id relationship
    executions_stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.project_id == project_id,
            AgentExecution.tenant_key == tenant_key,
        )
    )
    executions_result = await session.execute(executions_stmt)
    executions = executions_result.scalars().all()

    # Filter to exclude orchestrator (check by job_id) and skip statuses
    for execution in executions:
        # Skip the orchestrator itself
        if orchestrator_job_id and execution.job_id == orchestrator_job_id:
            continue

        # Skip decommissioned, cancelled, failed agents
        if execution.status in SKIP_STATUSES:
            continue

        summary["agents_checked"] += 1

        # Check 1: Agent status must be 'complete'
        if execution.status != "complete":
            summary["still_working"] += 1
            blockers.append(
                {
                    "job_id": execution.job_id,
                    "agent_id": execution.agent_id,
                    "agent_name": execution.agent_name or execution.agent_display_name,
                    "issue_type": "still_working",
                    "status": execution.status,
                }
            )
            continue  # Don't check further issues for this agent

        # Check 2: No unread messages
        if execution.messages_waiting_count > 0:
            summary["agents_with_unread"] += 1
            blockers.append(
                {
                    "job_id": execution.job_id,
                    "agent_id": execution.agent_id,
                    "agent_name": execution.agent_name or execution.agent_display_name,
                    "issue_type": "unread_messages",
                    "messages_waiting": execution.messages_waiting_count,
                }
            )

        # Check 3: All todos completed
        incomplete_todos_stmt = select(AgentTodoItem).where(
            AgentTodoItem.job_id == execution.job_id,
            AgentTodoItem.tenant_key == tenant_key,
            AgentTodoItem.status.in_(["pending", "in_progress"]),
        )
        incomplete_todos_result = await session.execute(incomplete_todos_stmt)
        incomplete_todos = incomplete_todos_result.scalars().all()

        if incomplete_todos:
            pending_count = sum(1 for t in incomplete_todos if t.status == "pending")
            in_progress_count = sum(1 for t in incomplete_todos if t.status == "in_progress")
            summary["agents_with_incomplete_todos"] += 1
            blockers.append(
                {
                    "job_id": execution.job_id,
                    "agent_id": execution.agent_id,
                    "agent_name": execution.agent_name or execution.agent_display_name,
                    "issue_type": "incomplete_todos",
                    "pending_count": pending_count,
                    "in_progress_count": in_progress_count,
                    "incomplete_items": [t.content for t in incomplete_todos],
                }
            )

    # Check 4: Orchestrator's own todos (if orchestrator_job_id provided)
    if orchestrator_job_id:
        orch_incomplete_stmt = select(AgentTodoItem).where(
            AgentTodoItem.job_id == orchestrator_job_id,
            AgentTodoItem.tenant_key == tenant_key,
            AgentTodoItem.status.in_(["pending", "in_progress"]),
        )
        orch_incomplete_result = await session.execute(orch_incomplete_stmt)
        orch_incomplete = orch_incomplete_result.scalars().all()

        if orch_incomplete:
            pending_count = sum(1 for t in orch_incomplete if t.status == "pending")
            in_progress_count = sum(1 for t in orch_incomplete if t.status == "in_progress")
            summary["orchestrator_incomplete_todos"] = len(orch_incomplete)
            blockers.append(
                {
                    "job_id": orchestrator_job_id,
                    "issue_type": "orchestrator_incomplete_todos",
                    "pending_count": pending_count,
                    "in_progress_count": in_progress_count,
                    "incomplete_items": [t.content for t in orch_incomplete],
                }
            )

    # Return results
    if blockers:
        return False, {
            "blockers": blockers,
            "summary": summary,
            "message": f"Closeout blocked: {len(blockers)} unresolved blocker(s) found",
            "action_required": "Resolve all blockers before closeout. Use report_error() if unable to resolve.",
        }

    return True, {
        "verified": {
            "all_complete": True,
            "all_messages_read": True,
            "all_todos_done": True,
            "agents_checked": summary["agents_checked"],
        }
    }

async def write_360_memory(
    project_id: str,
    tenant_key: str,
    summary: str,
    key_outcomes: list[str],
    decisions_made: list[str],
    entry_type: str = "project_completion",
    author_job_id: str | None = None,
    db_manager: DatabaseManager | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Write a 360 memory entry for project completion or handover.

    This tool allows agents to create entries in the product_memory_entries table
    during handovers or at project completion.

    Args:
        project_id: UUID of the project
        tenant_key: Tenant isolation key
        summary: 2-3 paragraph summary of work accomplished
        key_outcomes: 3-5 specific achievements
        decisions_made: 3-5 architectural/design decisions
        entry_type: Type of entry ("project_completion", "handover_closeout", or "session_handover")
        author_job_id: Job ID of agent writing entry (optional)
        db_manager: Database manager (dependency injection)
        session: Optional existing session

    Returns:
        Success/error dictionary with sequence number and entry_id
    """
    if not project_id:
        return {"success": False, "error": "project_id is required"}

    if not summary or not summary.strip():
        return {"success": False, "error": "summary is required"}

    if db_manager is None:
        return {"success": False, "error": "db_manager is required"}

    if len(summary) > MAX_SUMMARY_LENGTH:
        return {
            "success": False,
            "error": f"Summary too long (max {MAX_SUMMARY_LENGTH} characters)",
        }

    key_outcomes = key_outcomes or []
    decisions_made = decisions_made or []

    if len(key_outcomes) > MAX_KEY_OUTCOMES:
        logger.warning(
            f"Truncating key_outcomes from {len(key_outcomes)} to {MAX_KEY_OUTCOMES}",
            extra={"project_id": project_id},
        )
        key_outcomes = key_outcomes[:MAX_KEY_OUTCOMES]

    if len(decisions_made) > MAX_DECISIONS_MADE:
        logger.warning(
            f"Truncating decisions_made from {len(decisions_made)} to {MAX_DECISIONS_MADE}",
            extra={"project_id": project_id},
        )
        decisions_made = decisions_made[:MAX_DECISIONS_MADE]

    # Validate entry_type
    VALID_ENTRY_TYPES = {"project_completion", "handover_closeout", "session_handover"}
    if entry_type not in VALID_ENTRY_TYPES:
        return {
            "success": False,
            "error": f"Invalid entry_type '{entry_type}'. Must be one of: {VALID_ENTRY_TYPES}",
        }

    try:
        owns_session = session is None

        @asynccontextmanager
        async def _provided_session(existing_session: AsyncSession):
            yield existing_session

        session_ctx = db_manager.get_session_async() if owns_session else _provided_session(session)

        async with session_ctx as active_session:
            # Get project with tenant isolation
            project_stmt = select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
            project_result = await active_session.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            if iscoroutine(project):
                project = await project

            if not project:
                return {"success": False, "error": "Project not found or unauthorized for tenant"}

            if getattr(project, "tenant_key", None) != tenant_key:
                return {"success": False, "error": "Project not found or unauthorized for tenant"}

            if not project.product_id:
                return {"success": False, "error": "Project not associated with product"}

            # Get product with tenant isolation
            product_stmt = select(Product).where(
                Product.id == project.product_id,
                Product.tenant_key == tenant_key,
            )
            product_result = await active_session.execute(product_stmt)
            product = product_result.scalar_one_or_none()
            if iscoroutine(product):
                product = await product

            if not product:
                return {"success": False, "error": "Product not found for project"}

            # Handover 0431: Pre-closeout verification (only when author_job_id provided)
            # This ensures all agents are ready before allowing project closeout
            if author_job_id:
                is_ready, verification_result = await _check_closeout_readiness(
                    session=active_session,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    orchestrator_job_id=author_job_id,
                )

                if not is_ready:
                    logger.warning(
                        f"Closeout blocked for project {project_id}: "
                        f"{len(verification_result.get('blockers', []))} blocker(s) found",
                        extra={"project_id": project_id, "tenant_key": tenant_key},
                    )
                    return {
                        "success": False,
                        "error": "CLOSEOUT_BLOCKED",
                        **verification_result,
                    }

            # Get or initialize product_memory for git config
            product_memory: dict[str, Any] = product.product_memory or {}
            if not isinstance(product_memory, dict):
                product_memory = {}

            # Get git configuration and fetch commits if enabled
            git_config = _get_git_config(product_memory)
            git_commits: list[dict[str, Any | None]] = None

            if git_config.get("enabled") and git_config.get("repo_name") and git_config.get("repo_owner"):
                git_commits = await _fetch_github_commits(
                    repo_name=git_config.get("repo_name"),
                    repo_owner=git_config.get("repo_owner"),
                    access_token=git_config.get("access_token"),
                    project_created_at=project.created_at,
                    project_completed_at=project.completed_at or datetime.utcnow(),
                )

            if git_commits is None:
                git_commits = []

            # Initialize repository
            repo = ProductMemoryRepository()

            # Get next sequence number atomically
            sequence_number = await repo.get_next_sequence(
                session=active_session,
                product_id=UUID(product.id),
            )

            # Get author information if job_id provided
            author_name = None
            author_type = None
            if author_job_id:
                # Query the current execution for this job to get agent_name
                execution_stmt = (
                    select(AgentExecution)
                    .options(joinedload(AgentExecution.job))
                    .where(
                        AgentExecution.job_id == author_job_id,
                        AgentExecution.tenant_key == tenant_key,
                    )
                    .order_by(AgentExecution.started_at.desc())
                    .limit(1)
                )
                execution_result = await active_session.execute(execution_stmt)
                execution = execution_result.scalar_one_or_none()
                if execution:
                    author_name = execution.agent_name or execution.agent_display_name
                    author_type = execution.job.job_type if execution.job else None

            # Create entry in product_memory_entries table
            entry = await repo.create_entry(
                session=active_session,
                tenant_key=tenant_key,
                product_id=UUID(product.id),
                project_id=UUID(project_id),
                sequence=sequence_number,
                entry_type=entry_type,
                source="write_360_memory_v1",
                timestamp=datetime.utcnow(),
                project_name=project.name,
                summary=summary,
                key_outcomes=key_outcomes,
                decisions_made=decisions_made,
                git_commits=git_commits,
                author_job_id=UUID(author_job_id) if author_job_id else None,
                author_name=author_name,
                author_type=author_type,
            )

            if owns_session:
                await active_session.commit()

            logger.info(
                f"Wrote 360 Memory entry {entry.id} for product {product.id} "
                f"(sequence: {sequence_number}, type: {entry_type}, commits: {len(git_commits)})"
            )

            # Emit WebSocket event (Handover 0390c Phase 4)
            await _emit_websocket_event(
                event_type="product:memory:updated",
                tenant_key=tenant_key,
                product_id=str(product.id),
                data={"entry": entry.to_dict()},
            )

            # Build success response with optional verification details
            result = {
                "success": True,
                "sequence_number": sequence_number,
                "entry_id": str(entry.id),
                "git_commits_count": len(git_commits),
                "entry_type": entry_type,
                "message": "360 Memory entry written successfully",
            }

            # Include verification details if author_job_id was provided (Handover 0431)
            if author_job_id:
                # Re-run verification to get the summary counts for the response
                # (we know it passed at this point, so just get the verified dict)
                _, verification_result = await _check_closeout_readiness(
                    session=active_session,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    orchestrator_job_id=author_job_id,
                )
                result["verified"] = verification_result.get(
                    "verified",
                    {
                        "all_complete": True,
                        "all_messages_read": True,
                        "all_todos_done": True,
                    },
                )

            return result

    except (RuntimeError, ValueError, KeyError) as exc:
        logger.exception("Failed to write 360 memory entry", extra={"error": str(exc)})
        return {"success": False, "error": str(exc)}

async def _emit_websocket_event(
    event_type: str,
    tenant_key: str,
    product_id: str,
    data: dict[str, Any],
) -> None:
    """
    Emit WebSocket event; graceful no-op if manager unavailable.

    Args:
        event_type: Event type (e.g., "product:memory:updated")
        tenant_key: Tenant isolation key
        product_id: Product UUID
        data: Event payload data

    Side Effects:
        - Broadcasts event to tenant WebSocket clients
        - Logs warning if WebSocket fails (doesn't crash operation)
    """
    try:
        # Import app to access websocket manager from app state
        from api.app import app

        websocket_manager = getattr(app.state, "websocket_manager", None)

        if websocket_manager:
            await websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type=event_type,
                data={"product_id": product_id, **data},
            )
    except (RuntimeError, ValueError, KeyError) as exc:
        logger.warning(f"WebSocket emit failed for {event_type}: {exc}")

def _get_git_config(product_memory: dict[str, Any]) -> dict[str, Any]:
    """Normalize git integration configuration."""
    if not isinstance(product_memory, dict):
        return {}
    git_cfg = product_memory.get("git_integration") or product_memory.get("github") or {}
    return git_cfg if isinstance(git_cfg, dict) else {}

async def _fetch_github_commits(
    repo_name: str | None,
    repo_owner: str | None,
    access_token: str | None,
    project_created_at: datetime,
    project_completed_at: datetime | None,
) -> list[dict[str, Any | None]]:
    """
    Fetch GitHub commits between project creation and completion.

    Returns simplified commit dictionaries or None on failure/disabled config.
    """
    if not repo_name or not repo_owner:
        logger.info("GitHub integration not configured (missing repo details)")
        return None

    try:
        import httpx

        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits"
        params = {}
        if project_created_at:
            params["since"] = project_created_at.isoformat()
        if project_completed_at:
            params["until"] = project_completed_at.isoformat()

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GiljoAI-MCP",
        }
        if access_token:
            headers["Authorization"] = f"token {access_token}"

        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, params=params, headers=headers, timeout=10.0)
            if response.status_code != 200:
                logger.warning(
                    f"GitHub API returned {response.status_code}: {response.text[:200]}",
                    extra={"repo": f"{repo_owner}/{repo_name}"},
                )
                return None

            commits_data = response.json()
            commits: list[dict[str, Any]] = []
            for commit in commits_data[:100]:
                commits.append(
                    {
                        "sha": commit.get("sha"),
                        "message": commit.get("commit", {}).get("message"),
                        "author": commit.get("commit", {}).get("author", {}).get("name")
                        if isinstance(commit.get("commit", {}).get("author"), dict)
                        else commit.get("commit", {}).get("author"),
                        "date": commit.get("commit", {}).get("author", {}).get("date")
                        if isinstance(commit.get("commit", {}).get("author"), dict)
                        else None,
                        "url": commit.get("html_url"),
                        "files_changed": commit.get("files_changed"),
                        "lines_added": commit.get("lines_added") or commit.get("stats", {}).get("additions")
                        if isinstance(commit.get("stats"), dict)
                        else None,
                    }
                )

            logger.info(f"Fetched {len(commits)} GitHub commits for {repo_owner}/{repo_name}")
            return commits

    except (RuntimeError, ValueError, KeyError) as exc:
        logger.exception("Failed to fetch GitHub commits", extra={"error": str(exc)})
        return None
