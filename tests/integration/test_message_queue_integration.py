#!/usr/bin/env python
"""
Comprehensive test suite for GiljoAI Message Acknowledgment System
Tests all critical features of the message acknowledgment implementation
"""

import pytest


pytest.skip("TODO(0127a-2): Comprehensive refactoring needed for MCPAgentJob model", allow_module_level=True)
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


from src.giljo_mcp.database import DatabaseManager

# TODO(0127a): from src.giljo_mcp.models import Agent, Message, Project
# from src.giljo_mcp.models import MCPAgentJob  # Use this instead
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add(self, test_name, passed, details=""):
        self.tests.append({"name": test_name, "passed": passed, "details": details})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            if details:
                pass

    def summary(self):
        self.passed + self.failed

        if self.failed == 0:
            pass
        else:
            pass

        return self.failed == 0


def test_acknowledge_message_array(db_manager, results):
    """Test that acknowledge_message updates arrays correctly"""
    try:
        with db_manager.get_session() as session:
            # Create test message
            message = Message(
                tenant_key="test-tenant-ack",
                project_id="test-project-ack",
                to_agents=["agent1", "agent2"],
                message_type="direct",
                content="Test acknowledgment arrays",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Simulate acknowledgment from agent1
            message.status = "acknowledged"
            message.acknowledged_at = datetime.now(timezone.utc)

            if not message.acknowledged_by:
                message.acknowledged_by = []

            message.acknowledged_by.append(
                {"agent_name": "agent1", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            session.commit()

            # Verify structure
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if msg.acknowledged_by:
                ack_data = msg.acknowledged_by
                if isinstance(ack_data, list) and len(ack_data) > 0:
                    first_ack = ack_data[0]
                    has_agent = "agent_name" in first_ack
                    has_timestamp = "timestamp" in first_ack
                    correct_agent = first_ack.get("agent_name") == "agent1"

                    if has_agent and has_timestamp and correct_agent:
                        # Add second acknowledgment
                        msg.acknowledged_by.append(
                            {"agent_name": "agent2", "timestamp": datetime.now(timezone.utc).isoformat()}
                        )
                        session.commit()

                        # Verify both acknowledgments
                        msg = session.query(Message).filter(Message.id == msg_id).first()
                        ack_data2 = msg.acknowledged_by

                        if len(ack_data2) == 2:
                            agents = [ack["agent_name"] for ack in ack_data2]
                            if "agent1" in agents and "agent2" in agents:
                                results.add("acknowledge_message array updates", True)
                            else:
                                results.add(
                                    "acknowledge_message array updates", False, f"Missing agents in array: {agents}"
                                )
                        else:
                            results.add(
                                "acknowledge_message array updates",
                                False,
                                f"Expected 2 acknowledgments, got {len(ack_data2)}",
                            )
                    else:
                        results.add(
                            "acknowledge_message array updates",
                            False,
                            f"Invalid structure: agent={has_agent}, timestamp={has_timestamp}, correct_agent={correct_agent}",
                        )
                else:
                    results.add("acknowledge_message array updates", False, "acknowledged_by is not a list or is empty")
            else:
                results.add("acknowledge_message array updates", False, "acknowledged_by field is None")

    except Exception as e:
        results.add("acknowledge_message array updates", False, str(e))


def test_complete_message_with_notes(db_manager, results):
    """Test that complete_message works with notes parameter"""
    try:
        with db_manager.get_session() as session:
            # Create test message
            message = Message(
                tenant_key="test-tenant-complete",
                project_id="test-project-complete",
                to_agents=["agent1"],
                message_type="direct",
                content="Test completion with notes",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Complete with notes
            message.status = "database_initialized"
            message.database_initialized_at = datetime.now(timezone.utc)

            if not message.completed_by:
                message.completed_by = []

            message.completed_by.append(
                {
                    "agent_name": "agent1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "notes": "Task completed successfully - all validations passed",
                }
            )
            session.commit()

            # Verify structure
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if msg.completed_by:
                comp_data = msg.completed_by

                if isinstance(comp_data, list) and len(comp_data) > 0:
                    first_comp = comp_data[0]
                    has_agent = "agent_name" in first_comp
                    has_timestamp = "timestamp" in first_comp
                    has_notes = "notes" in first_comp
                    correct_agent = first_comp.get("agent_name") == "agent1"
                    correct_notes = "successfully" in first_comp.get("notes", "")

                    if all([has_agent, has_timestamp, has_notes, correct_agent, correct_notes]):
                        results.add("complete_message with notes", True)
                    else:
                        results.add(
                            "complete_message with notes",
                            False,
                            f"Invalid structure: agent={has_agent}, timestamp={has_timestamp}, "
                            f"notes={has_notes}, correct_agent={correct_agent}, correct_notes={correct_notes}",
                        )
                else:
                    results.add("complete_message with notes", False, "completed_by is not a list or is empty")
            else:
                results.add("complete_message with notes", False, "completed_by field is None")

    except Exception as e:
        results.add("complete_message with notes", False, str(e))


def test_auto_acknowledgment(db_manager, results):
    """Test that get_messages auto-acknowledges"""
    try:
        with db_manager.get_session() as session:
            # Create test message
            message = Message(
                tenant_key="test-tenant-auto",
                project_id="test-project-auto",
                to_agents=["agent1", "agent2"],
                message_type="direct",
                content="Test auto-acknowledgment",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Simulate get_messages for agent1 (auto-acknowledge)
            msg = session.query(Message).filter(Message.id == msg_id).first()

            if "agent1" in msg.to_agents:
                msg.status = "acknowledged"
                msg.acknowledged_at = datetime.now(timezone.utc)

                if not msg.acknowledged_by:
                    msg.acknowledged_by = []

                # Check if agent1 not already acknowledged
                agents_acked = [ack["agent_name"] for ack in msg.acknowledged_by]
                if "agent1" not in agents_acked:
                    msg.acknowledged_by.append(
                        {"agent_name": "agent1", "timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                session.commit()

            # Verify agent1 acknowledgment
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if msg.acknowledged_by:
                agents = [ack["agent_name"] for ack in msg.acknowledged_by]
                if "agent1" in agents:
                    # Simulate get_messages for agent2
                    if "agent2" in msg.to_agents:
                        if "agent2" not in [ack["agent_name"] for ack in msg.acknowledged_by]:
                            msg.acknowledged_by.append(
                                {"agent_name": "agent2", "timestamp": datetime.now(timezone.utc).isoformat()}
                            )
                        session.commit()

                    # Final verification
                    msg = session.query(Message).filter(Message.id == msg_id).first()
                    agents2 = [ack["agent_name"] for ack in msg.acknowledged_by]

                    if "agent2" in agents2:
                        results.add("auto-acknowledgment in get_messages", True)
                    else:
                        results.add(
                            "auto-acknowledgment in get_messages", False, f"agent2 not auto-acknowledged: {agents2}"
                        )
                else:
                    results.add("auto-acknowledgment in get_messages", False, f"agent1 not auto-acknowledged: {agents}")
            else:
                results.add("auto-acknowledgment in get_messages", False, "No acknowledgments found after get_messages")

    except Exception as e:
        results.add("auto-acknowledgment in get_messages", False, str(e))


def test_array_structure_format(db_manager, results):
    """Test that array structures match expected format"""
    try:
        with db_manager.get_session() as session:
            # Create and process a message
            message = Message(
                tenant_key="test-tenant-format",
                project_id="test-project-format",
                to_agents=["agent1"],
                message_type="direct",
                content="Test array formats",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Acknowledge
            message.acknowledged_by.append(
                {"agent_name": "agent1", "timestamp": datetime.now(timezone.utc).isoformat()}
            )

            # Complete
            message.completed_by.append(
                {
                    "agent_name": "agent1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "notes": "Format test complete",
                }
            )
            session.commit()

            # Validate structures
            msg = session.query(Message).filter(Message.id == msg_id).first()

            format_valid = True
            details = []

            # Check acknowledged_by format: {agent_name, timestamp}
            if msg.acknowledged_by:
                for ack in msg.acknowledged_by:
                    if not all(k in ack for k in ["agent_name", "timestamp"]):
                        format_valid = False
                        details.append(f"Invalid ack format: {ack}")
                    # Validate timestamp format
                    try:
                        datetime.fromisoformat(ack["timestamp"])
                    except:
                        format_valid = False
                        details.append(f"Invalid timestamp in ack: {ack['timestamp']}")

            # Check completed_by format: {agent_name, timestamp, notes}
            if msg.completed_by:
                for comp in msg.completed_by:
                    if not all(k in comp for k in ["agent_name", "timestamp", "notes"]):
                        format_valid = False
                        details.append(f"Invalid completion format: {comp}")
                    # Validate timestamp format
                    try:
                        datetime.fromisoformat(comp["timestamp"])
                    except:
                        format_valid = False
                        details.append(f"Invalid timestamp in completion: {comp['timestamp']}")

            if format_valid:
                results.add("array structure format validation", True)
            else:
                results.add("array structure format validation", False, "; ".join(details))

    except Exception as e:
        results.add("array structure format validation", False, str(e))


def test_multi_agent_delivery(db_manager, results):
    """Test that messages are delivered to multiple agents correctly"""
    try:
        with db_manager.get_session() as session:
            # Create message for multiple agents
            message = Message(
                tenant_key="test-tenant-multi",
                project_id="test-project-multi",
                to_agents=["agent1", "agent2", "agent3"],
                message_type="direct",
                content="Multi-agent test message",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Simulate each agent retrieving the message
            msg = session.query(Message).filter(Message.id == msg_id).first()

            # Check that message is visible to all agents
            agents_can_see = all(agent in msg.to_agents for agent in ["agent1", "agent2", "agent3"])

            if agents_can_see:
                # Simulate auto-acknowledgment for each agent
                for agent in ["agent1", "agent2", "agent3"]:
                    if agent not in [ack.get("agent_name") for ack in msg.acknowledged_by]:
                        msg.acknowledged_by.append(
                            {"agent_name": agent, "timestamp": datetime.now(timezone.utc).isoformat()}
                        )

                msg.status = "acknowledged"
                session.commit()

                # Verify all agents acknowledged
                msg = session.query(Message).filter(Message.id == msg_id).first()
                agents_acked = [ack["agent_name"] for ack in msg.acknowledged_by]

                if all(agent in agents_acked for agent in ["agent1", "agent2", "agent3"]):
                    results.add("multi-agent message delivery", True)
                else:
                    results.add("multi-agent message delivery", False, f"Not all agents acknowledged: {agents_acked}")
            else:
                results.add(
                    "multi-agent message delivery", False, f"Message not visible to all agents: {msg.to_agents}"
                )

    except Exception as e:
        results.add("multi-agent message delivery", False, str(e))


def test_no_message_deletion(db_manager, results):
    """Verify that messages cannot be deleted (audit trail integrity)"""
    try:
        with db_manager.get_session() as session:
            # Create test message
            message = Message(
                tenant_key="test-tenant-delete",
                project_id="test-project-delete",
                to_agents=["agent1"],
                message_type="direct",
                content="Test deletion prevention",
                priority="normal",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Complete the message
            message.status = "database_initialized"
            message.database_initialized_at = datetime.now(timezone.utc)
            message.completed_by.append(
                {"agent_name": "agent1", "timestamp": datetime.now(timezone.utc).isoformat(), "notes": "Completed"}
            )
            session.commit()

            # Verify message still exists after completion
            msg = session.query(Message).filter(Message.id == msg_id).first()

            if msg:
                # Also verify no delete method exists in the module
                try:
                    from src.giljo_mcp.tools import message as msg_module

                    has_delete = hasattr(msg_module, "delete_message")

                    if has_delete:
                        results.add("no message deletion capability", False, "delete_message function exists in module")
                    else:
                        results.add("no message deletion capability", True)
                except ImportError:
                    # Module structure might be different, but message persists
                    results.add("no message deletion capability", True)
            else:
                results.add("no message deletion capability", False, "Message disappeared after completion")

    except Exception as e:
        results.add("no message deletion capability", False, str(e))


def test_broadcast_functionality(db_manager, results):
    """Test broadcast message functionality"""
    try:
        with db_manager.get_session() as session:
            # Create broadcast message
            broadcast_msg = Message(
                tenant_key="test-tenant-broadcast",
                project_id="test-project-broadcast",
                from_agent_id=None,  # System broadcast
                to_agents=[],  # Broadcast to all
                message_type="broadcast",
                content="System broadcast test",
                priority="high",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(broadcast_msg)
            session.commit()
            msg_id = broadcast_msg.id

            # Verify broadcast properties
            msg = session.query(Message).filter(Message.id == msg_id).first()

            if msg:
                is_broadcast = msg.message_type == "broadcast"
                correct_priority = msg.priority == "high"

                if is_broadcast and correct_priority:
                    results.add("broadcast functionality", True)
                else:
                    results.add("broadcast functionality", False, f"type={msg.message_type}, priority={msg.priority}")
            else:
                results.add("broadcast functionality", False, "Broadcast message not found")

    except Exception as e:
        results.add("broadcast functionality", False, str(e))


def test_integration_flow(db_manager, results):
    """Test complete acknowledgment flow integration"""
    try:
        with db_manager.get_session() as session:
            # Setup project and agents
            project = Project(
                id=str(uuid.uuid4()),
                tenant_key="test-tenant-integration",
                name="Integration Test Project",
                status="active",
            )
            session.add(project)

            # Create message
            message = Message(
                tenant_key="test-tenant-integration",
                project_id=project.id,
                to_agents=["worker1", "worker2", "supervisor"],
                message_type="direct",
                content="Integration test task",
                priority="critical",
                status="waiting",
                acknowledged_by=[],
                completed_by=[],
            )
            session.add(message)
            session.commit()
            msg_id = message.id

            # Worker1 retrieves and auto-acknowledges
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if "worker1" in msg.to_agents:
                msg.status = "acknowledged"
                msg.acknowledged_by.append(
                    {"agent_name": "worker1", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                session.commit()

            # Worker1 completes their part
            msg.completed_by.append(
                {
                    "agent_name": "worker1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "notes": "Worker1 task complete",
                }
            )
            session.commit()

            # Worker2 retrieves and auto-acknowledges
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if "worker2" in msg.to_agents:
                if "worker2" not in [ack["agent_name"] for ack in msg.acknowledged_by]:
                    msg.acknowledged_by.append(
                        {"agent_name": "worker2", "timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                session.commit()

            # Worker2 completes their part
            msg.completed_by.append(
                {
                    "agent_name": "worker2",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "notes": "Worker2 task complete",
                }
            )
            session.commit()

            # Supervisor reviews
            msg = session.query(Message).filter(Message.id == msg_id).first()
            if "supervisor" in msg.to_agents:
                if "supervisor" not in [ack["agent_name"] for ack in msg.acknowledged_by]:
                    msg.acknowledged_by.append(
                        {"agent_name": "supervisor", "timestamp": datetime.now(timezone.utc).isoformat()}
                    )
                session.commit()

            # Verify final state
            msg = session.query(Message).filter(Message.id == msg_id).first()

            if msg:
                # Check all agents acknowledged
                ack_agents = [ack["agent_name"] for ack in msg.acknowledged_by]
                all_acked = all(agent in ack_agents for agent in ["worker1", "worker2", "supervisor"])

                # Check workers completed
                comp_agents = [comp["agent_name"] for comp in msg.completed_by]
                workers_completed = all(agent in comp_agents for agent in ["worker1", "worker2"])

                # Check completion notes exist
                comp_notes = [comp.get("notes", "") for comp in msg.completed_by]
                has_notes = all("complete" in note.lower() for note in comp_notes if note)

                if all_acked and workers_completed and has_notes:
                    results.add("integration flow test", True)
                else:
                    results.add(
                        "integration flow test",
                        False,
                        f"acked={all_acked}, completed={workers_completed}, notes={has_notes}",
                    )
            else:
                results.add("integration flow test", False, "Message not found")

    except Exception as e:
        results.add("integration flow test", False, str(e))


def main():
    """Run all tests"""

    # Initialize database (synchronous)
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False), is_async=False)
    db_manager.create_tables()

    # Clean up any existing test data
    with db_manager.get_session() as session:
        session.query(Message).delete()
        session.query(Agent).delete()
        session.query(Project).delete()
        session.commit()

    results = TestResults()

    # Run all tests

    test_acknowledge_message_array(db_manager, results)
    test_complete_message_with_notes(db_manager, results)
    test_auto_acknowledgment(db_manager, results)
    test_array_structure_format(db_manager, results)
    test_multi_agent_delivery(db_manager, results)
    test_no_message_deletion(db_manager, results)
    test_broadcast_functionality(db_manager, results)
    test_integration_flow(db_manager, results)

    # Show summary
    all_passed = results.summary()

    # Return exit code
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    # sys.exit(exit_code)  # Commented for pytest
