#!/usr/bin/env python
"""
End-to-End Workflow Test Suite for GiljoAI MCP
Tests complete project lifecycle and multi-agent coordination
"""

import sys
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import uuid

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager
from giljo_mcp.tools.project import create_project, list_projects, project_status, close_project
from giljo_mcp.tools.agent import ensure_agent, assign_job, handoff, agent_health, decommission_agent
from giljo_mcp.tools.message import send_message, get_messages, acknowledge_message, complete_message, broadcast
from giljo_mcp.tools.context import get_context_index, get_vision

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class WorkflowTestSuite:
    """End-to-end workflow testing"""
    
    def __init__(self):
        self.db_manager = None
        self.test_data = {}
        self.passed = 0
        self.failed = 0
        self.tests = []
        self.workflow_times = {}
    
    async def setup(self):
        """Initialize test environment"""
        print(f"{Colors.BLUE}Setting up E2E test environment...{Colors.RESET}")
        
        # Initialize test database
        self.db_manager = DatabaseManager("sqlite:///test_e2e.db", is_async=True)
        await self.db_manager.init_db()
        
        print(f"{Colors.GREEN}E2E test environment ready{Colors.RESET}")
    
    async def teardown(self):
        """Clean up test environment"""
        print(f"{Colors.BLUE}Cleaning up E2E test environment...{Colors.RESET}")
        
        # Close database
        if self.db_manager:
            await self.db_manager.close()
        
        # Clean up test database file
        test_db = Path("test_e2e.db")
        if test_db.exists():
            test_db.unlink()
    
    def record_test(self, test_name: str, passed: bool, details: str = "", time_ms: float = None):
        """Record test result"""
        self.tests.append({
            'name': test_name,
            'passed': passed,
            'details': details,
            'time_ms': time_ms
        })
        
        if passed:
            self.passed += 1
            status = f"{Colors.GREEN}✅ PASS{Colors.RESET}"
        else:
            self.failed += 1
            status = f"{Colors.RED}❌ FAIL{Colors.RESET}"
        
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
        if time_ms:
            print(f"   Time: {time_ms:.2f}ms")
    
    async def test_complete_project_lifecycle(self):
        """Test complete project lifecycle from creation to completion"""
        print(f"\n{Colors.BOLD}Testing Complete Project Lifecycle{Colors.RESET}")
        
        workflow_start = time.time()
        
        # Step 1: Create project
        start_time = time.time()
        result = await create_project(
            name="E2E Test Project",
            mission="Complete end-to-end testing of orchestration system",
            agents=["analyzer", "implementer", "validator"]
        )
        create_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Create project with agents",
            result.get("success", False),
            f"Project ID: {result.get('project_id')}",
            create_time
        )
        
        if result.get("success"):
            self.test_data["project_id"] = result["project_id"]
        else:
            return
        
        # Step 2: Verify project exists
        result = await list_projects(status="active")
        self.record_test(
            "Project appears in list",
            any(p["id"] == self.test_data["project_id"] for p in result.get("projects", [])),
            f"Found {len(result.get('projects', []))} active projects"
        )
        
        # Step 3: Get project status
        result = await project_status(project_id=self.test_data["project_id"])
        self.record_test(
            "Get project status",
            result.get("success", False),
            f"Status: {result.get('project', {}).get('status')}"
        )
        
        # Step 4: Close project
        start_time = time.time()
        result = await close_project(
            project_id=self.test_data["project_id"],
            summary="E2E test completed successfully"
        )
        close_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Close project",
            result.get("success", False),
            f"Project closed",
            close_time
        )
        
        # Record total workflow time
        total_time = (time.time() - workflow_start) * 1000
        self.workflow_times["project_lifecycle"] = total_time
        
        # Test against vision target: First project < 10 minutes
        self.record_test(
            "Project lifecycle < 10 seconds",
            total_time < 10000,
            f"Total time: {total_time:.2f}ms"
        )
    
    async def test_multi_agent_coordination(self):
        """Test multi-agent coordination and handoffs"""
        print(f"\n{Colors.BOLD}Testing Multi-Agent Coordination{Colors.RESET}")
        
        workflow_start = time.time()
        
        # Create project
        result = await create_project(
            name="Multi-Agent Test",
            mission="Test agent coordination and handoffs",
            agents=[]
        )
        
        if not result.get("success"):
            self.record_test("Create coordination project", False, "Failed to create project")
            return
        
        project_id = result["project_id"]
        self.test_data["coord_project_id"] = project_id
        
        # Create agents
        agents = ["orchestrator", "analyzer", "implementer"]
        for agent_name in agents:
            start_time = time.time()
            result = await ensure_agent(
                project_id=project_id,
                agent_name=agent_name,
                mission=f"Test agent {agent_name}"
            )
            agent_time = (time.time() - start_time) * 1000
            
            self.record_test(
                f"Create agent: {agent_name}",
                result.get("success", False),
                f"Agent created",
                agent_time
            )
        
        # Assign jobs to agents
        jobs = [
            ("analyzer", "analysis", ["Analyze codebase", "Find test gaps"]),
            ("implementer", "implementation", ["Build test suite", "Fix issues"])
        ]
        
        for agent_name, job_type, tasks in jobs:
            result = await assign_job(
                agent_name=agent_name,
                job_type=job_type,
                project_id=project_id,
                tasks=tasks,
                scope_boundary="Focus on testing only",
                vision_alignment="Ensure 90% test coverage"
            )
            
            self.record_test(
                f"Assign job to {agent_name}",
                result.get("success", False),
                f"Job type: {job_type}"
            )
        
        # Test handoff between agents
        start_time = time.time()
        result = await handoff(
            from_agent="analyzer",
            to_agent="implementer",
            project_id=project_id,
            context={
                "findings": "Found 5 critical test gaps",
                "priority": "high",
                "files": ["test1.py", "test2.py"]
            }
        )
        handoff_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Agent handoff",
            result.get("success", False),
            f"Handoff from analyzer to implementer",
            handoff_time
        )
        
        # Check agent health
        for agent_name in agents:
            result = await agent_health(agent_name=agent_name)
            self.record_test(
                f"Agent health: {agent_name}",
                result.get("success", False),
                f"Status: {result.get('health', {}).get('status')}"
            )
        
        # Decommission agents
        for agent_name in agents:
            result = await decommission_agent(
                agent_name=agent_name,
                project_id=project_id,
                reason="Test completed"
            )
            self.record_test(
                f"Decommission agent: {agent_name}",
                result.get("success", False),
                "Agent decommissioned"
            )
        
        # Record total workflow time
        total_time = (time.time() - workflow_start) * 1000
        self.workflow_times["multi_agent_coordination"] = total_time
    
    async def test_message_flow_pattern(self):
        """Test complete message flow with acknowledgments"""
        print(f"\n{Colors.BOLD}Testing Message Flow Pattern{Colors.RESET}")
        
        # Create project and agents
        result = await create_project(
            name="Message Flow Test",
            mission="Test message routing and acknowledgments"
        )
        
        if not result.get("success"):
            self.record_test("Create message project", False, "Failed to create project")
            return
        
        project_id = result["project_id"]
        
        # Create agents
        agents = ["sender", "receiver1", "receiver2"]
        for agent_name in agents:
            await ensure_agent(
                project_id=project_id,
                agent_name=agent_name
            )
        
        # Test 1: Direct message
        start_time = time.time()
        result = await send_message(
            to_agents=["receiver1"],
            content="Direct test message",
            project_id=project_id,
            message_type="direct",
            priority="high",
            from_agent="sender"
        )
        send_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Send direct message",
            result.get("success", False),
            f"Message ID: {result.get('message_id')}",
            send_time
        )
        
        if result.get("success"):
            message_id = result["message_id"]
            
            # Get messages
            result = await get_messages(
                agent_name="receiver1",
                project_id=project_id
            )
            self.record_test(
                "Receive message",
                len(result.get("messages", [])) > 0,
                f"Received {len(result.get('messages', []))} messages"
            )
            
            # Acknowledge message
            start_time = time.time()
            result = await acknowledge_message(
                message_id=message_id,
                agent_name="receiver1"
            )
            ack_time = (time.time() - start_time) * 1000
            
            self.record_test(
                "Acknowledge message",
                result.get("success", False),
                f"Acknowledged",
                ack_time
            )
            
            # Complete message
            result = await complete_message(
                message_id=message_id,
                agent_name="receiver1",
                result="Message processed successfully"
            )
            self.record_test(
                "Complete message",
                result.get("success", False),
                "Message completed"
            )
        
        # Test 2: Broadcast message
        start_time = time.time()
        result = await broadcast(
            content="Broadcast test message",
            project_id=project_id,
            priority="normal"
        )
        broadcast_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Broadcast message",
            result.get("success", False),
            f"Broadcast sent",
            broadcast_time
        )
        
        # Check all agents received broadcast
        for agent in ["receiver1", "receiver2"]:
            result = await get_messages(
                agent_name=agent,
                project_id=project_id
            )
            self.record_test(
                f"Broadcast received by {agent}",
                any(m.get("content") == "Broadcast test message" 
                    for m in result.get("messages", [])),
                f"Messages: {len(result.get('messages', []))}"
            )
        
        # Test message operations < 100ms target
        self.record_test(
            "Message send < 100ms",
            send_time < 100,
            f"Time: {send_time:.2f}ms"
        )
        
        self.record_test(
            "Message acknowledge < 100ms",
            ack_time < 100,
            f"Time: {ack_time:.2f}ms"
        )
    
    async def test_vision_driven_workflow(self):
        """Test vision-driven decision making flow"""
        print(f"\n{Colors.BOLD}Testing Vision-Driven Workflow{Colors.RESET}")
        
        # Get vision document
        start_time = time.time()
        result = await get_vision(part=1, max_tokens=1000)
        vision_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Retrieve vision document",
            result.get("success", False) or "content" in result,
            f"Retrieved part 1",
            vision_time
        )
        
        # Test vision chunk retrieval < 50ms target
        self.record_test(
            "Vision retrieval < 50ms",
            vision_time < 50,
            f"Time: {vision_time:.2f}ms"
        )
        
        # Get context index
        start_time = time.time()
        result = await get_context_index()
        index_time = (time.time() - start_time) * 1000
        
        self.record_test(
            "Get context index",
            result.get("success", False) or "index" in result,
            f"Index retrieved",
            index_time
        )
        
        # Create vision-aligned project
        result = await create_project(
            name="Vision-Aligned Project",
            mission="""
            Implement comprehensive testing suite aligned with vision:
            - Local-first philosophy
            - Multi-tenant architecture
            - Progressive enhancement
            - 90% test coverage target
            """
        )
        
        self.record_test(
            "Create vision-aligned project",
            result.get("success", False),
            "Project created with vision alignment"
        )
    
    async def test_error_recovery_workflow(self):
        """Test error handling and recovery scenarios"""
        print(f"\n{Colors.BOLD}Testing Error Recovery Workflow{Colors.RESET}")
        
        # Test 1: Invalid project operations
        result = await project_status(project_id="non-existent-id")
        self.record_test(
            "Handle non-existent project",
            not result.get("success", True),
            "Error handled gracefully"
        )
        
        # Test 2: Invalid agent operations
        result = await agent_health(agent_name="non-existent-agent")
        self.record_test(
            "Handle non-existent agent",
            not result.get("success", True),
            "Error handled gracefully"
        )
        
        # Test 3: Message to non-existent agent
        result = await create_project(name="Error Test", mission="Test errors")
        if result.get("success"):
            project_id = result["project_id"]
            
            result = await send_message(
                to_agents=["ghost_agent"],
                content="Test message",
                project_id=project_id
            )
            
            # Should succeed but message won't be delivered
            self.record_test(
                "Send message to non-existent agent",
                result.get("success", False),
                "Message queued (agent doesn't exist)"
            )
        
        # Test 4: Recovery after failure
        result = await create_project(
            name="Recovery Test",
            mission="Test recovery mechanisms"
        )
        
        if result.get("success"):
            project_id = result["project_id"]
            
            # Create agent
            await ensure_agent(
                project_id=project_id,
                agent_name="recovery_agent"
            )
            
            # Simulate failure by decommissioning
            await decommission_agent(
                agent_name="recovery_agent",
                project_id=project_id,
                reason="simulated_failure"
            )
            
            # Recreate agent (recovery)
            result = await ensure_agent(
                project_id=project_id,
                agent_name="recovery_agent"
            )
            
            self.record_test(
                "Agent recovery after failure",
                result.get("success", False),
                "Agent recreated successfully"
            )
    
    async def test_concurrent_operations(self):
        """Test concurrent project and agent operations"""
        print(f"\n{Colors.BOLD}Testing Concurrent Operations{Colors.RESET}")
        
        num_projects = 5
        projects = []
        
        # Create multiple projects concurrently
        start_time = time.time()
        tasks = []
        for i in range(num_projects):
            task = create_project(
                name=f"Concurrent Project {i}",
                mission=f"Test concurrent operations {i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        create_time = (time.time() - start_time) * 1000
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        self.record_test(
            f"Create {num_projects} projects concurrently",
            successful == num_projects,
            f"Created {successful}/{num_projects} projects",
            create_time
        )
        
        # Store project IDs
        for r in results:
            if isinstance(r, dict) and r.get("success"):
                projects.append(r["project_id"])
        
        # Create agents concurrently across projects
        if projects:
            agent_tasks = []
            for project_id in projects[:3]:  # Test with first 3 projects
                for agent_name in ["agent1", "agent2"]:
                    task = ensure_agent(
                        project_id=project_id,
                        agent_name=f"{agent_name}_{project_id[:8]}"
                    )
                    agent_tasks.append(task)
            
            start_time = time.time()
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            agent_time = (time.time() - start_time) * 1000
            
            successful_agents = sum(1 for r in agent_results 
                                  if isinstance(r, dict) and r.get("success"))
            self.record_test(
                "Create agents concurrently",
                successful_agents == len(agent_tasks),
                f"Created {successful_agents}/{len(agent_tasks)} agents",
                agent_time
            )
        
        # Test concurrent message sending
        if projects:
            message_tasks = []
            for project_id in projects[:3]:
                task = broadcast(
                    content=f"Concurrent broadcast for {project_id[:8]}",
                    project_id=project_id
                )
                message_tasks.append(task)
            
            start_time = time.time()
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            message_time = (time.time() - start_time) * 1000
            
            successful_messages = sum(1 for r in message_results 
                                    if isinstance(r, dict) and r.get("success"))
            self.record_test(
                "Send messages concurrently",
                successful_messages == len(message_tasks),
                f"Sent {successful_messages}/{len(message_tasks)} messages",
                message_time
            )
    
    async def run_all_tests(self):
        """Run complete E2E test suite"""
        print(f"\n{Colors.CYAN}{'='*60}")
        print(f"{Colors.BOLD}GiljoAI MCP END-TO-END WORKFLOW TEST SUITE")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
        await self.setup()
        
        try:
            # Run test categories
            await self.test_complete_project_lifecycle()
            await self.test_multi_agent_coordination()
            await self.test_message_flow_pattern()
            await self.test_vision_driven_workflow()
            await self.test_error_recovery_workflow()
            await self.test_concurrent_operations()
            
            # Print results
            self.print_results()
            
        finally:
            await self.teardown()
    
    def print_results(self):
        """Print test results summary"""
        print(f"\n{Colors.CYAN}{'='*60}")
        print(f"E2E WORKFLOW TEST RESULTS SUMMARY")
        print(f"{'='*60}{Colors.RESET}")
        
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.RESET}")
        print(f"Total: {total}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        # Workflow timing summary
        if self.workflow_times:
            print(f"\n{Colors.CYAN}Workflow Performance:{Colors.RESET}")
            for workflow, time_ms in self.workflow_times.items():
                print(f"  {workflow}: {time_ms:.2f}ms")
        
        # Performance tests summary
        perf_tests = [t for t in self.tests if t.get('time_ms')]
        if perf_tests:
            avg_time = sum(t['time_ms'] for t in perf_tests) / len(perf_tests)
            print(f"\n{Colors.CYAN}Average operation time: {avg_time:.2f}ms{Colors.RESET}")
        
        if self.failed > 0:
            print(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
            for test in self.tests:
                if not test['passed']:
                    print(f"  - {test['name']}: {test['details']}")
        
        # Overall status
        if pass_rate >= 90:
            status_color = Colors.GREEN
            status = "EXCELLENT - Ready for production"
        elif pass_rate >= 75:
            status_color = Colors.YELLOW
            status = "GOOD - Minor issues to address"
        else:
            status_color = Colors.RED
            status = "NEEDS IMPROVEMENT - Critical issues found"
        
        print(f"\n{status_color}{Colors.BOLD}Overall Status: {status}{Colors.RESET}")

async def main():
    """Main test runner"""
    suite = WorkflowTestSuite()
    await suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())