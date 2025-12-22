"""
Comprehensive tests for JobCoordinator component.

Tests job spawning, coordination, dependency chains, aggregation, and multi-tenant isolation.
Follows Test-Driven Development principles - tests written BEFORE implementation.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


@pytest.fixture
def db_manager():
    """Mock database manager with proper async context manager."""
    db_manager = Mock()

    # Create proper async context manager mock
    async_session_mock = AsyncMock()
    async_session_mock.__aenter__ = AsyncMock()
    async_session_mock.__aexit__ = AsyncMock(return_value=None)
    async_session_mock.begin = AsyncMock()
    async_session_mock.commit = AsyncMock()
    async_session_mock.rollback = AsyncMock()
    async_session_mock.add = Mock()
    async_session_mock.execute = AsyncMock()
    async_session_mock.flush = AsyncMock()

    db_manager.get_session = Mock(return_value=async_session_mock)
    db_manager.get_session_async = Mock(return_value=async_session_mock)
    async_session_mock.__aenter__.return_value = async_session_mock

    return db_manager


@pytest.fixture
def job_manager():
    """Mock AgentJobManager."""
    manager = AsyncMock()
    manager.create_job_batch = AsyncMock()
    manager.get_job = AsyncMock()
    manager.update_job_status = AsyncMock()
    manager.get_jobs_by_spawner = AsyncMock()
    return manager


@pytest.fixture
def comm_queue():
    """Mock AgentCommunicationQueue."""
    queue = AsyncMock()
    queue.send_notification = AsyncMock()
    return queue


@pytest.fixture
def job_coordinator(db_manager, job_manager, comm_queue):
    """Create JobCoordinator instance for testing."""
    from src.giljo_mcp.job_coordinator import JobCoordinator

    return JobCoordinator(db_manager, job_manager, comm_queue)


@pytest.fixture
def sample_parent_job():
    """Create a sample parent job."""
    return AgentExecution(
        id=1,
        tenant_key="test-tenant-123",
        job_id="parent-job-001",
        agent_type="orchestrator",
        mission="Parent orchestrator mission",
        status="active",
        spawned_by=None,
        context_chunks=[],
        messages=[],
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_child_jobs():
    """Create sample child jobs."""
    base_time = datetime.now(timezone.utc)
    return [
        AgentExecution(
            id=2,
            tenant_key="test-tenant-123",
            job_id="child-job-001",
            agent_type="analyzer",
            mission="Analyze codebase",
            status="completed",
            spawned_by="parent-job-001",
            context_chunks=["chunk-1"],
            messages=[],
            started_at=base_time,
            completed_at=base_time + timedelta(seconds=30),
            created_at=base_time,
        ),
        AgentExecution(
            id=3,
            tenant_key="test-tenant-123",
            job_id="child-job-002",
            agent_type="implementer",
            mission="Implement feature",
            status="completed",
            spawned_by="parent-job-001",
            context_chunks=["chunk-2"],
            messages=[],
            started_at=base_time,
            completed_at=base_time + timedelta(seconds=45),
            created_at=base_time,
        ),
        AgentExecution(
            id=4,
            tenant_key="test-tenant-123",
            job_id="child-job-003",
            agent_type="tester",
            mission="Test implementation",
            status="active",
            spawned_by="parent-job-001",
            context_chunks=["chunk-3"],
            messages=[],
            started_at=base_time,
            completed_at=None,
            created_at=base_time,
        ),
    ]


class TestJobSpawning:
    """Test job spawning functionality."""

    @pytest.mark.asyncio
    async def test_spawn_child_jobs_success(self, job_coordinator, job_manager, sample_parent_job):
        """Test successful spawning of child jobs."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        child_specs = [
            {"agent_type": "analyzer", "mission": "Analyze codebase", "context_chunks": ["chunk-1"]},
            {"agent_type": "implementer", "mission": "Implement feature", "context_chunks": ["chunk-2"]},
        ]

        # Mock create_job_batch to return job IDs
        job_manager.create_job_batch.return_value = {"job_ids": ["child-001", "child-002"], "count": 2}

        result = await job_coordinator.spawn_child_jobs(
            tenant_key=tenant_key, parent_job_id=parent_job_id, child_specs=child_specs
        )

        # Verify job_manager.create_job_batch was called correctly
        job_manager.create_job_batch.assert_called_once()
        call_args = job_manager.create_job_batch.call_args[1]

        assert call_args["tenant_key"] == tenant_key
        assert len(call_args["jobs"]) == 2
        assert call_args["jobs"][0]["agent_type"] == "analyzer"
        assert call_args["jobs"][0]["spawned_by"] == parent_job_id
        assert call_args["jobs"][1]["agent_type"] == "implementer"
        assert call_args["jobs"][1]["spawned_by"] == parent_job_id

        # Verify result
        assert result["success"] is True
        assert result["job_ids"] == ["child-001", "child-002"]
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_spawn_child_jobs_with_notifications(self, job_coordinator, job_manager, comm_queue):
        """Test spawning child jobs with notification sending."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        child_specs = [{"agent_type": "analyzer", "mission": "Analyze codebase", "notify_on_complete": True}]

        job_manager.create_job_batch.return_value = {"job_ids": ["child-001"], "count": 1}

        result = await job_coordinator.spawn_child_jobs(
            tenant_key=tenant_key, parent_job_id=parent_job_id, child_specs=child_specs, send_notifications=True
        )

        assert result["success"] is True
        # Notification should be sent for spawned jobs
        comm_queue.send_notification.assert_called()

    @pytest.mark.asyncio
    async def test_spawn_child_jobs_invalid_parent(self, job_coordinator, job_manager):
        """Test spawning with invalid/non-existent parent job."""
        tenant_key = "test-tenant-123"
        parent_job_id = "nonexistent-job"

        child_specs = [{"agent_type": "analyzer", "mission": "Test"}]

        # Mock get_job to return None (job not found)
        job_manager.get_job.return_value = None

        with pytest.raises(ValueError, match="Parent job not found"):
            await job_coordinator.spawn_child_jobs(
                tenant_key=tenant_key, parent_job_id=parent_job_id, child_specs=child_specs, validate_parent=True
            )

    @pytest.mark.asyncio
    async def test_spawn_parallel_jobs(self, job_coordinator, job_manager):
        """Test spawning parallel jobs without dependencies."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        parallel_specs = [
            {"agent_type": "analyzer", "mission": "Analyze module A"},
            {"agent_type": "analyzer", "mission": "Analyze module B"},
            {"agent_type": "analyzer", "mission": "Analyze module C"},
        ]

        job_manager.create_job_batch.return_value = {
            "job_ids": ["parallel-001", "parallel-002", "parallel-003"],
            "count": 3,
        }

        result = await job_coordinator.spawn_parallel_jobs(
            tenant_key=tenant_key, parent_job_id=parent_job_id, job_specs=parallel_specs
        )

        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["job_ids"]) == 3

    @pytest.mark.asyncio
    async def test_spawn_child_jobs_empty_specs(self, job_coordinator):
        """Test spawning with empty child specs list."""
        result = await job_coordinator.spawn_child_jobs(
            tenant_key="test-tenant-123", parent_job_id="parent-001", child_specs=[]
        )

        assert result["success"] is True
        assert result["count"] == 0
        assert result["job_ids"] == []


class TestJobCoordination:
    """Test job coordination and waiting functionality."""

    @pytest.mark.asyncio
    async def test_wait_for_children_all_complete(self, job_coordinator, job_manager):
        """Test waiting for children when all complete successfully."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        # Create completed child jobs
        completed_jobs = [
            Mock(job_id="child-001", status="completed", agent_type="analyzer"),
            Mock(job_id="child-002", status="completed", agent_type="implementer"),
        ]

        job_manager.get_jobs_by_spawner.return_value = completed_jobs

        result = await job_coordinator.wait_for_children(
            tenant_key=tenant_key, parent_job_id=parent_job_id, timeout=30.0
        )

        assert result["all_complete"] is True
        assert result["completed"] == 2
        assert result["failed"] == 0
        assert result["active"] == 0

    @pytest.mark.asyncio
    async def test_wait_for_children_timeout(self, job_coordinator, job_manager):
        """Test waiting for children with timeout."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        # Jobs that never complete
        active_jobs = [Mock(job_id="child-001", status="active", agent_type="analyzer")]

        job_manager.get_jobs_by_spawner.return_value = active_jobs

        result = await job_coordinator.wait_for_children(
            tenant_key=tenant_key,
            parent_job_id=parent_job_id,
            timeout=0.1,  # Very short timeout
            poll_interval=0.05,
        )

        assert result["all_complete"] is False
        assert result["timed_out"] is True
        assert result["active"] == 1

    @pytest.mark.asyncio
    async def test_wait_for_children_mixed_states(self, job_coordinator, job_manager):
        """Test waiting for children with mixed completion states."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        mixed_jobs = [
            Mock(job_id="child-001", status="completed", agent_type="analyzer"),
            Mock(job_id="child-002", status="failed", agent_type="implementer"),
            Mock(job_id="child-003", status="active", agent_type="tester"),
        ]

        # First call returns mixed, second call has active job completed
        job_manager.get_jobs_by_spawner.side_effect = [
            mixed_jobs,
            [
                Mock(job_id="child-001", status="completed", agent_type="analyzer"),
                Mock(job_id="child-002", status="failed", agent_type="implementer"),
                Mock(job_id="child-003", status="completed", agent_type="tester"),
            ],
        ]

        result = await job_coordinator.wait_for_children(
            tenant_key=tenant_key, parent_job_id=parent_job_id, timeout=5.0, poll_interval=0.1
        )

        assert result["all_complete"] is True
        assert result["completed"] == 2
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_aggregate_child_results_collect(self, job_coordinator, job_manager, sample_child_jobs):
        """Test aggregating child results with 'collect' strategy."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        # Add results to messages
        for job in sample_child_jobs:
            job.messages = [{"type": "result", "data": {"output": f"Result from {job.job_id}"}}]

        job_manager.get_jobs_by_spawner.return_value = sample_child_jobs

        result = await job_coordinator.aggregate_child_results(
            tenant_key=tenant_key, parent_job_id=parent_job_id, strategy="collect"
        )

        assert result["strategy"] == "collect"
        assert len(result["results"]) == 3
        assert all("job_id" in r for r in result["results"])
        assert all("messages" in r for r in result["results"])

    @pytest.mark.asyncio
    async def test_aggregate_child_results_merge(self, job_coordinator, job_manager, sample_child_jobs):
        """Test aggregating child results with 'merge' strategy."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        # Add results to messages
        for job in sample_child_jobs:
            job.messages = [{"type": "result", "data": {"key": f"value_{job.job_id}"}}]

        job_manager.get_jobs_by_spawner.return_value = sample_child_jobs

        result = await job_coordinator.aggregate_child_results(
            tenant_key=tenant_key, parent_job_id=parent_job_id, strategy="merge"
        )

        assert result["strategy"] == "merge"
        assert "merged_data" in result
        # Merged data should contain all messages from all children
        assert len(result["merged_data"]) >= 3

    @pytest.mark.asyncio
    async def test_aggregate_child_results_no_children(self, job_coordinator, job_manager):
        """Test aggregating when no child jobs exist."""
        job_manager.get_jobs_by_spawner.return_value = []

        result = await job_coordinator.aggregate_child_results(
            tenant_key="test-tenant-123", parent_job_id="parent-job-001", strategy="collect"
        )

        assert result["results"] == []
        assert result["count"] == 0


class TestJobDependencies:
    """Test job dependency chain functionality."""

    @pytest.mark.asyncio
    async def test_create_job_chain(self, job_coordinator, job_manager):
        """Test creating a sequential job dependency chain."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        chain_specs = [
            {"agent_type": "analyzer", "mission": "Analyze first"},
            {"agent_type": "implementer", "mission": "Implement second"},
            {"agent_type": "tester", "mission": "Test third"},
        ]

        # Mock job creation to return job IDs sequentially
        created_job_ids = ["chain-001", "chain-002", "chain-003"]
        job_manager.create_job_batch.return_value = {"job_ids": created_job_ids, "count": 3}

        result = await job_coordinator.create_job_chain(
            tenant_key=tenant_key, parent_job_id=parent_job_id, chain_specs=chain_specs
        )

        assert result["success"] is True
        assert result["chain_length"] == 3
        assert result["job_ids"] == created_job_ids
        assert "chain_id" in result

    @pytest.mark.asyncio
    async def test_execute_next_in_chain(self, job_coordinator, job_manager):
        """Test executing the next job in a dependency chain."""
        tenant_key = "test-tenant-123"
        chain_id = "chain-abc-123"

        # Mock chain metadata stored in job messages
        current_job = Mock(
            job_id="chain-001",
            status="completed",
            messages=[
                {"type": "chain_metadata", "chain_id": chain_id, "next_job_id": "chain-002", "position": 1, "total": 3}
            ],
        )

        job_manager.get_job.return_value = current_job
        job_manager.update_job_status.return_value = True

        result = await job_coordinator.execute_next_in_chain(tenant_key=tenant_key, current_job_id="chain-001")

        assert result["success"] is True
        assert result["next_job_id"] == "chain-002"
        # Should have updated next job to active status
        job_manager.update_job_status.assert_called_with(tenant_key=tenant_key, job_id="chain-002", status="active")

    @pytest.mark.asyncio
    async def test_execute_next_in_chain_completion(self, job_coordinator, job_manager):
        """Test executing next in chain when chain is complete."""
        tenant_key = "test-tenant-123"

        # Last job in chain
        last_job = Mock(
            job_id="chain-003",
            status="completed",
            messages=[
                {
                    "type": "chain_metadata",
                    "chain_id": "chain-abc-123",
                    "next_job_id": None,  # No next job
                    "position": 3,
                    "total": 3,
                }
            ],
        )

        job_manager.get_job.return_value = last_job

        result = await job_coordinator.execute_next_in_chain(tenant_key=tenant_key, current_job_id="chain-003")

        assert result["success"] is True
        assert result["chain_complete"] is True
        assert result["next_job_id"] is None


class TestJobStatusAggregation:
    """Test job tree status and metrics aggregation."""

    @pytest.mark.asyncio
    async def test_get_job_tree_status(self, job_coordinator, job_manager, sample_parent_job, sample_child_jobs):
        """Test getting recursive job tree status."""
        tenant_key = "test-tenant-123"
        root_job_id = "parent-job-001"

        # Mock job retrieval - need to return different jobs based on job_id
        def get_job_side_effect(tenant_key, job_id):
            if job_id == "parent-job-001":
                return sample_parent_job
            for child in sample_child_jobs:
                if child.job_id == job_id:
                    return child
            return None

        job_manager.get_job.side_effect = get_job_side_effect

        # Mock spawner lookup - return children for parent, empty for children
        def get_jobs_by_spawner_side_effect(tenant_key, spawner_id):
            if spawner_id == "parent-job-001":
                return sample_child_jobs
            return []

        job_manager.get_jobs_by_spawner.side_effect = get_jobs_by_spawner_side_effect

        result = await job_coordinator.get_job_tree_status(tenant_key=tenant_key, root_job_id=root_job_id)

        assert result["root_job_id"] == root_job_id
        assert result["total_jobs"] == 4  # 1 parent + 3 children
        assert result["completed"] == 2
        assert result["active"] == 2  # parent + 1 child
        assert "tree_depth" in result

    @pytest.mark.asyncio
    async def test_get_job_tree_status_recursive(self, job_coordinator, job_manager):
        """Test getting job tree status with nested hierarchy."""
        tenant_key = "test-tenant-123"

        # Create multi-level hierarchy
        root_job = Mock(job_id="root-001", status="active", spawned_by=None)
        level1_jobs = [
            Mock(job_id="l1-001", status="completed", spawned_by="root-001"),
            Mock(job_id="l1-002", status="active", spawned_by="root-001"),
        ]
        level2_jobs = [Mock(job_id="l2-001", status="completed", spawned_by="l1-002")]

        def get_jobs_by_spawner_side_effect(tenant_key, spawner_id):
            if spawner_id == "root-001":
                return level1_jobs
            if spawner_id == "l1-002":
                return level2_jobs
            return []

        job_manager.get_job.return_value = root_job
        job_manager.get_jobs_by_spawner.side_effect = get_jobs_by_spawner_side_effect

        result = await job_coordinator.get_job_tree_status(tenant_key=tenant_key, root_job_id="root-001", max_depth=3)

        assert result["total_jobs"] == 4  # root + 2 level1 + 1 level2
        assert result["tree_depth"] >= 2

    @pytest.mark.asyncio
    async def test_get_coordination_metrics(self, job_coordinator, job_manager, sample_child_jobs):
        """Test calculating coordination metrics."""
        tenant_key = "test-tenant-123"
        parent_job_id = "parent-job-001"

        job_manager.get_jobs_by_spawner.return_value = sample_child_jobs

        result = await job_coordinator.get_coordination_metrics(tenant_key=tenant_key, parent_job_id=parent_job_id)

        assert result["total_children"] == 3
        assert result["completed"] == 2
        assert result["failed"] == 0
        assert result["active"] == 1
        assert "success_rate" in result
        assert "avg_completion_time" in result
        # Success rate: 2 completed / 2 finished = 1.0 (active not counted in finished)
        assert result["success_rate"] == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_get_coordination_metrics_no_children(self, job_coordinator, job_manager):
        """Test metrics calculation with no children."""
        job_manager.get_jobs_by_spawner.return_value = []

        result = await job_coordinator.get_coordination_metrics(
            tenant_key="test-tenant-123", parent_job_id="parent-job-001"
        )

        assert result["total_children"] == 0
        assert result["success_rate"] == 0.0
        assert result["avg_completion_time"] is None


class TestMultiTenantIsolation:
    """Test multi-tenant isolation for job coordination."""

    @pytest.mark.asyncio
    async def test_spawn_child_jobs_tenant_isolation(self, job_coordinator, job_manager):
        """Test that spawned jobs maintain tenant isolation."""
        tenant_key = "tenant-A"
        parent_job_id = "parent-001"

        child_specs = [{"agent_type": "analyzer", "mission": "Analyze"}]

        job_manager.create_job_batch.return_value = {"job_ids": ["child-001"], "count": 1}

        await job_coordinator.spawn_child_jobs(
            tenant_key=tenant_key, parent_job_id=parent_job_id, child_specs=child_specs
        )

        # Verify tenant_key is passed correctly
        call_args = job_manager.create_job_batch.call_args[1]
        assert call_args["tenant_key"] == tenant_key
        assert all(job["tenant_key"] == tenant_key for job in call_args["jobs"])

    @pytest.mark.asyncio
    async def test_wait_for_children_tenant_filter(self, job_coordinator, job_manager):
        """Test that waiting only gets children from same tenant."""
        tenant_key = "tenant-A"
        parent_job_id = "parent-001"

        job_manager.get_jobs_by_spawner.return_value = [Mock(job_id="child-001", status="completed")]

        await job_coordinator.wait_for_children(tenant_key=tenant_key, parent_job_id=parent_job_id, timeout=0.1)

        # Verify tenant_key is used in query
        job_manager.get_jobs_by_spawner.assert_called()
        call_args = job_manager.get_jobs_by_spawner.call_args[0]
        assert call_args[0] == tenant_key

    @pytest.mark.asyncio
    async def test_aggregate_results_tenant_isolation(self, job_coordinator, job_manager):
        """Test that aggregation only includes same-tenant jobs."""
        tenant_key = "tenant-A"
        parent_job_id = "parent-001"

        # Mock children all from same tenant
        job_manager.get_jobs_by_spawner.return_value = [
            Mock(job_id="child-001", tenant_key=tenant_key, status="completed", messages=[])
        ]

        await job_coordinator.aggregate_child_results(
            tenant_key=tenant_key, parent_job_id=parent_job_id, strategy="collect"
        )

        # Verify tenant_key passed to get_jobs_by_spawner
        call_args = job_manager.get_jobs_by_spawner.call_args[0]
        assert call_args[0] == tenant_key


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_spawn_with_malformed_specs(self, job_coordinator):
        """Test spawning with malformed job specifications."""
        with pytest.raises(ValueError, match="Invalid job specification"):
            await job_coordinator.spawn_child_jobs(
                tenant_key="test-tenant",
                parent_job_id="parent-001",
                child_specs=[
                    {"agent_type": "analyzer"}  # Missing mission
                ],
            )

    @pytest.mark.asyncio
    async def test_wait_for_children_negative_timeout(self, job_coordinator):
        """Test wait_for_children with negative timeout."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            await job_coordinator.wait_for_children(tenant_key="test-tenant", parent_job_id="parent-001", timeout=-1.0)

    @pytest.mark.asyncio
    async def test_aggregate_with_invalid_strategy(self, job_coordinator):
        """Test aggregation with invalid strategy."""
        with pytest.raises(ValueError, match="Invalid aggregation strategy"):
            await job_coordinator.aggregate_child_results(
                tenant_key="test-tenant", parent_job_id="parent-001", strategy="invalid_strategy"
            )

    @pytest.mark.asyncio
    async def test_job_tree_status_max_depth_exceeded(self, job_coordinator, job_manager):
        """Test job tree traversal with depth limit."""
        # Create deep hierarchy
        root_job = Mock(job_id="root", status="active")
        child_job = Mock(job_id="child", status="active", spawned_by="root")

        def get_job_side_effect(tenant_key, job_id):
            if job_id == "root":
                return root_job
            if job_id == "child":
                return child_job
            return None

        job_manager.get_job.side_effect = get_job_side_effect

        # Return child for root, nothing for child
        def get_jobs_by_spawner_side_effect(tenant_key, spawner_id):
            if spawner_id == "root":
                return [child_job]
            return []

        job_manager.get_jobs_by_spawner.side_effect = get_jobs_by_spawner_side_effect

        result = await job_coordinator.get_job_tree_status(
            tenant_key="test-tenant",
            root_job_id="root",
            max_depth=0,  # Limit depth to 0 - only root
        )

        assert result["total_jobs"] == 1  # Only root since max_depth=0
        assert result["tree_depth"] == 0
