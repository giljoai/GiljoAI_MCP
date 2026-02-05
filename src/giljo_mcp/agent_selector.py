"""
AgentSelector for GiljoAI MCP Server.

Intelligently selects agents from AgentTemplate database with multi-tenant isolation.
Implements template priority cascade: product > tenant > system defaults.

This is a SECURITY-CRITICAL component enforcing tenant isolation.
"""

import logging
from typing import ClassVar, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DatabaseManager
from .models import AgentTemplate
from .orchestration_types import AgentConfig


logger = logging.getLogger(__name__)


class AgentSelector:
    """
    Select appropriate agents for a mission from database templates.

    Responsibilities:
    - Query AgentTemplate database with tenant isolation
    - Match requirements to available agents
    - Return agent configurations with priorities
    - Handle custom vs standard templates

    Security:
    - Enforces strict tenant isolation
    - Filters by tenant_key to prevent cross-tenant access
    - Validates template access rights
    """

    # Scope templates for different agent types
    SCOPE_TEMPLATES: ClassVar[dict[str, str]] = {
        "implementer": "Write production code following tech stack guidelines. Do NOT modify database schema or authentication logic.",
        "tester": "Write comprehensive tests. Do NOT modify production code.",
        "code-reviewer": "Review code for quality and security. Do NOT modify code, only suggest changes.",
        "frontend-implementer": "Build UI components and views. Do NOT modify backend API endpoints.",
        "database-specialist": "Design and modify database schemas. Ensure migration scripts are included.",
        "security-specialist": "Review security configurations. Do NOT implement features directly.",
        "documenter": "Write comprehensive documentation. Do NOT modify code.",
    }

    # Priority ordering for sorting
    PRIORITY_ORDER: ClassVar[dict[str, int]] = {
        "required": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize AgentSelector.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        if not db_manager.is_async:
            raise ValueError("AgentSelector requires async DatabaseManager")

        self.db_manager = db_manager

    async def select_agents(
        self,
        work_types: dict[str, str],
        tenant_key: str,
        product_id: Optional[str] = None,
    ) -> list[AgentConfig]:
        """
        Select appropriate agents based on work types and priority.

        Implements template priority cascade:
        1. Product-specific template (if product_id provided)
        2. Tenant-specific template
        3. System default template

        Args:
            work_types: Mapping of agent types to priorities
                       e.g., {'implementer': 'high', 'tester': 'medium'}
            tenant_key: Tenant identifier for isolation
            product_id: Optional product identifier for product-specific templates

        Returns:
            List of AgentConfig objects sorted by priority (required > high > medium > low)

        Security:
            - Enforces tenant isolation through filtered queries
            - Product templates only accessible to owning product
            - System templates accessible to all tenants
        """
        if not work_types:
            logger.debug("Empty work_types provided, returning empty agent list")
            return []

        agents = []

        for agent_display_name, priority in work_types.items():
            # Get template with priority cascade
            # Note: agent_display_name from work_types is used as agent_name for template lookup
            template = await self._get_template(
                agent_name=agent_display_name,
                tenant_key=tenant_key,
                product_id=product_id,
            )

            if template is None:
                logger.warning(
                    f"No template found for agent_name='{agent_display_name}', "
                    f"tenant_key='{tenant_key}', product_id='{product_id}'. Skipping."
                )
                continue

            # Determine scope boundary
            mission_scope = self._determine_scope(agent_display_name, priority)

            # Create agent configuration
            agent_config = AgentConfig(
                role=agent_display_name,
                template_id=template.id,
                priority=priority,
                mission_scope=mission_scope,
            )

            agents.append(agent_config)

        # Sort by priority
        agents.sort(key=lambda a: self.PRIORITY_ORDER.get(a.priority, 999))

        logger.info(f"Selected {len(agents)} agents for tenant_key='{tenant_key}', product_id='{product_id}'")

        return agents

    async def _get_template(
        self,
        agent_name: str,
        tenant_key: str,
        product_id: Optional[str] = None,
    ) -> Optional[AgentTemplate]:
        """
        Get agent template with priority cascade.

        Priority order:
        1. Product-specific template (if product_id provided)
        2. Tenant-specific template
        3. System default template

        Args:
            agent_name: Template name to match (e.g., 'implementer', 'implementer-frontend')
            tenant_key: Tenant identifier
            product_id: Optional product identifier

        Returns:
            AgentTemplate if found, None otherwise

        Security:
            - Only returns templates accessible to the tenant
            - Filters out inactive templates
            - Enforces product ownership for product templates
        """
        async with self.db_manager.get_session_async() as session:
            # 1. Try product-specific template (highest priority)
            if product_id is not None:
                template = await self._query_template(
                    session=session,
                    agent_name=agent_name,
                    tenant_key=tenant_key,
                    product_id=product_id,
                )
                if template is not None:
                    logger.debug(
                        f"Found product-specific template: {template.id} "
                        f"for agent_name='{agent_name}', product_id='{product_id}'"
                    )
                    return template

            # 2. Try tenant-specific template
            template = await self._query_template(
                session=session,
                agent_name=agent_name,
                tenant_key=tenant_key,
                product_id=None,  # Explicitly None to match tenant templates
            )
            if template is not None:
                logger.debug(
                    f"Found tenant-specific template: {template.id} "
                    f"for agent_name='{agent_name}', tenant_key='{tenant_key}'"
                )
                return template

            # 3. Try system default template (fallback)
            template = await self._query_template(
                session=session,
                agent_name=agent_name,
                tenant_key="system",
                product_id=None,
                is_default=True,
            )
            if template is not None:
                logger.debug(f"Found system default template: {template.id} for agent_name='{agent_name}'")
                return template

        logger.warning(f"No template found for agent_name='{agent_name}' after checking all priority levels")
        return None

    async def _query_template(
        self,
        session: AsyncSession,
        agent_name: str,
        tenant_key: str,
        product_id: Optional[str] = None,
        is_default: bool = False,
    ) -> Optional[AgentTemplate]:
        """
        Query database for specific template.

        Args:
            session: Active database session
            agent_name: Template name to match
            tenant_key: Tenant identifier
            product_id: Product identifier (None for tenant/system templates)
            is_default: Whether to filter for default templates

        Returns:
            AgentTemplate if found, None otherwise
        """
        # Build query with filters
        query = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.name == agent_name,
            AgentTemplate.is_active,  # Only active templates
        )

        # Add product_id filter
        if product_id is not None:
            query = query.where(AgentTemplate.product_id == product_id)
        else:
            # For tenant and system templates, product_id should be NULL
            query = query.where(AgentTemplate.product_id.is_(None))

        # Add default filter for system templates
        if is_default:
            query = query.where(AgentTemplate.is_default)

        # Execute query
        result = await session.execute(query)
        template = result.scalar_one_or_none()

        return template

    def _determine_scope(self, agent_display_name: str, _priority: str) -> str:
        """
        Determine scope boundary for agent based on type and priority.

        Scope boundaries define what the agent can and cannot do,
        providing clear constraints for agent operation.

        Args:
            agent_display_name: Type/role of agent
            _priority: Priority level (reserved for future use)

        Returns:
            Scope boundary description string
        """
        # Get predefined scope or create generic one
        scope = self.SCOPE_TEMPLATES.get(
            agent_display_name,
            f"Focus on {agent_display_name} tasks. Follow project guidelines and coding standards.",
        )

        return scope
