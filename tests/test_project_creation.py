#!/usr/bin/env python
"""Test project creation with product_id"""

import asyncio
import sys
from pathlib import Path


# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


async def main():
    """Test project creation"""
    # Load config
    config = get_config()

    # Initialize components
    db_manager = DatabaseManager(database_url=config.database.url)
    tenant_manager = TenantManager()
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    # Create project with product_id
    result = await tool_accessor.create_project(
        name="Direct Test Project",
        mission="Testing product_id assignment directly",
        product_id="e74a3a44-1d3e-48cd-b60d-9158d6b3aae6",
    )

    print("\n" + "=" * 60)
    print("Project Creation Result:")
    print("=" * 60)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("=" * 60 + "\n")

    # Verify in database
    if result.get("success"):
        project_id = result["project_id"]
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            from giljo_mcp.models import Project

            query = select(Project).where(Project.id == project_id)
            db_result = await session.execute(query)
            project = db_result.scalar_one_or_none()

            if project:
                print("Database Verification:")
                print(f"  ID: {project.id}")
                print(f"  Name: {project.name}")
                print(f"  Product ID: {project.product_id}")
                print(f"  Mission: {project.mission}")
            else:
                print("ERROR: Project not found in database!")

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
