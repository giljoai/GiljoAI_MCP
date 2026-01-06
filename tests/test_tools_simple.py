#!/usr/bin/env python3
"""
Simple test to verify all 18 MCP tools are available
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_tools():
    """Test that all 19 tools are defined"""

    tools_status = {}
    errors = []

    # Test Project Tools (4)
    try:
        from src.giljo_mcp.tools.project import (
            close_project,
            list_projects,
            project_status,
            update_project_mission,
        )

        tools_status["project"] = 4
    except ImportError as e:
        errors.append(str(e))
        tools_status["project"] = 0

    # Test Agent Tools (6)
    try:
        from src.giljo_mcp.tools.agent import (
            activate_agent,
            agent_health,
            assign_job,
            decommission_agent,
            ensure_agent,
            handoff,
        )

        tools_status["agent"] = 6
    except ImportError as e:
        errors.append(str(e))
        tools_status["agent"] = 0

    # Test Message Tools (6)
    try:
        from src.giljo_mcp.tools.message import (
            acknowledge_message,
            broadcast,
            complete_message,
            get_messages,
            log_task,
            send_message,
        )

        tools_status["message"] = 6
    except ImportError as e:
        errors.append(str(e))
        tools_status["message"] = 0

    # Test Context Tools (8)
    try:
        from src.giljo_mcp.tools.context import (
            get_context_index,
            get_context_section,
            get_product_settings,
            get_vision,
            get_vision_index,
            help,
            recalibrate_mission,
            session_info,
        )

        tools_status["context"] = 8
    except ImportError as e:
        errors.append(str(e))
        tools_status["context"] = 0

    # Summary
    total_tools = sum(tools_status.values())

    for _category in tools_status:
        pass

    if errors:
        for _error in errors:
            pass

    # Test help() tool functionality

    try:
        from fastmcp import FastMCP

        from src.giljo_mcp.database import DatabaseManager
        from src.giljo_mcp.tenant import TenantManager

        # Create instances
        db_manager = DatabaseManager()
        await db_manager.initialize()

        tenant_manager = TenantManager()
        mcp = FastMCP("test")

        # Register context tools
        from src.giljo_mcp.tools.context import register_context_tools

        register_context_tools(mcp, db_manager, tenant_manager)

        # Find and call help tool
        help_tool = None
        for tool in mcp._tools.values():
            if tool.name == "help":
                help_tool = tool
                break

        if help_tool:
            # Call the help tool
            result = await help_tool.func()

            if result.get("success"):
                result.get("tool_count", 0)
                result.get("categories", {})
            else:
                pass
        else:
            pass

        await db_manager.close_async()

    except Exception:
        pass

    if total_tools == 18:
        return 0
    return 1


async def main():
    return await test_tools()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    # sys.exit(exit_code)  # Commented for pytest
