"""
Comprehensive test suite for AgentJobManager.

Tests job creation, status management, retrieval, and multi-tenant isolation.
Following TDD principles - these tests are written BEFORE implementation.
"""

import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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


class TestAgentJobManagerCreation:
    """Test job creation operations."""

    def test_create_job_with_all_parameters(self, db_session, db_manager):
        """Test creating a job with all parameters specified."""
        tenant_key = str(uuid4())
        spawned_by = str(uuid4())
        context_chunks = ["chunk1", "chunk2", "chunk3"]

        manager = AgentJobManager(db_manager)

        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement feature X following TDD principles",
            spawned_by=spawned_by,
            context_chunks=context_chunks,
        )

        assert job is not None
        assert job.job_id is not None
        assert job.tenant_key == tenant_key
        assert job.agent_type == "implementer"
        assert job.mission == "Implement feature X following TDD principles"
        assert job.status == "pending"
        assert job.spawned_by == spawned_by
        assert job.context_chunks == context_chunks
        assert job.messages == []
        assert job.acknowledged is False
        assert job.started_at is None
        assert job.completed_at is None
        assert job.created_at is not None

    def test_create_job_with_job_metadata(self, db_session, db_manager):
        """Test creating a job with job_metadata parameter."""
        tenant_key = str(uuid4())
        job_metadata = {
            "field_priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "tech_stack": 1,
                "architecture": 2
            },
            "user_id": "user-123",
            "tool": "claude-code"
        }

        manager = AgentJobManager(db_manager)

        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="orchestrator",
            mission="Orchestrate project implementation",
            job_metadata=job_metadata,
        )

        assert job is not None
        assert job.job_id is not None
        assert job.job_metadata is not None
        assert job.job_metadata == job_metadata
        assert job.job_metadata["field_priorities"]["product_core"] == 1
        assert job.job_metadata["user_id"] == "user-123"
        assert job.job_metadata["tool"] == "claude-code"

    def test_create_job_without_job_metadata_defaults_to_empty_dict(self, db_session, db_manager):
        """Test creating a job without job_metadata defaults to empty dict."""
        tenant_key = str(uuid4())

        manager = AgentJobManager(db_manager)

        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission without metadata",
        )

        assert job is not None
        assert job.job_metadata is not None
        assert job.job_metadata == {}

    def test_create_job_metadata_persists_to_database(self, db_session, db_manager):
        """Test that job_metadata persists correctly to the database."""
        tenant_key = str(uuid4())
        job_metadata = {
            "field_priorities": {
                "vision_documents": 3,
                "git_history": 2
            },
            "custom_field": "custom_value"
        }

        manager = AgentJobManager(db_manager)

        # Create job with metadata
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Write integration tests",
            job_metadata=job_metadata,
        )

        # Retrieve the job from database
        retrieved_job = manager.get_job(tenant_key=tenant_key, job_id=job.job_id)

        # Verify metadata persisted correctly
        assert retrieved_job is not None
        assert retrieved_job.job_metadata == job_metadata
        assert retrieved_job.job_metadata["field_priorities"]["vision_documents"] == 3
        assert retrieved_job.job_metadata["custom_field"] == "custom_value"

    def test_create_job_with_minimal_parameters(self, db_session, db_manager):
        """Test creating a job with only required parameters."""
        tenant_key = str(uuid4())

        manager = AgentJobManager(db_manager)

        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="analyzer",
            mission="Analyze codebase structure",
        )

        assert job is not None
        assert job.job_id is not None
        assert job.tenant_key == tenant_key
        assert job.agent_type == "analyzer"
        assert job.mission == "Analyze codebase structure"
        assert job.status == "pending"
        assert job.spawned_by is None
        assert job.context_chunks == []
        assert job.messages == []
        assert job.acknowledged is False

    def test_create_job_batch(self, db_session, db_manager):
        """Test creating multiple jobs in batch."""
        tenant_key = str(uuid4())

        job_specs = [
            {
                "agent_type": "implementer",
                "mission": "Implement component A",
            },
            {
                "agent_type": "tester",
                "mission": "Write tests for component A",
            },
            {
                "agent_type": "implementer",
                "mission": "Implement component B",
            },
        ]

        manager = AgentJobManager(db_manager)

        jobs = manager.create_job_batch(tenant_key=tenant_key, job_specs=job_specs)

        assert len(jobs) == 3
        assert jobs[0].agent_type == "implementer"
        assert jobs[0].mission == "Implement component A"
        assert jobs[1].agent_type == "tester"
        assert jobs[1].mission == "Write tests for component A"
        assert jobs[2].agent_type == "implementer"
        assert jobs[2].mission == "Implement component B"

        # All should have same tenant_key
        for job in jobs:
            assert job.tenant_key == tenant_key
            assert job.status == "pending"

    def test_create_job_invalid_tenant_key(self, db_session, db_manager):
        """Test that invalid tenant_key raises ValueError."""
        manager = AgentJobManager(db_manager)

        with pytest.raises(ValueError, match="tenant_key cannot be empty"):
            manager.create_job(
                tenant_key="",
                agent_type="implementer",
                mission="Test mission",
            )

        with pytest.raises(ValueError, match="tenant_key cannot be empty"):
            manager.create_job(
                tenant_key=None,
                agent_type="implementer",
                mission="Test mission",
            )

    def test_create_job_invalid_agent_type(self, db_session, db_manager):
        """Test that invalid agent_type raises ValueError."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        with pytest.raises(ValueError, match="agent_type cannot be empty"):
            manager.create_job(
                tenant_key=tenant_key,
                agent_type="",
                mission="Test mission",
            )

        with pytest.raises(ValueError, match="agent_type cannot be empty"):
            manager.create_job(
                tenant_key=tenant_key,
                agent_type=None,
                mission="Test mission",
            )

    def test_create_job_invalid_mission(self, db_session, db_manager):
        """Test that invalid mission raises ValueError."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        with pytest.raises(ValueError, match="mission cannot be empty"):
            manager.create_job(
                tenant_key=tenant_key,
                agent_type="implementer",
                mission="",
            )

        with pytest.raises(ValueError, match="mission cannot be empty"):
            manager.create_job(
                tenant_key=tenant_key,
                agent_type="implementer",
                mission=None,
            )


class TestAgentJobManagerStatusManagement:
    """Test job status management operations."""

    def test_acknowledge_job_pending_to_active(self, db_session, db_manager):
        """Test acknowledging a pending job (pending -> active)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create pending job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )

        assert job.status == "pending"
        assert job.acknowledged is False
        assert job.started_at is None

        # Acknowledge job
        updated_job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        assert updated_job.status == "active"
        assert updated_job.acknowledged is True
        assert updated_job.started_at is not None

    def test_update_job_status_with_metadata(self, db_session, db_manager):
        """Test updating job status with metadata."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Add message metadata
        message = {
            "role": "agent",
            "content": "Working on implementation...",
            "timestamp": datetime.utcnow().isoformat(),
        }

        updated_job = manager.update_job_status(
            tenant_key=tenant_key,
            job_id=job.job_id,
            status="active",
            metadata={"message": message},
        )

        assert len(updated_job.messages) == 1
        assert updated_job.messages[0]["role"] == "agent"
        assert updated_job.messages[0]["content"] == "Working on implementation..."

    def test_complete_job_active_to_completed(self, db_session, db_manager):
        """Test completing an active job (active -> completed)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        assert job.status == "active"
        assert job.completed_at is None

        # Complete job
        result = {"status": "success", "output": "Implementation complete"}
        completed_job = manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result=result,
        )

        assert completed_job.status == "completed"
        assert completed_job.completed_at is not None
        # Result should be added as a message
        assert len(completed_job.messages) > 0

    def test_fail_job_active_to_failed(self, db_session, db_manager):
        """Test failing an active job (active -> failed)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Fail job
        error = {"error": "Database connection failed", "code": "DB_ERROR"}
        failed_job = manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error=error,
        )

        assert failed_job.status == "failed"
        assert failed_job.completed_at is not None
        # Error should be added as a message
        assert len(failed_job.messages) > 0

    def test_fail_job_pending_to_failed(self, db_session, db_manager):
        """Test failing a pending job (pending -> failed)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create pending job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )

        # Fail job directly from pending
        error = {"error": "Invalid configuration", "code": "CONFIG_ERROR"}
        failed_job = manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error=error,
        )

        assert failed_job.status == "failed"
        assert failed_job.completed_at is not None

    def test_invalid_status_transition_completed_to_active(self, db_session, db_manager):
        """Test that invalid status transitions are rejected (completed -> active)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create, acknowledge, and complete job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        job = manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"status": "success"},
        )

        # Try to update status to active (should fail)
        with pytest.raises(ValueError, match="Invalid status transition"):
            manager.update_job_status(
                tenant_key=tenant_key,
                job_id=job.job_id,
                status="active",
            )

    def test_invalid_status_transition_failed_to_active(self, db_session, db_manager):
        """Test that invalid status transitions are rejected (failed -> active)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create, acknowledge, and fail job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        job = manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error={"error": "Test error"},
        )

        # Try to update status to active (should fail)
        with pytest.raises(ValueError, match="Invalid status transition"):
            manager.update_job_status(
                tenant_key=tenant_key,
                job_id=job.job_id,
                status="active",
            )


class TestAgentJobManagerRetrieval:
    """Test job retrieval operations."""

    def test_get_job_by_job_id(self, db_session, db_manager):
        """Test retrieving a job by job_id."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )

        # Retrieve job
        retrieved_job = manager.get_job(tenant_key=tenant_key, job_id=job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.tenant_key == tenant_key
        assert retrieved_job.agent_type == "implementer"

    def test_get_job_not_found(self, db_session, db_manager):
        """Test retrieving non-existent job returns None."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        fake_job_id = str(uuid4())
        job = manager.get_job(tenant_key=tenant_key, job_id=fake_job_id)

        assert job is None

    def test_get_job_wrong_tenant(self, db_session, db_manager):
        """Test that jobs are isolated by tenant_key."""
        tenant_key1 = str(uuid4())
        tenant_key2 = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create job for tenant1
        job = manager.create_job(
            tenant_key=tenant_key1,
            agent_type="implementer",
            mission="Test mission",
        )

        # Try to retrieve with tenant2 (should fail)
        retrieved_job = manager.get_job(tenant_key=tenant_key2, job_id=job.job_id)

        assert retrieved_job is None

    def test_get_pending_jobs_no_filters(self, db_session, db_manager):
        """Test retrieving all pending jobs."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create multiple jobs
        job1 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Mission 1",
        )
        job2 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Mission 2",
        )
        # Acknowledge one
        manager.acknowledge_job(tenant_key=tenant_key, job_id=job1.job_id)

        # Get pending jobs (should only get job2)
        pending_jobs = manager.get_pending_jobs(tenant_key=tenant_key)

        assert len(pending_jobs) == 1
        assert pending_jobs[0].job_id == job2.job_id
        assert pending_jobs[0].status == "pending"

    def test_get_pending_jobs_with_agent_type_filter(self, db_session, db_manager):
        """Test retrieving pending jobs filtered by agent_type."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create multiple jobs
        manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Mission 1",
        )
        job2 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Mission 2",
        )
        manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Mission 3",
        )

        # Get pending jobs for tester only
        pending_jobs = manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_type="tester",
        )

        assert len(pending_jobs) == 1
        assert pending_jobs[0].job_id == job2.job_id
        assert pending_jobs[0].agent_type == "tester"

    def test_get_pending_jobs_with_limit(self, db_session, db_manager):
        """Test retrieving pending jobs with limit."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create multiple jobs
        for i in range(5):
            manager.create_job(
                tenant_key=tenant_key,
                agent_type="implementer",
                mission=f"Mission {i}",
            )

        # Get only 2 pending jobs
        pending_jobs = manager.get_pending_jobs(tenant_key=tenant_key, limit=2)

        assert len(pending_jobs) == 2

    def test_get_active_jobs_no_filters(self, db_session, db_manager):
        """Test retrieving all active jobs."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge multiple jobs
        job1 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Mission 1",
        )
        job2 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Mission 2",
        )
        manager.create_job(
            tenant_key=tenant_key,
            agent_type="analyzer",
            mission="Mission 3",
        )

        # Acknowledge two jobs
        manager.acknowledge_job(tenant_key=tenant_key, job_id=job1.job_id)
        manager.acknowledge_job(tenant_key=tenant_key, job_id=job2.job_id)

        # Get active jobs
        active_jobs = manager.get_active_jobs(tenant_key=tenant_key)

        assert len(active_jobs) == 2
        assert all(job.status == "active" for job in active_jobs)

    def test_get_active_jobs_with_agent_type_filter(self, db_session, db_manager):
        """Test retrieving active jobs filtered by agent_type."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge jobs
        job1 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Mission 1",
        )
        job2 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Mission 2",
        )

        manager.acknowledge_job(tenant_key=tenant_key, job_id=job1.job_id)
        manager.acknowledge_job(tenant_key=tenant_key, job_id=job2.job_id)

        # Get active implementer jobs only
        active_jobs = manager.get_active_jobs(
            tenant_key=tenant_key,
            agent_type="implementer",
        )

        assert len(active_jobs) == 1
        assert active_jobs[0].job_id == job1.job_id
        assert active_jobs[0].agent_type == "implementer"

    def test_get_job_hierarchy(self, db_session, db_manager):
        """Test retrieving job hierarchy (parent + children)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create parent job
        parent_job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="orchestrator",
            mission="Coordinate implementation",
        )

        # Create child jobs spawned by parent
        child1 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement component A",
            spawned_by=parent_job.job_id,
        )
        child2 = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Test component A",
            spawned_by=parent_job.job_id,
        )

        # Create unrelated job
        manager.create_job(
            tenant_key=tenant_key,
            agent_type="analyzer",
            mission="Analyze something else",
        )

        # Get hierarchy
        hierarchy = manager.get_job_hierarchy(
            tenant_key=tenant_key,
            job_id=parent_job.job_id,
        )

        assert hierarchy is not None
        assert "parent" in hierarchy
        assert "children" in hierarchy
        assert hierarchy["parent"].job_id == parent_job.job_id
        assert len(hierarchy["children"]) == 2

        child_ids = {child.job_id for child in hierarchy["children"]}
        assert child1.job_id in child_ids
        assert child2.job_id in child_ids


class TestAgentJobManagerTenantIsolation:
    """Test multi-tenant isolation."""

    def test_tenant_isolation_create_and_retrieve(self, db_session, db_manager):
        """Test that jobs are properly isolated by tenant."""
        tenant_key1 = str(uuid4())
        tenant_key2 = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create jobs for both tenants
        job1 = manager.create_job(
            tenant_key=tenant_key1,
            agent_type="implementer",
            mission="Tenant 1 mission",
        )
        job2 = manager.create_job(
            tenant_key=tenant_key2,
            agent_type="implementer",
            mission="Tenant 2 mission",
        )

        # Retrieve jobs for tenant 1
        tenant1_jobs = manager.get_pending_jobs(tenant_key=tenant_key1)
        assert len(tenant1_jobs) == 1
        assert tenant1_jobs[0].job_id == job1.job_id

        # Retrieve jobs for tenant 2
        tenant2_jobs = manager.get_pending_jobs(tenant_key=tenant_key2)
        assert len(tenant2_jobs) == 1
        assert tenant2_jobs[0].job_id == job2.job_id

    def test_tenant_isolation_status_updates(self, db_session, db_manager):
        """Test that status updates respect tenant isolation."""
        tenant_key1 = str(uuid4())
        tenant_key2 = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create job for tenant 1
        job1 = manager.create_job(
            tenant_key=tenant_key1,
            agent_type="implementer",
            mission="Tenant 1 mission",
        )

        # Try to acknowledge job1 with tenant2 credentials (should fail)
        with pytest.raises(ValueError, match="Job .* not found for tenant"):
            manager.acknowledge_job(tenant_key=tenant_key2, job_id=job1.job_id)

    def test_empty_results_for_tenant_with_no_jobs(self, db_session, db_manager):
        """Test that empty results are returned for tenants with no jobs."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # No jobs created for this tenant
        pending_jobs = manager.get_pending_jobs(tenant_key=tenant_key)
        active_jobs = manager.get_active_jobs(tenant_key=tenant_key)

        assert pending_jobs == []
        assert active_jobs == []


class TestAgentJobManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_completing_already_completed_job(self, db_session, db_manager):
        """Test completing a job that is already completed."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create, acknowledge, and complete job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        job = manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"status": "success"},
        )

        # Try to complete again (should raise error)
        with pytest.raises(ValueError, match="Invalid status transition"):
            manager.complete_job(
                tenant_key=tenant_key,
                job_id=job.job_id,
                result={"status": "success"},
            )

    def test_acknowledging_already_acknowledged_job(self, db_session, db_manager):
        """Test acknowledging a job that is already acknowledged."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Try to acknowledge again (should be idempotent)
        job2 = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Should return the job in active state
        assert job2.status == "active"
        assert job2.acknowledged is True

    def test_create_job_batch_empty_specs(self, db_session, db_manager):
        """Test creating job batch with empty specs."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        jobs = manager.create_job_batch(tenant_key=tenant_key, job_specs=[])

        assert jobs == []

    def test_get_job_hierarchy_for_job_with_no_children(self, db_session, db_manager):
        """Test getting hierarchy for a job with no children."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create job with no children
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )

        # Get hierarchy
        hierarchy = manager.get_job_hierarchy(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        assert hierarchy is not None
        assert hierarchy["parent"].job_id == job.job_id
        assert hierarchy["children"] == []

    def test_get_job_hierarchy_for_non_existent_job(self, db_session, db_manager):
        """Test getting hierarchy for non-existent job."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        fake_job_id = str(uuid4())
        hierarchy = manager.get_job_hierarchy(
            tenant_key=tenant_key,
            job_id=fake_job_id,
        )

        assert hierarchy is None

    def test_messages_accumulate_correctly(self, db_session, db_manager):
        """Test that messages accumulate in job."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Add multiple messages
        msg1 = {"role": "agent", "content": "Starting work"}
        msg2 = {"role": "agent", "content": "Still working"}
        msg3 = {"role": "agent", "content": "Almost done"}

        job = manager.update_job_status(
            tenant_key=tenant_key,
            job_id=job.job_id,
            status="active",
            metadata={"message": msg1},
        )
        job = manager.update_job_status(
            tenant_key=tenant_key,
            job_id=job.job_id,
            status="active",
            metadata={"message": msg2},
        )
        job = manager.update_job_status(
            tenant_key=tenant_key,
            job_id=job.job_id,
            status="active",
            metadata={"message": msg3},
        )

        assert len(job.messages) == 3
        assert job.messages[0]["content"] == "Starting work"
        assert job.messages[1]["content"] == "Still working"
        assert job.messages[2]["content"] == "Almost done"


class TestAgentJobDecommissioning:
    """Test decommissioning functionality for agent jobs (Handover 0113)."""

    def test_decommissioned_at_field_exists(self, db_session, db_manager):
        """Test that decommissioned_at field exists in MCPAgentJob model."""
        from src.giljo_mcp.models import MCPAgentJob

        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create a job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )

        # Verify decommissioned_at field exists and is NULL by default
        assert hasattr(job, 'decommissioned_at')
        assert job.decommissioned_at is None

    def test_decommissioned_at_is_nullable(self, db_session, db_manager):
        """Test that decommissioned_at field is nullable."""
        from src.giljo_mcp.models import MCPAgentJob
        from sqlalchemy import inspect

        # Get column metadata
        inspector = inspect(db_manager.engine)
        columns = {col['name']: col for col in inspector.get_columns('mcp_agent_jobs')}

        # Verify decommissioned_at is nullable
        assert 'decommissioned_at' in columns
        assert columns['decommissioned_at']['nullable'] is True

    def test_decommissioned_at_is_timezone_aware(self, db_session, db_manager):
        """Test that decommissioned_at field uses timezone-aware datetime."""
        from src.giljo_mcp.models import MCPAgentJob
        from sqlalchemy import inspect

        # Get column metadata
        inspector = inspect(db_manager.engine)
        columns = {col['name']: col for col in inspector.get_columns('mcp_agent_jobs')}

        # Verify decommissioned_at is timestamp with timezone
        assert 'decommissioned_at' in columns
        col_type = str(columns['decommissioned_at']['type']).lower()
        assert 'timestamp' in col_type or 'datetime' in col_type

    def test_decommission_job_from_complete_status(self, db_session, db_manager):
        """Test decommissioning a job that is in 'complete' status."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create, acknowledge, and complete job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        job = manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"status": "success"},
        )

        assert job.status == "completed"
        assert job.decommissioned_at is None

        # Decommission the job
        decommissioned_job = manager.decommission_job(
            tenant_key=tenant_key,
            job_id=job.job_id
        )

        # Verify decommissioning
        assert decommissioned_job.status == "decommissioned"
        assert decommissioned_job.decommissioned_at is not None
        assert isinstance(decommissioned_job.decommissioned_at, datetime)

    def test_decommission_job_invalid_from_pending(self, db_session, db_manager):
        """Test that decommissioning fails for non-complete jobs (pending)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create pending job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )

        # Try to decommission pending job (should fail)
        with pytest.raises(ValueError, match="Only completed jobs can be decommissioned"):
            manager.decommission_job(
                tenant_key=tenant_key,
                job_id=job.job_id
            )

    def test_decommission_job_invalid_from_active(self, db_session, db_manager):
        """Test that decommissioning fails for non-complete jobs (active)."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and acknowledge job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)

        # Try to decommission active job (should fail)
        with pytest.raises(ValueError, match="Only completed jobs can be decommissioned"):
            manager.decommission_job(
                tenant_key=tenant_key,
                job_id=job.job_id
            )

    def test_decommission_job_invalid_from_failed(self, db_session, db_manager):
        """Test that decommissioning fails for failed jobs."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create, acknowledge, and fail job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        job = manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error={"error": "Test failure"}
        )

        # Try to decommission failed job (should fail)
        with pytest.raises(ValueError, match="Only completed jobs can be decommissioned"):
            manager.decommission_job(
                tenant_key=tenant_key,
                job_id=job.job_id
            )

    def test_decommission_job_tenant_isolation(self, db_session, db_manager):
        """Test that decommissioning respects tenant isolation."""
        tenant_key1 = str(uuid4())
        tenant_key2 = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create and complete job for tenant1
        job = manager.create_job(
            tenant_key=tenant_key1,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key1, job_id=job.job_id)
        job = manager.complete_job(
            tenant_key=tenant_key1,
            job_id=job.job_id,
            result={"status": "success"}
        )

        # Try to decommission with tenant2 credentials (should fail)
        with pytest.raises(ValueError, match="Job .* not found for tenant"):
            manager.decommission_job(
                tenant_key=tenant_key2,
                job_id=job.job_id
            )

    def test_decommission_job_not_found(self, db_session, db_manager):
        """Test decommissioning a non-existent job."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        fake_job_id = str(uuid4())

        # Try to decommission non-existent job (should fail)
        with pytest.raises(ValueError, match="Job .* not found for tenant"):
            manager.decommission_job(
                tenant_key=tenant_key,
                job_id=fake_job_id
            )

    def test_decommission_job_idempotent(self, db_session, db_manager):
        """Test that decommissioning a job twice is idempotent."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create, acknowledge, and complete job
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
        )
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        job = manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"status": "success"}
        )

        # Decommission the job first time
        job1 = manager.decommission_job(
            tenant_key=tenant_key,
            job_id=job.job_id
        )
        first_decommission_time = job1.decommissioned_at

        # Decommission the same job again (should be idempotent)
        job2 = manager.decommission_job(
            tenant_key=tenant_key,
            job_id=job.job_id
        )

        # Verify idempotency (timestamp should be preserved)
        assert job2.status == "decommissioned"
        assert job2.decommissioned_at == first_decommission_time

    def test_project_closeout_workflow_decommissions_all_complete_agents(self, db_session, db_manager):
        """Test project closeout workflow sets decommissioned_at for all complete agents."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create multiple jobs (simulating a project)
        jobs = []
        for i in range(5):
            job = manager.create_job(
                tenant_key=tenant_key,
                agent_type="implementer",
                mission=f"Mission {i}",
            )
            job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
            job = manager.complete_job(
                tenant_key=tenant_key,
                job_id=job.job_id,
                result={"status": "success"}
            )
            jobs.append(job)

        # Decommission all jobs (simulating project closeout)
        decommissioned_jobs = []
        for job in jobs:
            decommissioned_job = manager.decommission_job(
                tenant_key=tenant_key,
                job_id=job.job_id
            )
            decommissioned_jobs.append(decommissioned_job)

        # Verify all jobs are decommissioned
        assert len(decommissioned_jobs) == 5
        for job in decommissioned_jobs:
            assert job.status == "decommissioned"
            assert job.decommissioned_at is not None


class TestAgentJobMetadataIntegration:
    """Test job_metadata integration with orchestrator workflow."""

    def test_orchestrator_job_with_field_priorities(self, db_session, db_manager):
        """Test creating orchestrator job with field priorities metadata."""
        tenant_key = str(uuid4())
        field_priorities = {
            "product_core": 1,
            "vision_documents": 2,
            "tech_stack": 1,
            "architecture": 2,
            "testing": 3,
            "360_memory": 2,
            "git_history": 2,
            "agent_templates": 3,
            "project_description": 1
        }

        manager = AgentJobManager(db_manager)

        # Create orchestrator job with field priorities
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="orchestrator",
            mission="Orchestrate project implementation with context prioritization",
            job_metadata={
                "field_priorities": field_priorities,
                "user_id": "user-123",
                "tool": "claude-code"
            }
        )

        # Verify metadata stored correctly
        assert job.job_metadata is not None
        assert "field_priorities" in job.job_metadata
        assert job.job_metadata["field_priorities"]["product_core"] == 1
        assert job.job_metadata["field_priorities"]["vision_documents"] == 2
        assert job.job_metadata["user_id"] == "user-123"
        assert job.job_metadata["tool"] == "claude-code"

    def test_job_metadata_survives_status_transitions(self, db_session, db_manager):
        """Test that job_metadata persists through status transitions."""
        tenant_key = str(uuid4())
        job_metadata = {
            "field_priorities": {"product_core": 1, "tech_stack": 2},
            "custom_field": "test_value"
        }

        manager = AgentJobManager(db_manager)

        # Create job with metadata
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Test mission",
            job_metadata=job_metadata
        )

        # Acknowledge job
        job = manager.acknowledge_job(tenant_key=tenant_key, job_id=job.job_id)
        assert job.job_metadata == job_metadata

        # Update status
        job = manager.update_job_status(
            tenant_key=tenant_key,
            job_id=job.job_id,
            status="active",
            metadata={"message": "Working on it"}
        )
        assert job.job_metadata == job_metadata

        # Complete job
        job = manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"status": "success"}
        )
        assert job.job_metadata == job_metadata

    def test_multiple_jobs_with_different_metadata(self, db_session, db_manager):
        """Test multiple jobs can have different metadata."""
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)

        # Create orchestrator job with field priorities
        orchestrator_job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="orchestrator",
            mission="Orchestrate",
            job_metadata={
                "field_priorities": {"product_core": 1, "vision_documents": 2},
                "tool": "claude-code"
            }
        )

        # Create implementer job with different metadata
        implementer_job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Implement",
            job_metadata={
                "assigned_component": "backend",
                "priority": "high"
            }
        )

        # Create tester job with no metadata
        tester_job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="tester",
            mission="Test"
        )

        # Verify each job has correct metadata
        assert orchestrator_job.job_metadata["field_priorities"]["product_core"] == 1
        assert orchestrator_job.job_metadata["tool"] == "claude-code"

        assert implementer_job.job_metadata["assigned_component"] == "backend"
        assert implementer_job.job_metadata["priority"] == "high"

        assert tester_job.job_metadata == {}
