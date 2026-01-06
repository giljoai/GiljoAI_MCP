"""
Template management tools for the MCP server.
Provides tools for managing agent templates with versioning and augmentation.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional

from fastmcp import FastMCP
from sqlalchemy import and_, select, update
from sqlalchemy.orm import selectinload

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentTemplate, TemplateArchive, TemplateAugmentation, TemplateUsageStats
from giljo_mcp.template_manager import extract_variables, process_template
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


def register_template_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register template management tools with the MCP server"""

    @mcp.tool()
    async def list_agent_templates(
        product_id: Optional[str] = None,
        category: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = True,
    ) -> dict[str, Any]:
        """
        List available agent templates with optional filters

        Args:
            product_id: Optional product ID filter
            category: Optional category filter ('role', 'project_type', 'custom')
            role: Optional role filter (e.g., 'orchestrator', 'analyzer')
            is_active: Filter by active status (default: True)

        Returns:
            List of available templates with metadata
        """
        try:
            async with db_manager.get_session_async() as session:
                query = select(AgentTemplate)

                # Apply filters
                filters = []
                if product_id:
                    filters.append(AgentTemplate.product_id == product_id)
                if category:
                    filters.append(AgentTemplate.category == category)
                if role:
                    filters.append(AgentTemplate.role == role)
                if is_active is not None:
                    filters.append(AgentTemplate.is_active == is_active)

                if filters:
                    query = query.where(and_(*filters))

                # Order by usage count for recommendations
                query = query.order_by(AgentTemplate.usage_count.desc())

                result = await session.execute(query)
                templates = result.scalars().all()

                template_list = []
                for template in templates:
                    template_list.append(
                        {
                            "id": str(template.id),
                            "name": template.name,
                            "category": template.category,
                            "role": template.role,
                            "project_type": template.project_type,
                            "description": template.description,
                            "version": template.version,
                            "is_default": template.is_default,
                            "usage_count": template.usage_count,
                            "variables": template.variables or [],
                            "tags": template.tags or [],
                            "created_at": (template.created_at.isoformat() if template.created_at else None),
                        }
                    )

                return {
                    "success": True,
                    "count": len(template_list),
                    "templates": template_list,
                }

        except Exception as e:
            logger.exception(f"Failed to list templates: {e}")
            return {"success": False, "error": str(e)}


    @mcp.tool()
    async def create_agent_template(
        name: str,
        category: str,
        template_content: str,
        product_id: Optional[str] = None,
        role: Optional[str] = None,
        project_type: Optional[str] = None,
        description: Optional[str] = None,
        behavioral_rules: Optional[list[str]] = None,
        success_criteria: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        is_default: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new agent template

        Args:
            name: Template name
            category: Template category ('role', 'project_type', 'custom')
            template_content: The template text with {variable} placeholders
            product_id: Optional product ID for product-specific templates
            role: Optional role designation
            project_type: Optional project type
            description: Optional description
            behavioral_rules: Optional list of behavioral rules
            success_criteria: Optional list of success criteria
            tags: Optional list of tags
            is_default: Whether this should be the default for its role

        Returns:
            Created template details
        """
        try:
            async with db_manager.get_session_async() as session:
                # Extract variables from template content
                variables = extract_variables(template_content)

                # Get tenant key
                tenant_key = tenant_manager.get_current_tenant()

                # If setting as default, unset other defaults for this role
                if is_default and role:
                    await session.execute(
                        update(AgentTemplate)
                        .where(
                            AgentTemplate.role == role,
                            AgentTemplate.product_id == product_id,
                        )
                        .values(is_default=False)
                    )

                # Create template
                template = AgentTemplate(
                    tenant_key=tenant_key or "",
                    product_id=product_id,
                    name=name,
                    category=category,
                    role=role,
                    project_type=project_type,
                    template_content=template_content,
                    description=description,
                    variables=variables,
                    behavioral_rules=behavioral_rules or [],
                    success_criteria=success_criteria or [],
                    tags=tags or [],
                    is_default=is_default,
                    created_by="system",
                    created_at=datetime.utcnow(),
                )

                session.add(template)
                await session.commit()

                logger.info(f"Created template '{name}' with ID {template.id}")

                return {
                    "success": True,
                    "template_id": str(template.id),
                    "name": name,
                    "category": category,
                    "variables": variables,
                    "version": template.version,
                }

        except Exception as e:
            logger.exception(f"Failed to create template: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def update_agent_template(
        template_id: str,
        template_content: Optional[str] = None,
        description: Optional[str] = None,
        behavioral_rules: Optional[list[str]] = None,
        success_criteria: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        archive_reason: str = "Manual update",
    ) -> dict[str, Any]:
        """
        Update an existing template (auto-archives previous version)

        Args:
            template_id: Template ID to update
            template_content: New template content
            description: New description
            behavioral_rules: New behavioral rules
            success_criteria: New success criteria
            tags: New tags
            archive_reason: Reason for archiving previous version

        Returns:
            Updated template details
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get existing template
                query = select(AgentTemplate).where(AgentTemplate.id == template_id)
                result = await session.execute(query)
                template = result.scalar_one_or_none()

                if not template:
                    return {
                        "success": False,
                        "error": f"Template {template_id} not found",
                    }

                # Archive current version
                archive = TemplateArchive(
                    tenant_key=template.tenant_key,
                    template_id=template.id,
                    product_id=template.product_id,
                    name=template.name,
                    category=template.category,
                    role=template.role,
                    template_content=template.template_content,
                    variables=template.variables,
                    behavioral_rules=template.behavioral_rules,
                    success_criteria=template.success_criteria,
                    version=template.version,
                    archive_reason=archive_reason,
                    archive_type="auto",
                    archived_by="system",
                    usage_count_at_archive=template.usage_count,
                    avg_generation_ms_at_archive=template.avg_generation_ms,
                )
                session.add(archive)

                # Update template
                if template_content:
                    template.template_content = template_content
                    # Re-extract variables
                    extract_variables(template_content)

                if description is not None:
                    template.description = description
                if behavioral_rules is not None:
                    template.behavioral_rules = behavioral_rules
                if success_criteria is not None:
                    template.success_criteria = success_criteria
                if tags is not None:
                    template.tags = tags

                # Increment version
                version_parts = template.version.split(".")
                version_parts[-1] = str(int(version_parts[-1]) + 1)
                template.version = ".".join(version_parts)
                template.updated_at = datetime.utcnow()

                await session.commit()

                logger.info(f"Updated template '{template.name}' to version {template.version}")

                return {
                    "success": True,
                    "template_id": str(template.id),
                    "name": template.name,
                    "new_version": template.version,
                    "archived_version": archive.version,
                }

        except Exception as e:
            logger.exception(f"Failed to update template: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def archive_template(template_id: str, reason: str, archive_type: str = "manual") -> dict[str, Any]:
        """
        Archive a template version (does not modify the template)

        Args:
            template_id: Template ID to archive
            reason: Reason for archiving
            archive_type: Type of archive ('manual', 'auto', 'scheduled')

        Returns:
            Archive confirmation
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get template
                query = select(AgentTemplate).where(AgentTemplate.id == template_id)
                result = await session.execute(query)
                template = result.scalar_one_or_none()

                if not template:
                    return {
                        "success": False,
                        "error": f"Template {template_id} not found",
                    }

                # Create archive
                archive = TemplateArchive(
                    tenant_key=template.tenant_key,
                    template_id=template.id,
                    product_id=template.product_id,
                    name=template.name,
                    category=template.category,
                    role=template.role,
                    template_content=template.template_content,
                    variables=template.variables,
                    behavioral_rules=template.behavioral_rules,
                    success_criteria=template.success_criteria,
                    version=template.version,
                    archive_reason=reason,
                    archive_type=archive_type,
                    archived_by="system",
                    usage_count_at_archive=template.usage_count,
                    avg_generation_ms_at_archive=template.avg_generation_ms,
                )

                session.add(archive)
                await session.commit()

                logger.info(f"Archived template '{template.name}' version {template.version}")

                return {
                    "success": True,
                    "archive_id": str(archive.id),
                    "template_name": template.name,
                    "archived_version": template.version,
                    "archive_reason": reason,
                }

        except Exception as e:
            logger.exception(f"Failed to archive template: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def create_template_augmentation(
        template_id: str,
        name: str,
        augmentation_type: str,
        content: str,
        target_section: Optional[str] = None,
        conditions: Optional[dict[str, Any]] = None,
        priority: int = 0,
    ) -> dict[str, Any]:
        """
        Create a template augmentation for runtime customization

        Args:
            template_id: Template to augment
            name: Augmentation name
            augmentation_type: Type ('append', 'prepend', 'replace', 'inject')
            content: Content to add/replace
            target_section: Section to target (for inject/replace)
            conditions: Conditions for applying augmentation
            priority: Order of application (lower = earlier)

        Returns:
            Created augmentation details
        """
        try:
            async with db_manager.get_session_async() as session:
                # Verify template exists
                query = select(AgentTemplate).where(AgentTemplate.id == template_id)
                result = await session.execute(query)
                template = result.scalar_one_or_none()

                if not template:
                    return {
                        "success": False,
                        "error": f"Template {template_id} not found",
                    }

                # Get tenant key
                tenant_key = tenant_manager.get_current_tenant()

                # Create augmentation
                augmentation = TemplateAugmentation(
                    tenant_key=tenant_key or "",
                    template_id=template_id,
                    name=name,
                    augmentation_type=augmentation_type,
                    target_section=target_section,
                    content=content,
                    conditions=conditions or {},
                    priority=priority,
                )

                session.add(augmentation)
                await session.commit()

                logger.info(f"Created augmentation '{name}' for template '{template.name}'")

                return {
                    "success": True,
                    "augmentation_id": str(augmentation.id),
                    "template_name": template.name,
                    "augmentation_name": name,
                    "type": augmentation_type,
                }

        except Exception as e:
            logger.exception(f"Failed to create augmentation: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def restore_template_version(archive_id: str, restore_as_new: bool = False) -> dict[str, Any]:
        """
        Restore an archived template version

        Args:
            archive_id: Archive ID to restore
            restore_as_new: Create as new template instead of overwriting

        Returns:
            Restoration confirmation
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get archive
                query = select(TemplateArchive).where(TemplateArchive.id == archive_id)
                result = await session.execute(query)
                archive = result.scalar_one_or_none()

                if not archive:
                    return {
                        "success": False,
                        "error": f"Archive {archive_id} not found",
                    }

                if not archive.is_restorable:
                    return {"success": False, "error": "This archive is not restorable"}

                if restore_as_new:
                    # Create new template from archive
                    template = AgentTemplate(
                        tenant_key=archive.tenant_key,
                        product_id=archive.product_id,
                        name=f"{archive.name}_restored",
                        category=archive.category,
                        role=archive.role,
                        template_content=archive.template_content,
                        variables=archive.variables,
                        behavioral_rules=archive.behavioral_rules,
                        success_criteria=archive.success_criteria,
                        version="1.0.0",
                        created_by="system_restore",
                    )
                    session.add(template)
                else:
                    # Overwrite existing template
                    query = select(AgentTemplate).where(AgentTemplate.id == archive.template_id)
                    result = await session.execute(query)
                    template = result.scalar_one_or_none()

                    if template:
                        # Archive current version first
                        new_archive = TemplateArchive(
                            tenant_key=template.tenant_key,
                            template_id=template.id,
                            product_id=template.product_id,
                            name=template.name,
                            category=template.category,
                            role=template.role,
                            template_content=template.template_content,
                            variables=template.variables,
                            behavioral_rules=template.behavioral_rules,
                            success_criteria=template.success_criteria,
                            version=template.version,
                            archive_reason="Replaced by restoration",
                            archive_type="auto",
                            archived_by="system_restore",
                        )
                        session.add(new_archive)

                        # Restore from archive
                        template.template_content = archive.template_content
                        template.variables = archive.variables
                        template.behavioral_rules = archive.behavioral_rules
                        template.success_criteria = archive.success_criteria
                        template.updated_at = datetime.utcnow()

                # Update archive record
                archive.restored_at = datetime.utcnow()
                archive.restored_by = "system"

                await session.commit()

                logger.info(f"Restored template from archive {archive_id}")

                return {
                    "success": True,
                    "template_id": str(template.id) if template else None,
                    "template_name": template.name if template else archive.name,
                    "restored_version": archive.version,
                    "restore_type": "new" if restore_as_new else "overwrite",
                }

        except Exception as e:
            logger.exception(f"Failed to restore template: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def suggest_template(
        project_type: Optional[str] = None,
        role: str = "orchestrator",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Suggest the best template based on context and usage stats

        Args:
            project_type: Type of project
            role: Agent role
            context: Additional context for selection

        Returns:
            Suggested template with reasoning
        """
        try:
            async with db_manager.get_session_async() as session:
                # Build query for templates
                query = select(AgentTemplate).where(AgentTemplate.is_active, AgentTemplate.role == role)

                if project_type:
                    # First try project-specific template
                    specific_query = query.where(AgentTemplate.project_type == project_type)
                    result = await session.execute(specific_query)
                    templates = result.scalars().all()

                    if templates:
                        # Sort by usage and success rate
                        best_template = max(templates, key=lambda t: t.usage_count)
                        reason = f"Project-specific template for {project_type}"
                    else:
                        # Fall back to general role template
                        result = await session.execute(query)
                        templates = result.scalars().all()

                        if templates:
                            best_template = max(templates, key=lambda t: (t.is_default, t.usage_count))
                            reason = f"Default template for {role} role"
                        else:
                            return {
                                "success": False,
                                "error": f"No templates found for role '{role}'",
                            }
                else:
                    # Get default or most used template for role
                    result = await session.execute(query)
                    templates = result.scalars().all()

                    if templates:
                        best_template = max(templates, key=lambda t: (t.is_default, t.usage_count))
                        reason = "Most frequently used template"
                    else:
                        return {
                            "success": False,
                            "error": f"No templates found for role '{role}'",
                        }

                # Get recent usage stats
                stats_query = (
                    select(TemplateUsageStats)
                    .where(TemplateUsageStats.template_id == best_template.id)
                    .order_by(TemplateUsageStats.used_at.desc())
                    .limit(10)
                )

                stats_result = await session.execute(stats_query)
                recent_stats = stats_result.scalars().all()

                avg_generation_ms = (
                    sum(s.generation_ms or 0 for s in recent_stats) / len(recent_stats) if recent_stats else 0
                )

                return {
                    "success": True,
                    "suggestion": {
                        "template_id": str(best_template.id),
                        "name": best_template.name,
                        "category": best_template.category,
                        "reason": reason,
                        "usage_count": best_template.usage_count,
                        "avg_generation_ms": avg_generation_ms,
                        "variables": best_template.variables or [],
                        "description": best_template.description,
                    },
                }

        except Exception as e:
            logger.exception(f"Failed to suggest template: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_template_stats(template_id: Optional[str] = None, days: int = 30) -> dict[str, Any]:
        """
        Get usage statistics for templates

        Args:
            template_id: Optional specific template ID
            days: Number of days to analyze (default: 30)

        Returns:
            Template usage statistics
        """
        try:
            async with db_manager.get_session_async() as session:
                from datetime import timedelta

                cutoff_date = datetime.utcnow() - timedelta(days=days)

                if template_id:
                    # Stats for specific template
                    query = select(TemplateUsageStats).where(
                        TemplateUsageStats.template_id == template_id,
                        TemplateUsageStats.used_at >= cutoff_date,
                    )
                else:
                    # Stats for all templates
                    query = select(TemplateUsageStats).where(TemplateUsageStats.used_at >= cutoff_date)

                result = await session.execute(query)
                stats = result.scalars().all()

                # Aggregate statistics
                template_stats = {}
                for stat in stats:
                    tid = str(stat.template_id)
                    if tid not in template_stats:
                        template_stats[tid] = {
                            "usage_count": 0,
                            "total_generation_ms": 0,
                            "completed_count": 0,
                            "total_tokens": 0,
                            "augmentations_used": set(),
                        }

                    template_stats[tid]["usage_count"] += 1
                    template_stats[tid]["total_generation_ms"] += stat.generation_ms or 0
                    if stat.agent_completed:
                        template_stats[tid]["completed_count"] += 1
                    template_stats[tid]["total_tokens"] += stat.tokens_used or 0
                    if stat.augmentations_applied:
                        template_stats[tid]["augmentations_used"].update(stat.augmentations_applied)

                # Calculate averages and format output
                results = []
                for tid, tstats in template_stats.items():
                    # Get template name
                    template_query = select(AgentTemplate).where(AgentTemplate.id == tid)
                    template_result = await session.execute(template_query)
                    template = template_result.scalar_one_or_none()

                    if template:
                        results.append(
                            {
                                "template_id": tid,
                                "template_name": template.name,
                                "usage_count": tstats["usage_count"],
                                "avg_generation_ms": (
                                    tstats["total_generation_ms"] / tstats["usage_count"]
                                    if tstats["usage_count"] > 0
                                    else 0
                                ),
                                "completion_rate": (
                                    tstats["completed_count"] / tstats["usage_count"]
                                    if tstats["usage_count"] > 0
                                    else 0
                                ),
                                "avg_tokens": (
                                    tstats["total_tokens"] / tstats["usage_count"] if tstats["usage_count"] > 0 else 0
                                ),
                                "unique_augmentations": len(tstats["augmentations_used"]),
                            }
                        )

                # Sort by usage count
                results.sort(key=lambda x: x["usage_count"], reverse=True)

                return {
                    "success": True,
                    "period_days": days,
                    "total_templates": len(results),
                    "total_usage": sum(r["usage_count"] for r in results),
                    "statistics": results,
                }

        except Exception as e:
            logger.exception(f"Failed to get template stats: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Template management tools registered")
