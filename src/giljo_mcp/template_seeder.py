"""
Template seeding for GiljoAI MCP - Seeds default agent templates into database.

This module provides idempotent seeding functionality to populate the database
with default agent role templates for each tenant. Templates are sourced from
the legacy hard-coded templates in template_manager.py.

Key Features:
- Idempotent: Safe to run multiple times (skips if templates already exist)
- Multi-tenant: Each tenant gets isolated template set
- Production-grade: Comprehensive error handling and logging
- Cross-platform: Uses proper path handling

Usage:
    from src.giljo_mcp.template_seeder import seed_tenant_templates

    async with db_session() as session:
        count = await seed_tenant_templates(session, tenant_key)
        print(f"Seeded {count} templates")
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Dict, List, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager

logger = logging.getLogger(__name__)


async def seed_tenant_templates(session: AsyncSession, tenant_key: str) -> int:
    """
    Seed default agent templates for a tenant.

    This function is idempotent - it checks if the tenant already has templates
    and skips seeding if any exist. This prevents duplicate seeding during
    repeated installation runs or database migrations.

    Templates are sourced from UnifiedTemplateManager._legacy_templates and
    include comprehensive metadata (behavioral rules, success criteria, variables).

    Args:
        session: AsyncSession - Database session for operations
        tenant_key: str - Tenant key to seed templates for (must be non-empty)

    Returns:
        int - Number of templates seeded (0 if skipped, 6 if successful)

    Raises:
        ValueError: If tenant_key is None or empty
        Exception: If database operations fail (propagates SQLAlchemy exceptions)

    Example:
        >>> async with db_manager.get_session_async() as session:
        ...     count = await seed_tenant_templates(session, "default_tenant")
        ...     print(f"Seeded {count} templates")
        Seeded 6 templates
    """
    # Input validation
    if not tenant_key:
        logger.error("Cannot seed templates: tenant_key is empty or None")
        raise ValueError("tenant_key must be non-empty string")

    try:
        # Idempotency check - skip if tenant already has templates
        existing_count_result = await session.execute(
            select(func.count(AgentTemplate.id)).where(
                AgentTemplate.tenant_key == tenant_key
            )
        )
        existing_count = existing_count_result.scalar()

        if existing_count > 0:
            logger.info(
                f"Tenant '{tenant_key}' already has {existing_count} templates, skipping seed"
            )
            return 0

        # Load legacy templates from template_manager
        logger.debug(f"Loading legacy templates for tenant '{tenant_key}'")
        template_mgr = UnifiedTemplateManager()
        legacy_templates = template_mgr._legacy_templates

        # Define comprehensive metadata for each template
        # Extracted from original template content and handover requirements
        template_metadata = _get_template_metadata()

        # Seed each template
        seeded_count = 0
        current_time = datetime.now(timezone.utc)

        for role, content in legacy_templates.items():
            # Get metadata for this role (with defaults for any missing roles)
            metadata = template_metadata.get(role, {
                "category": "role",
                "behavioral_rules": ["Follow mission requirements"],
                "success_criteria": ["Mission objectives met"],
                "variables": ["project_name", "mission"]
            })

            # Create template instance
            template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=None,  # Tenant-level template (not product-specific)
                name=role,
                category=metadata["category"],
                role=role,
                template_content=content,
                variables=metadata["variables"],
                behavioral_rules=metadata["behavioral_rules"],
                success_criteria=metadata["success_criteria"],
                preferred_tool="claude",
                version="3.0.0",
                is_active=True,
                is_default=False,  # Tenant templates are not system defaults
                tags=["default", "tenant"],
                created_at=current_time
            )

            session.add(template)
            seeded_count += 1
            logger.debug(f"Added template for role '{role}' (tenant: {tenant_key})")

        # Commit all templates in single transaction
        await session.commit()

        logger.info(
            f"Successfully seeded {seeded_count} templates for tenant '{tenant_key}'"
        )
        return seeded_count

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Log and re-raise database/unexpected errors
        logger.error(
            f"Failed to seed templates for tenant '{tenant_key}': {e}",
            exc_info=True
        )
        raise


def _get_template_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Get comprehensive metadata for each agent role template.

    This metadata is based on the handover specification (lines 402-450)
    and defines behavioral rules, success criteria, and required variables
    for each agent role.

    Returns:
        Dict mapping role names to metadata dictionaries

    Note:
        This is a private function used internally by seed_tenant_templates.
        Metadata is kept separate from template content for maintainability.
    """
    return {
        "orchestrator": {
            "category": "role",
            "behavioral_rules": [
                "Read vision document completely (all parts)",
                "Delegate instead of implementing (3-tool rule)",
                "Challenge scope drift proactively",
                "Create 3 documentation artifacts at project close"
            ],
            "success_criteria": [
                "All project objectives met",
                "Clean handoff documentation created",
                "Zero scope creep maintained",
                "Effective team coordination achieved"
            ],
            "variables": ["project_name", "product_name", "project_mission"]
        },
        "analyzer": {
            "category": "role",
            "behavioral_rules": [
                "Analyze thoroughly before recommending",
                "Document all findings clearly",
                "Use Serena MCP for code exploration",
                "Focus on architecture and patterns"
            ],
            "success_criteria": [
                "Complete requirements documented",
                "Architecture aligned with vision",
                "All risks and dependencies identified",
                "Clear specifications for implementer"
            ],
            "variables": ["project_name", "custom_mission"]
        },
        "implementer": {
            "category": "role",
            "behavioral_rules": [
                "Write clean, maintainable code",
                "Follow project specifications exactly",
                "Use Serena MCP symbolic operations for edits",
                "Test changes incrementally"
            ],
            "success_criteria": [
                "All specified features implemented correctly",
                "Code follows project standards",
                "Tests passing",
                "No unauthorized scope changes"
            ],
            "variables": ["project_name", "custom_mission"]
        },
        "tester": {
            "category": "role",
            "behavioral_rules": [
                "Test thoroughly and systematically",
                "Document all defects clearly",
                "Create comprehensive test coverage",
                "Validate against requirements"
            ],
            "success_criteria": [
                "All features have test coverage",
                "Tests validate requirements correctly",
                "Coverage meets project standards",
                "Test documentation complete"
            ],
            "variables": ["project_name", "custom_mission"]
        },
        "reviewer": {
            "category": "role",
            "behavioral_rules": [
                "Review objectively and constructively",
                "Provide actionable feedback",
                "Check security best practices",
                "Validate architectural compliance"
            ],
            "success_criteria": [
                "Code meets quality standards",
                "Security best practices followed",
                "No critical issues remaining",
                "All feedback is actionable"
            ],
            "variables": ["project_name", "custom_mission"]
        },
        "documenter": {
            "category": "role",
            "behavioral_rules": [
                "Document clearly and comprehensively",
                "Create usage examples and guides",
                "Update all relevant artifacts",
                "Focus on implemented features only"
            ],
            "success_criteria": [
                "Documentation complete and accurate",
                "Usage examples provided",
                "All artifacts updated",
                "Documentation follows project style"
            ],
            "variables": ["project_name", "custom_mission"]
        }
    }
