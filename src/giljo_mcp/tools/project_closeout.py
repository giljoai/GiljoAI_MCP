"""
Project Closeout MCP Tool (Handover 0138)

Handles project completion and updates product memory with learnings.
Integrates with GitHub to fetch commit history when enabled.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from fastmcp import FastMCP
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


async def fetch_github_commits(
    repo_url: str,
    access_token: Optional[str],
    since: datetime,
    until: datetime,
) -> List[Dict[str, Any]]:
    """
    Fetch GitHub commits for a repository within a date range.

    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
        access_token: GitHub personal access token (optional for public repos)
        since: Start date for commit range
        until: End date for commit range

    Returns:
        List of commit dictionaries with sha, message, author, timestamp

    Raises:
        httpx.HTTPError: If GitHub API request fails
    """
    # Extract owner and repo from URL
    # Format: https://github.com/owner/repo or https://github.com/owner/repo.git
    parts = repo_url.rstrip("/").rstrip(".git").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repo URL: {repo_url}")

    owner = parts[-2]
    repo = parts[-1]

    # GitHub API endpoint
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    # Request parameters
    params = {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "per_page": 100,  # Max commits per page
    }

    headers = {
        "Accept": "application/vnd.github.v3+json",
    }

    # Add authentication if token provided
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    # Fetch commits
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            commits_data = response.json()

            # Transform to our format
            commits = []
            for commit_data in commits_data:
                commits.append({
                    "sha": commit_data["sha"],
                    "message": commit_data["commit"]["message"],
                    "author": commit_data["commit"]["author"]["name"],
                    "email": commit_data["commit"]["author"]["email"],
                    "timestamp": commit_data["commit"]["author"]["date"],
                })

            logger.info(f"Fetched {len(commits)} commits from {owner}/{repo}")
            return commits

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch GitHub commits: {e}")
            # Return empty list on error - fallback to manual summary
            return []


async def emit_websocket_event(
    event_type: str,
    product_id: str,
    data: Dict[str, Any],
) -> None:
    """
    Emit WebSocket event for real-time UI updates.

    Args:
        event_type: Event type (e.g., "product_memory_updated")
        product_id: Product UUID
        data: Event payload
    """
    # TODO: Implement WebSocket event emission when WebSocket server is available
    # For now, just log the event
    logger.info(
        f"WebSocket event: {event_type} for product {product_id} - {data}"
    )


def register_project_closeout_tools(
    mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager
):
    """Register project closeout tools with the MCP server"""

    @mcp.tool()
    async def close_project_and_update_memory(
        project_id: str,
        summary: str,
        key_outcomes: List[str],
        decisions_made: List[str],
        tenant_key: str,
    ) -> Dict[str, Any]:
        """
        Close project and update product memory with learnings.

        This tool is called by the orchestrator when a project completes.
        It stores a learning entry in product_memory.learnings with:
        - Sequential numbering (auto-incrementing)
        - Project summary and outcomes
        - GitHub commits if integration enabled
        - Timestamp for historical tracking

        Args:
            project_id: UUID of the project being closed
            summary: User-provided summary of project work
            key_outcomes: List of key achievements/outcomes
            decisions_made: List of important decisions made
            tenant_key: Tenant isolation key

        Returns:
            Success/error response with learning_id and sequence number

        Example:
            >>> result = await close_project_and_update_memory(
            ...     project_id="abc-123",
            ...     summary="Implemented JWT authentication",
            ...     key_outcomes=["Secure token storage"],
            ...     decisions_made=["Chose JWT over sessions"],
            ...     tenant_key="tk_xyz"
            ... )
            >>> print(result)
            {
                "success": true,
                "learning_id": "learning_1",
                "sequence": 1,
                "product_id": "product-uuid"
            }
        """
        try:
            # Validation
            if not project_id:
                return {
                    "success": False,
                    "error": "project_id is required"
                }

            if not summary or not summary.strip():
                return {
                    "success": False,
                    "error": "summary is required and cannot be empty"
                }

            if not tenant_key:
                return {
                    "success": False,
                    "error": "tenant_key is required"
                }

            async with db_manager.get_session_async() as session:
                # 1. Fetch project
                project_query = select(Project).where(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                )
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found or access denied for tenant"
                    }

                # 2. Fetch product
                if not project.product_id:
                    return {
                        "success": False,
                        "error": f"Project {project_id} is not associated with a product"
                    }

                product_query = select(Product).where(
                    Product.id == project.product_id,
                    Product.tenant_key == tenant_key,
                )
                product_result = await session.execute(product_query)
                product = product_result.scalar_one_or_none()

                if not product:
                    return {
                        "success": False,
                        "error": f"Product {project.product_id} not found or access denied for tenant"
                    }

                # 3. Ensure product_memory is initialized
                if not product.product_memory:
                    product.product_memory = {
                        "github": {},
                        "learnings": [],
                        "context": {}
                    }

                # 4. Calculate next sequence number
                existing_learnings = product.product_memory.get("learnings", [])
                next_sequence = 1
                if existing_learnings:
                    max_sequence = max(
                        learning.get("sequence", 0)
                        for learning in existing_learnings
                    )
                    next_sequence = max_sequence + 1

                # 5. Fetch GitHub commits if integration enabled
                git_commits = []
                github_config = product.product_memory.get("github", {})
                if (
                    github_config.get("enabled") is True
                    and github_config.get("repo_url")
                ):
                    try:
                        git_commits = await fetch_github_commits(
                            repo_url=github_config["repo_url"],
                            access_token=github_config.get("access_token"),
                            since=project.created_at,
                            until=project.updated_at or datetime.now(timezone.utc),
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch GitHub commits for product {product.id}: {e}. "
                            "Using manual summary only."
                        )

                # 6. Create learning entry
                learning_entry = {
                    "sequence": next_sequence,
                    "type": "project_closeout",
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "summary": summary.strip(),
                    "key_outcomes": key_outcomes,
                    "decisions_made": decisions_made,
                    "git_commits": git_commits,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                # 7. Append to learnings array (create new dict to trigger SQLAlchemy change detection)
                updated_memory = dict(product.product_memory)
                updated_learnings = list(updated_memory.get("learnings", []))
                updated_learnings.append(learning_entry)
                updated_memory["learnings"] = updated_learnings
                product.product_memory = updated_memory

                # 8. Update product timestamp
                product.updated_at = datetime.now(timezone.utc)

                # 9. Commit changes
                await session.commit()
                await session.refresh(product)

                logger.info(
                    f"Added learning entry (sequence {next_sequence}) to product {product.id} "
                    f"for project {project.id}"
                )

                # 10. Emit WebSocket event for real-time UI updates
                await emit_websocket_event(
                    event_type="product_memory_updated",
                    product_id=str(product.id),
                    data={
                        "learning_id": f"learning_{next_sequence}",
                        "sequence": next_sequence,
                        "project_id": str(project.id),
                    }
                )

                return {
                    "success": True,
                    "learning_id": f"learning_{next_sequence}",
                    "sequence": next_sequence,
                    "product_id": str(product.id),
                    "github_commits_count": len(git_commits),
                }

        except Exception as e:
            logger.exception(f"Failed to close project and update memory: {e}")
            return {
                "success": False,
                "error": str(e)
            }
