# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Project Closeout MCP Tool (Handover 013B - Refactored)

Handles project completion and updates product memory with sequential history entries.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from inspect import iscoroutine
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ProjectStateError, ResourceNotFoundError, ValidationError
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

# Statuses that do not block closeout (aligned with write_360_memory.SKIP_STATUSES)
# Handover 0435b: 'closed' agents are already final-accepted, skip them too
_SKIP_STATUSES = {"decommissioned", "closed"}
# Statuses considered "active" — agents not yet finished
_ACTIVE_STATUSES = {"waiting", "working", "blocked", "silent"}


async def _fetch_project_and_product(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
) -> tuple[Any, Any]:
    """
    Fetch the Project and its associated Product from the database.

    Both queries are filtered by tenant_key for tenant isolation. Raises
    ResourceNotFoundError if either record is missing or belongs to a
    different tenant. Raises ValidationError when the project has no
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


async def _handle_force_close(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
    force: bool,
    blockers: list,
) -> None:
    """
    Handle force-close path: guard against orchestrator self-decommission, then decommission agents.

    When force=True and agents are still active, checks that the calling orchestrator
    is not among them (raising ProjectStateError if so), then calls
    _force_decommission_agents to set all remaining active agents to 'decommissioned'.
    Does nothing when force=False or when all agents are already ready.

    Args:
        session: Active database session.
        project_id: Project UUID being closed.
        tenant_key: Tenant isolation key.
        force: Whether force-close was requested by the caller.
        blockers: List of blocker dicts from _check_agent_readiness; empty means no action needed.
    """
    if not blockers or not force:
        return

    orch_stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            and_(
                AgentJob.project_id == project_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.status.in_(_ACTIVE_STATUSES),
            )
        )
    )
    orch_result = await session.execute(orch_stmt)
    active_orchestrator = orch_result.scalar_one_or_none()

    if active_orchestrator:
        raise ProjectStateError(
            "Cannot force-close: orchestrator is still active and would be decommissioned",
            context={
                "status": "ORCHESTRATOR_SELF_DECOMMISSION_BLOCKED",
                "message": (
                    "force=true will decommission ALL active agents including the orchestrator. "
                    "Complete your own job first, then the project will close cleanly."
                ),
                "required_sequence": [
                    f"1. complete_job(job_id='{active_orchestrator.job_id}') -- complete yourself first",
                    "2. write_360_memory(...) -- write memory entry (if not already written)",
                    "3. close_project_and_update_memory(force=false) -- should now pass since all agents are complete",
                ],
                "hint": "Or use write_360_memory() + complete_job() and let the frontend handle project archival.",
            },
        )

    decommissioned = await _force_decommission_agents(session, project_id, tenant_key)
    if decommissioned:
        logger.warning(
            "Force-closed project %s: auto-decommissioned %d agent(s): %s",
            project_id,
            len(decommissioned),
            ", ".join(decommissioned),
        )


async def close_project_and_update_memory(
    project_id: str,
    summary: str,
    key_outcomes: list[str],
    decisions_made: list[str],
    tenant_key: str,
    db_manager: DatabaseManager | None = None,
    session: AsyncSession | None = None,
    force: bool = False,
    git_commits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Close project and update product memory with history entry.

    Adds a rich entry to the product_memory_entries table.

    When force=False (default), verifies all agents are complete before
    proceeding. Returns CLOSEOUT_BLOCKED with blocker details if any agents
    are still active, have unread messages, or have incomplete TODOs.

    When force=True, auto-decommissions any remaining active agents before
    closing, and logs a warning with the affected agents.

    Args:
        git_commits: Agent-supplied commits from local git log. When provided,
            skips the GitHub API fetch entirely (passive server model).
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

    try:
        owns_session = session is None

        @asynccontextmanager
        async def _provided_session(existing_session: AsyncSession):
            yield existing_session

        session_ctx = db_manager.get_session_async() if owns_session else _provided_session(session)

        async with session_ctx as active_session:
            project, product = await _fetch_project_and_product(
                session=active_session,
                project_id=project_id,
                tenant_key=tenant_key,
            )

            # Closeout readiness gate: verify all agents are finished
            is_ready, blockers = await _check_agent_readiness(active_session, project_id, tenant_key)

            if not is_ready and not force:
                raise ProjectStateError(
                    "Cannot close project: agents have unfinished work",
                    context={
                        "status": "CLOSEOUT_BLOCKED",
                        "blockers": blockers,
                        "hint": "Resolve all blockers or pass force=true to auto-decommission remaining agents.",
                    },
                )

            # Handover 0824: force-close guard + agent decommission
            await _handle_force_close(
                session=active_session,
                project_id=project_id,
                tenant_key=tenant_key,
                force=force,
                blockers=blockers,
            )

            # Handover 0435b: transition all 'complete' agents to 'closed' during closeout
            await _close_completed_agents(active_session, project_id, tenant_key)

            product_memory: dict[str, Any] = product.product_memory or {}
            if not isinstance(product_memory, dict):
                product_memory = {}

            # Use agent-supplied commits (passive server); fall back to GitHub API
            if git_commits is not None:
                logger.info(
                    "Using %d agent-supplied git commits for project %s",
                    len(git_commits),
                    project_id,
                )
            else:
                git_config = _get_git_config(product_memory)
                if git_config.get("enabled") and git_config.get("repo_name") and git_config.get("repo_owner"):
                    git_commits = await _fetch_github_commits(
                        repo_name=git_config.get("repo_name"),
                        repo_owner=git_config.get("repo_owner"),
                        access_token=git_config.get("access_token"),
                        project_created_at=project.created_at,
                        project_completed_at=project.completed_at or datetime.now(timezone.utc),
                    )

            if git_commits is None:
                git_commits = []

            # Use repository for atomic sequence generation and entry creation
            repo = ProductMemoryRepository()
            sequence_number = await repo.get_next_sequence(session=active_session, product_id=product.id)

            deliverables = _extract_deliverables(key_outcomes)
            tags = _extract_tags(summary, key_outcomes, decisions_made)
            priority = _derive_priority(project, summary, key_outcomes)
            significance_score = _calculate_significance(project, key_outcomes, git_commits)
            token_estimate = _estimate_tokens(summary, key_outcomes, decisions_made)
            metrics = _build_metrics(git_commits)

            # Create entry in product_memory_entries table
            entry = await repo.create_entry(
                session=active_session,
                tenant_key=tenant_key,
                product_id=product.id,
                project_id=project.id,
                sequence=sequence_number,
                entry_type="project_closeout",
                source="closeout_v1",
                timestamp=datetime.now(timezone.utc),
                project_name=project.name,
                summary=summary,
                key_outcomes=key_outcomes,
                decisions_made=decisions_made,
                git_commits=git_commits,
                deliverables=deliverables,
                metrics=metrics,
                priority=priority,
                significance_score=significance_score,
                token_estimate=token_estimate,
                tags=tags,
            )

            if owns_session:
                await active_session.commit()

            logger.info(
                f"Updated 360 Memory for product {product.id} "
                f"(entry: {entry.id}, sequence: {sequence_number}, commits: {len(git_commits) if git_commits else 0})"
            )

            # Emit WebSocket event (Handover 0390c Phase 4)
            await emit_websocket_event(
                event_type="product:memory:updated",
                tenant_key=tenant_key,
                product_id=str(product.id),
                data={"entry": entry.to_dict()},
            )

            return {
                "entry_id": str(entry.id),
                "sequence_number": sequence_number,
                "git_commits_count": len(git_commits),
                "message": "Project closed and 360 Memory updated successfully",
            }

    except Exception as exc:  # Broad catch: tool boundary, logs and re-raises
        logger.exception("Failed to close project and update memory", extra={"error": str(exc)})
        raise


async def _check_agent_readiness(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Check whether all agents in the project are ready for closeout.

    Returns (is_ready, blockers) where blockers is a list of dicts
    describing each non-complete agent with issue_type, todo details,
    suggested_action, and a trailing summary entry.
    """
    exec_stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            and_(
                AgentJob.project_id == project_id,
                AgentExecution.tenant_key == tenant_key,
            )
        )
    )
    result = await session.execute(exec_stmt)
    executions = result.scalars().all()

    blockers: list[dict[str, Any]] = []
    summary = {
        "agents_checked": 0,
        "still_working": 0,
        "with_unread_messages": 0,
        "with_incomplete_todos": 0,
    }

    for execution in executions:
        if execution.status in _SKIP_STATUSES:
            continue
        summary["agents_checked"] += 1
        if execution.status == "complete":
            continue

        # Agent is not complete — it's blocking closeout
        agent_id = execution.agent_id
        agent_name = execution.agent_name or execution.agent_display_name
        job_id = execution.job_id
        messages_waiting = execution.messages_waiting_count or 0

        summary["still_working"] += 1
        if messages_waiting > 0:
            summary["with_unread_messages"] += 1

        # Query incomplete todos
        incomplete_stmt = select(AgentTodoItem).where(
            AgentTodoItem.job_id == job_id,
            AgentTodoItem.tenant_key == tenant_key,
            AgentTodoItem.status.in_(["pending", "in_progress"]),
        )
        incomplete_result = await session.execute(incomplete_stmt)
        incomplete_todos = incomplete_result.scalars().all()
        incomplete_count = len(incomplete_todos)
        incomplete_names = [t.content for t in incomplete_todos[:5]]
        if incomplete_count > 0:
            summary["with_incomplete_todos"] += 1

        # Build suggested_action with all relevant remediation steps
        steps = []
        if messages_waiting > 0:
            steps.append(f"Drain {messages_waiting} unread messages via receive_messages(agent_id='{agent_id}')")
        if incomplete_count > 0:
            steps.append(
                f"Update {incomplete_count} incomplete TODOs via "
                f"report_progress(job_id='{job_id}', todo_items=[...]) "
                f"marking as completed/skipped"
            )
        steps.append(f"Force-complete via complete_job(job_id='{job_id}')")
        suggested_action = ". ".join(steps) + "."

        blockers.append(
            {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "status": execution.status,
                "job_id": job_id,
                "issue_type": "still_working",
                "messages_waiting": messages_waiting,
                "incomplete_todo_count": incomplete_count,
                "incomplete_todo_names": incomplete_names,
                "suggested_action": suggested_action,
            }
        )

    if blockers:
        blockers.append({"_summary": summary})

    return (len(blockers) == 0, blockers)


async def _force_decommission_agents(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
) -> list[str]:
    """
    Decommission all active agents for project closeout.

    Sets execution status to 'decommissioned' for any still-active agents.
    Returns list of agent display names that were decommissioned.
    """
    exec_stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            and_(
                AgentJob.project_id == project_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status.in_(_ACTIVE_STATUSES),
            )
        )
    )
    result = await session.execute(exec_stmt)
    executions = result.scalars().all()

    decommissioned_names: list[str] = []
    for execution in executions:
        execution.status = "decommissioned"
        decommissioned_names.append(execution.agent_display_name or execution.agent_name or execution.agent_id)

    if decommissioned_names:
        await session.flush()

    return decommissioned_names


async def _close_completed_agents(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
) -> list[str]:
    """
    Transition all 'complete' agents to 'closed' during project closeout (Handover 0435b).

    Normal closeout = accepted work. Agents in 'complete' become 'closed' (final acceptance).
    Only agents in abnormal states get 'decommissioned' via _force_decommission_agents.

    Returns list of agent display names that were closed.
    """
    exec_stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            and_(
                AgentJob.project_id == project_id,
                AgentExecution.tenant_key == tenant_key,
                AgentExecution.status == "complete",
            )
        )
    )
    result = await session.execute(exec_stmt)
    executions = result.scalars().all()

    closed_names: list[str] = []
    for execution in executions:
        execution.status = "closed"
        closed_names.append(execution.agent_display_name or execution.agent_name or execution.agent_id)

    if closed_names:
        await session.flush()
        logger.info("Closed %d agent(s) during project closeout: %s", len(closed_names), ", ".join(closed_names))

    return closed_names


def _extract_deliverables(key_outcomes: list[str]) -> list[str]:
    """Derive deliverables from key outcomes (deduplicated)."""
    seen = set()
    deliverables: list[str] = []
    for outcome in key_outcomes or []:
        normalized = (outcome or "").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deliverables.append(normalized)
    return deliverables


def _extract_tags(summary: str, key_outcomes: list[str], decisions_made: list[str]) -> list[str]:
    """Extract lightweight tags from summary/outcomes/decisions."""
    tokens = (summary or "").split()
    for item in key_outcomes or []:
        tokens.extend((item or "").split())
    for decision in decisions_made or []:
        tokens.extend((decision or "").split())

    cleaned = []
    for token in tokens:
        t = token.strip(".,;:-").lower()
        if len(t) > 3:
            cleaned.append(t)

    tags = []
    for token in cleaned:
        if token not in tags:
            tags.append(token)
    return tags[:10]


def _derive_priority(project: Project, summary: str, key_outcomes: list[str]) -> int:
    """Derive memory entry importance (1=HIGH, 2=MEDIUM, 3=LOW)."""
    summary_text = summary.lower() if summary else ""
    outcome_text = " ".join(key_outcomes or []).lower()
    if any(word in summary_text or word in outcome_text for word in ["incident", "outage", "rollback", "failure"]):
        return 1
    if key_outcomes:
        return 2
    return 3


def _calculate_significance(project: Project, key_outcomes: list[str], git_commits: list[dict[str, Any]]) -> float:
    """Calculate significance score between 0.0 and 1.0."""
    outcome_factor = min(len(key_outcomes or []), 5) * 0.1
    commit_factor = min(len(git_commits or []), 20) * 0.01
    base = 0.3 + outcome_factor + commit_factor
    return round(min(1.0, base), 2)


def _estimate_tokens(summary: str, key_outcomes: list[str], decisions_made: list[str]) -> int:
    """Rough token estimate based on content length."""
    lengths = [len(summary or "")]
    lengths.extend(len(item or "") for item in key_outcomes or [])
    lengths.extend(len(item or "") for item in decisions_made or [])
    estimate = sum(lengths) // 4
    return max(estimate, 1)


def _count_files_changed(git_commits: list[dict[str, Any]]) -> int:
    """Count files changed across commits."""
    total = 0
    for commit in git_commits or []:
        if not isinstance(commit, dict):
            continue
        if "files_changed" in commit:
            total += int(commit.get("files_changed") or 0)
        elif isinstance(commit.get("files"), list):
            total += len(commit["files"])
    return total


def _count_lines_added(git_commits: list[dict[str, Any]]) -> int:
    """Count lines added across commits."""
    total = 0
    for commit in git_commits or []:
        if not isinstance(commit, dict):
            continue
        if "lines_added" in commit:
            total += int(commit.get("lines_added") or 0)
        elif isinstance(commit.get("stats"), dict):
            total += int(commit["stats"].get("additions", 0))
    return total


def _build_metrics(git_commits: list[dict[str, Any]]) -> dict[str, Any]:
    """Build metrics block for history entry."""
    test_coverage = 0.0

    if git_commits:
        return {
            "commits": len(git_commits),
            "files_changed": _count_files_changed(git_commits),
            "lines_added": _count_lines_added(git_commits),
            "test_coverage": test_coverage,
        }

    return {
        "commits": 0,
        "files_changed": 0,
        "lines_added": 0,
        "test_coverage": test_coverage,
    }
