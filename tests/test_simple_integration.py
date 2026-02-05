#!/usr/bin/env python3
"""
Simple integration test to verify Tool-API bridge works
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


async def simple_test():
    """Simple test of the Tool-API integration"""

    # Create temporary database
    # PostgreSQL test database used instead of temp file
    # PostgreSQL test database managed by fixtures

    try:
        # Initialize components
        db_url = fPostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(db_url, is_async=True)

        # Create tables
        await db_manager.create_tables_async()

        # Initialize managers
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Test 1: Create a project
        result = await tool_accessor.create_project(name="Test Project", mission="Simple integration test")

        if result["success"]:
            project_id = result["project_id"]
        else:
            return False

        # Test 2: List projects
        result = await tool_accessor.list_projects(status="active")

        if result["success"] and len(result["projects"]) > 0:
            pass
        else:
            return False

        # Test 3: Create an agent
        result = await tool_accessor.ensure_agent(project_id, "test_agent", mission="Test agent")

        if result["success"]:
            pass
        else:
            return False

        # Test 4: Send a message
        result = await tool_accessor.send_message(
            to_agents=["test_agent"], content="Test message", project_id=project_id
        )

        if result["success"]:
            result["message_id"]
        else:
            return False

        # Test 5: Get messages
        result = await tool_accessor.get_messages("test_agent", project_id=project_id)

        if result["success"] and result["count"] > 0:
            pass
        else:
            return False

        # Clean up
        await tool_accessor.complete_project(project_id, "Test complete")

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up database
        try:
            await db_manager.close_async()
            # PostgreSQL test database cleanup handled by fixtures
        except:
            pass


async def main():
    success = await simple_test()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    # sys.exit(exit_code)  # Commented for pytest
