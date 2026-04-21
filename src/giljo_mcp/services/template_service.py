# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from contextlib import asynccontextmanager
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    BaseGiljoError,
    TemplateNotFoundError,
    ValidationError,
)

# Model imports: Use domain-specific imports (Post-0128a)
from giljo_mcp.models.templates import AgentTemplate, TemplateArchive
from giljo_mcp.repositories.template_repository import TemplateRepository
from giljo_mcp.schemas.jsonb_validators import validate_behavioral_rules, validate_success_criteria
from giljo_mcp.schemas.service_responses import (
    TemplateCreateResult,
    TemplateDetail,
    TemplateGetResult,
    TemplateListResult,
    TemplateUpdateResult,
)
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

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager, session: AsyncSession | None = None):
        """
        Initialize TemplateService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            session: Optional AsyncSession for test transaction isolation
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._session = session
        self._repo = TemplateRepository()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.

        Returns:
            Context manager for database session
        """
        if self._session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._session

            return _test_session_wrapper()

        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

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

            async with self._get_session() as session:
                # TENANT ISOLATION: Only return templates for the specified tenant
                templates = await self._repo.list_by_tenant(session, tenant_key)

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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

            async with self._get_session() as session:
                # Retrieve template by ID or name
                if template_id:
                    template = await self._repo.get_by_id(session, template_id, tenant_key)
                else:
                    template = await self._repo.get_by_name(session, template_name, tenant_key)

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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
            cli_tool: AI coding agent identifier
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

            async with self._get_session() as session:
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

                await self._repo.add_template(session, template)
                await self._repo.commit(session)

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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

            async with self._get_session() as session:
                # Get template with tenant isolation
                template = await self._repo.get_by_id(session, template_id, tenant_key)

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

                await self._repo.commit(session)

                self._logger.info(f"Updated template {template_id}")

                return TemplateUpdateResult(
                    template_id=template_id,
                    updated=True,
                )

        except (ValidationError, TemplateNotFoundError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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
            role = await self._repo.get_template_role(session, template_id)
            if not role:
                return False, "Template not found"

        # Count currently active distinct roles (excluding the one being toggled)
        active_roles = await self._repo.get_active_distinct_roles(session, tenant_key, template_id)

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
        return await self._repo.get_by_id(session, template_id, tenant_key)

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
        return await self._repo.list_with_filters(session, tenant_key, role, is_active)

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
        return await self._repo.check_name_exists(session, tenant_key, name)

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
        return await self._repo.get_defaults_by_role(session, tenant_key, role, product_id)

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
        return await self._repo.count_active_user_managed(session, tenant_key)

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
        await self._repo.nullify_job_template_refs(session, template_id)

        # 2. Delete related TemplateUsageStats records
        await self._repo.delete_usage_stats(session, template_id)

        # 3. Delete related TemplateArchive records (version history)
        await self._repo.delete_archives(session, template_id)

        # 4. Delete the template itself
        await self._repo.delete_template(session, template)

        await self._repo.commit(session)

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
        return await self._repo.get_template_history(session, template_id, tenant_key)

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
        return await self._repo.get_archive_by_id(session, archive_id, template_id, tenant_key)

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
        await self._repo.add_archive(session, archive)
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
        template.behavioral_rules = validate_behavioral_rules(archive.behavioral_rules)
        template.success_criteria = validate_success_criteria(archive.success_criteria)
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
        template.behavioral_rules = validate_behavioral_rules([])
        template.success_criteria = validate_success_criteria([])
        template.tags = []

    async def reset_system_instructions(
        self,
        session: AsyncSession,
        template: AgentTemplate,
    ) -> None:
        """
        Reset system instructions to canonical MCP bootstrap (Handover 0814).

        Uses _get_mcp_bootstrap_section() as the single source of truth,
        replacing the stale hardcoded fallback.

        Args:
            session: Database session
            template: AgentTemplate ORM object to reset
        """
        from giljo_mcp.template_seeder import _get_mcp_bootstrap_section

        template.system_instructions = _get_mcp_bootstrap_section()

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
        return await self._repo.check_template_exists_any_tenant(session, template_id)

    # ============================================================================
    # Export Tracking (Sprint 003b)
    # ============================================================================

    async def mark_templates_exported(
        self,
        template_ids: list[str],
        tenant_key: str,
    ) -> int:
        """
        Update last_exported_at timestamp for a set of templates.

        Used by list_agent_templates MCP tool after exporting templates
        to detect staleness on next export.

        Args:
            template_ids: List of template UUIDs to mark as exported.
            tenant_key: Tenant isolation key (REQUIRED).

        Returns:
            Number of templates updated.

        Example:
            >>> updated = await service.mark_templates_exported(
            ...     ["tpl-1", "tpl-2"], "tenant-1"
            ... )
        """
        from datetime import datetime, timezone

        if not template_ids:
            return 0

        export_timestamp = datetime.now(timezone.utc)

        async with self._get_session() as session:
            updated_count = await self._repo.update_exported_timestamps(
                session, template_ids, tenant_key, export_timestamp
            )
            self._logger.info(
                "Updated last_exported_at for %d template(s) via MCP export",
                updated_count,
            )
            return updated_count

    # ============================================================================
    # Session Commit Helpers (write discipline — no endpoint commits)
    # ============================================================================

    async def add_and_commit_template(
        self,
        session: AsyncSession,
        template: "AgentTemplate",
    ) -> "AgentTemplate":
        """
        Add a new template to the session, commit, and refresh.

        Used by endpoints that construct the AgentTemplate entity themselves
        (e.g., create_template with complex validation logic).

        Args:
            session: Database session
            template: Fully constructed AgentTemplate ORM object

        Returns:
            The refreshed AgentTemplate after commit.
        """
        return await self._repo.add_and_commit_template(session, template)

    async def commit_and_refresh_template(
        self,
        session: AsyncSession,
        template: "AgentTemplate",
    ) -> "AgentTemplate":
        """
        Commit pending changes and refresh the template.

        Used after chained service operations (archive + restore, archive + reset)
        that mutate the template in-session but do not commit.

        Args:
            session: Database session
            template: AgentTemplate ORM object with pending changes

        Returns:
            The refreshed AgentTemplate after commit.
        """
        return await self._repo.commit_and_refresh_template(session, template)

    # ============================================================================
    # Product Scoping (Handover: setup-split)
    # ============================================================================

    async def clone_templates_to_product(
        self,
        source_product_id: Optional[str],
        target_product_id: str,
        tenant_key: Optional[str] = None,
        seed_mode: bool = False,
    ) -> int:
        """
        Clone templates from one product (or tenant-level) to another product.

        Copies all active templates from source_product_id to target_product_id.
        Skips templates that already exist on the target (by name + version).

        Args:
            source_product_id: Source product UUID, or None for tenant-level templates.
            target_product_id: Target product UUID (required).
            tenant_key: Tenant key for isolation.
            seed_mode: If True, cloned agents are enabled (for new product seeding).
                      If False, cloned agents are disabled (for user-initiated clones).

        Returns:
            Number of templates cloned.

        Raises:
            ValidationError: If target_product_id is missing or no tenant context.
        """
        from datetime import datetime, timezone

        if not target_product_id:
            raise ValidationError(
                message="target_product_id is required",
                context={"operation": "clone_templates_to_product"},
            )

        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(
                message="No tenant context available",
                context={"operation": "clone_templates_to_product"},
            )

        async with self._get_session() as session:
            # Fetch source templates
            source_templates = await self._repo.get_active_by_product(session, tenant_key, source_product_id)

            if not source_templates:
                self._logger.info("No source templates to clone")
                return 0

            # Check existing on target to avoid duplicates
            existing_keys = await self._repo.get_existing_name_versions(session, tenant_key, target_product_id)

            cloned_count = 0
            current_time = datetime.now(timezone.utc)

            for src in source_templates:
                if (src.name, src.version) in existing_keys:
                    continue

                clone = AgentTemplate(
                    id=str(uuid4()),
                    tenant_key=tenant_key,
                    product_id=target_product_id,
                    name=src.name,
                    category=src.category,
                    role=src.role,
                    cli_tool=src.cli_tool,
                    background_color=src.background_color,
                    description=src.description,
                    system_instructions=src.system_instructions,
                    user_instructions=src.user_instructions,
                    model=src.model,
                    tools=src.tools,
                    variables=src.variables or [],
                    behavioral_rules=src.behavioral_rules or [],
                    success_criteria=src.success_criteria or [],
                    tool=src.tool,
                    version=src.version,
                    is_active=seed_mode,  # seed_mode=True: new product gets enabled agents; False: user-initiated clone
                    is_default=src.is_default,
                    tags=src.tags or [],
                    created_at=current_time,
                )
                session.add(clone)
                cloned_count += 1

            if cloned_count > 0:
                await self._repo.commit(session)

            self._logger.info(
                "Cloned %d template(s) to product %s for tenant %s",
                cloned_count,
                target_product_id,
                tenant_key,
            )
            return cloned_count

    async def seed_product_defaults(
        self,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Seed agent templates for a product. Three paths:

        1. Product already has templates → do nothing (idempotent)
        2. Orphan templates exist (product_id=NULL) → adopt them to this product
           (fallback for edge cases; main orphan migration runs at startup)
        3. No orphans → clone from system defaults (enabled, ready to use)

        Args:
            product_id: Product UUID to seed templates for.
            tenant_key: Tenant key for isolation.

        Returns:
            Number of templates seeded/adopted (0 if product already has templates).
        """
        async with self._get_session() as session:
            # Check if product already has templates
            existing_count = await self._repo.count_by_product(session, tenant_key, product_id)

            if existing_count > 0:
                self._logger.info(
                    "Product %s already has %d templates, skipping seed",
                    product_id,
                    existing_count,
                )
                return 0

            # Path 2: Adopt orphan templates (active AND inactive) from this tenant
            orphans = await self._repo.get_orphans(session, tenant_key)
            if orphans:
                adopted = 0
                for template in orphans:
                    template.product_id = product_id
                    adopted += 1
                await self._repo.commit(session)
                self._logger.info(
                    "Adopted %d orphan template(s) to product %s",
                    adopted,
                    product_id,
                )
                return adopted

        # Path 3: No orphans — seed from code-defined defaults (fresh install)
        return await self._seed_from_code_defaults(product_id, tenant_key)

    async def _seed_from_code_defaults(self, product_id: str, tenant_key: str) -> int:
        """Seed a product with factory-default templates from code (not DB).

        Source of truth is _get_default_templates_v103() in template_seeder.py.
        These can never be accidentally deleted or mutated by users.
        """
        from datetime import datetime, timezone
        from uuid import uuid4

        from giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
        from giljo_mcp.template_seeder import _get_default_templates_v103, _get_mcp_bootstrap_section

        defaults = _get_default_templates_v103()
        bootstrap = _get_mcp_bootstrap_section()
        current_time = datetime.now(timezone.utc)
        seeded = 0

        async with self._get_session() as session:
            for tpl in defaults:
                if tpl["role"] in SYSTEM_MANAGED_ROLES:
                    continue

                template = AgentTemplate(
                    id=str(uuid4()),
                    tenant_key=tenant_key,
                    product_id=product_id,
                    name=tpl["name"],
                    category="role",
                    role=tpl["role"],
                    cli_tool=tpl["cli_tool"],
                    background_color=tpl["background_color"],
                    description=tpl["description"],
                    system_instructions=bootstrap,
                    user_instructions=tpl["user_instructions"],
                    model=tpl.get("model", "sonnet"),
                    tools=tpl.get("tools"),
                    variables=[],
                    behavioral_rules=tpl.get("behavioral_rules", []),
                    success_criteria=tpl.get("success_criteria", []),
                    tool=tpl["cli_tool"],
                    version=tpl.get("version", "1.0.0"),
                    is_active=True,  # New product gets enabled agents
                    is_default=True,
                    tags=["default"],
                    created_at=current_time,
                )
                session.add(template)
                seeded += 1

            if seeded > 0:
                await self._repo.commit(session)

            self._logger.info(
                "Seeded %d default template(s) from code for product %s",
                seeded,
                product_id,
            )
            return seeded
