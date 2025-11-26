"""
Project Closeout MCP Tool (Handover 013B - Refactored)

Handles project completion and updates product memory with sequential history entries.

REMOVED: GitHub API integration (over-engineered)
Git integration is handled by CLI agents (Claude Code, Codex, Gemini).
This tool now only stores project history in product_memory.sequential_history.
"""

import logging
from datetime import datetime, timezone
from inspect import iscoroutine
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastmcp import FastMCP
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


# Field length constraints (added for validation)
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100




def register_project_closeout_tools(
    mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager
):
    """Register project closeout tools with the MCP server"""

    @mcp.tool()
    async def close_project_and_update_memory_wrapper(
        project_id: str,
        summary: str,
        key_outcomes: List[str],
        decisions_made: List[str],
        tenant_key: str,
    ) -> Dict[str, Any]:
        """
        MCP wrapper for close_project_and_update_memory.

        Automatically injects db_manager dependency.
        """
        return await close_project_and_update_memory(
            project_id=project_id,
            summary=summary,
            key_outcomes=key_outcomes,
            decisions_made=decisions_made,
            tenant_key=tenant_key,
            db_manager=db_manager,
        )


async def close_project_and_update_memory(
    project_id: str,
    summary: str,
    key_outcomes: List[str],
    decisions_made: List[str],
    tenant_key: str,
    db_manager: Optional[DatabaseManager] = None,
) -> Dict[str, Any]:
    """
    Close project and update product memory with sequential history entry.

    Adds a rich entry to product_memory.sequential_history and mirrors to the legacy
    product_memory.learnings array for backward compatibility.
    """
    if not project_id:
        return {"success": False, "error": "project_id is required"}

    if not summary or not summary.strip():
        return {"success": False, "error": "summary is required"}

    if db_manager is None:
        return {"success": False, "error": "db_manager is required"}

    # Validate field lengths
    if len(summary) > MAX_SUMMARY_LENGTH:
        return {
            "success": False,
            "error": f"Summary too long (max {MAX_SUMMARY_LENGTH} characters)"
        }

    if len(key_outcomes) > MAX_KEY_OUTCOMES:
        logger.warning(
            f"Truncating key_outcomes from {len(key_outcomes)} to {MAX_KEY_OUTCOMES}",
            extra={"project_id": project_id}
        )
        key_outcomes = key_outcomes[:MAX_KEY_OUTCOMES]

    if len(decisions_made) > MAX_DECISIONS_MADE:
        logger.warning(
            f"Truncating decisions_made from {len(decisions_made)} to {MAX_DECISIONS_MADE}",
            extra={"project_id": project_id}
        )
        decisions_made = decisions_made[:MAX_DECISIONS_MADE]

    try:
        async with db_manager.get_session_async() as session:
            # Fetch project with tenant isolation
            project_stmt = select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
            project_result = await session.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            if iscoroutine(project):
                project = await project

            if not project:
                return {"success": False, "error": "Project not found or unauthorized for tenant"}

            if getattr(project, "tenant_key", None) != tenant_key:
                return {"success": False, "error": "Project not found or unauthorized for tenant"}

            # Fetch product with tenant isolation
            product_stmt = select(Product).where(Product.id == project.product_id, Product.tenant_key == tenant_key)
            product_result = await session.execute(product_stmt)
            product = product_result.scalar_one_or_none()
            if iscoroutine(product):
                product = await product

            if not product:
                return {"success": False, "error": "Product not found for project"}

            # Normalize arrays
            product_memory = product.product_memory or {}
            sequential_history = product_memory.get("sequential_history") or []
            learnings = product_memory.get("learnings") or []

            # Validate list types
            if not isinstance(key_outcomes, list):
                logger.warning("key_outcomes should be a list; defaulting to empty", extra={"tenant_key": tenant_key})
                key_outcomes = []
            if not isinstance(decisions_made, list):
                logger.warning("decisions_made should be a list; defaulting to empty", extra={"tenant_key": tenant_key})
                decisions_made = []

            # Sequence number (use existing history if present)
            existing_sequences = [
                entry.get("sequence", 0)
                for entry in (sequential_history or [])
                if isinstance(entry, dict)
            ] + [
                entry.get("sequence", 0)
                for entry in (learnings or [])
                if isinstance(entry, dict)
            ]
            next_sequence = (max(existing_sequences) if existing_sequences else 0) + 1

            now_iso = datetime.now(timezone.utc).isoformat()
            entry_id = str(uuid4())
            token_estimate = max(len(summary) // 4, 1)

            git_commits: list = []
            github_cfg = product_memory.get("github") or {}
            if github_cfg.get("enabled"):
                try:
                    git_commits = await fetch_github_commits()
                except Exception as exc:  # pragma: no cover - best-effort
                    logger.warning("Failed to fetch GitHub commits", extra={"error": str(exc)})
                    git_commits = []

            normalized_commits: List[Dict[str, Any]] = []
            for commit in git_commits or []:
                if not isinstance(commit, dict):
                    normalized_commits.append({"sha": None, "message": str(commit)})
                    continue

                normalized_commits.append(
                    {
                        "sha": commit.get("sha"),
                        "message": commit.get("message")
                        or commit.get("commit", {}).get("message"),
                        "author": commit.get("author") or commit.get("commit", {}).get("author"),
                    }
                )

            git_commits = normalized_commits

            rich_entry = {
                "id": entry_id,
                "sequence": next_sequence,
                "type": "project_closeout",
                "project_id": str(project.id),
                "project_name": project.name,
                "timestamp": now_iso,
                "summary": summary,
                "key_outcomes": key_outcomes,
                "decisions_made": decisions_made,
                "deliverables": [],
                "metrics": {},
                "git_commits": git_commits,
                "priority": 3,
                "significance_score": 0.5,
                "token_estimate": token_estimate,
                "source": "closeout_v1",
            }

            # Append to sequential_history (rich) and legacy learnings
            sequential_history.append(rich_entry)
            learnings.append(
                {
                    "id": entry_id,
                    "sequence": next_sequence,
                    "type": "project_closeout",
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "summary": summary,
                    "key_outcomes": key_outcomes,
                    "decisions_made": decisions_made,
                    "git_commits": rich_entry["git_commits"],
                    "timestamp": now_iso,
                }
            )

            product_memory["sequential_history"] = sequential_history
            product_memory["learnings"] = learnings
            product.product_memory = product_memory
            product.updated_at = datetime.now(timezone.utc)

            await session.commit()

            await emit_websocket_event(
                event_type="product_memory_updated",
                tenant_key=tenant_key,
                product_id=str(product.id),
                data={
                    "sequence": next_sequence,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "summary": summary,
                    "priority": rich_entry["priority"],
                },
            )

            return {
                "success": True,
                "learning_id": entry_id,
                "sequence": next_sequence,
            }
    except Exception as exc:
        logger.exception("Failed to close project and update memory", extra={"error": str(exc)})
        return {"success": False, "error": str(exc)}


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


async def fetch_github_commits(*args: Any, **kwargs: Any) -> list:
    """
    Fetch GitHub commits for project closeout.

    **Status**: PLACEHOLDER - Not yet implemented

    When implemented, this function should:
    - Fetch commits from GitHub API v3: GET /repos/{owner}/{repo}/commits
    - Return format: [{"sha": "abc123", "message": "...", "author": {...}}]
    - Normalize commits to include top-level sha/message/author fields

    The normalization code (lines 145-160) is ready and handles both:
    - Direct format: {"sha": "...", "message": "...", "author": "..."}
    - Nested format: {"commit": {"message": "...", "author": "..."}}

    TODO: Implement GitHub OAuth integration (see handover 0249)

    Returns:
        Empty list until GitHub integration is implemented.
    """
    return []
