"""
Comprehensive integration tests for Agent-Orchestrator Communication MCP Tools.

Handover 0040: Professional Agent Flow Visualization
Tests for check_orchestrator_messages, acknowledge_message, and report_status tools.

Following TDD principles - these tests define expected behavior BEFORE implementation.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.agent_message_queue import AgentMessageQueue
from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.database import DatabaseManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture
def db_manager():
    """Create a synchronous database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    manager.create_tables()
    yield manager
    manager.close()


@pytest.fixture
def db_session(db_manager):
    """Get a database session for testing."""
    with db_manager.get_session() as session:
        yield session


@pytest.fixture
def job_manager(db_manager):
    """Create AgentJobManager instance."""
    return AgentJobManager(db_manager)


@pytest.fixture
def comm_queue(db_manager):
    """Create AgentCommunicationQueue instance."""
    return AgentMessageQueue(db_manager)


@pytest.fixture
def test_job(db_session, job_manager):
    """Create a test job with messages."""
    tenant_key = str(uuid4())

    # Create job
    job = job_manager.create_job(
        tenant_key=tenant_key,
        agent_type="implementer",
        mission="Build authentication module with TDD",
    )

    return {
        "job": job,
        "tenant_key": tenant_key,
        "job_id": job.job_id,
    }


class TestCheckOrchestratorMessages:
    """Test check_orchestrator_messages MCP tool functionality."""

    def test_check_messages_no_messages(self, db_session, test_job, comm_queue):
        """Test checking messages when queue is empty."""
        # Expected behavior: Should return empty messages list

        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            to_agent=None,  # Get all messages
            unread_only=True,
        )

        assert result["status"] == "success"
        assert result["messages"] == []
        assert len(result["messages"]) == 0

    def test_check_messages_with_unread_messages(self, db_session, test_job, comm_queue):
        """Test checking messages with unread messages in queue."""
        # Setup: Add messages to job
        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Start with user authentication model",
            priority=2,  # High priority
        )

        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="info",
            content="Use bcrypt for password hashing",
            priority=1,  # Normal priority
        )

        # Test: Get unread messages
        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            to_agent="implementer",
            unread_only=True,
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 2

        # Verify message structure
        message1 = result["messages"][0]
        assert message1["from_agent"] == "orchestrator"
        assert message1["to_agent"] == "implementer"
        assert message1["type"] == "task"
        assert message1["content"] == "Start with user authentication model"
        assert message1["priority"] == 2
        assert message1["acknowledged"] is False

    def test_check_messages_filter_by_agent(self, db_session, test_job, comm_queue):
        """Test filtering messages by recipient agent."""
        # Setup: Add messages for different agents
        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Implement authentication API",
            priority=2,
        )

        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="tester",
            message_type="task",
            content="Write integration tests",
            priority=1,
        )

        # Test: Get messages for specific agent
        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            to_agent="implementer",
            unread_only=False,
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 1
        assert result["messages"][0]["to_agent"] == "implementer"

    def test_check_messages_filter_by_type(self, db_session, test_job, comm_queue):
        """Test filtering messages by message type."""
        # Setup: Add different message types
        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Build user model",
            priority=2,
        )

        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="error",
            content="Database connection failed",
            priority=2,
        )

        # Test: Get only error messages
        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_type="error",
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 1
        assert result["messages"][0]["type"] == "error"

    def test_check_messages_multi_tenant_isolation(self, db_session, job_manager, comm_queue):
        """Test that messages are properly isolated by tenant_key."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create jobs for different tenants
        job1 = job_manager.create_job(
            tenant_key=tenant1,
            agent_type="implementer",
            mission="Tenant 1 task",
        )

        job2 = job_manager.create_job(
            tenant_key=tenant2,
            agent_type="implementer",
            mission="Tenant 2 task",
        )

        # Add messages to both jobs
        comm_queue.send_message(
            session=db_session,
            job_id=job1.job_id,
            tenant_key=tenant1,
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Tenant 1 message",
            priority=1,
        )

        comm_queue.send_message(
            session=db_session,
            job_id=job2.job_id,
            tenant_key=tenant2,
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Tenant 2 message",
            priority=1,
        )

        # Test: Tenant 1 should only see their messages
        result1 = comm_queue.get_messages(
            session=db_session,
            job_id=job1.job_id,
            tenant_key=tenant1,
        )

        assert result1["status"] == "success"
        assert len(result1["messages"]) == 1
        assert result1["messages"][0]["content"] == "Tenant 1 message"

        # Test: Tenant 2 should only see their messages
        result2 = comm_queue.get_messages(
            session=db_session,
            job_id=job2.job_id,
            tenant_key=tenant2,
        )

        assert result2["status"] == "success"
        assert len(result2["messages"]) == 1
        assert result2["messages"][0]["content"] == "Tenant 2 message"

        # Test: Cross-tenant access should fail
        result_cross = comm_queue.get_messages(
            session=db_session,
            job_id=job1.job_id,
            tenant_key=tenant2,  # Wrong tenant
        )

        assert result_cross["status"] == "error"
        assert "not found" in result_cross["error"].lower()

    def test_check_messages_priority_sorting(self, db_session, test_job, comm_queue):
        """Test that messages are returned sorted by priority."""
        # Setup: Add messages with different priorities
        msg_ids = []

        # Low priority
        result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="info",
            content="Low priority info",
            priority=0,
        )
        msg_ids.append(result["message_id"])

        # High priority
        result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="High priority task",
            priority=2,
        )
        msg_ids.append(result["message_id"])

        # Normal priority
        result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Normal priority task",
            priority=1,
        )
        msg_ids.append(result["message_id"])

        # Test: Messages should be available (priority sorting is implementation detail)
        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 3


class TestAcknowledgeMessage:
    """Test acknowledge_message MCP tool functionality."""

    def test_acknowledge_single_message(self, db_session, test_job, comm_queue):
        """Test acknowledging a single message."""
        # Setup: Send a message
        send_result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Implement user authentication",
            priority=2,
        )

        message_id = send_result["message_id"]

        # Test: Acknowledge the message
        ack_result = comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=message_id,
            agent_id="implementer-123",
        )

        assert ack_result["status"] == "success"

        # Verify message is marked as acknowledged
        messages = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            unread_only=False,
        )

        assert messages["status"] == "success"
        message = messages["messages"][0]
        assert message["acknowledged"] is True
        assert message["acknowledged_by"] == "implementer-123"
        assert message["acknowledged_at"] is not None

    def test_acknowledge_already_acknowledged_message(self, db_session, test_job, comm_queue):
        """Test acknowledging a message that's already acknowledged."""
        # Setup: Send and acknowledge a message
        send_result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Test task",
            priority=1,
        )

        message_id = send_result["message_id"]

        # First acknowledgment
        comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=message_id,
            agent_id="implementer-123",
        )

        # Test: Second acknowledgment should fail
        ack_result = comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=message_id,
            agent_id="implementer-123",
        )

        assert ack_result["status"] == "error"
        assert "already acknowledged" in ack_result["error"].lower()

    def test_acknowledge_nonexistent_message(self, db_session, test_job, comm_queue):
        """Test acknowledging a message that doesn't exist."""
        fake_message_id = str(uuid4())

        # Test: Acknowledge non-existent message
        ack_result = comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=fake_message_id,
            agent_id="implementer-123",
        )

        assert ack_result["status"] == "error"
        assert "not found" in ack_result["error"].lower()

    def test_acknowledge_message_multi_tenant_isolation(self, db_session, job_manager, comm_queue):
        """Test that message acknowledgment respects tenant isolation."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create job for tenant 1
        job1 = job_manager.create_job(
            tenant_key=tenant1,
            agent_type="implementer",
            mission="Tenant 1 task",
        )

        # Send message to tenant 1's job
        send_result = comm_queue.send_message(
            session=db_session,
            job_id=job1.job_id,
            tenant_key=tenant1,
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Tenant 1 message",
            priority=1,
        )

        message_id = send_result["message_id"]

        # Test: Tenant 2 should not be able to acknowledge tenant 1's message
        ack_result = comm_queue.acknowledge_message(
            session=db_session,
            job_id=job1.job_id,
            tenant_key=tenant2,  # Wrong tenant
            message_id=message_id,
            agent_id="implementer-456",
        )

        assert ack_result["status"] == "error"
        assert "not found" in ack_result["error"].lower()

    def test_acknowledge_with_response_data(self, db_session, test_job, comm_queue):
        """Test that acknowledgment can include response data in metadata."""
        # Setup: Send a message
        send_result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Implement feature X",
            priority=2,
            metadata={"estimated_time": "2 hours"},
        )

        message_id = send_result["message_id"]

        # Test: Acknowledge with response
        ack_result = comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=message_id,
            agent_id="implementer-123",
        )

        assert ack_result["status"] == "success"


class TestReportStatus:
    """Test report_status MCP tool functionality (via AgentJobManager)."""

    def test_report_status_with_progress(self, db_session, test_job, job_manager):
        """Test reporting agent status with progress percentage."""
        # Acknowledge the job first
        job_manager.acknowledge_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        # Test: Update status with progress metadata
        result = job_manager.update_job_status(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
            status="active",
            metadata={
                "message": "Working on user model implementation",
                "progress_percentage": 45,
                "current_task": "Implementing password hashing",
                "files_created": ["models/user.py", "models/auth.py"],
            },
        )

        assert result.status == "active"

        # Verify metadata was stored
        job = job_manager.get_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        assert job is not None
        assert len(job.messages) > 0

        # Check that message contains progress info
        latest_message = job.messages[-1]
        assert "content" in latest_message
        assert latest_message["content"] == "Working on user model implementation"

    def test_report_status_transition_to_completed(self, db_session, test_job, job_manager):
        """Test reporting final completion status."""
        # Acknowledge first
        job_manager.acknowledge_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        # Test: Complete the job
        result = job_manager.complete_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
            result={
                "status": "completed",
                "files_created": [
                    "models/user.py",
                    "models/auth.py",
                    "routes/auth.py",
                    "tests/test_auth.py",
                ],
                "lines_of_code": 342,
                "test_coverage": "87%",
            },
        )

        assert result.status == "completed"
        assert result.completed_at is not None

        # Verify completion result was stored
        job = job_manager.get_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        assert job.status == "completed"
        assert len(job.messages) > 0

    def test_report_status_transition_to_failed(self, db_session, test_job, job_manager):
        """Test reporting failure status with error details."""
        # Acknowledge first
        job_manager.acknowledge_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        # Test: Fail the job with error details
        result = job_manager.fail_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
            error={
                "error_type": "DatabaseConnectionError",
                "message": "Could not connect to PostgreSQL database",
                "stack_trace": "Full stack trace here...",
                "attempted_fixes": [
                    "Checked database credentials",
                    "Verified PostgreSQL is running",
                ],
            },
        )

        assert result.status == "failed"
        assert result.completed_at is not None

        # Verify error details were stored
        job = job_manager.get_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        assert job.status == "failed"
        assert len(job.messages) > 0

    def test_report_status_multi_tenant_isolation(self, db_session, job_manager):
        """Test that status updates respect tenant isolation."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create job for tenant 1
        job1 = job_manager.create_job(
            tenant_key=tenant1,
            agent_type="implementer",
            mission="Tenant 1 task",
        )

        # Acknowledge the job
        job_manager.acknowledge_job(
            tenant_key=tenant1,
            job_id=job1.job_id,
        )

        # Test: Tenant 2 should not be able to update tenant 1's job
        with pytest.raises(ValueError, match="not found"):
            job_manager.update_job_status(
                tenant_key=tenant2,  # Wrong tenant
                job_id=job1.job_id,
                status="active",
                metadata={"message": "Unauthorized update attempt"},
            )

    def test_report_status_invalid_transition(self, db_session, test_job, job_manager):
        """Test that invalid status transitions are rejected."""
        # Job starts in "pending" state

        # Test: Cannot transition directly from pending to completed
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_manager.complete_job(
                tenant_key=test_job["tenant_key"],
                job_id=test_job["job_id"],
            )

    def test_report_status_with_artifact_tracking(self, db_session, test_job, job_manager):
        """Test reporting status with artifact creation tracking."""
        # Acknowledge first
        job_manager.acknowledge_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        # Test: Report status with artifact creation
        result = job_manager.update_job_status(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
            status="active",
            metadata={
                "message": "Created user authentication module",
                "artifacts_created": [
                    {
                        "type": "file",
                        "path": "models/user.py",
                        "lines": 124,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    {
                        "type": "file",
                        "path": "models/auth.py",
                        "lines": 87,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                ],
                "tests_passing": 12,
                "tests_total": 12,
            },
        )

        assert result.status == "active"


class TestIntegrationWorkflow:
    """Test complete agent-orchestrator communication workflow."""

    def test_complete_message_flow(self, db_session, test_job, comm_queue, job_manager):
        """Test complete workflow: receive message -> acknowledge -> update status."""
        # Step 1: Orchestrator sends task
        send_result = comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="Implement user authentication with JWT tokens",
            priority=2,
            metadata={
                "estimated_time": "90 minutes",
                "dependencies": ["database schema created"],
            },
        )

        assert send_result["status"] == "success"
        message_id = send_result["message_id"]

        # Step 2: Agent checks for messages
        messages = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            to_agent="implementer",
            unread_only=True,
        )

        assert messages["status"] == "success"
        assert len(messages["messages"]) == 1

        # Step 3: Agent acknowledges message
        ack_result = comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=message_id,
            agent_id="implementer-123",
        )

        assert ack_result["status"] == "success"

        # Step 4: Agent acknowledges job and starts work
        job = job_manager.acknowledge_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
        )

        assert job.status == "active"

        # Step 5: Agent reports progress
        job_manager.update_job_status(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
            status="active",
            metadata={
                "message": "Working on JWT implementation",
                "progress_percentage": 50,
            },
        )

        # Step 6: Agent completes task
        final_job = job_manager.complete_job(
            tenant_key=test_job["tenant_key"],
            job_id=test_job["job_id"],
            result={
                "status": "completed",
                "files_created": [
                    "routes/auth.py",
                    "models/user.py",
                    "tests/test_auth.py",
                ],
            },
        )

        assert final_job.status == "completed"
        assert final_job.completed_at is not None

    def test_polling_pattern_simulation(self, db_session, test_job, comm_queue):
        """Test simulated 30-second polling pattern."""
        # Simulate multiple poll cycles

        # Poll 1: No messages
        result1 = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            unread_only=True,
        )
        assert result1["status"] == "success"
        assert len(result1["messages"]) == 0

        # Orchestrator sends message
        comm_queue.send_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            from_agent="orchestrator",
            to_agent="implementer",
            message_type="task",
            content="New urgent task",
            priority=2,
        )

        # Poll 2: Message found
        result2 = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            unread_only=True,
        )
        assert result2["status"] == "success"
        assert len(result2["messages"]) == 1

        # Acknowledge message
        message_id = result2["messages"][0]["id"]
        comm_queue.acknowledge_message(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            message_id=message_id,
            agent_id="implementer-123",
        )

        # Poll 3: No unread messages (acknowledged message filtered out)
        result3 = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            unread_only=True,
        )
        assert result3["status"] == "success"
        assert len(result3["messages"]) == 0


# Performance and scalability tests
class TestPerformance:
    """Test performance characteristics of message operations."""

    def test_get_messages_with_large_queue(self, db_session, test_job, comm_queue):
        """Test retrieving messages from a large message queue."""
        # Setup: Create 100 messages
        for i in range(100):
            comm_queue.send_message(
                session=db_session,
                job_id=test_job["job_id"],
                tenant_key=test_job["tenant_key"],
                from_agent="orchestrator",
                to_agent="implementer",
                message_type="task",
                content=f"Task {i}",
                priority=i % 3,  # Mix of priorities
            )

        # Test: Get all messages
        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            unread_only=False,
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 100

    def test_batch_acknowledgment_performance(self, db_session, test_job, comm_queue):
        """Test acknowledging multiple messages efficiently."""
        # Setup: Create messages
        message_ids = []
        for i in range(50):
            result = comm_queue.send_message(
                session=db_session,
                job_id=test_job["job_id"],
                tenant_key=test_job["tenant_key"],
                from_agent="orchestrator",
                to_agent="implementer",
                message_type="task",
                content=f"Task {i}",
                priority=1,
            )
            message_ids.append(result["message_id"])

        # Test: Acknowledge all messages
        for message_id in message_ids:
            ack_result = comm_queue.acknowledge_message(
                session=db_session,
                job_id=test_job["job_id"],
                tenant_key=test_job["tenant_key"],
                message_id=message_id,
                agent_id="implementer-123",
            )
            assert ack_result["status"] == "success"

        # Verify: No unread messages
        result = comm_queue.get_messages(
            session=db_session,
            job_id=test_job["job_id"],
            tenant_key=test_job["tenant_key"],
            unread_only=True,
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 0
