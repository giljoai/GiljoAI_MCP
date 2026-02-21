"""
Database seeding script for enhanced orchestrator template.
Populates the database with the Phase 3 enhanced orchestrator template
from OrchestratorUpgrade.md specification.

Usage:
    python scripts/seed_orchestrator_template.py [--tenant-key TENANT_KEY]
"""

import argparse
import logging
import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def seed_orchestrator_template(db_manager: DatabaseManager, tenant_key: str) -> None:
    """
    Seed the default orchestrator template for a tenant.

    Args:
        db_manager: Database manager instance
        tenant_key: Tenant key for multi-tenant isolation

    Raises:
        Exception: If seeding fails
    """
    logger.info(f"Seeding default orchestrator template for tenant: {tenant_key}")

    try:
        with db_manager.get_session() as session:
            # Check if orchestrator template already exists
            existing = (
                session.query(AgentTemplate)
                .filter(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.name == "orchestrator",
                    AgentTemplate.is_default == True,  # noqa: E712
                )
                .first()
            )

            if existing:
                logger.info("Default orchestrator template already exists - skipping")
                return

            # Get orchestrator template from UnifiedTemplateManager
            template_mgr = UnifiedTemplateManager()
            orchestrator_content = template_mgr._legacy_templates["orchestrator"]  # noqa: SLF001

            # Create template with enhanced Phase 3 features
            template = AgentTemplate(
                tenant_key=tenant_key,
                product_id=None,  # Global template (all products)
                name="orchestrator",
                category="role",
                role="orchestrator",
                template_content=orchestrator_content,
                variables=["project_name", "project_mission", "product_name"],
                behavioral_rules=[
                    "Coordinate all agents effectively",
                    "Ensure project goals are met through delegation",
                    "Handle conflicts and blockers",
                    "Maintain project momentum",
                    "Read vision document completely (all parts)",
                    "Challenge scope drift",
                    "Enforce 3-tool rule (delegate if using >3 tools)",
                    "Create specific missions based on discoveries",
                    "Create 3 documentation artifacts at project close",
                ],
                success_criteria=[
                    "Vision document fully read (all parts if chunked)",
                    "All product config_data reviewed",
                    "Serena MCP discoveries documented",
                    "All agents spawned with SPECIFIC missions",
                    "Project goals achieved and validated",
                    "Handoffs completed successfully",
                    "Three documentation artifacts created",
                ],
                is_default=True,  # Default orchestrator template
                is_active=True,
                description="Enhanced orchestrator template with discovery-first workflow, 30-80-10 principle, and 3-tool delegation rule",
                version="2.0.0",
                tags=["orchestrator", "discovery", "delegation", "default"],
            )

            session.add(template)
            session.commit()

            logger.info("Default orchestrator template seeded successfully")

    except Exception:
        logger.exception("Failed to seed orchestrator template")
        raise


def main():
    """Main entry point for seeding script."""
    parser = argparse.ArgumentParser(description="Seed enhanced orchestrator template to database")
    parser.add_argument(
        "--tenant-key",
        type=str,
        default="default",
        help="Tenant key for multi-tenant isolation (default: 'default')",
    )

    args = parser.parse_args()

    # Initialize database manager
    try:
        db_manager = DatabaseManager()
        logger.info("Database connection established")
    except Exception:
        logger.exception("Failed to connect to database")
        sys.exit(1)

    # Seed the template
    try:
        seed_orchestrator_template(db_manager, args.tenant_key)
        logger.info("Seeding completed successfully")
    except Exception:
        logger.exception("Seeding failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
