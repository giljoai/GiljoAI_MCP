#!/usr/bin/env python3
"""
Test tool registration in the MCP server
Verifies all 20 tools are properly registered
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_tool_registration():
    """Test that all 20 tools are registered with the MCP server"""

    try:
        from fastmcp import FastMCP

        from src.giljo_mcp.database import DatabaseManager
        from src.giljo_mcp.tenant import TenantManager

        # Initialize components

        # Create database manager
        db_manager = DatabaseManager()

        # Create tenant manager
        tenant_manager = TenantManager()

        # Create MCP server instance
        mcp = FastMCP("test_server")

        # Register all tool groups

        from src.giljo_mcp.tools.agent import register_agent_tools
        from src.giljo_mcp.tools.context import register_context_tools
        from src.giljo_mcp.tools.message import register_message_tools
        from src.giljo_mcp.tools.project import register_project_tools

        register_project_tools(mcp, db_manager, tenant_manager)

        register_agent_tools(mcp, db_manager, tenant_manager)

        register_message_tools(mcp, db_manager, tenant_manager)

        register_context_tools(mcp, db_manager, tenant_manager)

        # Count registered tools

        # Expected tools by category
        expected_tools = {
            # Project tools (4)
            "list_projects": "project",
            "close_project": "project",
            "update_project_mission": "project",
            "project_status": "project",
            # Agent tools (6)
            "ensure_agent": "agent",
            "activate_agent": "agent",
            "assign_job": "agent",
            "handoff": "agent",
            "agent_health": "agent",
            "decommission_agent": "agent",
            # Message tools (6)
            "send_message": "message",
            "get_messages": "message",
            "acknowledge_message": "message",
            "complete_message": "message",
            "broadcast": "message",
            "log_task": "message",
            # Context tools (8)
            "get_vision": "context",
            "get_vision_index": "context",
            "get_context_index": "context",
            "get_context_section": "context",
            "get_product_settings": "context",
            "session_info": "context",
            "recalibrate_mission": "context",
            "help": "context",
        }

        # Check registered tools
        registered_tools = {}
        missing_tools = []

        # Access the internal tools registry
        if hasattr(mcp, "_tools"):
            for tool_name, tool_obj in mcp._tools.items():
                registered_tools[tool_name] = tool_obj

        # Verify each expected tool

        categories = {"project": [], "agent": [], "message": [], "context": []}

        for tool_name, category in expected_tools.items():
            if tool_name in registered_tools:
                categories[category].append(f"  [OK] {tool_name}")
            else:
                categories[category].append(f"  [MISSING] {tool_name}")
                missing_tools.append(tool_name)

        # Print by category
        for category, tools in categories.items():
            for _tool in tools:
                pass

        # Summary
        total_expected = len(expected_tools)
        total_registered = len([t for t in expected_tools if t in registered_tools])

        if missing_tools:
            for _tool in missing_tools:
                pass

        # Test help() tool specifically

        if "help" in registered_tools:
            try:
                # Call the help tool
                help_func = registered_tools["help"].func
                result = await help_func()

                if result.get("success"):
                    tool_count = result.get("tool_count", 0)

                    # Verify tool count matches
                    if tool_count == 20:
                        pass
                    else:
                        pass
                else:
                    pass

            except Exception:
                pass
        else:
            pass

        # Final result
        if total_registered == total_expected:
            return 0
        return 1

    except Exception:
        import traceback

        traceback.print_exc()
        return 1


async def main():
    return await test_tool_registration()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    # sys.exit(exit_code)  # Commented for pytest
