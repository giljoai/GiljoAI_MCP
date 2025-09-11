#!/usr/bin/env python3
"""
Final test to verify all 20 MCP tools are properly registered
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_tools():
    """Test that all 20 tools are registered"""
    
    print("MCP Tools Registration Test")
    print("=" * 50)
    
    try:
        from fastmcp import FastMCP
        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tenant import TenantManager
        
        # Initialize components
        print("\nInitializing components...")
        db_manager = DatabaseManager()
        tenant_manager = TenantManager()
        mcp = FastMCP("test_server")
        
        # Register all tool groups
        print("\nRegistering tool groups...")
        from giljo_mcp.tools.project import register_project_tools
        from giljo_mcp.tools.agent import register_agent_tools
        from giljo_mcp.tools.message import register_message_tools
        from giljo_mcp.tools.context import register_context_tools
        
        register_project_tools(mcp, db_manager, tenant_manager)
        register_agent_tools(mcp, db_manager, tenant_manager)
        register_message_tools(mcp, db_manager, tenant_manager)
        register_context_tools(mcp, db_manager, tenant_manager)
        
        # Get registered tools using the proper method
        print("\nChecking registered tools...")
        tools = await mcp.get_tools()
        
        print(f"Total tools registered: {len(tools)}")
        
        # List all tool names
        print(f"Tools type: {type(tools)}")
        if hasattr(tools, 'keys'):
            tool_names = list(tools.keys())
        elif isinstance(tools, list):
            tool_names = tools
        else:
            tool_names = [str(t) for t in tools]
        
        # Expected tools
        expected = [
            # Project (6)
            "create_project", "list_projects", "switch_project",
            "close_project", "update_project_mission", "project_status",
            
            # Agent (6)
            "ensure_agent", "activate_agent", "assign_job",
            "handoff", "agent_health", "decommission_agent",
            
            # Message (6)
            "send_message", "get_messages", "acknowledge_message",
            "complete_message", "broadcast", "log_task",
            
            # Context (8)
            "get_vision", "get_vision_index", "get_context_index",
            "get_context_section", "get_product_settings",
            "session_info", "recalibrate_mission", "help"
        ]
        
        # Check each expected tool
        print("\nTool Status:")
        print("-" * 40)
        
        missing = []
        for tool in expected:
            if tool in tool_names:
                print(f"  [OK] {tool}")
            else:
                print(f"  [MISSING] {tool}")
                missing.append(tool)
        
        # Check for unexpected tools
        unexpected = [t for t in tool_names if t not in expected]
        if unexpected:
            print("\nUnexpected tools found:")
            for tool in unexpected:
                print(f"  - {tool}")
        
        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print(f"Expected: {len(expected)} tools")
        print(f"Found: {len(tools)} tools")
        print(f"Missing: {len(missing)} tools")
        
        if missing:
            print("\nMissing tools:")
            for tool in missing:
                print(f"  - {tool}")
        
        # Test help() tool specifically
        if "help" in tool_names:
            print("\nTesting help() tool:")
            help_tool = await mcp.get_tool("help")
            if help_tool:
                try:
                    # Call the help tool directly via the tools dict
                    if isinstance(tools, dict) and "help" in tools:
                        result = await tools["help"]()
                        if result.get("success"):
                            print(f"  [OK] help() returned data for {result.get('tool_count', 0)} tools")
                        else:
                            print(f"  [ERROR] help() failed: {result.get('error')}")
                except Exception as e:
                    print(f"  [ERROR] Failed to call help(): {e}")
        
        # Return status
        if len(missing) == 0 and len(tools) == 20:
            print("\nSUCCESS: All 20 tools are registered!")
            return 0
        else:
            print(f"\nFAILURE: {len(missing)} tools missing")
            return 1
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

async def main():
    return await test_tools()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)