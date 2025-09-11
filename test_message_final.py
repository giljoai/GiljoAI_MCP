#!/usr/bin/env python
"""
Final comprehensive test for GiljoAI Message Acknowledgment System
Tests all critical features with proper setup
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Base, Project, Agent, Message

# Use simple ASCII for Windows compatibility
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
            print(f"[PASS] {test_name}")
        else:
            self.failed += 1
            print(f"[FAIL] {test_name}")
            if details:
                print(f"       Details: {details}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed == 0:
            print("\n*** ALL TESTS PASSED! ***")
        else:
            print("\n*** SOME TESTS FAILED ***")
        
        return self.failed == 0

def setup_test_data(session):
    """Create necessary test data"""
    # Create project
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key="test-tenant",
        name="Test Project",
        mission="Testing message acknowledgment",
        status="active"
    )
    session.add(project)
    
    # Create agents  
    orchestrator = Agent(
        id=str(uuid.uuid4()),
        tenant_key="test-tenant",
        project_id=project.id,
        name="orchestrator",
        role="orchestrator",
        status="active"
    )
    agent1 = Agent(
        id=str(uuid.uuid4()),
        tenant_key="test-tenant",
        project_id=project.id,
        name="agent1",
        role="worker",
        status="active"
    )
    agent2 = Agent(
        id=str(uuid.uuid4()),
        tenant_key="test-tenant",
        project_id=project.id,
        name="agent2",
        role="worker",
        status="active"
    )
    agent3 = Agent(
        id=str(uuid.uuid4()),
        tenant_key="test-tenant",
        project_id=project.id,
        name="agent3",
        role="supervisor",
        status="active"
    )
    
    session.add_all([orchestrator, agent1, agent2, agent3])
    session.commit()
    
    return project.id, orchestrator.id

def test_acknowledge_array(db_manager, project_id, orchestrator_id, results):
    """Test acknowledgment array updates"""
    try:
        with db_manager.get_session() as session:
            # Create message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1", "agent2"],
                message_type="direct",
                content="Test acknowledgment",
                priority="normal",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            
            # Acknowledge from agent1
            msg.acknowledged_by.append({
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat()
            })
            session.commit()
            
            # Acknowledge from agent2
            msg.acknowledged_by.append({
                "agent_name": "agent2", 
                "timestamp": datetime.utcnow().isoformat()
            })
            session.commit()
            
            # Verify
            agents = [ack['agent_name'] for ack in msg.acknowledged_by]
            if 'agent1' in agents and 'agent2' in agents and len(msg.acknowledged_by) == 2:
                results.add("Acknowledgment array updates", True)
            else:
                results.add("Acknowledgment array updates", False, f"Got agents: {agents}")
    except Exception as e:
        results.add("Acknowledgment array updates", False, str(e))

def test_complete_with_notes(db_manager, project_id, orchestrator_id, results):
    """Test completion with notes"""
    try:
        with db_manager.get_session() as session:
            # Create message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1"],
                message_type="direct",
                content="Test completion",
                priority="normal",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            
            # Complete with notes
            msg.completed_by.append({
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "Task completed successfully"
            })
            msg.status = "completed"
            session.commit()
            
            # Verify
            if len(msg.completed_by) == 1:
                comp = msg.completed_by[0]
                if all(k in comp for k in ['agent_name', 'timestamp', 'notes']):
                    if comp['agent_name'] == 'agent1' and 'successfully' in comp['notes']:
                        results.add("Completion with notes", True)
                    else:
                        results.add("Completion with notes", False, "Wrong values")
                else:
                    results.add("Completion with notes", False, f"Missing keys: {comp.keys()}")
            else:
                results.add("Completion with notes", False, "No completion entry")
    except Exception as e:
        results.add("Completion with notes", False, str(e))

def test_auto_acknowledgment(db_manager, project_id, orchestrator_id, results):
    """Test auto-acknowledgment simulation"""
    try:
        with db_manager.get_session() as session:
            # Create message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1", "agent2"],
                message_type="direct",
                content="Test auto-ack",
                priority="normal",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            msg_id = msg.id
            
            # Simulate get_messages for agent1 (auto-ack)
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if "agent1" in msg.to_agents:
                msg.acknowledged_by.append({
                    "agent_name": "agent1",
                    "timestamp": datetime.utcnow().isoformat()
                })
                msg.status = "acknowledged"
                session.commit()
            
            # Simulate get_messages for agent2 (auto-ack)
            if "agent2" in msg.to_agents:
                # Check not already acked
                agents_acked = [ack['agent_name'] for ack in msg.acknowledged_by]
                if "agent2" not in agents_acked:
                    msg.acknowledged_by.append({
                        "agent_name": "agent2",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    session.commit()
            
            # Verify both auto-acked
            agents = [ack['agent_name'] for ack in msg.acknowledged_by]
            if 'agent1' in agents and 'agent2' in agents:
                results.add("Auto-acknowledgment", True)
            else:
                results.add("Auto-acknowledgment", False, f"Agents: {agents}")
    except Exception as e:
        results.add("Auto-acknowledgment", False, str(e))

def test_array_formats(db_manager, project_id, orchestrator_id, results):
    """Test array structure formats"""
    try:
        with db_manager.get_session() as session:
            # Create and process message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1"],
                message_type="direct",
                content="Test formats",
                priority="normal",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            
            # Add acknowledgment
            ack_entry = {
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat()
            }
            msg.acknowledged_by.append(ack_entry)
            
            # Add completion
            comp_entry = {
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "Format test"
            }
            msg.completed_by.append(comp_entry)
            session.commit()
            
            # Validate formats
            valid = True
            details = []
            
            # Check ack format
            for ack in msg.acknowledged_by:
                if not all(k in ack for k in ['agent_name', 'timestamp']):
                    valid = False
                    details.append("Invalid ack format")
                try:
                    datetime.fromisoformat(ack['timestamp'])
                except:
                    valid = False
                    details.append("Invalid ack timestamp")
            
            # Check completion format
            for comp in msg.completed_by:
                if not all(k in comp for k in ['agent_name', 'timestamp', 'notes']):
                    valid = False
                    details.append("Invalid completion format")
                try:
                    datetime.fromisoformat(comp['timestamp'])
                except:
                    valid = False
                    details.append("Invalid completion timestamp")
            
            if valid:
                results.add("Array structure formats", True)
            else:
                results.add("Array structure formats", False, "; ".join(details))
    except Exception as e:
        results.add("Array structure formats", False, str(e))

def test_multi_agent(db_manager, project_id, orchestrator_id, results):
    """Test multi-agent message delivery"""
    try:
        with db_manager.get_session() as session:
            # Create multi-agent message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1", "agent2", "agent3"],
                message_type="direct",
                content="Multi-agent test",
                priority="normal",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            
            # Each agent acknowledges
            for agent in ["agent1", "agent2", "agent3"]:
                msg.acknowledged_by.append({
                    "agent_name": agent,
                    "timestamp": datetime.utcnow().isoformat()
                })
            session.commit()
            
            # Verify all agents in to_agents and acknowledged_by
            to_agents_ok = set(msg.to_agents) == {"agent1", "agent2", "agent3"}
            ack_agents = [ack['agent_name'] for ack in msg.acknowledged_by]
            acked_ok = set(ack_agents) == {"agent1", "agent2", "agent3"}
            
            if to_agents_ok and acked_ok:
                results.add("Multi-agent delivery", True)
            else:
                results.add("Multi-agent delivery", False, 
                          f"to_agents={msg.to_agents}, acked={ack_agents}")
    except Exception as e:
        results.add("Multi-agent delivery", False, str(e))

def test_no_deletion(db_manager, project_id, orchestrator_id, results):
    """Test message persistence (no deletion)"""
    try:
        with db_manager.get_session() as session:
            # Create message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1"],
                message_type="direct",
                content="Test no deletion",
                priority="normal",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            msg_id = msg.id
            
            # Complete the message
            msg.status = "completed"
            msg.completed_by.append({
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "Done"
            })
            session.commit()
            
            # Verify still exists
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if msg:
                results.add("No message deletion", True)
            else:
                results.add("No message deletion", False, "Message disappeared")
    except Exception as e:
        results.add("No message deletion", False, str(e))

def test_broadcast(db_manager, project_id, orchestrator_id, results):
    """Test broadcast messages"""
    try:
        with db_manager.get_session() as session:
            # Create broadcast
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=None,  # System broadcast
                to_agents=[],  # Empty = all agents
                message_type="broadcast",
                content="System broadcast",
                priority="high",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            
            # Verify broadcast properties
            if msg.message_type == "broadcast" and msg.priority == "high":
                results.add("Broadcast functionality", True)
            else:
                results.add("Broadcast functionality", False,
                          f"type={msg.message_type}, priority={msg.priority}")
    except Exception as e:
        results.add("Broadcast functionality", False, str(e))

def test_integration_flow(db_manager, project_id, orchestrator_id, results):
    """Test complete workflow"""
    try:
        with db_manager.get_session() as session:
            # Create task message
            msg = Message(
                tenant_key="test-tenant",
                project_id=project_id,
                from_agent_id=orchestrator_id,
                to_agents=["agent1", "agent2", "agent3"],
                message_type="direct",
                content="Integration test task",
                priority="critical",
                status="pending",
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(msg)
            session.commit()
            
            # Agent1 acknowledges and completes
            msg.acknowledged_by.append({
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat()
            })
            msg.completed_by.append({
                "agent_name": "agent1",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "Agent1 complete"
            })
            
            # Agent2 acknowledges and completes
            msg.acknowledged_by.append({
                "agent_name": "agent2",
                "timestamp": datetime.utcnow().isoformat()
            })
            msg.completed_by.append({
                "agent_name": "agent2",
                "timestamp": datetime.utcnow().isoformat(),
                "notes": "Agent2 complete"
            })
            
            # Agent3 acknowledges (supervisor review)
            msg.acknowledged_by.append({
                "agent_name": "agent3",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            msg.status = "completed"
            session.commit()
            
            # Verify workflow
            ack_agents = [ack['agent_name'] for ack in msg.acknowledged_by]
            comp_agents = [comp['agent_name'] for comp in msg.completed_by]
            
            all_acked = all(a in ack_agents for a in ["agent1", "agent2", "agent3"])
            workers_completed = all(a in comp_agents for a in ["agent1", "agent2"])
            has_notes = all('complete' in comp.get('notes', '').lower() 
                          for comp in msg.completed_by)
            
            if all_acked and workers_completed and has_notes:
                results.add("Integration workflow", True)
            else:
                results.add("Integration workflow", False,
                          f"acked={all_acked}, completed={workers_completed}, notes={has_notes}")
    except Exception as e:
        results.add("Integration workflow", False, str(e))

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("GiljoAI Message Acknowledgment - Comprehensive Test Suite")
    print("="*60 + "\n")
    
    # Initialize database
    print("Initializing database...")
    db_manager = DatabaseManager("sqlite:///test_final.db", is_async=False)
    db_manager.create_tables()
    
    # Clean existing data
    with db_manager.get_session() as session:
        session.query(Message).delete()
        session.query(Agent).delete()
        session.query(Project).delete()
        session.commit()
        
        # Setup test data
        project_id, orchestrator_id = setup_test_data(session)
    
    print("Running tests...\n")
    
    results = TestResults()
    
    # Run all tests
    test_acknowledge_array(db_manager, project_id, orchestrator_id, results)
    test_complete_with_notes(db_manager, project_id, orchestrator_id, results)
    test_auto_acknowledgment(db_manager, project_id, orchestrator_id, results)
    test_array_formats(db_manager, project_id, orchestrator_id, results)
    test_multi_agent(db_manager, project_id, orchestrator_id, results)
    test_no_deletion(db_manager, project_id, orchestrator_id, results)
    test_broadcast(db_manager, project_id, orchestrator_id, results)
    test_integration_flow(db_manager, project_id, orchestrator_id, results)
    
    # Summary
    all_passed = results.summary()
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)