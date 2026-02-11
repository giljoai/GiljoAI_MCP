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

Updated Handover 0731: Migrated from dict returns to typed
TemplateListResult, TemplateGetResult, TemplateCreateResult, TemplateUpdateResult.
"""

import logging
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    TemplateNotFoundError,
    ValidationError,
)

# Model imports: Use domain-specific imports (Post-0128a)
from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.models.templates import AgentTemplate, TemplateArchive, TemplateUsageStats
from src.giljo_mcp.schemas.service_responses import (
    TemplateCreateResult,
    TemplateDetail,
    TemplateGetResult,
    TemplateListResult,
    TemplateUpdateResult,
)
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from src.giljo_mcp.tenant import TenantManager


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

    async def list_templates(self, tenant_key: Optional[str] = None) -> TemplateListResult:
        """
        List all agent templates for a tenant.

        Args:
            tenant_key: Tenant key for filtering (uses current tenant if not provided)

        Returns:
            TemplateListResult with templates list and count.

        Raises:
            ValidationError: When no tenant context is available
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.list_templates()
            >>> for template in result.templates:
            ...     print(template["name"])
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_templates"})

            async with self.db_manager.get_session_async() as session:
                # TENANT ISOLATION: Only return templates for the specified tenant
                result = await session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
                templates = result.scalars().all()

                template_list = [
                    {
                        "id": str(t.id),
                        "name": t.name,
                        "role": t.role,
                        "content": t.system_instructions,
                        "cli_tool": t.cli_tool,
                        "background_color": t.background_color,
                        "category": t.category,
                        "tenant_key": t.tenant_key,
                        "product_id": t.product_id,
                    }
                    for t in templates
                ]

                return TemplateListResult(templates=template_list, count=len(template_list))

        except ValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to list templates")
            raise BaseGiljoError(message=f"Failed to list templates: {e!s}", context={"tenant_key": tenant_key}) from e

    async def get_template(
        self, template_id: Optional[str] = None, template_name: Optional[str] = None, tenant_key: Optional[str] = None
    ) -> TemplateGetResult:
        """
        Get a specific template by ID or name.

        Args:
            template_id: Template UUID (optional if template_name provided)
            template_name: Template name (optional if template_id provided)
            tenant_key: Tenant key for filtering (uses current tenant if not provided)

        Returns:
            TemplateGetResult with template detail.

        Raises:
            ValidationError: When neither template_id nor template_name provided, or no tenant context
            TemplateNotFoundError: When template not found
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.get_template(template_name="orchestrator")
            >>> print(result.template.content)
        """
        try:
            if not template_id and not template_name:
                raise ValidationError(
                    message="Either template_id or template_name must be provided",
                    context={"operation": "get_template"},
                )

            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "get_template"})

            async with self.db_manager.get_session_async() as session:
                # Build query based on provided identifier
                if template_id:
                    query = select(AgentTemplate).where(
                        AgentTemplate.id == template_id, AgentTemplate.tenant_key == tenant_key
                    )
                else:
                    query = select(AgentTemplate).where(
                        AgentTemplate.name == template_name, AgentTemplate.tenant_key == tenant_key
                    )

                result = await session.execute(query)
                template = result.scalar_one_or_none()

                if not template:
                    identifier = template_id if template_id else template_name
                    raise TemplateNotFoundError(
                        message=f"Template '{identifier}' not found",
                        context={
                            "template_id": template_id,
                            "template_name": template_name,
                            "tenant_key": tenant_key,
                        },
                    )

                return TemplateGetResult(
                    template=TemplateDetail(
                        id=str(template.id),
                        name=template.name,
                        role=template.role,
                        content=template.system_instructions,
                        cli_tool=template.cli_tool,
                        background_color=template.background_color,
                        category=template.category,
                        tenant_key=template.tenant_key,
                        product_id=template.product_id,
                    )
                )

        except (ValidationError, TemplateNotFoundError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to get template")
            raise BaseGiljoError(
                message=f"Failed to get template: {e!s}",
                context={
                    "template_id": template_id,
                    "template_name": template_name,
                    "tenant_key": tenant_key,
                },
            ) from e

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
        **kwargs,
    ) -> TemplateCreateResult:
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
            TemplateCreateResult with template_id, name, and tenant_key.

        Raises:
            ValidationError: When no tenant context is available
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.create_template(
            ...     name="custom-analyzer",
            ...     content="You are an analyzer agent for...",
            ...     role="analyzer"
            ... )
            >>> print(result.template_id)
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "create_template"})

            async with self.db_manager.get_session_async() as session:
                # Create template entity
                template = AgentTemplate(
                    id=str(uuid4()),
                    tenant_key=tenant_key,
                    product_id=product_id,
                    name=name,
                    role=role or name,  # Default role to name if not provided
                    category=category,
                    cli_tool=cli_tool,
                    background_color=background_color,
                )

                session.add(template)
                await session.commit()

                template_id = str(template.id)

                self._logger.info(f"Created template '{name}' (ID: {template_id}) for tenant {tenant_key}")

                return TemplateCreateResult(
                    template_id=template_id,
                    name=name,
                    tenant_key=tenant_key,
                )

        except ValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to create template")
            raise BaseGiljoError(
                message=f"Failed to create template: {e!s}",
                context={
                    "name": name,
                    "tenant_key": tenant_key,
                },
            ) from e

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
        **kwargs,
    ) -> TemplateUpdateResult:
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
            TemplateUpdateResult with template_id and updated flag.

        Raises:
            ValidationError: When no tenant context is available
            TemplateNotFoundError: When template not found
            BaseGiljoError: When operation fails

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
                raise ValidationError(message="No tenant context available", context={"operation": "update_template"})

            async with self.db_manager.get_session_async() as session:
                # Get template with tenant isolation
                result = await session.execute(
                    select(AgentTemplate).where(AgentTemplate.id == template_id, AgentTemplate.tenant_key == tenant_key)
                )
                template = result.scalar_one_or_none()

                if not template:
                    raise TemplateNotFoundError(
                        message=f"Template '{template_id}' not found",
                        context={
                            "template_id": template_id,
                            "tenant_key": tenant_key,
                        },
                    )

                # Update fields if provided
                if name is not None:
                    template.name = name
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

                return TemplateUpdateResult(
                    template_id=template_id,
                    updated=True,
                )

        except (ValidationError, TemplateNotFoundError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to update template")
            raise BaseGiljoError(
                message=f"Failed to update template: {e!s}",
                context={
                    "template_id": template_id,
                    "tenant_key": tenant_key,
                },
            ) from e

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
                AgentTemplate.is_active,
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

    # ============================================================================
    # Template Retrieval Methods (Phase 2 - Handover 1011)
    # ============================================================================

    async def get_template_by_id(
        self,
        session: AsyncSession,
        template_id: str,
        tenant_key: str,
    ) -> Optional[AgentTemplate]:
        """
        Get a template by ID with tenant isolation.

        Args:
            session: Database session
            template_id: Template UUID
            tenant_key: Tenant key for isolation (REQUIRED)

        Returns:
            AgentTemplate ORM object or None if not found

        Example:
            >>> template = await service.get_template_by_id(session, "abc-123", "tenant-1")
            >>> if template:
            ...     print(template.name)
        """
        # ORIGINAL QUERY: crud.py line 115-122 (get_template endpoint)
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_templates_with_filters(
        self,
        session: AsyncSession,
        tenant_key: str,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[AgentTemplate]:
        """
        List templates with optional filters.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation (REQUIRED)
            role: Filter by role (optional)
            is_active: Filter by active status (optional)

        Returns:
            List of AgentTemplate ORM objects

        Example:
            >>> templates = await service.list_templates_with_filters(
            ...     session, "tenant-1", role="orchestrator", is_active=True
            ... )
        """
        # ORIGINAL QUERY: crud.py line 151-160 (list_templates endpoint)
        query = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)

        if role:
            query = query.where(AgentTemplate.role == role)
        if is_active is not None:
            query = query.where(AgentTemplate.is_active == is_active)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def check_template_name_exists(
        self,
        session: AsyncSession,
        tenant_key: str,
        name: str,
    ) -> bool:
        """
        Check if a template name already exists for a tenant.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation (REQUIRED)
            name: Template name to check

        Returns:
            True if name exists, False otherwise

        Example:
            >>> exists = await service.check_template_name_exists(
            ...     session, "tenant-1", "my-analyzer"
            ... )
        """
        # ORIGINAL QUERY: crud.py line 197-205 (create_template uniqueness check)
        stmt = select(AgentTemplate).where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.name == name))
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_default_templates_by_role(
        self,
        session: AsyncSession,
        tenant_key: str,
        role: str,
        product_id: Optional[str] = None,
    ) -> list[AgentTemplate]:
        """
        Get all default templates for a specific role.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation (REQUIRED)
            role: Role to filter by
            product_id: Optional product filter

        Returns:
            List of default AgentTemplate ORM objects for the role

        Example:
            >>> defaults = await service.get_default_templates_by_role(
            ...     session, "tenant-1", "orchestrator", "product-1"
            ... )
        """
        # ORIGINAL QUERY: crud.py line 229-240 (create_template default flag management)
        filters = [
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.role == role,
            AgentTemplate.is_default,
        ]
        if product_id:
            filters.append(AgentTemplate.product_id == product_id)

        stmt = select(AgentTemplate).where(and_(*filters))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_user_managed_count(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Get count of active user-managed templates (excludes system-managed roles).

        Args:
            session: Database session
            tenant_key: Tenant key for isolation (REQUIRED)

        Returns:
            Count of active user-managed templates

        Example:
            >>> count = await service.get_active_user_managed_count(session, "tenant-1")
            >>> print(f"Active: {count}/{USER_MANAGED_AGENT_LIMIT}")
        """
        # ORIGINAL QUERY: crud.py line 496-504 (get_active_count endpoint)
        stmt = select(func.count(AgentTemplate.id)).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active,
                AgentTemplate.role.not_in(SYSTEM_MANAGED_ROLES),
            )
        )
        result = await session.execute(stmt)
        return result.scalar()

    # ============================================================================
    # Template Deletion Methods (Phase 2 - Handover 1011)
    # ============================================================================

    async def hard_delete_template(
        self,
        session: AsyncSession,
        template_id: str,
        tenant_key: str,
    ) -> bool:
        """
        Hard delete a template and all related records (CASCADE).

        Deletes in order:
        1. Sets AgentJob.template_id to NULL for historical jobs
        2. Deletes TemplateUsageStats records
        3. Deletes TemplateArchive records (version history)
        4. Deletes the template itself

        Args:
            session: Database session
            template_id: Template UUID to delete
            tenant_key: Tenant key for isolation (REQUIRED)

        Returns:
            True if deleted successfully, False if not found

        Example:
            >>> deleted = await service.hard_delete_template(session, "tpl-123", "tenant-1")
        """
        # ORIGINAL QUERIES: crud.py lines 427-471 (delete_template endpoint)

        # Get template first to verify ownership
        template = await self.get_template_by_id(session, template_id, tenant_key)
        if not template:
            return False

        # 1. Set AgentJob.template_id to NULL for historical jobs
        await session.execute(update(AgentJob).where(AgentJob.template_id == template_id).values(template_id=None))

        # NOTE: TemplateAugmentation deletion removed (Handover 0423 - table removed)

        # 2. Delete related TemplateUsageStats records
        await session.execute(sql_delete(TemplateUsageStats).where(TemplateUsageStats.template_id == template_id))

        # 4. Delete related TemplateArchive records (version history)
        await session.execute(sql_delete(TemplateArchive).where(TemplateArchive.template_id == template_id))

        # 5. Delete the template itself
        await session.delete(template)

        return True

    # ============================================================================
    # Template History Methods (Phase 2 - Handover 1011)
    # ============================================================================

    async def get_template_history(
        self,
        session: AsyncSession,
        template_id: str,
        tenant_key: str,
    ) -> list[TemplateArchive]:
        """
        Get template version history ordered by archived_at descending.

        Args:
            session: Database session
            template_id: Template UUID
            tenant_key: Tenant key for isolation (REQUIRED)

        Returns:
            List of TemplateArchive ORM objects (most recent first)

        Example:
            >>> history = await service.get_template_history(session, "tpl-123", "tenant-1")
            >>> for archive in history:
            ...     print(f"{archive.version} - {archive.archive_reason}")
        """
        # ORIGINAL QUERY: history.py line 41-50 (get_template_history endpoint)
        stmt = (
            select(TemplateArchive)
            .where(
                TemplateArchive.template_id == template_id,
                TemplateArchive.tenant_key == tenant_key,
            )
            .order_by(TemplateArchive.archived_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_archive_by_id(
        self,
        session: AsyncSession,
        archive_id: str,
        template_id: str,
        tenant_key: str,
    ) -> Optional[TemplateArchive]:
        """
        Get a specific archive entry with tenant isolation.

        Args:
            session: Database session
            archive_id: Archive entry UUID
            template_id: Template UUID (for additional validation)
            tenant_key: Tenant key for isolation (REQUIRED)

        Returns:
            TemplateArchive ORM object or None if not found

        Example:
            >>> archive = await service.get_archive_by_id(
            ...     session, "arc-456", "tpl-123", "tenant-1"
            ... )
        """
        # ORIGINAL QUERY: history.py line 91-98 (restore_template endpoint)
        stmt = select(TemplateArchive).where(
            TemplateArchive.id == archive_id,
            TemplateArchive.template_id == template_id,
            TemplateArchive.tenant_key == tenant_key,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_template_archive(
        self,
        session: AsyncSession,
        template: AgentTemplate,
        archive_reason: str,
        archive_type: str,
        archived_by: str,
    ) -> TemplateArchive:
        """
        Create an archive entry from a template's current state.

        Args:
            session: Database session
            template: AgentTemplate ORM object to archive
            archive_reason: Reason for archiving
            archive_type: Type of archive (e.g., "auto", "manual")
            archived_by: Username of person triggering archive

        Returns:
            Created TemplateArchive ORM object

        Example:
            >>> archive = await service.create_template_archive(
            ...     session, template, "Update user instructions", "auto", "alice"
            ... )
        """
        archive = TemplateArchive(
            tenant_key=template.tenant_key,
            template_id=template.id,
            product_id=template.product_id,
            name=template.name,
            category=template.category,
            role=template.role,
            system_instructions=template.system_instructions,
            user_instructions=template.user_instructions,
            variables=template.variables,
            behavioral_rules=template.behavioral_rules,
            success_criteria=template.success_criteria,
            version=template.version,
            archive_reason=archive_reason,
            archive_type=archive_type,
            archived_by=archived_by,
            usage_count_at_archive=template.usage_count,
            avg_generation_ms_at_archive=template.avg_generation_ms,
        )
        session.add(archive)
        return archive

    async def restore_template_from_archive(
        self,
        session: AsyncSession,
        template: AgentTemplate,
        archive: TemplateArchive,
    ) -> None:
        """
        Restore a template's content from an archive entry.

        Args:
            session: Database session
            template: AgentTemplate ORM object to restore into
            archive: TemplateArchive ORM object to restore from

        Example:
            >>> await service.restore_template_from_archive(session, template, archive)
        """
        # ORIGINAL QUERY: history.py line 135-139 (restore_template endpoint)
        template.variables = archive.variables
        template.behavioral_rules = archive.behavioral_rules
        template.success_criteria = archive.success_criteria
        template.version = archive.version

    async def reset_template_to_defaults(
        self,
        session: AsyncSession,
        template: AgentTemplate,
    ) -> None:
        """
        Reset a template's editable fields to default values.

        Args:
            session: Database session
            template: AgentTemplate ORM object to reset

        Example:
            >>> await service.reset_template_to_defaults(session, template)
        """
        # ORIGINAL QUERY: history.py line 198-201 (reset_template endpoint)
        template.user_instructions = None
        template.behavioral_rules = []
        template.success_criteria = []
        template.tags = []

    async def reset_system_instructions(
        self,
        session: AsyncSession,
        template: AgentTemplate,
    ) -> None:
        """
        Reset system instructions to canonical default.

        Args:
            session: Database session
            template: AgentTemplate ORM object to reset

        Example:
            >>> await service.reset_system_instructions(session, template)
        """
        # ORIGINAL QUERY: history.py line 264-270 (reset_system_instructions endpoint)
        template.system_instructions = (
            "# System Instructions\n\n"
            "Use acknowledge_job() to claim tasks.\n"
            "Use report_progress() to send updates.\n"
            "Use complete_job() when the task is finished.\n"
            "Use receive_messages() to check for orchestrator messages.\n"
        )

    # ============================================================================
    # Template Preview/Diff Methods (Phase 2 - Handover 1011)
    # ============================================================================

    async def check_cross_tenant_template_exists(
        self,
        session: AsyncSession,
        template_id: str,
    ) -> bool:
        """
        Check if a template exists across any tenant (for access denial detection).

        Args:
            session: Database session
            template_id: Template UUID

        Returns:
            True if template exists in any tenant, False otherwise

        Example:
            >>> exists = await service.check_cross_tenant_template_exists(session, "tpl-123")
        """
        # ORIGINAL QUERIES: crud.py line 311-314, history.py lines 169-172, 231-234
        # (update_template, reset_template, reset_system_instructions cross-tenant checks)
        stmt = select(AgentTemplate).where(AgentTemplate.id == template_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ============================================================================
    # Template Download Methods (Handover 1011 - Phase 4)
    # ============================================================================

    async def list_active_user_templates(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> list[AgentTemplate]:
        """
        List all active user-managed templates (excludes system roles).

        Used by agent template download endpoint to list downloadable templates.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation (REQUIRED)

        Returns:
            List of active AgentTemplate ORM objects (user-managed only)

        Example:
            >>> templates = await service.list_active_user_templates(session, "tenant-1")
            >>> for template in templates:
            ...     print(f"{template.role}: {template.name}")
        """
        # ORIGINAL QUERY: agent_templates.py lines 146-155 (list_agent_templates endpoint)
        stmt = (
            select(AgentTemplate)
            .where(AgentTemplate.tenant_key == tenant_key)
            .where(AgentTemplate.is_active)
            .where(AgentTemplate.role.notin_(list(SYSTEM_MANAGED_ROLES)))
            .order_by(AgentTemplate.role, AgentTemplate.name)
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_template_by_role(
        self,
        session: AsyncSession,
        tenant_key: str,
        role: str,
    ) -> Optional[AgentTemplate]:
        """
        Get an active template by role with tenant isolation.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation (REQUIRED)
            role: Template role to retrieve

        Returns:
            AgentTemplate ORM object or None if not found/inactive

        Example:
            >>> template = await service.get_template_by_role(session, "tenant-1", "backend developer")
            >>> if template:
            ...     print(template.system_instructions)
        """
        # ORIGINAL QUERY: agent_templates.py lines 218-226 (download_agent_template endpoint)
        stmt = (
            select(AgentTemplate)
            .where(AgentTemplate.tenant_key == tenant_key)
            .where(AgentTemplate.role == role)
            .where(AgentTemplate.is_active)
        )

        result = await session.execute(stmt)
        return result.scalar_one_or_none()
