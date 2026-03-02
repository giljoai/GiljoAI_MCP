"""Shared helpers for project_closeout and write_360_memory tools."""

import logging
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)

# Field length constraints
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100


def _get_git_config(product_memory: dict[str, Any]) -> dict[str, Any]:
    """Normalize git integration configuration."""
    if not isinstance(product_memory, dict):
        return {}
    git_cfg = product_memory.get("git_integration") or product_memory.get("github") or {}
    return git_cfg if isinstance(git_cfg, dict) else {}


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

    except Exception as exc:  # Broad catch: tool boundary, logs and re-raises
        logger.exception("Failed to fetch GitHub commits", extra={"error": str(exc)})
        return None
