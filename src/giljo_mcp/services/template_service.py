"""
TemplateService - Dedicated service for agent template management

This service extracts all template-related operations from ToolAccessor
as part of Phase 2 of the god object refactoring (Handover 0123).

Responsibilities:
- CRUD operations for agent templates
- Template retrieval and listing
- Template variable management
- Template tenant isolation

Design Principles:
- Single Responsibility: Only template domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentTemplate
from giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

# Agent limit constants (Handover 0103)
USER_MANAGED_AGENT_LIMIT = 7  # Reserve one slot for orchestrator


class TemplateService:
    """
    Service for managing agent templates.

    This service handles all template-related operations including:
    - Creating, reading, updating templates
    - Listing templates by tenant
    - Template variable management
    - Multi-tenant template isolation

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize TemplateService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    async def list_templates(
        self,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List all agent templates for a tenant.

        Args:
            tenant_key: Tenant key for filtering (uses current tenant if not provided)

        Returns:
            Dict with success status and list of templates or error

        Example:
            >>> result = await service.list_templates()
            >>> for template in result["templates"]:
            ...     print(template["name"])
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                # TENANT ISOLATION: Only return templates for the specified tenant
                result = await session.execute(
                    select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
                )
                templates = result.scalars().all()

                template_list = []
                for t in templates:
                    template_list.append({
                        "id": str(t.id),
                        "name": t.name,
                        "role": t.role,
                        "content": t.template_content,
                        "cli_tool": t.cli_tool,
                        "background_color": t.background_color,
                        "category": t.category,
                        "tenant_key": t.tenant_key,
                        "product_id": t.product_id,
                    })

                return {
                    "success": True,
                    "templates": template_list,
                    "count": len(template_list)
                }

        except Exception as e:
            self._logger.exception(f"Failed to list templates: {e}")
            return {"success": False, "error": str(e)}

    async def get_template(
        self,
        template_id: Optional[str] = None,
        template_name: Optional[str] = None,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get a specific template by ID or name.

        Args:
            template_id: Template UUID (optional if template_name provided)
            template_name: Template name (optional if template_id provided)
            tenant_key: Tenant key for filtering (uses current tenant if not provided)

        Returns:
            Dict with success status and template details or error

        Example:
            >>> result = await service.get_template(template_name="orchestrator")
            >>> if result["success"]:
            ...     print(result["template"]["content"])
        """
        try:
            if not template_id and not template_name:
                return {
                    "success": False,
                    "error": "Either template_id or template_name must be provided"
                }

            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                # Build query based on provided identifier
                if template_id:
                    query = select(AgentTemplate).where(
                        AgentTemplate.id == template_id,
                        AgentTemplate.tenant_key == tenant_key
                    )
                else:
                    query = select(AgentTemplate).where(
                        AgentTemplate.name == template_name,
                        AgentTemplate.tenant_key == tenant_key
                    )

                result = await session.execute(query)
                template = result.scalar_one_or_none()

                if not template:
                    identifier = template_id if template_id else template_name
                    return {
                        "success": False,
                        "error": f"Template '{identifier}' not found"
                    }

                return {
                    "success": True,
                    "template": {
                        "id": str(template.id),
                        "name": template.name,
                        "role": template.role,
                        "content": template.template_content,
                        "cli_tool": template.cli_tool,
                        "background_color": template.background_color,
                        "category": template.category,
                        "tenant_key": template.tenant_key,
                        "product_id": template.product_id,
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to get template: {e}")
            return {"success": False, "error": str(e)}

    async def create_template(
        self,
        name: str,
        content: str,
        role: Optional[str] = None,
        category: str = "custom",
        cli_tool: Optional[str] = None,
        background_color: Optional[str] = None,
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Create a new agent template.

        Args:
            name: Template name (required)
            content: Template content/text (required)
            role: Agent role this template is for
            category: Template category (default: "custom")
            cli_tool: CLI tool identifier
            background_color: Background color for UI
            product_id: Parent product ID if template belongs to a product
            tenant_key: Tenant key for multi-tenancy (auto-determined if not provided)

        Returns:
            Dict with success status and template details or error

        Example:
            >>> result = await service.create_template(
            ...     name="custom-analyzer",
            ...     content="You are an analyzer agent for...",
            ...     role="analyzer"
            ... )
            >>> print(result["template_id"])
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                # Create template entity
                template = AgentTemplate(
                    id=str(uuid4()),
                    tenant_key=tenant_key,
                    product_id=product_id,
                    name=name,
                    template_content=content,
                    role=role or name,  # Default role to name if not provided
                    category=category,
                    cli_tool=cli_tool,
                    background_color=background_color,
                )

                session.add(template)
                await session.commit()

                template_id = str(template.id)

                self._logger.info(
                    f"Created template '{name}' (ID: {template_id}) "
                    f"for tenant {tenant_key}"
                )

                return {
                    "success": True,
                    "template_id": template_id,
                    "name": name,
                    "tenant_key": tenant_key,
                }

        except Exception as e:
            self._logger.exception(f"Failed to create template: {e}")
            return {"success": False, "error": str(e)}

    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        role: Optional[str] = None,
        category: Optional[str] = None,
        cli_tool: Optional[str] = None,
        background_color: Optional[str] = None,
        tenant_key: Optional[str] = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Update an existing template.

        Args:
            template_id: Template UUID (required)
            name: New template name (optional)
            content: New template content (optional)
            role: New role (optional)
            category: New category (optional)
            cli_tool: New CLI tool (optional)
            background_color: New background color (optional)
            tenant_key: Tenant key for validation (uses current tenant if not provided)

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.update_template(
            ...     template_id="abc-123",
            ...     content="Updated template content..."
            ... )
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                # Get template with tenant isolation
                result = await session.execute(
                    select(AgentTemplate).where(
                        AgentTemplate.id == template_id,
                        AgentTemplate.tenant_key == tenant_key
                    )
                )
                template = result.scalar_one_or_none()

                if not template:
                    return {
                        "success": False,
                        "error": f"Template '{template_id}' not found"
                    }

                # Update fields if provided
                if name is not None:
                    template.name = name
                if content is not None:
                    template.template_content = content
                if role is not None:
                    template.role = role
                if category is not None:
                    template.category = category
                if cli_tool is not None:
                    template.cli_tool = cli_tool
                if background_color is not None:
                    template.background_color = background_color

                await session.commit()

                self._logger.info(f"Updated template {template_id}")

                return {
                    "success": True,
                    "template_id": template_id,
                    "updated": True,
                }

        except Exception as e:
            self._logger.exception(f"Failed to update template: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Validation Methods
    # ============================================================================

    @staticmethod
    def _is_system_managed_role(role: Optional[str]) -> bool:
        """
        Check if a role is system-managed and cannot be toggled by users.

        Args:
            role: Role name to check

        Returns:
            True if role is system-managed, False otherwise

        Example:
            >>> TemplateService._is_system_managed_role("orchestrator")
            True
            >>> TemplateService._is_system_managed_role("reviewer")
            False
        """
        return bool(role and role in SYSTEM_MANAGED_ROLES)

    async def validate_active_agent_limit(
        self,
        session: AsyncSession,
        tenant_key: str,
        template_id: str,
        new_is_active: bool,
        role: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Validate 8-role active limit before toggling (Handover 0103).

        Claude Code context budget constraint: Maximum 8 distinct active roles
        to ensure optimal performance and sufficient tokens for code analysis.

        Args:
            session: Database session (for transaction context)
            tenant_key: Tenant key for isolation
            template_id: Template being toggled
            new_is_active: Desired active state
            role: Role of the template being toggled (optional, will be fetched if not provided)

        Returns:
            (is_valid, error_message) tuple
            - (True, "") if validation passes
            - (False, error_msg) if validation fails

        Example:
            >>> async with db_manager.get_session_async() as session:
            ...     valid, msg = await service.validate_active_agent_limit(
            ...         session, "tenant-1", "tpl-123", True, "orchestrator"
            ...     )
            ...     if not valid:
            ...         raise HTTPException(409, msg)
        """
        # System-managed roles are not user-toggleable
        if self._is_system_managed_role(role):
            return False, "System-managed roles cannot be toggled"

        # If deactivating, always allow
        if not new_is_active:
            return True, ""

        # Get current template to fetch its role if not provided
        if role is None:
            stmt = select(AgentTemplate.role).where(AgentTemplate.id == template_id)
            result = await session.execute(stmt)
            role = result.scalar_one_or_none()
            if not role:
                return False, "Template not found"

        # Count currently active distinct roles (excluding the one being toggled)
        system_roles = list(SYSTEM_MANAGED_ROLES)
        stmt = (
            select(AgentTemplate.role)
            .where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True,  # noqa: E712
                AgentTemplate.id != template_id,
            )
            .where(AgentTemplate.role.notin_(system_roles))
            .distinct()
        )

        result = await session.execute(stmt)
        active_roles = {row[0] for row in result.all()}

        # If this role is already active elsewhere, allow toggle
        if role in active_roles:
            return True, ""

        # If we have 7 distinct active roles, block new role activation (orchestrator is reserved)
        if len(active_roles) >= USER_MANAGED_AGENT_LIMIT:
            return (
                False,
                f"Maximum {USER_MANAGED_AGENT_LIMIT} active agent roles allowed "
                f"(currently {len(active_roles)}). Deactivate another role first.",
            )

        return True, ""
