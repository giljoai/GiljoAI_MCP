"""
Project Closeout MCP Tool (Handover 013B - Refactored)

Handles project completion and updates product memory with sequential history entries.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from inspect import iscoroutine
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


# Field length constraints (added for validation)
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100


async def close_project_and_update_memory(
    project_id: str,
    summary: str,
    key_outcomes: List[str],
    decisions_made: List[str],
    tenant_key: str,
    db_manager: Optional[DatabaseManager] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Close project and update product memory with sequential history entry.

    Adds a rich entry to product_memory.sequential_history.
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

            product_memory: Dict[str, Any] = product.product_memory or {}
            if not isinstance(product_memory, dict):
                product_memory = {}

            sequential_history: List[Dict[str, Any]] = product_memory.get("sequential_history") or []
            product_memory["sequential_history"] = sequential_history

            git_config = _get_git_config(product_memory)
            git_commits: Optional[List[Dict[str, Any]]] = None

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

            sequence_number = (
                max([entry.get("sequence", 0) for entry in sequential_history if isinstance(entry, dict)] or [0]) + 1
            )

            deliverables = _extract_deliverables(key_outcomes)
            tags = _extract_tags(summary, key_outcomes, decisions_made)
            priority = _derive_priority(project, summary, key_outcomes)
            significance_score = _calculate_significance(project, key_outcomes, git_commits)
            token_estimate = _estimate_tokens(summary, key_outcomes, decisions_made)
            metrics = _build_metrics(git_commits, project.meta_data or {})

            history_entry = {
                "sequence": sequence_number,
                "project_id": project_id,
                "project_name": project.name,
                "type": "project_closeout",
                "timestamp": datetime.utcnow().isoformat(),
                "summary": summary,
                "key_outcomes": key_outcomes,
                "decisions_made": decisions_made,
                "deliverables": deliverables,
                "metrics": metrics,
                "git_commits": git_commits,
                "priority": priority,
                "significance_score": significance_score,
                "token_estimate": token_estimate,
                "tags": tags,
                "source": "closeout_v1",
            }

            sequential_history.append(history_entry)
            product.product_memory = dict(product_memory)
            product.updated_at = datetime.utcnow()
            flag_modified(product, "product_memory")
            await active_session.flush()

            if owns_session:
                await active_session.commit()

            logger.info(
                f"Updated 360 Memory for product {product.id} "
                f"(sequence: {sequence_number}, commits: {len(git_commits) if git_commits else 0})"
            )

            return {
                "success": True,
                "sequence_number": sequence_number,
                "git_commits_count": len(git_commits),
                "message": "Project closed and 360 Memory updated successfully",
            }

    except Exception as exc:
        logger.exception("Failed to close project and update memory", extra={"error": str(exc)})
        return {"success": False, "error": str(exc)}


def _get_git_config(product_memory: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize git integration configuration."""
    if not isinstance(product_memory, dict):
        return {}
    git_cfg = product_memory.get("git_integration") or product_memory.get("github") or {}
    return git_cfg if isinstance(git_cfg, dict) else {}


def _extract_deliverables(key_outcomes: List[str]) -> List[str]:
    """Derive deliverables from key outcomes (deduplicated)."""
    seen = set()
    deliverables: List[str] = []
    for outcome in key_outcomes or []:
        normalized = (outcome or "").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deliverables.append(normalized)
    return deliverables


def _extract_tags(summary: str, key_outcomes: List[str], decisions_made: List[str]) -> List[str]:
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


def _derive_priority(project: Project, summary: str, key_outcomes: List[str]) -> int:
    """Derive priority (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)."""
    summary_text = summary.lower() if summary else ""
    outcome_text = " ".join(key_outcomes or []).lower()
    if any(word in summary_text or word in outcome_text for word in ["incident", "outage", "rollback", "failure"]):
        return 1
    if key_outcomes:
        return 2
    return 3


def _calculate_significance(project: Project, key_outcomes: List[str], git_commits: List[Dict[str, Any]]) -> float:
    """Calculate significance score between 0.0 and 1.0."""
    outcome_factor = min(len(key_outcomes or []), 5) * 0.1
    commit_factor = min(len(git_commits or []), 20) * 0.01
    base = 0.3 + outcome_factor + commit_factor
    return round(min(1.0, base), 2)


def _estimate_tokens(summary: str, key_outcomes: List[str], decisions_made: List[str]) -> int:
    """Rough token estimate based on content length."""
    lengths = [len(summary or "")]
    lengths.extend(len(item or "") for item in key_outcomes or [])
    lengths.extend(len(item or "") for item in decisions_made or [])
    estimate = sum(lengths) // 4
    return max(estimate, 1)


def _count_files_changed(git_commits: List[Dict[str, Any]]) -> int:
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


def _count_lines_added(git_commits: List[Dict[str, Any]]) -> int:
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


def _build_metrics(git_commits: List[Dict[str, Any]], meta_data: Dict[str, Any]) -> Dict[str, Any]:
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
    data: Dict[str, Any],
) -> None:
    """Emit WebSocket event; graceful no-op if manager unavailable."""
    try:
        from giljo_mcp.websocket_client import websocket_manager

        if websocket_manager:
            await websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event=event_type,
                data={"product_id": product_id, **data},
            )
    except Exception as exc:  # pragma: no cover - best-effort emit
        logger.warning("WebSocket emit failed", extra={"error": str(exc), "event_type": event_type})


async def _fetch_github_commits(
    repo_name: Optional[str],
    repo_owner: Optional[str],
    access_token: Optional[str],
    project_created_at: datetime,
    project_completed_at: Optional[datetime],
) -> Optional[List[Dict[str, Any]]]:
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
            commits: List[Dict[str, Any]] = []
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
                        "lines_added": commit.get("lines_added")
                        or commit.get("stats", {}).get("additions")
                        if isinstance(commit.get("stats"), dict)
                        else None,
                    }
                )

            logger.info(f"Fetched {len(commits)} GitHub commits for {repo_owner}/{repo_name}")
            return commits

    except Exception as exc:
        logger.exception("Failed to fetch GitHub commits", extra={"error": str(exc)})
        return None


async def fetch_github_commits(*args: Any, **kwargs: Any) -> list:
    """Backward-compatible wrapper for GitHub commit fetcher."""
    result = await _fetch_github_commits(*args, **kwargs)
    return result or []
