#!/usr/bin/env python
"""
Comprehensive test suite for GiljoAI Message Acknowledgment System
Tests all critical features of the message acknowledgment implementation
"""

import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Message
from giljo_mcp.tools.message import (
    send_message,
    get_messages,
    acknowledge_message,
    complete_message,
    broadcast
)

# Initialize database manager globally
db_manager = DatabaseManager("sqlite:///test_comprehensive.db", is_async=True)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add(self, test_name, passed, details=""):
        self.tests.append({
            'name': test_name,
            'passed': passed,
            'details': details
        })
        if passed:
            self.passed += 1
            print(f"{Colors.GREEN}✅ PASS{Colors.RESET}: {test_name}")
        else:
            self.failed += 1
            print(f"{Colors.RED}❌ FAIL{Colors.RESET}: {test_name}")
            if details:
                print(f"   {Colors.YELLOW}Details: {details}{Colors.RESET}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.RESET}")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️  SOME TESTS FAILED{Colors.RESET}")
        
        return self.failed == 0

async def test_acknowledge_message_array(results):
    """Test that acknowledge_message updates arrays correctly"""
    try:
        # Create a test message
        msg = await send_message(
            project_id="test-project-ack",
            to_agents=["agent1", "agent2"],
            content="Test acknowledgment arrays",
            from_agent="test-sender"
        )
        
        # Acknowledge from first agent
        ack1 = await acknowledge_message(msg['id'], "agent1")
        
        # Get message and check acknowledged_by array
        async with db_manager.get_session_async() as session:
            msg_obj = await session.get(Message, msg['id'])
        
        if msg_obj.acknowledged_by:
            ack_data = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
            
            # Check structure
            if isinstance(ack_data, list) and len(ack_data) > 0:
                first_ack = ack_data[0]
                has_agent = 'agent_name' in first_ack
                has_timestamp = 'timestamp' in first_ack
                correct_agent = first_ack.get('agent_name') == 'agent1'
                
                if has_agent and has_timestamp and correct_agent:
                    # Acknowledge from second agent
                    ack2 = await acknowledge_message(msg['id'], "agent2")
                    
                    # Refresh and check both acknowledgments
                    await session.refresh(msg_obj)
                    ack_data2 = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
                    
                    if len(ack_data2) == 2:
                        agents = [ack['agent_name'] for ack in ack_data2]
                        if 'agent1' in agents and 'agent2' in agents:
                            results.add("acknowledge_message array updates", True)
                        else:
                            results.add("acknowledge_message array updates", False, 
                                      f"Missing agents in array: {agents}")
                    else:
                        results.add("acknowledge_message array updates", False, 
                                  f"Expected 2 acknowledgments, got {len(ack_data2)}")
                else:
                    results.add("acknowledge_message array updates", False, 
                              f"Invalid structure: agent={has_agent}, timestamp={has_timestamp}, correct_agent={correct_agent}")
            else:
                results.add("acknowledge_message array updates", False, 
                          "acknowledged_by is not a list or is empty")
        else:
            results.add("acknowledge_message array updates", False, 
                      "acknowledged_by field is None")
        
    except Exception as e:
        results.add("acknowledge_message array updates", False, str(e))

async def test_complete_message_with_notes(results):
    """Test that complete_message works with notes parameter"""
    try:
        # Create a test message
        msg = await send_message(
            project_id="test-project-complete",
            to_agents=["agent1"],
            content="Test completion with notes",
            from_agent="test-sender"
        )
        
        # Complete with notes
        complete_result = await complete_message(
            msg['id'], 
            "agent1", 
            "Task completed successfully - all validations passed"
        )
        
        # Get message and check completed_by array
        async with db_manager.get_session_async() as session:
            msg_obj = await session.get(Message, msg['id'])
        
        if msg_obj.completed_by:
            comp_data = json.loads(msg_obj.completed_by) if isinstance(msg_obj.completed_by, str) else msg_obj.completed_by
            
            if isinstance(comp_data, list) and len(comp_data) > 0:
                first_comp = comp_data[0]
                has_agent = 'agent_name' in first_comp
                has_timestamp = 'timestamp' in first_comp
                has_notes = 'notes' in first_comp
                correct_agent = first_comp.get('agent_name') == 'agent1'
                correct_notes = 'successfully' in first_comp.get('notes', '')
                
                if all([has_agent, has_timestamp, has_notes, correct_agent, correct_notes]):
                    results.add("complete_message with notes", True)
                else:
                    results.add("complete_message with notes", False,
                              f"Invalid structure: agent={has_agent}, timestamp={has_timestamp}, "
                              f"notes={has_notes}, correct_agent={correct_agent}, correct_notes={correct_notes}")
            else:
                results.add("complete_message with notes", False, 
                          "completed_by is not a list or is empty")
        else:
            results.add("complete_message with notes", False, 
                      "completed_by field is None")
        
    except Exception as e:
        results.add("complete_message with notes", False, str(e))

async def test_auto_acknowledgment(results):
    """Test that get_messages auto-acknowledges"""
    try:
        # Create a test message
        msg = await send_message(
            project_id="test-project-auto",
            to_agents=["agent1", "agent2"],
            content="Test auto-acknowledgment",
            from_agent="test-sender"
        )
        
        # Get the message ID for verification
        msg_id = msg['id']
        
        # Get messages for agent1 (should auto-acknowledge)
        messages1 = await get_messages("agent1", project_id="test-project-auto")
        
        # Check if message was auto-acknowledged
        async with db_manager.get_session_async() as session:
            msg_obj = await session.get(Message, msg_id)
        
        if msg_obj.acknowledged_by:
            ack_data = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
            
            if isinstance(ack_data, list) and len(ack_data) > 0:
                agents = [ack['agent_name'] for ack in ack_data]
                if 'agent1' in agents:
                    # Get messages for agent2 (should also auto-acknowledge)
                    messages2 = await get_messages("agent2", project_id="test-project-auto")
                    
                    await session.refresh(msg_obj)
                    ack_data2 = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
                    agents2 = [ack['agent_name'] for ack in ack_data2]
                    
                    if 'agent2' in agents2:
                        results.add("auto-acknowledgment in get_messages", True)
                    else:
                        results.add("auto-acknowledgment in get_messages", False,
                                  f"agent2 not auto-acknowledged: {agents2}")
                else:
                    results.add("auto-acknowledgment in get_messages", False,
                              f"agent1 not auto-acknowledged: {agents}")
            else:
                results.add("auto-acknowledgment in get_messages", False,
                          "No acknowledgments found after get_messages")
        else:
            results.add("auto-acknowledgment in get_messages", False,
                      "acknowledged_by is None after get_messages")
        
    except Exception as e:
        results.add("auto-acknowledgment in get_messages", False, str(e))

async def test_array_structure_format(results):
    """Test that array structures match expected format"""
    try:
        # Create and process a message
        msg = await send_message(
            project_id="test-project-format",
            to_agents=["agent1"],
            content="Test array formats",
            from_agent="test-sender"
        )
        
        # Acknowledge and complete
        await acknowledge_message(msg['id'], "agent1")
        await complete_message(msg['id'], "agent1", "Format test complete")
        
        # Get message and validate structures
        async with db_manager.get_session_async() as session:
            msg_obj = await session.get(Message, msg['id'])
        
        format_valid = True
        details = []
        
        # Check acknowledged_by format: {agent_name, timestamp}
        if msg_obj.acknowledged_by:
            ack_data = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
            for ack in ack_data:
                if not all(k in ack for k in ['agent_name', 'timestamp']):
                    format_valid = False
                    details.append(f"Invalid ack format: {ack}")
                # Validate timestamp format
                try:
                    datetime.fromisoformat(ack['timestamp'])
                except:
                    format_valid = False
                    details.append(f"Invalid timestamp in ack: {ack['timestamp']}")
        
        # Check completed_by format: {agent_name, timestamp, notes}
        if msg_obj.completed_by:
            comp_data = json.loads(msg_obj.completed_by) if isinstance(msg_obj.completed_by, str) else msg_obj.completed_by
            for comp in comp_data:
                if not all(k in comp for k in ['agent_name', 'timestamp', 'notes']):
                    format_valid = False
                    details.append(f"Invalid completion format: {comp}")
                # Validate timestamp format
                try:
                    datetime.fromisoformat(comp['timestamp'])
                except:
                    format_valid = False
                    details.append(f"Invalid timestamp in completion: {comp['timestamp']}")
        
        if format_valid:
            results.add("array structure format validation", True)
        else:
            results.add("array structure format validation", False, "; ".join(details))
        
    except Exception as e:
        results.add("array structure format validation", False, str(e))

async def test_multi_agent_delivery(results):
    """Test that messages are delivered to multiple agents correctly"""
    try:
        # Send to multiple agents
        msg = await send_message(
            project_id="test-project-multi",
            to_agents=["agent1", "agent2", "agent3"],
            content="Multi-agent test message",
            from_agent="test-sender"
        )
        
        # Each agent should be able to retrieve the message
        messages1 = await get_messages("agent1", project_id="test-project-multi")
        messages2 = await get_messages("agent2", project_id="test-project-multi")
        messages3 = await get_messages("agent3", project_id="test-project-multi")
        
        found1 = any(m['id'] == msg['id'] for m in messages1['messages'])
        found2 = any(m['id'] == msg['id'] for m in messages2['messages'])
        found3 = any(m['id'] == msg['id'] for m in messages3['messages'])
        
        if all([found1, found2, found3]):
            # Check that all agents are auto-acknowledged
            async with db_manager.get_session_async() as session:
                msg_obj = await session.get(Message, msg['id'])
            
            if msg_obj.acknowledged_by:
                ack_data = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
                agents = [ack['agent_name'] for ack in ack_data]
                
                if all(agent in agents for agent in ["agent1", "agent2", "agent3"]):
                    results.add("multi-agent message delivery", True)
                else:
                    results.add("multi-agent message delivery", False,
                              f"Not all agents acknowledged: {agents}")
            else:
                results.add("multi-agent message delivery", False,
                          "No acknowledgments found")
        else:
            results.add("multi-agent message delivery", False,
                      f"Message not received by all agents: agent1={found1}, agent2={found2}, agent3={found3}")
        
    except Exception as e:
        results.add("multi-agent message delivery", False, str(e))

async def test_no_message_deletion(results):
    """Verify that messages cannot be deleted (audit trail integrity)"""
    try:
        # Create a test message
        msg = await send_message(
            project_id="test-project-delete",
            to_agents=["agent1"],
            content="Test deletion prevention",
            from_agent="test-sender"
        )
        
        msg_id = msg['id']
        
        # Try to find a delete function (should not exist)
        from giljo_mcp.tools import message as msg_module
        has_delete = hasattr(msg_module, 'delete_message')
        
        if has_delete:
            results.add("no message deletion capability", False,
                      "delete_message function exists in module")
        else:
            # Also verify message persists after completion
            await acknowledge_message(msg_id, "agent1")
            await complete_message(msg_id, "agent1", "Completed")
            
            # Message should still exist
            async with db_manager.get_session_async() as session:
                msg_obj = await session.get(Message, msg_id)
            
            if msg_obj:
                results.add("no message deletion capability", True)
            else:
                results.add("no message deletion capability", False,
                          "Message disappeared after completion")
        
    except Exception as e:
        results.add("no message deletion capability", False, str(e))

async def test_broadcast_functionality(results):
    """Test broadcast message functionality"""
    try:
        # Create multiple agents in project
        project_id = "test-project-broadcast"
        
        # Send broadcast
        broadcast_result = await broadcast(
            content="System broadcast test",
            project_id=project_id,
            priority="high"
        )
        
        # Check that message type is broadcast
        if broadcast_result and 'id' in broadcast_result:
            async with db_manager.get_session_async() as session:
                msg_obj = await session.get(Message, broadcast_result['id'])
            
            if msg_obj:
                is_broadcast = msg_obj.message_type == "broadcast"
                correct_priority = msg_obj.priority == "high"
                
                if is_broadcast and correct_priority:
                    results.add("broadcast functionality", True)
                else:
                    results.add("broadcast functionality", False,
                              f"type={msg_obj.message_type}, priority={msg_obj.priority}")
            else:
                results.add("broadcast functionality", False,
                          "Broadcast message not found")
        else:
            results.add("broadcast functionality", False,
                      "Broadcast did not return message ID")
        
    except Exception as e:
        results.add("broadcast functionality", False, str(e))

async def test_integration_flow(results):
    """Test complete acknowledgment flow integration"""
    try:
        project_id = "test-project-integration"
        
        # 1. Send message to multiple agents
        msg = await send_message(
            project_id=project_id,
            to_agents=["worker1", "worker2", "supervisor"],
            content="Integration test task",
            from_agent="orchestrator",
            priority="critical"
        )
        
        msg_id = msg['id']
        
        # 2. Worker1 retrieves (auto-acknowledges)
        worker1_msgs = await get_messages("worker1", project_id=project_id)
        
        # 3. Worker1 completes their part
        await complete_message(msg_id, "worker1", "Worker1 task complete")
        
        # 4. Worker2 retrieves (auto-acknowledges)
        worker2_msgs = await get_messages("worker2", project_id=project_id)
        
        # 5. Worker2 completes their part
        await complete_message(msg_id, "worker2", "Worker2 task complete")
        
        # 6. Supervisor reviews
        supervisor_msgs = await get_messages("supervisor", project_id=project_id)
        
        # 7. Verify final state
        async with db_manager.get_session_async() as session:
            msg_obj = await session.get(Message, msg_id)
        
        if msg_obj:
            # Parse arrays
            ack_data = json.loads(msg_obj.acknowledged_by) if isinstance(msg_obj.acknowledged_by, str) else msg_obj.acknowledged_by
            comp_data = json.loads(msg_obj.completed_by) if isinstance(msg_obj.completed_by, str) else msg_obj.completed_by
            
            # Check all agents acknowledged
            ack_agents = [ack['agent_name'] for ack in (ack_data or [])]
            all_acked = all(agent in ack_agents for agent in ["worker1", "worker2", "supervisor"])
            
            # Check workers completed
            comp_agents = [comp['agent_name'] for comp in (comp_data or [])]
            workers_completed = all(agent in comp_agents for agent in ["worker1", "worker2"])
            
            # Check completion notes exist
            comp_notes = [comp.get('notes', '') for comp in (comp_data or [])]
            has_notes = all('complete' in note.lower() for note in comp_notes if note)
            
            if all_acked and workers_completed and has_notes:
                results.add("integration flow test", True)
            else:
                results.add("integration flow test", False,
                          f"acked={all_acked}, completed={workers_completed}, notes={has_notes}")
        else:
            results.add("integration flow test", False, "Message not found")
        
    except Exception as e:
        results.add("integration flow test", False, str(e))

async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}GiljoAI Message Acknowledgment System - Comprehensive Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    # Initialize database
    print(f"{Colors.BLUE}Initializing database...{Colors.RESET}")
    await db_manager.create_tables_async()
    
    results = TestResults()
    
    # Run all tests
    print(f"\n{Colors.BOLD}Running Tests:{Colors.RESET}\n")
    
    await test_acknowledge_message_array(results)
    await test_complete_message_with_notes(results)
    await test_auto_acknowledgment(results)
    await test_array_structure_format(results)
    await test_multi_agent_delivery(results)
    await test_no_message_deletion(results)
    await test_broadcast_functionality(results)
    await test_integration_flow(results)
    
    # Show summary
    all_passed = results.summary()
    
    # Database will close automatically with context managers
    
    # Return exit code
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)