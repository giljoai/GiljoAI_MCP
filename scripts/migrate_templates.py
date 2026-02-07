#!/usr/bin/env python3
"""
Migration script to move templates from mission_templates.py to database.
This is a one-time migration for Project 3.9.b.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.giljo_mcp.config_manager import load_config
from src.giljo_mcp.template_adapter import MissionTemplateGenerator


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_templates():
    """Migrate hardcoded templates to database"""

    # Load configuration
    config = load_config()

    # Build database URL
    if config.database.type == "postgresql":
        db_url = DatabaseManager.build_postgresql_url(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database_name,
            username=config.database.username,
            password=config.database.password or "4010",
        )
    else:
        db_url = DatabaseManager.build_sqlite_url(str(config.database.sqlite_path))

    # Create database manager
    db_manager = DatabaseManager(db_url, is_async=True)

    try:
        # Ensure tables exist
        await db_manager.create_tables_async()
        logger.info("Database tables verified/created")

        # Get a session
        async with db_manager.get_session() as session:
            # Create template generator to access templates
            generator = MissionTemplateGenerator()

            # Default tenant key for system templates
            tenant_key = str(uuid4())

            # Define templates to migrate
            templates_to_migrate = [
                {
                    "name": "orchestrator",
                    "category": "role",
                    "role": "orchestrator",
                    "template_content": generator.ORCHESTRATOR_TEMPLATE,
                    "description": "Default orchestrator template for project coordination",
                    "behavioral_rules": [
                        "Tell user if agents should run in parallel at start",
                        "Tell all agents to acknowledge messages",
                        "Only use handoff upon context limit",
                        "Agents communicate through orchestrator",
                        "Agents report completion status",
                    ],
                    "success_criteria": [
                        "Vision document fully read",
                        "All agents spawned with clear missions",
                        "Project goals achieved",
                        "Handoffs completed successfully",
                    ],
                    "is_default": True,
                },
                {
                    "name": "analyzer",
                    "category": "role",
                    "role": "analyzer",
                    "template_content": generator.ANALYZER_TEMPLATE,
                    "description": "Default analyzer template for system analysis and design",
                    "behavioral_rules": [
                        "Deep analysis of existing system",
                        "Identify patterns and anti-patterns",
                        "Design optimal solutions",
                        "Document findings clearly",
                    ],
                    "success_criteria": [
                        "Complete system analysis",
                        "Design documents created",
                        "Integration points identified",
                        "Risks assessed",
                    ],
                    "is_default": True,
                },
                {
                    "name": "implementer",
                    "category": "role",
                    "role": "implementer",
                    "template_content": generator.IMPLEMENTER_TEMPLATE,
                    "description": "Default implementer template for code implementation",
                    "behavioral_rules": [
                        "Follow design specifications exactly",
                        "Write clean, maintainable code",
                        "Add appropriate error handling",
                        "Document complex logic",
                    ],
                    "success_criteria": [
                        "All features implemented",
                        "Code follows project standards",
                        "Tests pass",
                        "No breaking changes",
                    ],
                    "is_default": True,
                },
                {
                    "name": "tester",
                    "category": "role",
                    "role": "tester",
                    "template_content": generator.TESTER_TEMPLATE,
                    "description": "Default tester template for quality assurance",
                    "behavioral_rules": [
                        "Test all functionality thoroughly",
                        "Write comprehensive test cases",
                        "Document test results",
                        "Verify edge cases",
                    ],
                    "success_criteria": [
                        "All tests written and passing",
                        "Edge cases covered",
                        "Performance validated",
                        "Regression tests included",
                    ],
                    "is_default": True,
                },
                {
                    "name": "reviewer",
                    "category": "role",
                    "role": "reviewer",
                    "template_content": generator.REVIEWER_TEMPLATE,
                    "description": "Default reviewer template for code review and validation",
                    "behavioral_rules": [
                        "Review code for quality and standards",
                        "Verify requirements are met",
                        "Check for security issues",
                        "Ensure documentation is complete",
                    ],
                    "success_criteria": [
                        "Code review complete",
                        "All issues addressed",
                        "Standards compliance verified",
                        "Documentation approved",
                    ],
                    "is_default": True,
                },
                {
                    "name": "documenter",
                    "category": "role",
                    "role": "documenter",
                    "template_content": """You are the Documentation Agent for: {project_name}

PROJECT GOAL: {project_mission}

YOUR MISSION:
Create comprehensive documentation for all project deliverables, ensuring future developers
and users can understand and maintain the system.

YOUR RESPONSIBILITIES:
1. Document all implemented features
2. Create usage examples and tutorials
3. Write API documentation
4. Update README and setup guides
5. Document architectural decisions
6. Create troubleshooting guides

BEHAVIORAL RULES:
- Use clear, concise language
- Include code examples where helpful
- Follow project documentation standards
- Organize content logically
- Keep documentation up-to-date

SUCCESS CRITERIA:
- All features documented
- Examples provided for common use cases
- Setup instructions clear and complete
- Architecture documented
- Future developers can understand the system""",
                    "description": "Default documenter template for project documentation",
                    "behavioral_rules": [
                        "Use clear, concise language",
                        "Include code examples",
                        "Follow documentation standards",
                        "Organize content logically",
                    ],
                    "success_criteria": [
                        "All features documented",
                        "Examples provided",
                        "Setup instructions complete",
                        "Architecture documented",
                    ],
                    "is_default": True,
                },
            ]

            # Migrate each template
            migrated_count = 0
            for template_data in templates_to_migrate:
                # Check if template already exists
                from sqlalchemy import select

                existing = await session.execute(
                    select(AgentTemplate).where(
                        AgentTemplate.name == template_data["name"], AgentTemplate.role == template_data.get("role")
                    )
                )

                if existing.scalar_one_or_none():
                    logger.info(f"Template '{template_data['name']}' already exists, skipping")
                    continue

                # Extract variables from template
                import re

                variables = list(set(re.findall(r"\{(\w+)\}", template_data["template_content"])))

                # Create new template
                template = AgentTemplate(
                    tenant_key=tenant_key,
                    name=template_data["name"],
                    category=template_data["category"],
                    role=template_data.get("role"),
                    template_content=template_data["template_content"],
                    description=template_data["description"],
                    variables=variables,
                    behavioral_rules=template_data.get("behavioral_rules", []),
                    success_criteria=template_data.get("success_criteria", []),
                    version="1.0.0",
                    is_active=True,
                    is_default=template_data.get("is_default", False),
                    created_by="migration_script",
                    created_at=datetime.now(timezone.utc),
                )

                session.add(template)
                migrated_count += 1
                logger.info(f"Migrated template: {template_data['name']}")

            # Commit all changes
            await session.commit()
            logger.info(f"Successfully migrated {migrated_count} templates to database")

            # Verify migration
            result = await session.execute(select(AgentTemplate))
            all_templates = result.scalars().all()
            logger.info(f"Total templates in database: {len(all_templates)}")

            for template in all_templates:
                logger.info(f"  - {template.name} ({template.role}): v{template.version}")

    finally:
        await db_manager.close_async()
        logger.info("Database connection closed")


if __name__ == "__main__":
    logger.info("Starting template migration...")
    asyncio.run(migrate_templates())
    logger.info("Migration complete!")
