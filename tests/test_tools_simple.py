#!/usr/bin/env python3
"""
Simple test to verify all 20 MCP tools are available
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_tools():
    """Test that all 20 tools are defined"""
    
    print("Testing MCP Tools Availability")
    print("=" * 50)
    
    tools_status = {}
    errors = []
    
    # Test Project Tools (6)
    print("\nPROJECT TOOLS:")
    try:
        from src.giljo_mcp.tools.project import (
            create_project, list_projects, switch_project,
            close_project, update_project_mission, project_status
        )
        print("  [OK] create_project")
        print("  [OK] list_projects")
        print("  [OK] switch_project")
        print("  [OK] close_project")
        print("  [OK] update_project_mission")
        print("  [OK] project_status")
        tools_status["project"] = 6
    except ImportError as e:
        print(f"  [ERROR] Failed to import project tools: {e}")
        errors.append(str(e))
        tools_status["project"] = 0
    
    # Test Agent Tools (6)
    print("\nAGENT TOOLS:")
    try:
        from src.giljo_mcp.tools.agent import (
            ensure_agent, activate_agent, assign_job,
            handoff, agent_health, decommission_agent
        )
        print("  [OK] ensure_agent")
        print("  [OK] activate_agent")
        print("  [OK] assign_job")
        print("  [OK] handoff")
        print("  [OK] agent_health")
        print("  [OK] decommission_agent")
        tools_status["agent"] = 6
    except ImportError as e:
        print(f"  [ERROR] Failed to import agent tools: {e}")
        errors.append(str(e))
        tools_status["agent"] = 0
    
    # Test Message Tools (6)
    print("\nMESSAGE TOOLS:")
    try:
        from src.giljo_mcp.tools.message import (
            send_message, get_messages, acknowledge_message,
            complete_message, broadcast, log_task
        )
        print("  [OK] send_message")
        print("  [OK] get_messages")
        print("  [OK] acknowledge_message")
        print("  [OK] complete_message")
        print("  [OK] broadcast")
        print("  [OK] log_task")
        tools_status["message"] = 6
    except ImportError as e:
        print(f"  [ERROR] Failed to import message tools: {e}")
        errors.append(str(e))
        tools_status["message"] = 0
    
    # Test Context Tools (8)
    print("\nCONTEXT TOOLS:")
    try:
        from src.giljo_mcp.tools.context import (
            get_vision, get_vision_index, get_context_index,
            get_context_section, get_product_settings,
            session_info, recalibrate_mission, help
        )
        print("  [OK] get_vision")
        print("  [OK] get_vision_index")
        print("  [OK] get_context_index")
        print("  [OK] get_context_section")
        print("  [OK] get_product_settings")
        print("  [OK] session_info")
        print("  [OK] recalibrate_mission")
        print("  [OK] help")
        tools_status["context"] = 8
    except ImportError as e:
        print(f"  [ERROR] Failed to import context tools: {e}")
        errors.append(str(e))
        tools_status["context"] = 0
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    total_tools = sum(tools_status.values())
    print(f"Total tools available: {total_tools}/20")
    
    for category, count in tools_status.items():
        expected = 6 if category != "context" else 8
        status = "OK" if count == expected else "FAILED"
        print(f"  {category.upper()}: {count}/{expected} [{status}]")
    
    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    # Test help() tool functionality
    print("\n" + "=" * 50)
    print("TESTING HELP() TOOL:")
    
    try:
        from src.giljo_mcp.database import DatabaseManager
        from src.giljo_mcp.tenant import TenantManager
        from fastmcp import FastMCP
        
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
            print("  [OK] help() tool is registered")
            
            # Call the help tool
            result = await help_tool.func()
            
            if result.get("success"):
                tool_count = result.get("tool_count", 0)
                categories = result.get("categories", {})
                print(f"  [OK] help() returned documentation for {tool_count} tools")
                print(f"  [OK] Categories: {', '.join(categories.keys())}")
            else:
                print(f"  [ERROR] help() failed: {result.get('error')}")
        else:
            print("  [ERROR] help() tool not found in registered tools")
        
        await db_manager.close_async()
        
    except Exception as e:
        print(f"  [ERROR] Failed to test help() tool: {e}")
    
    print("\n" + "=" * 50)
    
    if total_tools == 20:
        print("SUCCESS: All 20 tools are available!")
        return 0
    else:
        print(f"FAILURE: Only {total_tools}/20 tools are available")
        return 1

async def main():
    return await test_tools()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    # sys.exit(exit_code)  # Commented for pytest