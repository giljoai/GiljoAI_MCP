"""
Write 360 Memory Tool (Handover 0412)

Allows agents to write 360 memory entries during handovers or project completion.
Similar to close_project_and_update_memory but more flexible for agent usage.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from inspect import iscoroutine
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


# Field length constraints
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100


async def write_360_memory(
    project_id: str,
    tenant_key: str,
    summary: str,
    key_outcomes: List[str],
    decisions_made: List[str],
    entry_type: str = "project_completion",
    author_job_id: Optional[str] = None,
    db_manager: Optional[DatabaseManager] = None,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Write a 360 memory entry for project completion or handover.

    This tool allows agents to append entries to Product.product_memory.sequential_history
    during handovers or at project completion.

    Args:
        project_id: UUID of the project
        tenant_key: Tenant isolation key
        summary: 2-3 paragraph summary of work accomplished
        key_outcomes: 3-5 specific achievements
        decisions_made: 3-5 architectural/design decisions
        entry_type: Type of entry ("project_completion" or "handover_closeout")
        author_job_id: Job ID of agent writing entry (optional)
        db_manager: Database manager (dependency injection)
        session: Optional existing session

    Returns:
        Success/error dictionary with sequence number
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
    if entry_type not in ["project_completion", "handover_closeout"]:
        return {
            "success": False,
            "error": f"Invalid entry_type '{entry_type}'. Must be 'project_completion' or 'handover_closeout'",
        }

    try:
        owns_session = session is None

        @asynccontextmanager
        async def _provided_session(existing_session: AsyncSession):
            yield existing_session

        session_ctx = db_manager.get_session_async() if owns_session else _provided_session(session)

        async with session_ctx as active_session:
            # Get project with tenant isolation
            project_stmt = select(Project).where(
                Project.id == project_id,
                Project.tenant_key == tenant_key
            )
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

            # Get or initialize product_memory
            product_memory: Dict[str, Any] = product.product_memory or {}
            if not isinstance(product_memory, dict):
                product_memory = {}

            sequential_history: List[Dict[str, Any]] = product_memory.get("sequential_history") or []
            product_memory["sequential_history"] = sequential_history

            # Get git configuration and fetch commits if enabled
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

            # Calculate next sequence number
            sequence_number = (
                max([entry.get("sequence", 0) for entry in sequential_history if isinstance(entry, dict)] or [0]) + 1
            )

            # Get author information if job_id provided
            author_info = {}
            if author_job_id:
                # Query the current execution for this job to get agent_name
                execution_stmt = (
                    select(AgentExecution)
                    .options(joinedload(AgentExecution.job))
                    .where(
                        AgentExecution.job_id == author_job_id,
                        AgentExecution.tenant_key == tenant_key,
                    )
                    .order_by(AgentExecution.instance_number.desc())
                    .limit(1)
                )
                execution_result = await active_session.execute(execution_stmt)
                execution = execution_result.scalar_one_or_none()
                if execution:
                    author_info = {
                        "author_job_id": author_job_id,
                        "author_name": execution.agent_name or execution.agent_display_name,
                        "author_type": execution.job.job_type if execution.job else None,
                    }

            # Build history entry
            history_entry = {
                "sequence": sequence_number,
                "project_id": project_id,
                "project_name": project.name,
                "type": entry_type,
                "timestamp": datetime.utcnow().isoformat(),
                "summary": summary,
                "key_outcomes": key_outcomes,
                "decisions_made": decisions_made,
                "git_commits": git_commits,
                "source": "write_360_memory_v1",
                **author_info,  # Add author info if available
            }

            # Append to history and save
            sequential_history.append(history_entry)
            product.product_memory = dict(product_memory)
            product.updated_at = datetime.utcnow()
            flag_modified(product, "product_memory")
            await active_session.flush()

            if owns_session:
                await active_session.commit()

            logger.info(
                f"Wrote 360 Memory entry for product {product.id} "
                f"(sequence: {sequence_number}, type: {entry_type}, commits: {len(git_commits)})"
            )

            return {
                "success": True,
                "sequence_number": sequence_number,
                "git_commits_count": len(git_commits),
                "entry_type": entry_type,
                "message": "360 Memory entry written successfully",
            }

    except Exception as exc:
        logger.exception("Failed to write 360 memory entry", extra={"error": str(exc)})
        return {"success": False, "error": str(exc)}


def _get_git_config(product_memory: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize git integration configuration."""
    if not isinstance(product_memory, dict):
        return {}
    git_cfg = product_memory.get("git_integration") or product_memory.get("github") or {}
    return git_cfg if isinstance(git_cfg, dict) else {}


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
