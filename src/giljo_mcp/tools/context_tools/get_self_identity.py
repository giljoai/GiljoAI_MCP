"""
Get agent self-identity (template) context tool.

Handover 0430: Internal tool for fetch_context() self_identity category.

Fetches the agent's own template from the database, providing behavioral guidance,
success criteria, and protocol instructions from the AgentTemplate stored in Admin Settings.
"""

import json
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate


logger = structlog.get_logger(__name__)


def estimate_tokens(data: dict[str, Any]) -> int:
    """
    Estimate token count for response data.

    Uses rough approximation: ~4 characters per token.

    Args:
        data: Dictionary to estimate tokens for

    Returns:
        Estimated token count
    """
    json_str = json.dumps(data, default=str)
    return len(json_str) // 4


async def get_self_identity(
    agent_name: str,
    tenant_key: str,
    db_manager: DatabaseManager | None = None,
    session: AsyncSession | None = None,  # For testing only
) -> dict[str, Any]:
    """
    Fetch agent template by name for self-identity context.

    Handover 0430: Internal tool for fetch_context() self_identity category.

    Returns the agent's template content including:
    - system_instructions: Protected MCP coordination instructions
    - user_instructions: User-customizable role-specific guidance
    - behavioral_rules: Role-specific behavioral constraints
    - success_criteria: Success metrics and completion criteria

    Args:
        agent_name: Template name (matches AgentTemplate.name, e.g., "orchestrator-coordinator")
        tenant_key: Tenant isolation key
        db_manager: Database manager instance

    Returns:
        Dict with agent identity info:
        {
            "source": "self_identity",
            "data": {
                "name": "orchestrator-coordinator",
                "role": "Orchestrator",
                "description": "...",
                "system_instructions": "...",
                "user_instructions": "...",
                "behavioral_rules": [...],
                "success_criteria": [...]
            },
            "metadata": {
                "agent_name": "orchestrator-coordinator",
                "tenant_key": "...",
                "estimated_tokens": 2000
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key.

    Example:
        result = await get_self_identity(
            agent_name="orchestrator-coordinator",
            tenant_key="tenant_abc",
            db_manager=db_manager
        )
    """
    logger.info("fetching_self_identity", agent_name=agent_name, tenant_key=tenant_key)

    if db_manager is None and session is None:
        logger.error("db_manager or session is required", operation="get_self_identity")
        raise ValueError("db_manager or session parameter is required")

    # Use provided session (for testing) or create new one
    if session is not None:
        # Use provided session directly (for testing)
        session_to_use = session
        should_close = False
    else:
        # Create new session from db_manager
        session_to_use = await db_manager.get_session_async().__aenter__()
        should_close = True

    try:
        # Query template by name with multi-tenant isolation
        stmt = select(AgentTemplate).where(
            AgentTemplate.name == agent_name, AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active
        )
        result = await session_to_use.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            logger.warning(
                "template_not_found", agent_name=agent_name, tenant_key=tenant_key, operation="get_self_identity"
            )
            return {
                "source": "self_identity",
                "data": {},
                "metadata": {"agent_name": agent_name, "tenant_key": tenant_key, "error": "template_not_found"},
            }

        # Build data dict with all identity fields
        data = {
            "name": template.name,
            "role": template.role or "",
            "description": template.description or "",
            "system_instructions": template.system_instructions or "",
            "user_instructions": template.user_instructions or "",
            "behavioral_rules": template.behavioral_rules or [],
            "success_criteria": template.success_criteria or [],
            "capabilities": template.meta_data.get("capabilities", []) if template.meta_data else [],
            "expertise": template.meta_data.get("expertise", []) if template.meta_data else [],
        }

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "self_identity_fetched",
            agent_name=agent_name,
            tenant_key=tenant_key,
            has_system_instructions=bool(template.system_instructions),
            has_user_instructions=bool(template.user_instructions),
            num_behavioral_rules=len(data["behavioral_rules"]),
            num_success_criteria=len(data["success_criteria"]),
            estimated_tokens=total_tokens,
        )

        return {
            "source": "self_identity",
            "data": data,
            "metadata": {"agent_name": agent_name, "tenant_key": tenant_key, "estimated_tokens": total_tokens},
        }
    finally:
        if should_close and session_to_use:
            await session_to_use.close()
