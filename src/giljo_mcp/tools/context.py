"""
Context tools for GiljoAI MCP.
Handles context retrieval for agent executions.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


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

            # Resolve project and product for this job (executor -> job -> project -> product)
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
                "agent_id": execution.agent_id,
                "job_id": execution.job_id,
                "context": product_context,
            }

    except Exception:  # Broad catch: tool boundary, logs and re-raises
        logger.exception("Failed to fetch context")
        raise
