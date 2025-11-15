"""
Slash commands for importing GiljoAI agent templates to Claude Code.

Provides /gil_import_productagents and /gil_import_personalagents commands
that invoke the complex backend export logic (backups, active filtering, etc.)

Handover 0084b: Agent Import Slash Commands
"""

import logging
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AgentTemplate, Product, User


logger = logging.getLogger(__name__)


async def handle_import_productagents(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Handle /gil_import_productagents slash command.

    Imports active agent templates to current product's .claude/agents folder.

    Args:
        db_session: Database session instance
        tenant_key: Current tenant key for multi-tenant isolation
        project_id: Optional project ID (currently unused)
        **kwargs: Additional arguments (reserved for future use)

    Returns:
        {
            "success": bool,
            "message": str,
            "exported_count": int,
            "files": list,
            "error": str (optional)
        }

    Process:
    1. Get user's active product from database
    2. Validate product has project_path configured
    3. Construct export path: {project_path}/.claude/agents
    4. Call export_templates_to_claude_code() with product path
    5. Return formatted result
    """
    try:
        # Late import to avoid circular dependency
        from api.endpoints.claude_export import (
            create_backup,
            create_zip_backup,
            generate_yaml_frontmatter,
        )

        # Get user by tenant key
        user_stmt = select(User).where(User.tenant_key == tenant_key)
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "message": f"User not found for tenant: {tenant_key}",
                "error": "USER_NOT_FOUND",
            }

        # Get active product for tenant
        product_stmt = select(Product).where(
            and_(
                Product.tenant_key == tenant_key,
                Product.is_active == True,
            )
        )
        product_result = await db_session.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        if not product:
            return {
                "success": False,
                "message": "No active product found. Please activate a product in the dashboard.",
                "error": "NO_ACTIVE_PRODUCT",
            }

        # Validate product has project_path configured
        if not product.project_path:
            return {
                "success": False,
                "message": (
                    f"Product '{product.name}' does not have a project path configured. "
                    "Please set the project path in the product settings."
                ),
                "error": "NO_PROJECT_PATH",
            }

        # Construct export path: {project_path}/.claude/agents
        project_path = Path(product.project_path).expanduser()
        export_path = project_path / ".claude" / "agents"

        # Validate project path exists
        if not project_path.exists():
            return {
                "success": False,
                "message": (
                    f"Product project path does not exist: {project_path}\n"
                    "Please verify the project path in product settings."
                ),
                "error": "INVALID_PROJECT_PATH",
            }

        # Create .claude/agents directory if it doesn't exist
        export_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"[handle_import_productagents] Exporting to product path: {export_path} "
            f"(tenant={tenant_key}, product={product.name})"
        )

        # Create backup before export
        backup_path = create_zip_backup(export_path)
        backup_info = None
        if backup_path:
            backup_info = {
                "backup_created": True,
                "backup_path": str(backup_path),
                "backup_size_bytes": backup_path.stat().st_size,
            }
            logger.info(f"[handle_import_productagents] Created pre-export backup: {backup_path}")
        else:
            backup_info = {"backup_created": False, "reason": "No existing files to backup"}

        # Query active templates for user's tenant (multi-tenant isolation)
        templates_stmt = (
            select(AgentTemplate)
            .where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active,
            )
            .order_by(AgentTemplate.name)
        )

        templates_result = await db_session.execute(templates_stmt)
        templates = templates_result.scalars().all()

        if not templates:
            logger.warning(f"No active templates found for tenant: {tenant_key}")
            return {
                "success": True,
                "exported_count": 0,
                "files": [],
                "message": "No active templates found for export",
            }

        # Export each template
        exported_files = []

        for template in templates:
            try:
                # Generate filename
                filename = f"{template.name}.md"
                file_path = export_path / filename

                # Create backup if file exists
                if file_path.exists():
                    create_backup(file_path)

                # Generate YAML frontmatter
                frontmatter = generate_yaml_frontmatter(
                    name=template.name,
                    role=template.role or template.name,
                    preferred_tool=template.tool,
                    description=template.description,
                )

                # Build complete file content
                content_parts = [frontmatter]

                # Add template content
                content_parts.append("\n")
                content_parts.append(template.template_content.strip())
                content_parts.append("\n")

                # Add behavioral rules if present
                if template.behavioral_rules and len(template.behavioral_rules) > 0:
                    content_parts.append("\n## Behavioral Rules\n")
                    content_parts.extend(f"- {rule}\n" for rule in template.behavioral_rules)

                # Add success criteria if present
                if template.success_criteria and len(template.success_criteria) > 0:
                    content_parts.append("\n## Success Criteria\n")
                    content_parts.extend(f"- {criterion}\n" for criterion in template.success_criteria)

                # Write file
                full_content = "".join(content_parts)
                file_path.write_text(full_content, encoding="utf-8")

                logger.info(f"Exported template: {template.name} to {file_path}")

                exported_files.append(
                    {
                        "name": template.name,
                        "path": str(file_path),
                    }
                )

            except Exception as e:
                logger.exception(f"Failed to export template {template.name}: {e}")
                # Continue with other templates rather than failing completely
                continue

        # Format success message
        exported_count = len(exported_files)
        backup_msg = ""
        if backup_info.get("backup_created"):
            backup_msg = f"\nBackup created: {backup_info.get('backup_path')}"

        return {
            "success": True,
            "message": (
                f"Successfully imported {exported_count} agent template(s) "
                f"to product '{product.name}'\n"
                f"Export path: {export_path}{backup_msg}"
            ),
            "exported_count": exported_count,
            "files": exported_files,
        }

    except Exception as e:
        logger.exception(f"[handle_import_productagents] Failed to import agents: {e}")
        return {
            "success": False,
            "message": f"Failed to import agents to product: {e!s}",
            "error": "UNEXPECTED_ERROR",
            "details": str(e),
        }


async def handle_import_personalagents(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Handle /gil_import_personalagents slash command.

    Imports active agent templates to ~/.claude/agents (global personal).

    Args:
        db_session: Database session instance
        tenant_key: Current tenant key for multi-tenant isolation
        project_id: Optional project ID (currently unused)
        **kwargs: Additional arguments (reserved for future use)

    Returns:
        {
            "success": bool,
            "message": str,
            "exported_count": int,
            "files": list,
            "error": str (optional)
        }

    Process:
    1. Use personal export path: ~/.claude/agents
    2. Export templates using sync database operations
    3. Return formatted result
    """
    try:
        # Late import to avoid circular dependency
        from api.endpoints.claude_export import (
            create_backup,
            create_zip_backup,
            generate_yaml_frontmatter,
        )

        # Get user by tenant key
        user_stmt = select(User).where(User.tenant_key == tenant_key)
        user_result = await db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "message": f"User not found for tenant: {tenant_key}",
                "error": "USER_NOT_FOUND",
            }

        # Use personal export path: ~/.claude/agents
        export_path = Path.home() / ".claude" / "agents"

        # Create directory if it doesn't exist
        export_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"[handle_import_personalagents] Exporting to personal path: {export_path} (tenant={tenant_key})")

        # Create backup before export
        backup_path = create_zip_backup(export_path)
        backup_info = None
        if backup_path:
            backup_info = {
                "backup_created": True,
                "backup_path": str(backup_path),
                "backup_size_bytes": backup_path.stat().st_size,
            }
            logger.info(f"[handle_import_personalagents] Created pre-export backup: {backup_path}")
        else:
            backup_info = {"backup_created": False, "reason": "No existing files to backup"}

        # Query active templates for user's tenant (multi-tenant isolation)
        templates_stmt = (
            select(AgentTemplate)
            .where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active,
            )
            .order_by(AgentTemplate.name)
        )

        templates_result = await db_session.execute(templates_stmt)
        templates = templates_result.scalars().all()

        if not templates:
            logger.warning(f"No active templates found for tenant: {tenant_key}")
            return {
                "success": True,
                "exported_count": 0,
                "files": [],
                "message": "No active templates found for export",
            }

        # Export each template
        exported_files = []

        for template in templates:
            try:
                # Generate filename
                filename = f"{template.name}.md"
                file_path = export_path / filename

                # Create backup if file exists
                if file_path.exists():
                    create_backup(file_path)

                # Generate YAML frontmatter
                frontmatter = generate_yaml_frontmatter(
                    name=template.name,
                    role=template.role or template.name,
                    preferred_tool=template.tool,
                    description=template.description,
                )

                # Build complete file content
                content_parts = [frontmatter]

                # Add template content
                content_parts.append("\n")
                content_parts.append(template.template_content.strip())
                content_parts.append("\n")

                # Add behavioral rules if present
                if template.behavioral_rules and len(template.behavioral_rules) > 0:
                    content_parts.append("\n## Behavioral Rules\n")
                    content_parts.extend(f"- {rule}\n" for rule in template.behavioral_rules)

                # Add success criteria if present
                if template.success_criteria and len(template.success_criteria) > 0:
                    content_parts.append("\n## Success Criteria\n")
                    content_parts.extend(f"- {criterion}\n" for criterion in template.success_criteria)

                # Write file
                full_content = "".join(content_parts)
                file_path.write_text(full_content, encoding="utf-8")

                logger.info(f"Exported template: {template.name} to {file_path}")

                exported_files.append(
                    {
                        "name": template.name,
                        "path": str(file_path),
                    }
                )

            except Exception as e:
                logger.exception(f"Failed to export template {template.name}: {e}")
                # Continue with other templates rather than failing completely
                continue

        # Format success message
        exported_count = len(exported_files)
        backup_msg = ""
        if backup_info.get("backup_created"):
            backup_msg = f"\nBackup created: {backup_info.get('backup_path')}"

        return {
            "success": True,
            "message": (
                f"Successfully imported {exported_count} agent template(s) "
                f"to personal agents\n"
                f"Export path: {export_path}{backup_msg}"
            ),
            "exported_count": exported_count,
            "files": exported_files,
        }

    except Exception as e:
        logger.exception(f"[handle_import_personalagents] Failed to import agents: {e}")
        return {
            "success": False,
            "message": f"Failed to import agents to personal directory: {e!s}",
            "error": "UNEXPECTED_ERROR",
            "details": str(e),
        }
