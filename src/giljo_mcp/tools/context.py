"""
Context and Discovery Tools for GiljoAI MCP
Handles vision documents, context retrieval, and product settings
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select


logger = logging.getLogger(__name__)


# Expose MCP tools as importable async functions for API endpoints
async def get_context_index(product_id: Optional[str] = None) -> dict[str, Any]:
    """Wrapper for MCP tool - Get the context index for intelligent querying"""

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.discovery import DiscoveryManager, PathResolver
    from giljo_mcp.models import Project
    from giljo_mcp.tenant import TenantManager

    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()
    path_resolver = PathResolver(db_manager, tenant_manager)
    discovery_manager = DiscoveryManager(db_manager, tenant_manager, path_resolver)

    try:
        tenant_key = tenant_manager.get_current_tenant()
        project_id = None

        if tenant_key:
            async with db_manager.get_session_async() as session:
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()
                if project:
                    project_id = str(project.id)

        # Get all discovery paths
        paths = await discovery_manager.get_discovery_paths(project_id)

        # Build context source information
        context_sources = {}
        for path_key, path in paths.items():
            if path.exists():
                if path.is_dir():
                    files = list(path.glob("*"))
                    context_sources[path_key] = {
                        "path": str(path),
                        "type": "directory",
                        "files": len(files),
                        "exists": True,
                    }
                else:
                    context_sources[path_key] = {
                        "path": str(path),
                        "type": "file",
                        "exists": True,
                        "size": path.stat().st_size,
                    }
            else:
                context_sources[path_key] = {"path": str(path), "exists": False}

        # Build index
        index = {
            "product_id": product_id or "default",
            "sources": context_sources,
            "documents": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        return {"success": True, "index": index}

    except Exception as e:
        logger.exception("Failed to get vision index")
        return {"success": False, "error": str(e)}


async def get_vision(part: int = 1, max_tokens: int = 20000, force_reindex: bool = False) -> dict[str, Any]:
    """Wrapper for MCP tool - Get the vision document for the active product"""

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.discovery import PathResolver
    from giljo_mcp.models import Project, Vision
    from giljo_mcp.tenant import TenantManager

    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()
    PathResolver(db_manager, tenant_manager)

    try:
        tenant_key = tenant_manager.get_current_tenant()
        if not tenant_key:
            return {"success": False, "error": "No tenant context available"}

        async with db_manager.get_tenant_session_async(tenant_key) as session:
            project_query = select(Project).where(Project.tenant_key == tenant_key)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "Project not found"}

            # Check for existing vision chunks in database
            vision_query = (
                select(Vision)
                .where(Vision.project_id == project.id, Vision.tenant_key == tenant_key)
                .order_by(Vision.chunk_number)
            )
            vision_result = await session.execute(vision_query)
            visions = vision_result.scalars().all()

            if visions:
                # Return from database
                if part <= len(visions):
                    vision = visions[part - 1]
                    return {
                        "success": True,
                        "part": part,
                        "total_parts": len(visions),
                        "content": vision.content,
                        "tokens": vision.tokens,
                        "boundary_type": vision.boundary_type,
                        "keywords": vision.keywords or [],
                        "headers": vision.headers or [],
                        "has_more": part < len(visions),
                        "indexed": True,
                    }
                return {
                    "success": False,
                    "error": f"Part {part} not found. Document has {len(visions)} parts.",
                }

            # No vision data in database, return placeholder
            return {
                "success": True,
                "part": 1,
                "total_parts": 1,
                "content": "# Vision Document\n\nNo vision documents have been indexed yet. Use the MCP tools to initialize vision documents.",
                "tokens": 20,
                "boundary_type": "paragraph",
                "keywords": ["vision", "placeholder"],
                "headers": ["Vision Document"],
                "has_more": False,
                "indexed": False,
                "message": "No vision documents found - returning placeholder",
            }

    except Exception as e:
        logger.exception("Failed to get vision")
        return {"success": False, "error": str(e)}


async def get_vision_index() -> dict[str, Any]:
    """Wrapper for MCP tool - Get the vision document index"""

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.discovery import PathResolver
    from giljo_mcp.models import ContextIndex, Project
    from giljo_mcp.tenant import TenantManager

    db_manager = DatabaseManager(is_async=True)
    tenant_manager = TenantManager()
    PathResolver(db_manager, tenant_manager)

    try:
        tenant_key = tenant_manager.get_current_tenant()
        if not tenant_key:
            return {"success": False, "error": "No tenant context available"}

        async with db_manager.get_tenant_session_async(tenant_key) as session:
            project_query = select(Project).where(Project.tenant_key == tenant_key)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "Project not found"}

            # Check for context index in database
            index_query = select(ContextIndex).where(
                ContextIndex.project_id == project.id,
                ContextIndex.tenant_key == tenant_key,
                ContextIndex.index_type == "vision",
            )
            index_result = await session.execute(index_query)
            index_entries = index_result.scalars().all()

            if index_entries:
                # Return from database
                index = {
                    "files": [],
                    "total_files": len(index_entries),
                    "chunks": {},
                    "from_database": True,
                }

                for entry in index_entries:
                    file_info = {
                        "name": entry.document_name,
                        "summary": entry.summary,
                        "token_count": entry.token_count,
                        "keywords": entry.keywords or [],
                        "chunk_numbers": entry.chunk_numbers or [],
                        "content_hash": entry.content_hash,
                    }
                    index["files"].append(file_info)

                return {"success": True, "index": index}

            # No index found, return placeholder
            return {
                "success": True,
                "index": {
                    "files": [],
                    "total_files": 0,
                    "chunks": {},
                    "from_database": False,
                    "message": "No vision index found - use MCP tools to initialize vision documents",
                },
            }

    except Exception as e:
        logger.exception("Failed to get vision index")
        return {"success": False, "error": str(e)}


async def fetch_context(
    agent_id: str,
    tenant_key: str,
    categories: list[str],
) -> dict[str, Any]:
    """
    Fetch context for an agent execution (executor-specific context window).

    Args:
        agent_id: Executor UUID (WHO is executing)
        tenant_key: Tenant key for multi-tenant isolation
        categories: List of context categories to fetch

    Returns:
        Agent execution context with current usage metrics and product/project context
        for the requested categories (memory_360, git_history, testing, etc.).
    """
    try:
        from sqlalchemy import select

        import giljo_mcp.database as db_module
        from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
        from giljo_mcp.models.products import Product
        from giljo_mcp.models.projects import Project

        from .context_tools.fetch_context import fetch_context as fetch_product_context

        # Use existing database manager (NO hardcoded test URL!)
        if db_module._db_manager is None:
            raise RuntimeError("Database manager not initialized")
        db_manager = db_module._db_manager

        async with db_manager.get_session_async() as session:
            # Query AgentExecution + AgentJob (+ optional Project/Product) by agent_id + tenant_key
            query = (
                select(AgentExecution, AgentJob, Project, Product)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .outerjoin(Project, Project.id == AgentJob.project_id)
                .outerjoin(Product, Product.id == Project.product_id)
                .where(
                    AgentExecution.agent_id == agent_id,
                    AgentExecution.tenant_key == tenant_key,
                )
            )
            result = await session.execute(query)
            row = result.first()

            if not row:
                return {
                    "success": False,
                    "error": "Agent execution not found or unauthorized",
                }

            execution, _job, project, product = row

            # Resolve project and product for this job (executor → job → project → product)
            project_id = str(project.id) if project is not None else None
            product_id = str(product.id) if product is not None else None

            product_context: dict[str, Any] = {}
            if product_id:
                # Delegate to unified product-level fetch_context for actual category data
                product_context = await fetch_product_context(
                    product_id=product_id,
                    tenant_key=tenant_key,
                    project_id=project_id,
                    categories=categories,
                    db_manager=db_manager,
                )

            return {
                "success": True,
                "agent_id": execution.agent_id,
                "job_id": execution.job_id,
                "context_used": execution.context_used,
                "context_budget": execution.context_budget,
                "context": product_context,
            }

    except Exception as e:
        logger.exception("Failed to fetch context")
        return {"success": False, "error": str(e)}


# NOTE: update_context_usage() was removed in Handover 0422 - the MCP server is passive
# and cannot track external CLI tool context usage. See orchestration_service.py for details.


async def get_context_history(
    agent_id: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Get context usage history for an agent execution.

    Args:
        agent_id: Executor UUID
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        Context history with agent and job metadata
    """
    try:
        from sqlalchemy import select

        import giljo_mcp.database as db_module
        from giljo_mcp.models.agent_identity import AgentExecution

        # Use existing database manager (NO hardcoded test URL!)
        if db_module._db_manager is None:
            raise RuntimeError("Database manager not initialized")
        db_manager = db_module._db_manager

        async with db_manager.get_session_async() as session:
            # Query AgentExecution by agent_id + tenant_key
            query = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            result = await session.execute(query)
            execution = result.scalar_one_or_none()

            if not execution:
                return {
                    "success": False,
                    "error": "Agent execution not found or unauthorized",
                }

            # Build context history (placeholder - real implementation would track history)
            context_history = [
                {
                    "timestamp": execution.last_progress_at.isoformat() if execution.last_progress_at else None,
                    "tokens_used": execution.context_used,
                    "tokens_budget": execution.context_budget,
                }
            ]

            return {
                "success": True,
                "agent_id": execution.agent_id,
                "job_id": execution.job_id,
                "agent_display_name": execution.agent_display_name,
                "context_history": context_history,
            }

    except Exception as e:
        logger.exception("Failed to get context history")
        return {"success": False, "error": str(e)}


async def get_succession_context(
    agent_id: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Get full succession chain with context windows for an agent execution.

    Traces the spawned_by chain to find all executors in the succession.

    Args:
        agent_id: Executor UUID (current agent)
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        Succession chain with all executor context windows
    """
    try:
        from sqlalchemy import select

        import giljo_mcp.database as db_module
        from giljo_mcp.models.agent_identity import AgentExecution

        # Use existing database manager (NO hardcoded test URL!)
        if db_module._db_manager is None:
            raise RuntimeError("Database manager not initialized")
        db_manager = db_module._db_manager

        async with db_manager.get_session_async() as session:
            # Query current AgentExecution
            query = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            result = await session.execute(query)
            current_execution = result.scalar_one_or_none()

            if not current_execution:
                return {
                    "success": False,
                    "error": "Agent execution not found or unauthorized",
                }

            # Build succession chain by following spawned_by links
            succession_chain = []

            # Get all executions for this job
            all_executions_query = (
                select(AgentExecution)
                .where(
                    AgentExecution.job_id == current_execution.job_id,
                    AgentExecution.tenant_key == tenant_key,
                )
                .order_by(AgentExecution.started_at)
            )

            all_result = await session.execute(all_executions_query)
            all_executions = all_result.scalars().all()

            # Build chain in order
            for execution in all_executions:
                succession_chain.append(
                    {
                        "agent_id": execution.agent_id,
                        "agent_display_name": execution.agent_display_name,
                        "status": execution.status,
                        "context_used": execution.context_used,
                        "context_budget": execution.context_budget,
                        "spawned_by": execution.spawned_by,
                    }
                )

            return {
                "success": True,
                "agent_id": current_execution.agent_id,
                "job_id": current_execution.job_id,
                "succession_chain": succession_chain,
            }

    except Exception as e:
        logger.exception("Failed to get succession context")
        return {"success": False, "error": str(e)}
