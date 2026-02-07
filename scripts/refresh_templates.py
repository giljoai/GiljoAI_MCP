#!/usr/bin/env python3
"""
Refresh MCP coordination instructions in existing agent templates.

This script updates the system_instructions field of all agent templates
across all tenants without overwriting user customizations.

Usage:
    python scripts/refresh_templates.py

    # Or for a specific tenant:
    python scripts/refresh_templates.py --tenant tk_xxx
"""

import asyncio
import os
import sys
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import logging

from sqlalchemy import select


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def refresh_all_tenants():
    """Refresh templates for all tenants in the database."""
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.models import AgentTemplate
    from src.giljo_mcp.template_seeder import refresh_tenant_template_instructions

    # Get database URL from environment or config
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Try loading from config.yaml
        import yaml

        config_path = project_root / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            db_config = config.get("database", {})
            db_url = (
                f"postgresql+asyncpg://{db_config.get('user', 'postgres')}:"
                f"{db_config.get('password', '')}@{db_config.get('host', 'localhost')}:"
                f"{db_config.get('port', 5432)}/{db_config.get('database', 'giljo_mcp')}"
            )
        else:
            raise ValueError("DATABASE_URL not set and config.yaml not found")

    db_manager = DatabaseManager(database_url=db_url, is_async=True)

    async with db_manager.get_session_async() as session:
        # Get all unique tenant_keys
        stmt = select(AgentTemplate.tenant_key).distinct()
        result = await session.execute(stmt)
        tenant_keys = [row[0] for row in result.fetchall()]

        if not tenant_keys:
            logger.info("No tenants found with templates")
            return

        logger.info(f"Found {len(tenant_keys)} tenants with templates")

        total_updated = 0
        for tenant_key in tenant_keys:
            count = await refresh_tenant_template_instructions(session, tenant_key)
            total_updated += count
            logger.info(f"  Tenant '{tenant_key}': {count} templates refreshed")

        logger.info(f"Total: {total_updated} templates refreshed across {len(tenant_keys)} tenants")


async def refresh_single_tenant(tenant_key: str):
    """Refresh templates for a specific tenant."""
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.template_seeder import refresh_tenant_template_instructions

    # Get database URL from environment or config
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        import yaml

        config_path = project_root / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            db_config = config.get("database", {})
            db_url = (
                f"postgresql+asyncpg://{db_config.get('user', 'postgres')}:"
                f"{db_config.get('password', '')}@{db_config.get('host', 'localhost')}:"
                f"{db_config.get('port', 5432)}/{db_config.get('database', 'giljo_mcp')}"
            )
        else:
            raise ValueError("DATABASE_URL not set and config.yaml not found")

    db_manager = DatabaseManager(database_url=db_url, is_async=True)

    async with db_manager.get_session_async() as session:
        count = await refresh_tenant_template_instructions(session, tenant_key)
        logger.info(f"Refreshed {count} templates for tenant '{tenant_key}'")


def main():
    parser = argparse.ArgumentParser(description="Refresh MCP coordination in agent templates")
    parser.add_argument("--tenant", "-t", help="Specific tenant key to refresh (default: all tenants)")
    args = parser.parse_args()

    if args.tenant:
        asyncio.run(refresh_single_tenant(args.tenant))
    else:
        asyncio.run(refresh_all_tenants())


if __name__ == "__main__":
    main()
