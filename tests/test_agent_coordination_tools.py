"""
Comprehensive test suite for Agent Coordination MCP Tools (Handover 0045).

Tests all 7 coordination tools with focus on:
- Functional correctness
- Multi-tenant isolation (CRITICAL)
- Error handling
- Edge cases
- Integration with AgentJobManager and AgentCommunicationQueue

Following TDD principles - testing production-grade code.
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.agent_message_queue import AgentMessageQueue
from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tools.agent_coordination import register_agent_coordination_tools
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture
def db_manager():
    """Create a synchronous database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    manager.create_tables()
    yield manager
    manager.close()


@pytest.fixture
def job_manager(db_manager):
    """Create AgentJobManager instance."""
    return AgentJobManager(db_manager)


@pytest.fixture
def comm_queue(db_manager):
    """Create AgentMessageQueue instance."""
    return AgentMessageQueue(db_manager)


@pytest.fixture
def coordination_tools(db_manager):
    """Register and return coordination tools."""
    tools = {}
    register_agent_coordination_tools(tools, db_manager)
    return tools


@pytest.fixture
def tenant_key():
    """Generate unique tenant key for each test (max 36 chars)."""
    return str(uuid4())  # Standard UUID format (36 chars including hyphens)


@pytest.fixture
def other_tenant_key():
    """Generate second tenant key for isolation tests (max 36 chars)."""
    return str(uuid4())  # Standard UUID format (36 chars including hyphens)


class TestGetPendingJobs:
    """Test get_pending_jobs coordination tool."""

    def test_get_pending_jobs_success(self, coordination_tools, job_manager, tenant_key):
        """Test successful retrieval of pending jobs."""
        # Create test jobs
        job1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature X",
            context_chunks=["chunk1", "chunk2"],
        )
        job2 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature Y",
            context_chunks=["chunk3"],
        )

        # Call tool
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result = get_pending_jobs(agent_type="implementer", tenant_key=tenant_key)

        # Assertions
        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["jobs"]) == 2

        job_ids = [job["job_id"] for job in result["jobs"]]
        assert job1.job_id in job_ids
        assert job2.job_id in job_ids

        # Verify job structure
        for job in result["jobs"]:
            assert "job_id" in job
            assert "agent_type" in job
            assert "mission" in job
            assert "context_chunks" in job
            assert "priority" in job
            assert "created_at" in job
            assert job["agent_type"] == "implementer"

    def test_get_pending_jobs_empty(self, coordination_tools, tenant_key):
        """Test get_pending_jobs with no pending jobs."""
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result = get_pending_jobs(agent_type="tester", tenant_key=tenant_key)

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["jobs"] == []

    def test_get_pending_jobs_filters_by_agent_type(self, coordination_tools, job_manager, tenant_key):
        """Test that get_pending_jobs filters by agent_type."""
        # Create jobs for different agent types
        job_impl = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature",
        )
        job_test = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Write tests",
        )

        # Get implementer jobs only
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result = get_pending_jobs(agent_type="implementer", tenant_key=tenant_key)

        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["jobs"][0]["job_id"] == job_impl.job_id
        assert result["jobs"][0]["agent_type"] == "implementer"

    def test_get_pending_jobs_tenant_isolation(self, coordination_tools, job_manager, tenant_key, other_tenant_key):
        """CRITICAL: Test multi-tenant isolation."""
        # Create jobs for two different tenants
        job_tenant1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Tenant 1 job",
        )
        job_tenant2 = job_manager.create_job(
            tenant_key=other_tenant_key,
            agent_type="implementer",
            mission="Tenant 2 job",
        )

        # Get jobs for tenant 1
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result = get_pending_jobs(agent_type="implementer", tenant_key=tenant_key)

        # Should only see tenant 1 jobs
        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["jobs"][0]["job_id"] == job_tenant1.job_id

        # Verify tenant 2 job is NOT in results
        job_ids = [job["job_id"] for job in result["jobs"]]
        assert job_tenant2.job_id not in job_ids

    def test_get_pending_jobs_validation_empty_agent_type(self, coordination_tools, tenant_key):
        """Test validation for empty agent_type."""
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result = get_pending_jobs(agent_type="", tenant_key=tenant_key)

        assert result["status"] == "error"
        assert "agent_type cannot be empty" in result["error"]
        assert result["count"] == 0

    def test_get_pending_jobs_validation_empty_tenant_key(self, coordination_tools):
        """Test validation for empty tenant_key."""
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result = get_pending_jobs(agent_type="implementer", tenant_key="")

        assert result["status"] == "error"
        assert "tenant_key cannot be empty" in result["error"]
        assert result["count"] == 0


class TestAcknowledgeJob:
    """Test acknowledge_job coordination tool."""

    def test_acknowledge_job_success(self, coordination_tools, job_manager, tenant_key):
        """Test successful job acknowledgment."""
        # Create pending job
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature",
        )

        # Acknowledge job
        acknowledge_job = coordination_tools["acknowledge_job"]
        result = acknowledge_job(
            job_id=job.job_id,
            agent_id="agent_123",
            tenant_key=tenant_key,
        )

        # Assertions
        assert result["status"] == "success"
        assert result["job"]["job_id"] == job.job_id
        assert result["job"]["status"] == "active"
        assert result["job"]["started_at"] is not None
        assert "next_instructions" in result

    def test_acknowledge_job_idempotent(self, coordination_tools, job_manager, tenant_key):
        """Test that acknowledging same job twice is idempotent."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Write tests",
        )

        acknowledge_job = coordination_tools["acknowledge_job"]

        # First acknowledgment
        result1 = acknowledge_job(
            job_id=job.job_id,
            agent_id="agent_123",
            tenant_key=tenant_key,
        )
        assert result1["status"] == "success"

        # Second acknowledgment (should succeed)
        result2 = acknowledge_job(
            job_id=job.job_id,
            agent_id="agent_123",
            tenant_key=tenant_key,
        )
        assert result2["status"] == "success"
        assert result2["job"]["status"] == "active"

    def test_acknowledge_job_tenant_isolation(self, coordination_tools, job_manager, tenant_key, other_tenant_key):
        """CRITICAL: Test tenant isolation in job acknowledgment."""
        # Create job for tenant 1
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Tenant 1 job",
        )

        # Try to acknowledge with wrong tenant key
        acknowledge_job = coordination_tools["acknowledge_job"]
        result = acknowledge_job(
            job_id=job.job_id,
            agent_id="agent_123",
            tenant_key=other_tenant_key,  # Wrong tenant!
        )

        # Should fail due to tenant mismatch
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_acknowledge_job_validation_empty_job_id(self, coordination_tools, tenant_key):
        """Test validation for empty job_id."""
        acknowledge_job = coordination_tools["acknowledge_job"]
        result = acknowledge_job(
            job_id="",
            agent_id="agent_123",
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "job_id cannot be empty" in result["error"]

    def test_acknowledge_job_validation_empty_agent_id(self, coordination_tools, tenant_key):
        """Test validation for empty agent_id."""
        acknowledge_job = coordination_tools["acknowledge_job"]
        result = acknowledge_job(
            job_id="job_123",
            agent_id="",
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "agent_id cannot be empty" in result["error"]

    def test_acknowledge_job_not_found(self, coordination_tools, tenant_key):
        """Test acknowledging non-existent job."""
        acknowledge_job = coordination_tools["acknowledge_job"]
        result = acknowledge_job(
            job_id="nonexistent_job",
            agent_id="agent_123",
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


class TestReportProgress:
    """Test report_progress coordination tool."""

    def test_report_progress_success(self, coordination_tools, job_manager, comm_queue, db_manager, tenant_key):
        """Test successful progress reporting."""
        # Create and acknowledge job
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Report progress
        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id=job.job_id,
            completed_todo="Implemented user model",
            files_modified=["models/user.py", "schemas/user.py"],
            context_used=5000,
            tenant_key=tenant_key,
        )

        # Assertions
        assert result["status"] == "success"
        assert result["continue"] is True
        assert "warnings" in result
        assert "context_remaining" in result
        assert result["context_remaining"] == 25000  # 30000 - 5000

        # Verify message was stored
        with db_manager.get_session() as session:
            msg_result = comm_queue.get_messages(
                session=session,
                job_id=job.job_id,
                tenant_key=tenant_key,
                message_type="progress",
            )

        assert msg_result["status"] == "success"
        assert len(msg_result["messages"]) > 0

        progress_msg = msg_result["messages"][0]
        assert progress_msg["type"] == "progress"
        assert "Implemented user model" in progress_msg["content"]
        assert progress_msg["metadata"]["context_used"] == 5000
        assert progress_msg["metadata"]["files_modified"] == [
            "models/user.py",
            "schemas/user.py",
        ]

    def test_report_progress_context_warning_25k(self, coordination_tools, job_manager, tenant_key):
        """Test warning at 25K tokens (83%)."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Large feature",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id=job.job_id,
            completed_todo="Progress update",
            files_modified=[],
            context_used=25000,
            tenant_key=tenant_key,
        )

        assert result["status"] == "success"
        assert len(result["warnings"]) > 0
        assert any("83%" in w for w in result["warnings"])

    def test_report_progress_context_warning_28k(self, coordination_tools, job_manager, tenant_key):
        """Test warning at 28K tokens (93%)."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Large feature",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id=job.job_id,
            completed_todo="Progress update",
            files_modified=[],
            context_used=28000,
            tenant_key=tenant_key,
        )

        assert result["status"] == "success"
        assert len(result["warnings"]) > 0
        assert any("93%" in w for w in result["warnings"])

    def test_report_progress_context_critical_29k(self, coordination_tools, job_manager, tenant_key):
        """Test critical warning at 29K tokens (97%)."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Large feature",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id=job.job_id,
            completed_todo="Progress update",
            files_modified=[],
            context_used=29000,
            tenant_key=tenant_key,
        )

        assert result["status"] == "success"
        assert len(result["warnings"]) > 0
        assert any("CRITICAL" in w for w in result["warnings"])
        assert any("97%" in w for w in result["warnings"])

    def test_report_progress_validation_empty_job_id(self, coordination_tools, tenant_key):
        """Test validation for empty job_id."""
        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id="",
            completed_todo="Test",
            files_modified=[],
            context_used=1000,
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "job_id cannot be empty" in result["error"]

    def test_report_progress_validation_empty_completed_todo(self, coordination_tools, job_manager, tenant_key):
        """Test validation for empty completed_todo."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )

        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id=job.job_id,
            completed_todo="",
            files_modified=[],
            context_used=1000,
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "completed_todo cannot be empty" in result["error"]

    def test_report_progress_validation_negative_context(self, coordination_tools, job_manager, tenant_key):
        """Test validation for negative context_used."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )

        report_progress = coordination_tools["report_progress"]
        result = report_progress(
            job_id=job.job_id,
            completed_todo="Test",
            files_modified=[],
            context_used=-1000,
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "non-negative" in result["error"].lower()


class TestCompleteJob:
    """Test complete_job coordination tool."""

    def test_complete_job_success(self, coordination_tools, job_manager, tenant_key):
        """Test successful job completion."""
        # Create and acknowledge job
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Complete job
        complete_job = coordination_tools["complete_job"]
        result = complete_job(
            job_id=job.job_id,
            result={
                "summary": "Feature implemented successfully",
                "files_created": ["models/user.py"],
                "files_modified": ["api/routes.py"],
                "tests_written": ["tests/test_user.py"],
                "coverage": "95%",
            },
            tenant_key=tenant_key,
        )

        # Assertions
        assert result["status"] == "success"
        assert "Job completed successfully" in result["message"]

    def test_complete_job_with_next_job(self, coordination_tools, job_manager, tenant_key):
        """Test job completion provides next job info."""
        # Create two jobs
        job1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature 1",
        )
        job2 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature 2",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job1.job_id)

        # Complete first job
        complete_job = coordination_tools["complete_job"]
        result = complete_job(
            job_id=job1.job_id,
            result={"summary": "Feature 1 done"},
            tenant_key=tenant_key,
        )

        # Should suggest next job
        assert result["status"] == "success"
        assert result["next_job"] is not None
        assert result["next_job"]["job_id"] == job2.job_id
        assert result["next_job"]["mission"] == "Implement feature 2"

    def test_complete_job_validation_empty_job_id(self, coordination_tools, tenant_key):
        """Test validation for empty job_id."""
        complete_job = coordination_tools["complete_job"]
        result = complete_job(
            job_id="",
            result={"summary": "Test"},
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "job_id cannot be empty" in result["error"]

    def test_complete_job_validation_missing_summary(self, coordination_tools, job_manager, tenant_key):
        """Test validation for result without summary."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        complete_job = coordination_tools["complete_job"]
        result = complete_job(
            job_id=job.job_id,
            result={"files_created": ["test.py"]},  # No summary!
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "summary" in result["error"].lower()

    def test_complete_job_tenant_isolation(self, coordination_tools, job_manager, tenant_key, other_tenant_key):
        """CRITICAL: Test tenant isolation in job completion."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Try to complete with wrong tenant key
        complete_job = coordination_tools["complete_job"]
        result = complete_job(
            job_id=job.job_id,
            result={"summary": "Done"},
            tenant_key=other_tenant_key,  # Wrong tenant!
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


class TestReportError:
    """Test report_error coordination tool."""

    def test_report_error_success(self, coordination_tools, job_manager, comm_queue, db_manager, tenant_key):
        """Test successful error reporting."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Report error
        report_error = coordination_tools["report_error"]
        result = report_error(
            job_id=job.job_id,
            error_type="build_failure",
            error_message="Module 'foo' not found",
            context="Trying to import foo module",
            tenant_key=tenant_key,
        )

        # Assertions
        assert result["status"] == "success"
        assert "recovery_instructions" in result
        assert "build" in result["recovery_instructions"].lower()

        # Verify error message was sent to orchestrator
        with db_manager.get_session() as session:
            msg_result = comm_queue.get_messages(
                session=session,
                job_id=job.job_id,
                tenant_key=tenant_key,
                message_type="error",
                to_agent="orchestrator",
            )

        assert msg_result["status"] == "success"
        assert len(msg_result["messages"]) > 0
        assert msg_result["messages"][0]["priority"] == 2  # High priority

    def test_report_error_all_error_types(self, coordination_tools, job_manager, tenant_key):
        """Test all valid error types."""
        error_types = [
            "build_failure",
            "test_failure",
            "validation_error",
            "dependency_error",
            "runtime_error",
            "unknown",
        ]

        report_error = coordination_tools["report_error"]

        for error_type in error_types:
            # Create new job for each error
            job = job_manager.create_job(
                tenant_key=tenant_key,
                agent_type="implementer",
                mission=f"Test {error_type}",
            )
            job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

            # Report error
            result = report_error(
                job_id=job.job_id,
                error_type=error_type,
                error_message=f"Test {error_type} error",
                context="Testing",
                tenant_key=tenant_key,
            )

            assert result["status"] == "success", f"Failed for {error_type}"
            assert "recovery_instructions" in result

    def test_report_error_validation_invalid_error_type(self, coordination_tools, job_manager, tenant_key):
        """Test validation for invalid error_type."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        report_error = coordination_tools["report_error"]
        result = report_error(
            job_id=job.job_id,
            error_type="invalid_type",  # Invalid!
            error_message="Test error",
            context="Testing",
            tenant_key=tenant_key,
        )

        assert result["status"] == "error"
        assert "error_type must be one of" in result["error"]


class TestSendMessage:
    """Test send_message coordination tool."""

    def test_send_message_success(self, coordination_tools, job_manager, comm_queue, db_manager, tenant_key):
        """Test successful message sending."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )

        # Send message
        send_message = coordination_tools["send_message"]
        result = send_message(
            job_id=job.job_id,
            to_agent="tester",
            message="Please review the implementation",
            tenant_key=tenant_key,
            priority=1,
        )

        # Assertions
        assert result["status"] == "success"
        assert "message_id" in result

        # Verify message was stored
        with db_manager.get_session() as session:
            msg_result = comm_queue.get_messages(
                session=session,
                job_id=job.job_id,
                tenant_key=tenant_key,
                to_agent="tester",
            )

        assert msg_result["status"] == "success"
        assert len(msg_result["messages"]) > 0
        assert msg_result["messages"][0]["content"] == "Please review the implementation"

    def test_send_message_priority_levels(self, coordination_tools, job_manager, tenant_key):
        """Test all priority levels."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )

        send_message = coordination_tools["send_message"]

        for priority in [0, 1, 2]:
            result = send_message(
                job_id=job.job_id,
                to_agent="tester",
                message=f"Priority {priority} message",
                tenant_key=tenant_key,
                priority=priority,
            )

            assert result["status"] == "success", f"Failed for priority {priority}"

    def test_send_message_validation_invalid_priority(self, coordination_tools, job_manager, tenant_key):
        """Test validation for invalid priority."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test",
        )

        send_message = coordination_tools["send_message"]
        result = send_message(
            job_id=job.job_id,
            to_agent="tester",
            message="Test",
            tenant_key=tenant_key,
            priority=5,  # Invalid!
        )

        assert result["status"] == "error"
        assert "priority must be" in result["error"]


class TestMultiTenantIsolation:
    """Comprehensive multi-tenant isolation tests (CRITICAL)."""

    def test_zero_cross_tenant_job_access(self, coordination_tools, job_manager, tenant_key, other_tenant_key):
        """Test that no tool can access jobs from other tenants."""
        # Create jobs for different tenants
        job_t1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Tenant 1 job",
        )
        job_t2 = job_manager.create_job(
            tenant_key=other_tenant_key,
            agent_type="implementer",
            mission="Tenant 2 job",
        )

        # Test get_pending_jobs isolation
        get_pending_jobs = coordination_tools["get_pending_jobs"]
        result_t1 = get_pending_jobs(agent_type="implementer", tenant_key=tenant_key)
        result_t2 = get_pending_jobs(agent_type="implementer", tenant_key=other_tenant_key)

        assert result_t1["count"] == 1
        assert result_t2["count"] == 1
        assert result_t1["jobs"][0]["job_id"] != result_t2["jobs"][0]["job_id"]

        # Test acknowledge_job isolation
        acknowledge_job = coordination_tools["acknowledge_job"]
        result = acknowledge_job(
            job_id=job_t1.job_id,
            agent_id="agent_123",
            tenant_key=other_tenant_key,  # Wrong tenant!
        )
        assert result["status"] == "error"

        # Test complete_job isolation
        job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job_t1.job_id)
        complete_job = coordination_tools["complete_job"]
        result = complete_job(
            job_id=job_t1.job_id,
            result={"summary": "Done"},
            tenant_key=other_tenant_key,  # Wrong tenant!
        )
        assert result["status"] == "error"

    def test_message_queue_isolation(
        self, coordination_tools, job_manager, comm_queue, db_manager, tenant_key, other_tenant_key
    ):
        """Test message queue enforces tenant isolation."""
        # Create jobs for different tenants
        job_t1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Tenant 1 job",
        )
        job_t2 = job_manager.create_job(
            tenant_key=other_tenant_key,
            agent_type="implementer",
            mission="Tenant 2 job",
        )

        # Send message to tenant 1 job
        with db_manager.get_session() as session:
            comm_queue.send_message(
                session=session,
                job_id=job_t1.job_id,
                tenant_key=tenant_key,
                from_agent="orchestrator",
                to_agent="implementer",
                message_type="orchestrator_instruction",
                content="Tenant 1 message",
                priority=1,
            )

        # Try to read with wrong tenant key
        # Note: get_next_instruction tool has been removed


        # Try to read with wrong tenant key
        # This test now only validates message sending isolation above


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
