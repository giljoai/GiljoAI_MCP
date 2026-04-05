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
from datetime import datetime, timezone
from inspect import iscoroutine
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
from src.giljo_mcp.tools._memory_helpers import (
    MAX_DECISIONS_MADE,
    MAX_KEY_OUTCOMES,
    MAX_SUMMARY_LENGTH,
    _fetch_github_commits,
    _get_git_config,
    emit_websocket_event,
)


logger = logging.getLogger(__name__)

# Statuses to skip during verification (they don't block closeout)
SKIP_STATUSES = {"decommissioned"}


async def _resolve_project_and_product(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
) -> tuple[Any, Any]:
    """
    Fetch the Project and its associated Product from the database.

    Both queries are filtered by tenant_key for isolation. Raises
    ResourceNotFoundError if either record is missing or belongs to
    a different tenant. Raises ValidationError if the project has no
    linked product.

    Returns:
        Tuple of (project, product) ORM instances.
    """
    project_stmt = select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
    project_result = await session.execute(project_stmt)
    project = project_result.scalar_one_or_none()
    if iscoroutine(project):
        project = await project

    if not project:
        raise ResourceNotFoundError("Project not found or unauthorized for tenant")

    if getattr(project, "tenant_key", None) != tenant_key:
        raise ResourceNotFoundError("Project not found or unauthorized for tenant")

    if not project.product_id:
        raise ValidationError("Project not associated with product")

    product_stmt = select(Product).where(
        Product.id == project.product_id,
        Product.tenant_key == tenant_key,
    )
    product_result = await session.execute(product_stmt)
    product = product_result.scalar_one_or_none()
    if iscoroutine(product):
        product = await product

    if not product:
        raise ResourceNotFoundError("Product not found for project")

    return project, product


async def _resolve_author_info(
    session: AsyncSession,
    author_job_id: str | None,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Resolve the display name and job type for the agent writing the entry.

    Queries the most-recent AgentExecution for author_job_id, filtered by
    tenant_key. Returns a dict with ``author_name`` and ``author_type`` keys,
    or an empty dict when no author_job_id is provided.
    """
    if not author_job_id:
        return {}

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
    execution_result = await session.execute(execution_stmt)
    execution = execution_result.scalar_one_or_none()

    if not execution:
        return {"author_name": None, "author_type": None}

    return {
        "author_name": execution.agent_name or execution.agent_display_name,
        "author_type": execution.job.job_type if execution.job else None,
    }


async def _fetch_git_commits_for_project(
    product_memory: dict[str, Any],
    project: Any,
) -> list[dict[str, Any]]:
    """
    Fetch GitHub commits for the project if git integration is configured.

    Reads git config from product_memory and calls _fetch_github_commits when
    both ``repo_name`` and ``repo_owner`` are present. Returns an empty list
    when git integration is disabled or not configured.
    """
    git_config = _get_git_config(product_memory)
    if not (git_config.get("enabled") and git_config.get("repo_name") and git_config.get("repo_owner")):
        return []

    commits = await _fetch_github_commits(
        repo_name=git_config.get("repo_name"),
        repo_owner=git_config.get("repo_owner"),
        access_token=git_config.get("access_token"),
        project_created_at=project.created_at,
        project_completed_at=project.completed_at or datetime.now(timezone.utc),
    )
    return commits or []


async def _check_and_emit_tuning_staleness(
    db_manager: DatabaseManager,
    tenant_key: str,
    product: Any,
    websocket_manager: Any = None,
) -> None:
    """
    Check whether the product's context tuning is stale and notify via WebSocket.

    Performs a lightweight integer comparison via ProductTuningService. Emits
    a ``notification:new`` WebSocket event when the product is due for a
    context review. Errors are caught and logged at DEBUG level so they never
    interrupt the calling flow.
    """
    try:
        from giljo_mcp.services.product_tuning_service import ProductTuningService

        tuning_service = ProductTuningService(
            db_manager=db_manager,
            tenant_key=tenant_key,
        )
        staleness = await tuning_service.check_tuning_staleness(
            product_id=str(product.id),
            user_id=str(product.tenant_key),
        )
        if staleness.get("is_stale"):
            await emit_websocket_event(
                event_type="notification:new",
                tenant_key=tenant_key,
                product_id=str(product.id),
                data={
                    "type": "context_tuning",
                    "title": "Context Review Suggested",
                    "message": (
                        f"{staleness['projects_since_tune']} projects completed since your last "
                        f"context review. Tune your product context?"
                    ),
                    "severity": "info",
                    "metadata": {"product_id": str(product.id), "product_name": product.name},
                },
            )
    except (RuntimeError, ValueError, KeyError, OSError) as staleness_err:
        logger.debug(f"Tuning staleness check skipped: {staleness_err}")


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
                    "suggested_action": (
                        f"Send message to agent asking for status, or drain messages via "
                        f"receive_messages(agent_id='{execution.agent_id}') and force-complete "
                        f"via complete_job(job_id='{execution.job_id}')"
                    ),
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
                    "suggested_action": (
                        f"Agent has {execution.messages_waiting_count} unread messages. "
                        f"Drain via receive_messages(agent_id='{execution.agent_id}'), "
                        f"process, then complete_job(job_id='{execution.job_id}')"
                    ),
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
            incomplete_names = [t.content for t in incomplete_todos]
            blockers.append(
                {
                    "job_id": execution.job_id,
                    "agent_id": execution.agent_id,
                    "agent_name": execution.agent_name or execution.agent_display_name,
                    "issue_type": "incomplete_todos",
                    "pending_count": pending_count,
                    "in_progress_count": in_progress_count,
                    "incomplete_items": incomplete_names,
                    "suggested_action": (
                        f"Agent has {len(incomplete_todos)} incomplete TODO items: "
                        f"{incomplete_names[:5]}. Update via "
                        f"report_progress(job_id='{execution.job_id}', todo_items=[...]) "
                        f"marking as completed, then complete_job(job_id='{execution.job_id}')"
                    ),
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
            orch_incomplete_names = [t.content for t in orch_incomplete]
            blockers.append(
                {
                    "job_id": orchestrator_job_id,
                    "issue_type": "orchestrator_incomplete_todos",
                    "pending_count": pending_count,
                    "in_progress_count": in_progress_count,
                    "incomplete_items": orch_incomplete_names,
                    "suggested_action": (
                        f"Orchestrator has {len(orch_incomplete)} incomplete TODO items: "
                        f"{orch_incomplete_names[:5]}. Update via "
                        f"report_progress(job_id='{orchestrator_job_id}', todo_items=[...]) "
                        f"marking as completed"
                    ),
                }
            )

    # Return results
    if blockers:
        return False, {
            "blockers": blockers,
            "summary": summary,
            "message": f"Closeout blocked: {len(blockers)} unresolved blocker(s) found",
            "action_required": "Resolve all blockers before closeout. Use set_agent_status(status='blocked') if unable to resolve.",
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
        raise ValidationError("project_id is required")

    if not summary or not summary.strip():
        raise ValidationError("summary is required")

    if db_manager is None:
        raise ValidationError("db_manager is required")

    if len(summary) > MAX_SUMMARY_LENGTH:
        raise ValidationError(f"Summary too long (max {MAX_SUMMARY_LENGTH} characters)")

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
    valid_entry_types = {"project_completion", "handover_closeout", "session_handover"}
    if entry_type not in valid_entry_types:
        raise ValidationError(f"Invalid entry_type '{entry_type}'. Must be one of: {valid_entry_types}")

    try:
        owns_session = session is None

        @asynccontextmanager
        async def _provided_session(existing_session: AsyncSession):
            yield existing_session

        session_ctx = db_manager.get_session_async() if owns_session else _provided_session(session)

        async with session_ctx as active_session:
            project, product = await _resolve_project_and_product(
                session=active_session,
                project_id=project_id,
                tenant_key=tenant_key,
            )

            # Handover 0431: Pre-closeout verification.
            # Only enforce readiness check for project_completion (not handover_closeout).
            # Handovers document incomplete work in 360 memory rather than requiring clean state.
            if author_job_id and entry_type == "project_completion":
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

            product_memory: dict[str, Any] = product.product_memory or {}
            if not isinstance(product_memory, dict):
                product_memory = {}

            git_commits = await _fetch_git_commits_for_project(
                product_memory=product_memory,
                project=project,
            )

            repo = ProductMemoryRepository()
            sequence_number = await repo.get_next_sequence(
                session=active_session,
                product_id=UUID(product.id),
            )

            author_info = await _resolve_author_info(
                session=active_session,
                author_job_id=author_job_id,
                tenant_key=tenant_key,
            )

            entry = await repo.create_entry(
                session=active_session,
                tenant_key=tenant_key,
                product_id=UUID(product.id),
                project_id=UUID(project_id),
                sequence=sequence_number,
                entry_type=entry_type,
                source="write_360_memory_v1",
                timestamp=datetime.now(timezone.utc),
                project_name=project.name,
                summary=summary,
                key_outcomes=key_outcomes,
                decisions_made=decisions_made,
                git_commits=git_commits,
                author_job_id=UUID(author_job_id) if author_job_id else None,
                author_name=author_info.get("author_name"),
                author_type=author_info.get("author_type"),
            )

            if owns_session:
                await active_session.commit()

            logger.info(
                f"Wrote 360 Memory entry {entry.id} for product {product.id} "
                f"(sequence: {sequence_number}, type: {entry_type}, commits: {len(git_commits)})"
            )

            await emit_websocket_event(
                event_type="product:memory:updated",
                tenant_key=tenant_key,
                product_id=str(product.id),
                data={"entry": entry.to_dict()},
            )

            # Handover 0831: Check tuning staleness after memory write.
            await _check_and_emit_tuning_staleness(
                db_manager=db_manager,
                tenant_key=tenant_key,
                product=product,
            )

            result = {
                "sequence_number": sequence_number,
                "entry_id": str(entry.id),
                "git_commits_count": len(git_commits),
                "entry_type": entry_type,
                "message": "360 Memory entry written successfully",
            }

            # Include verification details if author_job_id was provided (Handover 0431).
            if author_job_id:
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
        raise
