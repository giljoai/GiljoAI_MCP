# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared helpers for project_closeout and write_memory_entry tools."""

import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from inspect import iscoroutine
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project


logger = logging.getLogger(__name__)


@asynccontextmanager
async def provided_session(existing_session: AsyncSession):
    """No-op async context manager yielding an existing session unchanged.

    Lets the write tools `async with` either a fresh ``db_manager`` session or a
    caller-supplied one through a single code path. Extracted from the identical
    inline definitions in project_closeout / write_memory_entry (BE-9157).
    """
    yield existing_session


def refuse_if_superseded(project: Any) -> dict[str, Any] | None:
    """Return a structured rejection when writing 360 memory to a superseded project.

    BE-9157: a ``superseded`` project is an audit-trail row whose work moved to a
    successor. Writing a closeout / 360 memory entry against it would attach
    history to the wrong (retired) project, so both write paths
    (``write_360_memory`` and ``close_project_and_update_memory``) refuse it.

    This is a DELIBERATE, agent-actionable domain rejection (the BE-6081 Tier-2
    carve-out shape), not an internal error: the caller returns this dict rather
    than raising, so it reaches the agent as normal tool content (not isError)
    and points them at the successor. Returns ``None`` when the project is not
    superseded (the write proceeds unchanged).
    """
    if project is None or getattr(project, "status", None) != ProjectStatus.SUPERSEDED:
        return None
    return {
        "success": False,
        "error": "PROJECT_SUPERSEDED",
        "project_id": str(project.id),
        "successor_project_id": getattr(project, "successor_project_id", None),
        "message": (
            "This project was superseded — its work moved to a successor project. "
            "360 memory / closeout writes against a superseded project are refused so "
            "history is not attached to retired work. Write to the successor project instead."
        ),
        "hint": (
            "Use the successor_project_id above (if set) as the project_id for this write, "
            "or list_projects(include_superseded=false) to find the live project."
        ),
    }


# Field length constraints
MAX_SUMMARY_LENGTH = 10000  # ~2,500 tokens
MAX_KEY_OUTCOMES = 100
MAX_DECISIONS_MADE = 100

# GitHub owner/repo path-segment validation. GitHub's own allowed character set
# for owner/repo names is alphanumerics plus '.', '_' and '-'. We validate at the
# function boundary BEFORE interpolating the value into the GitHub API URL so a
# malformed/injection-ish config value (path traversal, query/host injection)
# can never reach the request.
_GITHUB_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_GITHUB_SEGMENT_MAX_LEN = 100


def _validate_github_segment(value: str, field_name: str) -> None:
    """Reject a repo_owner / repo_name that is not a safe URL path segment.

    Raises ``ValueError`` (a 422-style validation error at the tool boundary)
    rather than letting an injection-ish value reach the GitHub API URL. MUST be
    called BEFORE the request is built AND outside the broad ``try/except`` in
    ``_fetch_github_commits`` (which would otherwise swallow the rejection into a
    silent ``None``).
    """
    if len(value) > _GITHUB_SEGMENT_MAX_LEN:
        raise ValueError(f"Invalid {field_name}: exceeds {_GITHUB_SEGMENT_MAX_LEN}-character limit")
    if not _GITHUB_SEGMENT_RE.match(value):
        raise ValueError(f"Invalid {field_name}: only letters, digits, '.', '_' and '-' are allowed")
    # Block path-traversal tokens that still pass the charset ('..' or all-dots)
    # so the value cannot collapse the URL path (e.g. '/repos/../x/commits').
    if ".." in value or value.strip(".") == "":
        raise ValueError(f"Invalid {field_name}: must not contain path-traversal sequences")


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
        from giljo_mcp.app_registry.service_registry import get_websocket_manager

        websocket_manager = get_websocket_manager()

        if websocket_manager:
            await websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type=event_type,
                data={"product_id": product_id, **data},
            )
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:  # pragma: no cover - best-effort emit
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

    # Validate charset/length BEFORE the URL is built and BEFORE the broad
    # try/except below (which returns None on error) — a malformed value is a
    # caller-config bug to surface loudly, not a transient fetch failure to skip.
    _validate_github_segment(repo_owner, "repo_owner")
    _validate_github_segment(repo_name, "repo_name")

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
