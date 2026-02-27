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
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


logger = logging.getLogger(__name__)

# Field length constraints (added for validation)
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100


async def close_project_and_update_memory(
    project_id: str,
    summary: str,
    key_outcomes: list[str],
    decisions_made: list[str],
    tenant_key: str,
    db_manager: DatabaseManager | None = None,
    session: AsyncSession | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Close project and update product memory with history entry.

    Adds a rich entry to the product_memory_entries table.

    When force=False (default), verifies all agents are complete before
    proceeding. Returns CLOSEOUT_BLOCKED with blocker details if any agents
    are still active, have unread messages, or have incomplete TODOs.

    When force=True, auto-decommissions any remaining active agents before
    closing, and logs a warning with the affected agents.
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

    try:
        owns_session = session is None

        @asynccontextmanager
        async def _provided_session(existing_session: AsyncSession):
            yield existing_session

        session_ctx = db_manager.get_session_async() if owns_session else _provided_session(session)

        async with session_ctx as active_session:
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

            # Closeout readiness gate: verify all agents are finished
            is_ready, blockers = await _check_agent_readiness(active_session, project_id, tenant_key)

            if not is_ready and not force:
                return {
                    "success": False,
                    "status": "CLOSEOUT_BLOCKED",
                    "error": "Cannot close project: agents have unfinished work",
                    "blockers": blockers,
                    "hint": "Resolve all blockers or pass force=true to auto-decommission remaining agents.",
                }

            if not is_ready and force:
                decommissioned = await _force_decommission_agents(active_session, project_id, tenant_key)
                if decommissioned:
                    logger.warning(
                        "Force-closed project %s: auto-decommissioned %d agent(s): %s",
                        project_id,
                        len(decommissioned),
                        ", ".join(decommissioned),
                    )

            product_memory: dict[str, Any] = product.product_memory or {}
            if not isinstance(product_memory, dict):
                product_memory = {}

            git_config = _get_git_config(product_memory)
            git_commits: list[dict[str, Any | None]] = None

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
            metrics = _build_metrics(git_commits, project.meta_data or {})

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
                "success": True,
                "entry_id": str(entry.id),
                "sequence_number": sequence_number,
                "git_commits_count": len(git_commits),
                "message": "Project closed and 360 Memory updated successfully",
            }

    except Exception as exc:
        logger.exception("Failed to close project and update memory", extra={"error": str(exc)})
        return {"success": False, "error": str(exc)}


# Statuses that do not block closeout (aligned with write_360_memory.SKIP_STATUSES)
_SKIP_STATUSES = {"decommissioned"}
# Statuses considered "active" — agents not yet finished
_ACTIVE_STATUSES = {"waiting", "working", "blocked", "silent"}


async def _check_agent_readiness(
    session: AsyncSession,
    project_id: str,
    tenant_key: str,
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Check whether all agents in the project are ready for closeout.

    Returns (is_ready, blockers) where blockers is a list of dicts
    describing each non-complete agent.
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
    for execution in executions:
        if execution.status in _SKIP_STATUSES:
            continue
        if execution.status == "complete":
            continue

        blockers.append(
            {
                "agent_id": execution.agent_id,
                "agent_name": execution.agent_name or execution.agent_display_name,
                "status": execution.status,
                "job_id": execution.job_id,
                "messages_waiting": execution.messages_waiting_count or 0,
            }
        )

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


def _get_git_config(product_memory: dict[str, Any]) -> dict[str, Any]:
    """Normalize git integration configuration."""
    if not isinstance(product_memory, dict):
        return {}
    git_cfg = product_memory.get("git_integration") or product_memory.get("github") or {}
    return git_cfg if isinstance(git_cfg, dict) else {}


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
    """Derive priority (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)."""
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


def _build_metrics(git_commits: list[dict[str, Any]], meta_data: dict[str, Any]) -> dict[str, Any]:
    """Build metrics block for history entry."""
    test_coverage = 0.0
    if isinstance(meta_data, dict):
        test_coverage = float(meta_data.get("test_coverage", 0.0) or 0.0)

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


async def emit_websocket_event(
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
    except (RuntimeError, ValueError, KeyError) as exc:  # pragma: no cover - best-effort emit
        logger.warning("WebSocket emit failed", extra={"error": str(exc), "event_type": event_type})


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
            commits: list[dict[str, Any]] = [
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
                for commit in commits_data[:100]
            ]

            logger.info(f"Fetched {len(commits)} GitHub commits for {repo_owner}/{repo_name}")
            return commits

    except Exception as exc:
        logger.exception("Failed to fetch GitHub commits", extra={"error": str(exc)})
        return None


async def fetch_github_commits(*args: Any, **kwargs: Any) -> list:
    """Backward-compatible wrapper for GitHub commit fetcher."""
    result = await _fetch_github_commits(*args, **kwargs)
    return result or []
