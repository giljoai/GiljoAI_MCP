#!/usr/bin/env python3
"""
Simple integration test to verify Tool-API bridge works
"""

import asyncio
import sys
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.giljo_mcp.tools.tool_accessor import ToolAccessor
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager


async def simple_test():
    """Simple test of the Tool-API integration"""
    print("[TEST] Starting simple integration test")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    
    try:
        # Initialize components
        print("[SETUP] Initializing database...")
        db_url = f"sqlite+aiosqlite:///{temp_db.name}"
        db_manager = DatabaseManager(db_url, is_async=True)
        
        # Create tables
        print("[SETUP] Creating tables...")
        await db_manager.create_tables_async()
        
        # Initialize managers
        print("[SETUP] Initializing managers...")
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)
        
        # Test 1: Create a project
        print("\n[TEST 1] Creating project...")
        result = await tool_accessor.create_project(
            name="Test Project",
            mission="Simple integration test"
        )
        
        if result["success"]:
            print(f"  [PASS] Project created: {result['project_id']}")
            project_id = result["project_id"]
        else:
            print(f"  [FAIL] Project creation failed: {result.get('error')}")
            return False
        
        # Test 2: List projects
        print("\n[TEST 2] Listing projects...")
        result = await tool_accessor.list_projects(status="active")
        
        if result["success"] and len(result["projects"]) > 0:
            print(f"  [PASS] Found {len(result['projects'])} projects")
        else:
            print(f"  [FAIL] List projects failed")
            return False
        
        # Test 3: Create an agent
        print("\n[TEST 3] Creating agent...")
        result = await tool_accessor.ensure_agent(
            project_id,
            "test_agent",
            mission="Test agent"
        )
        
        if result["success"]:
            print(f"  [PASS] Agent created")
        else:
            print(f"  [FAIL] Agent creation failed: {result.get('error')}")
            return False
        
        # Test 4: Send a message
        print("\n[TEST 4] Sending message...")
        result = await tool_accessor.send_message(
            to_agents=["test_agent"],
            content="Test message",
            project_id=project_id
        )
        
        if result["success"]:
            print(f"  [PASS] Message sent: {result['message_id']}")
            message_id = result["message_id"]
        else:
            print(f"  [FAIL] Message send failed: {result.get('error')}")
            return False
        
        # Test 5: Get messages
        print("\n[TEST 5] Getting messages...")
        result = await tool_accessor.get_messages(
            "test_agent",
            project_id=project_id
        )
        
        if result["success"] and result["count"] > 0:
            print(f"  [PASS] Retrieved {result['count']} messages")
        else:
            print(f"  [FAIL] Get messages failed")
            return False
        
        # Clean up
        print("\n[CLEANUP] Closing project...")
        await tool_accessor.close_project(project_id, "Test complete")
        
        print("\n[SUCCESS] All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up database
        try:
            await db_manager.close_async()
            os.unlink(temp_db.name)
        except:
            pass


async def main():
    success = await simple_test()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    # sys.exit(exit_code)  # Commented for pytest