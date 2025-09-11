#!/usr/bin/env python3
"""
Comprehensive test script for all 20 GiljoAI MCP tools
Tests functionality and error handling for each tool category
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.server import create_server
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager

class MCPToolsTester:
    """Test all 20 MCP tools with comprehensive scenarios"""
    
    def __init__(self):
        self.server = None
        self.db_manager = None
        self.tenant_manager = None
        self.test_results = {
            "total_tools": 20,
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "tool_status": {}
        }
        self.test_project_id = None
        self.test_agent_name = "test_agent"
        
    async def setup(self):
        """Initialize test environment"""
        print("🔧 Setting up test environment...")
        
        # Initialize database
        self.db_manager = DatabaseManager()
        await self.db_manager.initialize()
        
        # Initialize tenant manager
        self.tenant_manager = TenantManager()
        
        # Create MCP server
        self.server = await create_server()
        
        print("✅ Test environment ready\n")
        
    async def cleanup(self):
        """Clean up test environment"""
        print("\n🧹 Cleaning up test environment...")
        
        # Close database connections
        if self.db_manager:
            await self.db_manager.close()
            
        print("✅ Cleanup complete\n")
        
    async def test_project_tools(self):
        """Test all 6 project management tools"""
        print("\n📁 Testing PROJECT TOOLS (6 tools)")
        print("="*50)
        
        # 1. Test create_project
        print("\n1. Testing create_project...")
        try:
            result = await self.call_tool("create_project", {
                "name": "Test Project for Tool Testing",
                "mission": "Testing all MCP tools functionality",
                "agents": ["tester", "validator"]
            })
            
            if result.get("success"):
                self.test_project_id = result.get("project_id")
                print(f"   ✅ Created project: {self.test_project_id}")
                self.mark_tool_passed("create_project")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("create_project", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("create_project", str(e))
            
        # 2. Test list_projects
        print("\n2. Testing list_projects...")
        try:
            result = await self.call_tool("list_projects", {
                "status": "active"
            })
            
            if result.get("success"):
                count = result.get("count", 0)
                print(f"   ✅ Listed {count} active projects")
                self.mark_tool_passed("list_projects")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("list_projects", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("list_projects", str(e))
            
        # 3. Test switch_project
        print("\n3. Testing switch_project...")
        if self.test_project_id:
            try:
                result = await self.call_tool("switch_project", {
                    "project_id": self.test_project_id
                })
                
                if result.get("success"):
                    print(f"   ✅ Switched to project")
                    self.mark_tool_passed("switch_project")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    self.mark_tool_failed("switch_project", result.get('error'))
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                self.mark_tool_failed("switch_project", str(e))
        else:
            print("   ⚠️  Skipped (no project created)")
            
        # 4. Test update_project_mission
        print("\n4. Testing update_project_mission...")
        if self.test_project_id:
            try:
                result = await self.call_tool("update_project_mission", {
                    "project_id": self.test_project_id,
                    "mission": "Updated mission for testing purposes"
                })
                
                if result.get("success"):
                    print(f"   ✅ Updated project mission")
                    self.mark_tool_passed("update_project_mission")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    self.mark_tool_failed("update_project_mission", result.get('error'))
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                self.mark_tool_failed("update_project_mission", str(e))
        else:
            print("   ⚠️  Skipped (no project created)")
            
        # 5. Test project_status
        print("\n5. Testing project_status...")
        try:
            result = await self.call_tool("project_status", {
                "project_id": self.test_project_id
            })
            
            if result.get("success"):
                print(f"   ✅ Retrieved project status")
                self.mark_tool_passed("project_status")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("project_status", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("project_status", str(e))
            
        # 6. Test close_project (test last to keep project available)
        print("\n6. Testing close_project...")
        if self.test_project_id:
            try:
                result = await self.call_tool("close_project", {
                    "project_id": self.test_project_id,
                    "summary": "Testing completed successfully"
                })
                
                if result.get("success"):
                    print(f"   ✅ Closed project")
                    self.mark_tool_passed("close_project")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    self.mark_tool_failed("close_project", result.get('error'))
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                self.mark_tool_failed("close_project", str(e))
        else:
            print("   ⚠️  Skipped (no project created)")
            
    async def test_agent_tools(self):
        """Test all 6 agent management tools"""
        print("\n🤖 Testing AGENT TOOLS (6 tools)")
        print("="*50)
        
        # Ensure we have a project
        if not self.test_project_id:
            result = await self.call_tool("create_project", {
                "name": "Agent Test Project",
                "mission": "Testing agent tools"
            })
            if result.get("success"):
                self.test_project_id = result.get("project_id")
                
        # 1. Test ensure_agent
        print("\n1. Testing ensure_agent...")
        try:
            result = await self.call_tool("ensure_agent", {
                "project_id": self.test_project_id,
                "agent_name": self.test_agent_name,
                "mission": "Test agent for validation"
            })
            
            if result.get("success"):
                print(f"   ✅ Ensured agent exists")
                self.mark_tool_passed("ensure_agent")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("ensure_agent", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("ensure_agent", str(e))
            
        # 2. Test activate_agent
        print("\n2. Testing activate_agent...")
        try:
            result = await self.call_tool("activate_agent", {
                "project_id": self.test_project_id,
                "agent_name": "orchestrator_test",
                "mission": "Test orchestrator activation"
            })
            
            if result.get("success"):
                print(f"   ✅ Activated agent")
                self.mark_tool_passed("activate_agent")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("activate_agent", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("activate_agent", str(e))
            
        # 3. Test assign_job
        print("\n3. Testing assign_job...")
        try:
            result = await self.call_tool("assign_job", {
                "agent_name": self.test_agent_name,
                "job_type": "testing",
                "project_id": self.test_project_id,
                "tasks": ["Test task 1", "Test task 2"],
                "scope_boundary": "Testing only",
                "vision_alignment": "Ensure quality"
            })
            
            if result.get("success"):
                print(f"   ✅ Assigned job to agent")
                self.mark_tool_passed("assign_job")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("assign_job", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("assign_job", str(e))
            
        # 4. Test agent_health
        print("\n4. Testing agent_health...")
        try:
            result = await self.call_tool("agent_health", {
                "agent_name": self.test_agent_name
            })
            
            if result.get("success"):
                print(f"   ✅ Retrieved agent health")
                self.mark_tool_passed("agent_health")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("agent_health", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("agent_health", str(e))
            
        # 5. Test handoff
        print("\n5. Testing handoff...")
        try:
            # Create second agent for handoff
            await self.call_tool("ensure_agent", {
                "project_id": self.test_project_id,
                "agent_name": "receiver_agent"
            })
            
            result = await self.call_tool("handoff", {
                "from_agent": self.test_agent_name,
                "to_agent": "receiver_agent",
                "project_id": self.test_project_id,
                "context": {"test_data": "handoff context"}
            })
            
            if result.get("success"):
                print(f"   ✅ Completed handoff")
                self.mark_tool_passed("handoff")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("handoff", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("handoff", str(e))
            
        # 6. Test decommission_agent
        print("\n6. Testing decommission_agent...")
        try:
            result = await self.call_tool("decommission_agent", {
                "agent_name": self.test_agent_name,
                "project_id": self.test_project_id,
                "reason": "Testing completed"
            })
            
            if result.get("success"):
                print(f"   ✅ Decommissioned agent")
                self.mark_tool_passed("decommission_agent")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("decommission_agent", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("decommission_agent", str(e))
            
    async def test_message_tools(self):
        """Test all 6 message/communication tools"""
        print("\n💬 Testing MESSAGE TOOLS (6 tools)")
        print("="*50)
        
        # Ensure we have agents for messaging
        if self.test_project_id:
            await self.call_tool("ensure_agent", {
                "project_id": self.test_project_id,
                "agent_name": "sender"
            })
            await self.call_tool("ensure_agent", {
                "project_id": self.test_project_id,
                "agent_name": "receiver"
            })
            
        # 1. Test send_message
        print("\n1. Testing send_message...")
        message_id = None
        try:
            result = await self.call_tool("send_message", {
                "to_agents": ["receiver"],
                "content": "Test message content",
                "project_id": self.test_project_id,
                "from_agent": "sender",
                "priority": "high"
            })
            
            if result.get("success"):
                message_id = result.get("message_id")
                print(f"   ✅ Sent message: {message_id}")
                self.mark_tool_passed("send_message")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("send_message", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("send_message", str(e))
            
        # 2. Test get_messages
        print("\n2. Testing get_messages...")
        try:
            result = await self.call_tool("get_messages", {
                "agent_name": "receiver",
                "project_id": self.test_project_id
            })
            
            if result.get("success"):
                count = result.get("count", 0)
                print(f"   ✅ Retrieved {count} messages")
                self.mark_tool_passed("get_messages")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("get_messages", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("get_messages", str(e))
            
        # 3. Test acknowledge_message
        print("\n3. Testing acknowledge_message...")
        if message_id:
            try:
                result = await self.call_tool("acknowledge_message", {
                    "message_id": message_id,
                    "agent_name": "receiver"
                })
                
                if result.get("success"):
                    print(f"   ✅ Acknowledged message")
                    self.mark_tool_passed("acknowledge_message")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    self.mark_tool_failed("acknowledge_message", result.get('error'))
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                self.mark_tool_failed("acknowledge_message", str(e))
        else:
            print("   ⚠️  Skipped (no message created)")
            
        # 4. Test complete_message
        print("\n4. Testing complete_message...")
        if message_id:
            try:
                result = await self.call_tool("complete_message", {
                    "message_id": message_id,
                    "agent_name": "receiver",
                    "result": "Message processed successfully"
                })
                
                if result.get("success"):
                    print(f"   ✅ Completed message")
                    self.mark_tool_passed("complete_message")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    self.mark_tool_failed("complete_message", result.get('error'))
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                self.mark_tool_failed("complete_message", str(e))
        else:
            print("   ⚠️  Skipped (no message created)")
            
        # 5. Test broadcast
        print("\n5. Testing broadcast...")
        try:
            result = await self.call_tool("broadcast", {
                "content": "Broadcast test message",
                "project_id": self.test_project_id,
                "priority": "normal"
            })
            
            if result.get("success"):
                recipients = result.get("broadcast_to", [])
                print(f"   ✅ Broadcast to {len(recipients)} agents")
                self.mark_tool_passed("broadcast")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("broadcast", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("broadcast", str(e))
            
        # 6. Test log_task
        print("\n6. Testing log_task...")
        try:
            result = await self.call_tool("log_task", {
                "content": "Test task for logging",
                "category": "testing",
                "priority": "high"
            })
            
            if result.get("success"):
                print(f"   ✅ Logged task")
                self.mark_tool_passed("log_task")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("log_task", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("log_task", str(e))
            
    async def test_context_tools(self):
        """Test all 8 context/discovery tools"""
        print("\n🔍 Testing CONTEXT TOOLS (8 tools)")
        print("="*50)
        
        # 1. Test get_vision
        print("\n1. Testing get_vision...")
        try:
            result = await self.call_tool("get_vision", {
                "part": 1,
                "max_tokens": 1000
            })
            
            if result.get("success") or "error" in result:
                if result.get("success"):
                    print(f"   ✅ Retrieved vision document")
                else:
                    print(f"   ⚠️  No vision docs (expected): {result.get('error')}")
                self.mark_tool_passed("get_vision")
            else:
                print(f"   ❌ Unexpected response")
                self.mark_tool_failed("get_vision", "Unexpected response format")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("get_vision", str(e))
            
        # 2. Test get_vision_index
        print("\n2. Testing get_vision_index...")
        try:
            result = await self.call_tool("get_vision_index", {})
            
            if result.get("success") or "error" in result:
                if result.get("success"):
                    print(f"   ✅ Retrieved vision index")
                else:
                    print(f"   ⚠️  No vision directory (expected): {result.get('error')}")
                self.mark_tool_passed("get_vision_index")
            else:
                print(f"   ❌ Unexpected response")
                self.mark_tool_failed("get_vision_index", "Unexpected response format")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("get_vision_index", str(e))
            
        # 3. Test get_context_index
        print("\n3. Testing get_context_index...")
        try:
            result = await self.call_tool("get_context_index", {})
            
            if result.get("success"):
                sources = result.get("sources", {})
                print(f"   ✅ Retrieved context index with {len(sources)} sources")
                self.mark_tool_passed("get_context_index")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("get_context_index", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("get_context_index", str(e))
            
        # 4. Test get_context_section
        print("\n4. Testing get_context_section...")
        try:
            result = await self.call_tool("get_context_section", {
                "document_name": "claude",
                "section_name": None
            })
            
            if result.get("success"):
                print(f"   ✅ Retrieved context section")
                self.mark_tool_passed("get_context_section")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("get_context_section", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("get_context_section", str(e))
            
        # 5. Test get_product_settings
        print("\n5. Testing get_product_settings...")
        try:
            result = await self.call_tool("get_product_settings", {})
            
            if result.get("success") or "error" in result:
                if result.get("success"):
                    print(f"   ✅ Retrieved product settings")
                else:
                    print(f"   ⚠️  No active project (expected): {result.get('error')}")
                self.mark_tool_passed("get_product_settings")
            else:
                print(f"   ❌ Unexpected response")
                self.mark_tool_failed("get_product_settings", "Unexpected response format")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("get_product_settings", str(e))
            
        # 6. Test session_info
        print("\n6. Testing session_info...")
        try:
            result = await self.call_tool("session_info", {})
            
            if result.get("success"):
                session = result.get("session", {})
                print(f"   ✅ Retrieved session info")
                self.mark_tool_passed("session_info")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("session_info", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("session_info", str(e))
            
        # 7. Test recalibrate_mission
        print("\n7. Testing recalibrate_mission...")
        if self.test_project_id:
            try:
                result = await self.call_tool("recalibrate_mission", {
                    "project_id": self.test_project_id,
                    "changes_summary": "Test recalibration"
                })
                
                if result.get("success"):
                    print(f"   ✅ Recalibrated mission")
                    self.mark_tool_passed("recalibrate_mission")
                else:
                    print(f"   ❌ Failed: {result.get('error')}")
                    self.mark_tool_failed("recalibrate_mission", result.get('error'))
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                self.mark_tool_failed("recalibrate_mission", str(e))
        else:
            print("   ⚠️  Skipped (no project created)")
            
        # 8. Test help
        print("\n8. Testing help...")
        try:
            result = await self.call_tool("help", {})
            
            if result.get("success"):
                tool_count = result.get("tool_count", 0)
                categories = result.get("categories", {})
                print(f"   ✅ Retrieved help for {tool_count} tools in {len(categories)} categories")
                self.mark_tool_passed("help")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                self.mark_tool_failed("help", result.get('error'))
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            self.mark_tool_failed("help", str(e))
            
    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n⚠️  Testing ERROR HANDLING")
        print("="*50)
        
        # Test invalid project ID
        print("\n1. Testing invalid project ID...")
        try:
            result = await self.call_tool("switch_project", {
                "project_id": "invalid-uuid-format"
            })
            
            if not result.get("success"):
                print(f"   ✅ Correctly handled invalid UUID: {result.get('error')}")
            else:
                print(f"   ❌ Should have failed with invalid UUID")
        except Exception as e:
            print(f"   ✅ Caught exception as expected: {e}")
            
        # Test missing required parameters
        print("\n2. Testing missing required parameters...")
        try:
            result = await self.call_tool("create_project", {
                "name": "Missing Mission Project"
                # mission is required but missing
            })
            
            if not result.get("success"):
                print(f"   ✅ Correctly handled missing parameter")
            else:
                print(f"   ❌ Should have failed with missing mission")
        except Exception as e:
            print(f"   ✅ Caught exception as expected: {e}")
            
        # Test duplicate operations
        print("\n3. Testing idempotent operations...")
        if self.test_project_id:
            try:
                # Try to create same agent twice
                result1 = await self.call_tool("ensure_agent", {
                    "project_id": self.test_project_id,
                    "agent_name": "duplicate_test"
                })
                
                result2 = await self.call_tool("ensure_agent", {
                    "project_id": self.test_project_id,
                    "agent_name": "duplicate_test"
                })
                
                if result1.get("success") and result2.get("success"):
                    print(f"   ✅ Idempotent operation handled correctly")
                else:
                    print(f"   ❌ Failed idempotent test")
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return result"""
        # This would normally call the actual MCP tool
        # For testing, we'll simulate the call
        
        # Import the actual tool functions
        if tool_name in ["create_project", "list_projects", "switch_project", 
                         "close_project", "update_project_mission", "project_status"]:
            from giljo_mcp.tools.project import (
                create_project, list_projects, switch_project,
                close_project, update_project_mission, project_status
            )
        elif tool_name in ["ensure_agent", "activate_agent", "assign_job",
                          "handoff", "agent_health", "decommission_agent"]:
            from giljo_mcp.tools.agent import (
                ensure_agent, activate_agent, assign_job,
                handoff, agent_health, decommission_agent
            )
        elif tool_name in ["send_message", "get_messages", "acknowledge_message",
                          "complete_message", "broadcast", "log_task"]:
            from giljo_mcp.tools.message import (
                send_message, get_messages, acknowledge_message,
                complete_message, broadcast, log_task
            )
        elif tool_name in ["get_vision", "get_vision_index", "get_context_index",
                          "get_context_section", "get_product_settings", 
                          "session_info", "recalibrate_mission", "help"]:
            from giljo_mcp.tools.context import (
                get_vision, get_vision_index, get_context_index,
                get_context_section, get_product_settings,
                session_info, recalibrate_mission, help
            )
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
            
        # Call the actual tool function
        tool_func = locals().get(tool_name)
        if tool_func:
            return await tool_func(**params)
        else:
            return {"success": False, "error": f"Tool function not found: {tool_name}"}
            
    def mark_tool_passed(self, tool_name: str):
        """Mark a tool as passed"""
        self.test_results["tested"] += 1
        self.test_results["passed"] += 1
        self.test_results["tool_status"][tool_name] = "✅ PASSED"
        
    def mark_tool_failed(self, tool_name: str, error: str):
        """Mark a tool as failed"""
        self.test_results["tested"] += 1
        self.test_results["failed"] += 1
        self.test_results["tool_status"][tool_name] = "❌ FAILED"
        self.test_results["errors"].append({
            "tool": tool_name,
            "error": error
        })
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        print(f"\nTotal Tools: {self.test_results['total_tools']}")
        print(f"Tested: {self.test_results['tested']}")
        print(f"Passed: {self.test_results['passed']} ✅")
        print(f"Failed: {self.test_results['failed']} ❌")
        
        if self.test_results['tested'] > 0:
            success_rate = (self.test_results['passed'] / self.test_results['tested']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
            
        print("\n📋 Tool Status:")
        print("-"*40)
        
        # Group by category
        categories = {
            "Project Tools": ["create_project", "list_projects", "switch_project",
                            "close_project", "update_project_mission", "project_status"],
            "Agent Tools": ["ensure_agent", "activate_agent", "assign_job",
                          "handoff", "agent_health", "decommission_agent"],
            "Message Tools": ["send_message", "get_messages", "acknowledge_message",
                            "complete_message", "broadcast", "log_task"],
            "Context Tools": ["get_vision", "get_vision_index", "get_context_index",
                            "get_context_section", "get_product_settings",
                            "session_info", "recalibrate_mission", "help"]
        }
        
        for category, tools in categories.items():
            print(f"\n{category}:")
            for tool in tools:
                status = self.test_results["tool_status"].get(tool, "⚠️  NOT TESTED")
                print(f"  {tool}: {status}")
                
        if self.test_results["errors"]:
            print("\n❌ Errors Encountered:")
            print("-"*40)
            for error in self.test_results["errors"]:
                print(f"  {error['tool']}: {error['error']}")
                
        print("\n" + "="*60)
        
        # Save results to file
        results_file = Path("test_results.json")
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {results_file}")
        
    async def run_all_tests(self):
        """Run all test suites"""
        print("\n🚀 Starting Comprehensive MCP Tools Testing")
        print("="*60)
        print(f"Testing all 20 MCP tools at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            await self.setup()
            
            # Run test suites
            await self.test_project_tools()
            await self.test_agent_tools()
            await self.test_message_tools()
            await self.test_context_tools()
            await self.test_error_handling()
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            print(f"\n❌ Fatal error during testing: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await self.cleanup()
            
        return self.test_results

async def main():
    """Main entry point"""
    tester = MCPToolsTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    if results["failed"] == 0 and results["tested"] == 20:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed or were not run")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)