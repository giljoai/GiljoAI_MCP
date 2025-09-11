#!/usr/bin/env python3
"""
Test tool registration in the MCP server
Verifies all 20 tools are properly registered
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_tool_registration():
    """Test that all 20 tools are registered with the MCP server"""
    
    print("Testing MCP Tool Registration")
    print("=" * 50)
    
    try:
        from fastmcp import FastMCP
        from giljo_mcp.database import DatabaseManager
        from giljo_mcp.tenant import TenantManager
        
        # Initialize components
        print("\nInitializing test environment...")
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Create tenant manager
        tenant_manager = TenantManager()
        
        # Create MCP server instance
        mcp = FastMCP("test_server")
        
        print("  [OK] Environment initialized")
        
        # Register all tool groups
        print("\nRegistering tool groups...")
        
        from giljo_mcp.tools.project import register_project_tools
        from giljo_mcp.tools.agent import register_agent_tools
        from giljo_mcp.tools.message import register_message_tools
        from giljo_mcp.tools.context import register_context_tools
        
        register_project_tools(mcp, db_manager, tenant_manager)
        print("  [OK] Project tools registered")
        
        register_agent_tools(mcp, db_manager, tenant_manager)
        print("  [OK] Agent tools registered")
        
        register_message_tools(mcp, db_manager, tenant_manager)
        print("  [OK] Message tools registered")
        
        register_context_tools(mcp, db_manager, tenant_manager)
        print("  [OK] Context tools registered")
        
        # Count registered tools
        print("\nAnalyzing registered tools...")
        
        # Expected tools by category
        expected_tools = {
            # Project tools (6)
            "create_project": "project",
            "list_projects": "project",
            "switch_project": "project",
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
            "help": "context"
        }
        
        # Check registered tools
        registered_tools = {}
        missing_tools = []
        
        # Access the internal tools registry
        if hasattr(mcp, '_tools'):
            for tool_name, tool_obj in mcp._tools.items():
                registered_tools[tool_name] = tool_obj
        
        # Verify each expected tool
        print("\nTool Registration Status:")
        print("-" * 40)
        
        categories = {
            "project": [],
            "agent": [],
            "message": [],
            "context": []
        }
        
        for tool_name, category in expected_tools.items():
            if tool_name in registered_tools:
                categories[category].append(f"  [OK] {tool_name}")
            else:
                categories[category].append(f"  [MISSING] {tool_name}")
                missing_tools.append(tool_name)
        
        # Print by category
        for category, tools in categories.items():
            print(f"\n{category.upper()} TOOLS:")
            for tool in tools:
                print(tool)
        
        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY:")
        total_expected = len(expected_tools)
        total_registered = len([t for t in expected_tools if t in registered_tools])
        
        print(f"Total tools registered: {total_registered}/{total_expected}")
        
        if missing_tools:
            print(f"\nMissing tools ({len(missing_tools)}):")
            for tool in missing_tools:
                print(f"  - {tool}")
        
        # Test help() tool specifically
        print("\n" + "=" * 50)
        print("TESTING HELP() TOOL:")
        
        if "help" in registered_tools:
            print("  [OK] help() tool is registered")
            
            try:
                # Call the help tool
                help_func = registered_tools["help"].func
                result = await help_func()
                
                if result.get("success"):
                    tool_count = result.get("tool_count", 0)
                    print(f"  [OK] help() returned documentation for {tool_count} tools")
                    
                    # Verify tool count matches
                    if tool_count == 20:
                        print("  [OK] Tool count matches expected (20)")
                    else:
                        print(f"  [WARNING] Tool count mismatch: {tool_count} vs 20 expected")
                else:
                    print(f"  [ERROR] help() failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"  [ERROR] Failed to call help(): {e}")
        else:
            print("  [ERROR] help() tool not registered")
        
        print("\n" + "=" * 50)
        
        # Final result
        if total_registered == total_expected:
            print("SUCCESS: All 20 tools are properly registered!")
            return 0
        else:
            print(f"FAILURE: Only {total_registered}/{total_expected} tools registered")
            return 1
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

async def main():
    return await test_tool_registration()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)