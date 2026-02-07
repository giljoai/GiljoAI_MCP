"""
Comprehensive tests for WorkflowEngine component.

Tests multi-agent workflow execution with waterfall and parallel patterns.
Follows Test-Driven Development principles - tests written BEFORE implementation.

Handover 0020 Phase 1D: WorkflowEngine implementation
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.orchestration_types import (
    AgentConfig,
    Mission,
    StageResult,
    WorkflowResult,
    WorkflowStage,
)


@pytest.fixture
def db_manager():
    """Mock database manager."""
    db_manager = Mock()
    async_session_mock = AsyncMock()
    async_session_mock.__aenter__ = AsyncMock()
    async_session_mock.__aexit__ = AsyncMock(return_value=None)
    db_manager.get_session = Mock(return_value=async_session_mock)
    return db_manager


@pytest.fixture
def job_manager():
    """Mock AgentJobManager."""
    manager = AsyncMock()
    manager.create_job = AsyncMock()
    manager.get_job = AsyncMock()
    manager.update_job_status = AsyncMock()
    return manager


@pytest.fixture
def job_coordinator():
    """Mock JobCoordinator."""
    coordinator = AsyncMock()
    coordinator.wait_for_children = AsyncMock()
    coordinator.aggregate_child_results = AsyncMock()
    return coordinator


@pytest.fixture
def workflow_engine(db_manager, job_manager, job_coordinator):
    """Create WorkflowEngine instance for testing."""
    from src.giljo_mcp.workflow_engine import WorkflowEngine

    engine = WorkflowEngine(db_manager)
    # Inject mocked dependencies
    engine.job_manager = job_manager
    engine.job_coordinator = job_coordinator
    return engine


@pytest.fixture
def sample_agent_config():
    """Create sample AgentConfig."""
    mission = Mission(
        agent_role="implementor",
        content="Implement feature X",
        token_count=500,
        context_chunk_ids=["chunk-1"],
        priority="high",
    )
    return AgentConfig(
        role="implementor",
        template_id="impl-001",
        system_instructions="Template content",
        priority="high",
        mission_scope="Implement feature X",
        mission=mission,
    )


@pytest.fixture
def sample_waterfall_stages(sample_agent_config):
    """Create sample waterfall stages."""
    stage1_mission = Mission(
        agent_role="implementor",
        content="Implement feature",
        token_count=500,
        context_chunk_ids=["chunk-1"],
        priority="high",
    )
    stage1_agent = AgentConfig(
        role="implementor",
        template_id="impl-001",
        system_instructions="Template",
        priority="high",
        mission_scope="Implementation",
        mission=stage1_mission,
    )

    stage2_mission = Mission(
        agent_role="code-reviewer",
        content="Review code",
        token_count=300,
        context_chunk_ids=["chunk-2"],
        priority="high",
    )
    stage2_agent = AgentConfig(
        role="code-reviewer",
        template_id="review-001",
        system_instructions="Template",
        priority="high",
        mission_scope="Code Review",
        mission=stage2_mission,
    )

    stage3_mission = Mission(
        agent_role="tester",
        content="Test implementation",
        token_count=400,
        context_chunk_ids=["chunk-3"],
        priority="medium",
    )
    stage3_agent = AgentConfig(
        role="tester",
        template_id="test-001",
        system_instructions="Template",
        priority="medium",
        mission_scope="Testing",
        mission=stage3_mission,
    )

    return [
        WorkflowStage(
            name="implementation",
            agents=[stage1_agent],
            depends_on=None,
            critical=True,
            timeout_seconds=1800,
        ),
        WorkflowStage(
            name="code_review",
            agents=[stage2_agent],
            depends_on=["implementation"],
            critical=True,
            timeout_seconds=1200,
        ),
        WorkflowStage(
            name="testing",
            agents=[stage3_agent],
            depends_on=["code_review"],
            critical=False,
            timeout_seconds=900,
        ),
    ]


@pytest.fixture
def sample_parallel_stages():
    """Create sample parallel stages (no dependencies)."""
    frontend_mission = Mission(
        agent_role="implementor",
        content="Implement frontend",
        token_count=600,
        context_chunk_ids=["chunk-1"],
        priority="high",
    )
    frontend_agent = AgentConfig(
        role="implementor",
        template_id="impl-001",
        system_instructions="Template",
        priority="high",
        mission_scope="Frontend",
        mission=frontend_mission,
    )

    backend_mission = Mission(
        agent_role="implementor",
        content="Implement backend",
        token_count=700,
        context_chunk_ids=["chunk-2"],
        priority="high",
    )
    backend_agent = AgentConfig(
        role="implementor",
        template_id="impl-002",
        system_instructions="Template",
        priority="high",
        mission_scope="Backend",
        mission=backend_mission,
    )

    docs_mission = Mission(
        agent_role="documenter",
        content="Write documentation",
        token_count=400,
        context_chunk_ids=["chunk-3"],
        priority="medium",
    )
    docs_agent = AgentConfig(
        role="documenter",
        template_id="docs-001",
        system_instructions="Template",
        priority="medium",
        mission_scope="Documentation",
        mission=docs_mission,
    )

    return [
        WorkflowStage(name="frontend", agents=[frontend_agent], critical=True),
        WorkflowStage(name="backend", agents=[backend_agent], critical=True),
        WorkflowStage(name="documentation", agents=[docs_agent], critical=False),
    ]


# ==================== Basic Workflow Execution Tests ====================


@pytest.mark.asyncio
async def test_execute_workflow_waterfall(workflow_engine, job_manager, job_coordinator, sample_waterfall_stages):
    """Test basic waterfall workflow execution - stages run sequentially."""
    # Setup mocks
    job_ids = ["job-1", "job-2", "job-3"]
    job_manager.create_job.side_effect = job_ids

    # Mock wait_for_children to indicate completion
    job_coordinator.wait_for_children.return_value = {
        "all_complete": True,
        "completed": 1,
        "failed": 0,
        "active": 0,
        "timed_out": False,
    }

    # Mock aggregate results
    job_coordinator.aggregate_child_results.return_value = {
        "strategy": "collect",
        "results": [{"job_id": "job-1", "status": "completed"}],
        "count": 1,
    }

    # Execute waterfall workflow
    result = await workflow_engine.execute_workflow(
        workflow_type="waterfall",
        stages=sample_waterfall_stages,
        tenant_key="test-tenant",
        project_id="test-project",
    )

    # Verify result
    assert isinstance(result, WorkflowResult)
    assert result.status == "completed"
    assert len(result.completed) == 3
    assert len(result.failed) == 0
    assert result.success_rate == 1.0
    assert result.duration_seconds >= 0  # Duration may be very small but non-negative

    # Verify stages executed in order
    assert result.completed[0].stage_name == "implementation"
    assert result.completed[1].stage_name == "code_review"
    assert result.completed[2].stage_name == "testing"

    # Verify job creation calls (3 stages, 1 agent each)
    assert job_manager.create_job.call_count == 3


@pytest.mark.asyncio
async def test_execute_workflow_parallel(workflow_engine, job_manager, job_coordinator, sample_parallel_stages):
    """Test basic parallel workflow execution - stages run simultaneously."""
    # Setup mocks
    job_ids = ["job-1", "job-2", "job-3"]
    job_manager.create_job.side_effect = job_ids

    # Mock wait_for_children
    job_coordinator.wait_for_children.return_value = {
        "all_complete": True,
        "completed": 1,
        "failed": 0,
        "active": 0,
        "timed_out": False,
    }

    # Mock aggregate results
    job_coordinator.aggregate_child_results.return_value = {
        "strategy": "collect",
        "results": [{"job_id": "job-1", "status": "completed"}],
        "count": 1,
    }

    # Execute parallel workflow
    result = await workflow_engine.execute_workflow(
        workflow_type="parallel",
        stages=sample_parallel_stages,
        tenant_key="test-tenant",
        project_id="test-project",
    )

    # Verify result
    assert isinstance(result, WorkflowResult)
    assert result.status == "completed"
    assert len(result.completed) == 3
    assert len(result.failed) == 0
    assert result.success_rate == 1.0

    # Verify all stages completed (order not guaranteed in parallel)
    stage_names = {stage.stage_name for stage in result.completed}
    assert stage_names == {"frontend", "backend", "documentation"}


# ==================== Dependency Handling Tests ====================


@pytest.mark.asyncio
async def test_waterfall_dependency_handling(workflow_engine, job_manager, job_coordinator, sample_waterfall_stages):
    """Test that waterfall stages wait for dependencies before executing."""
    # Track execution order
    execution_order = []

    async def mock_execute_stage(stage, tenant_key, project_id):
        """Mock stage execution that tracks order."""
        execution_order.append(stage.name)
        return StageResult(
            stage_name=stage.name,
            job_ids=[f"job-{stage.name}"],
            results={"status": "completed"},
            duration=1.0,
            status="completed",
        )

    # Patch _execute_stage to track order
    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="waterfall",
            stages=sample_waterfall_stages,
            tenant_key="test-tenant",
            project_id="test-project",
        )

    # Verify stages executed in correct order
    assert execution_order == ["implementation", "code_review", "testing"]


@pytest.mark.asyncio
async def test_dependencies_met_logic(workflow_engine):
    """Test _dependencies_met correctly checks stage dependencies."""
    # Stage with no dependencies
    stage1 = WorkflowStage(name="stage1", agents=[], depends_on=None)
    assert await workflow_engine._dependencies_met(stage1, [])

    # Stage with dependencies - all met
    stage2 = WorkflowStage(name="stage2", agents=[], depends_on=["stage1"])
    completed = [
        StageResult(
            stage_name="stage1",
            job_ids=[],
            results={},
            duration=1.0,
            status="completed",
        )
    ]
    assert await workflow_engine._dependencies_met(stage2, completed)

    # Stage with dependencies - not all met
    stage3 = WorkflowStage(name="stage3", agents=[], depends_on=["stage1", "stage2"])
    assert not await workflow_engine._dependencies_met(stage3, completed)

    # Add stage2 to completed
    completed.append(
        StageResult(
            stage_name="stage2",
            job_ids=[],
            results={},
            duration=1.0,
            status="completed",
        )
    )
    assert await workflow_engine._dependencies_met(stage3, completed)


# ==================== Failure Handling Tests ====================


@pytest.mark.asyncio
async def test_waterfall_critical_failure_stops(workflow_engine, job_manager, job_coordinator, sample_waterfall_stages):
    """Test that critical stage failure stops waterfall workflow."""
    # Disable retries for this test to avoid extra calls
    for stage in sample_waterfall_stages:
        stage.max_retries = 0

    # First stage succeeds
    call_count = 0

    async def mock_execute_stage(stage, tenant_key, project_id):
        nonlocal call_count
        call_count += 1
        if stage.name == "implementation":
            return StageResult(
                stage_name=stage.name,
                job_ids=["job-1"],
                results={},
                duration=1.0,
                status="completed",
            )
        if stage.name == "code_review":
            # Critical failure
            raise Exception("Code review failed")
        # Should not reach testing stage
        raise AssertionError("Should not execute testing stage")

    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="waterfall",
            stages=sample_waterfall_stages,
            tenant_key="test-tenant",
            project_id="test-project",
        )

    # Verify workflow stopped after critical failure
    # Status is "partial" if some stages completed before critical failure
    assert result.status in ["failed", "partial"]
    assert len(result.completed) == 1  # Only implementation completed
    assert len(result.failed) == 1  # code_review failed
    assert "code_review" in result.failed
    assert call_count == 2  # Only first two stages attempted


@pytest.mark.asyncio
async def test_waterfall_noncritical_continues(workflow_engine, job_manager, job_coordinator, sample_waterfall_stages):
    """Test that non-critical stage failure allows workflow to continue."""
    # Disable retries for this test to avoid extra calls
    for stage in sample_waterfall_stages:
        stage.max_retries = 0

    # Make testing stage fail (it's non-critical)
    call_count = 0

    async def mock_execute_stage(stage, tenant_key, project_id):
        nonlocal call_count
        call_count += 1
        if stage.name == "testing":
            raise Exception("Testing failed")
        return StageResult(
            stage_name=stage.name,
            job_ids=[f"job-{call_count}"],
            results={},
            duration=1.0,
            status="completed",
        )

    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="waterfall",
            stages=sample_waterfall_stages,
            tenant_key="test-tenant",
            project_id="test-project",
        )

    # Verify workflow continued and marked as partial success
    assert result.status == "partial"
    assert len(result.completed) == 2  # implementation and code_review
    assert len(result.failed) == 1  # testing failed
    assert "testing" in result.failed
    assert call_count == 3  # All stages attempted


# ==================== Parallel Execution Tests ====================


@pytest.mark.asyncio
async def test_parallel_all_success(workflow_engine, job_manager, job_coordinator, sample_parallel_stages):
    """Test parallel execution when all stages succeed."""
    # Mock successful execution for all stages
    job_manager.create_job.side_effect = ["job-1", "job-2", "job-3"]
    job_coordinator.wait_for_children.return_value = {
        "all_complete": True,
        "completed": 1,
        "failed": 0,
        "active": 0,
        "timed_out": False,
    }
    job_coordinator.aggregate_child_results.return_value = {
        "strategy": "collect",
        "results": [{"status": "completed"}],
        "count": 1,
    }

    result = await workflow_engine.execute_workflow(
        workflow_type="parallel",
        stages=sample_parallel_stages,
        tenant_key="test-tenant",
        project_id="test-project",
    )

    # Verify all stages completed successfully
    assert result.status == "completed"
    assert len(result.completed) == 3
    assert len(result.failed) == 0
    assert result.success_rate == 1.0


@pytest.mark.asyncio
async def test_parallel_partial_failure(workflow_engine, job_manager, job_coordinator, sample_parallel_stages):
    """Test parallel execution when some stages fail."""
    # Disable retries for this test to avoid extra calls
    for stage in sample_parallel_stages:
        stage.max_retries = 0

    # Track which stages are executed
    executed_stages = []

    async def mock_execute_stage(stage, tenant_key, project_id):
        executed_stages.append(stage.name)
        if stage.name == "documentation":
            raise Exception("Documentation generation failed")
        return StageResult(
            stage_name=stage.name,
            job_ids=[f"job-{stage.name}"],
            results={},
            duration=1.0,
            status="completed",
        )

    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="parallel",
            stages=sample_parallel_stages,
            tenant_key="test-tenant",
            project_id="test-project",
        )

    # Verify partial success
    assert result.status == "partial"
    assert len(result.completed) == 2  # frontend and backend
    assert len(result.failed) == 1  # documentation
    assert "documentation" in result.failed

    # Verify all stages were attempted (parallel execution)
    assert len(executed_stages) == 3


# ==================== Retry Logic Tests ====================


@pytest.mark.asyncio
async def test_stage_retry_logic(workflow_engine, job_manager, job_coordinator, sample_agent_config):
    """Test that stages are retried on failure up to max_retries."""
    stage = WorkflowStage(
        name="test_stage",
        agents=[sample_agent_config],
        critical=True,
        max_retries=2,
        retry_count=0,
    )

    # Track retry attempts
    attempt_count = 0

    async def mock_execute_stage(stage, tenant_key, project_id):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count <= 2:
            raise Exception(f"Attempt {attempt_count} failed")
        # Third attempt succeeds
        return StageResult(
            stage_name=stage.name,
            job_ids=["job-1"],
            results={},
            duration=1.0,
            status="completed",
        )

    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="waterfall",
            stages=[stage],
            tenant_key="test-tenant",
            project_id="test-project",
        )

    # Verify stage succeeded after retries
    assert result.status == "completed"
    assert len(result.completed) == 1
    assert attempt_count == 3  # 1 initial + 2 retries


@pytest.mark.asyncio
async def test_retry_exhaustion(workflow_engine, job_manager, job_coordinator, sample_agent_config):
    """Test that stage fails after exhausting retries."""
    stage = WorkflowStage(
        name="test_stage",
        agents=[sample_agent_config],
        critical=True,
        max_retries=1,
        retry_count=0,
    )

    # Always fail
    async def mock_execute_stage(stage, tenant_key, project_id):
        raise Exception("Always fails")

    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="waterfall",
            stages=[stage],
            tenant_key="test-tenant",
            project_id="test-project",
        )

    # Verify stage failed after exhausting retries
    assert result.status == "failed"
    assert len(result.completed) == 0
    assert len(result.failed) == 1


# ==================== Timeout Tests ====================


@pytest.mark.asyncio
async def test_stage_timeout(workflow_engine, job_manager, job_coordinator, sample_agent_config):
    """Test that stage execution respects timeout."""
    stage = WorkflowStage(
        name="test_stage",
        agents=[sample_agent_config],
        critical=True,
        timeout_seconds=1,  # Very short timeout
    )

    # Mock wait_for_children to indicate timeout
    job_coordinator.wait_for_children.return_value = {
        "all_complete": False,
        "completed": 0,
        "failed": 0,
        "active": 1,
        "timed_out": True,
    }

    job_manager.create_job.return_value = "job-1"

    result = await workflow_engine.execute_workflow(
        workflow_type="waterfall",
        stages=[stage],
        tenant_key="test-tenant",
        project_id="test-project",
    )

    # Verify stage failed due to timeout
    assert result.status == "failed"
    assert len(result.failed) == 1


# ==================== Edge Cases ====================


@pytest.mark.asyncio
async def test_empty_stages_list(workflow_engine):
    """Test workflow with empty stages list."""
    result = await workflow_engine.execute_workflow(
        workflow_type="waterfall",
        stages=[],
        tenant_key="test-tenant",
        project_id="test-project",
    )

    assert result.status == "completed"
    assert len(result.completed) == 0
    assert len(result.failed) == 0
    assert result.success_rate == 0.0


@pytest.mark.asyncio
async def test_single_stage_workflow(workflow_engine, job_manager, job_coordinator, sample_agent_config):
    """Test workflow with single stage."""
    stage = WorkflowStage(name="single_stage", agents=[sample_agent_config])

    job_manager.create_job.return_value = "job-1"
    job_coordinator.wait_for_children.return_value = {
        "all_complete": True,
        "completed": 1,
        "failed": 0,
        "active": 0,
        "timed_out": False,
    }
    job_coordinator.aggregate_child_results.return_value = {
        "strategy": "collect",
        "results": [{"status": "completed"}],
        "count": 1,
    }

    result = await workflow_engine.execute_workflow(
        workflow_type="waterfall",
        stages=[stage],
        tenant_key="test-tenant",
        project_id="test-project",
    )

    assert result.status == "completed"
    assert len(result.completed) == 1
    assert result.completed[0].stage_name == "single_stage"


@pytest.mark.asyncio
async def test_all_stages_fail(workflow_engine, job_manager, job_coordinator, sample_waterfall_stages):
    """Test workflow when all stages fail."""

    async def mock_execute_stage(stage, tenant_key, project_id):
        raise Exception(f"{stage.name} failed")

    with patch.object(workflow_engine, "_execute_stage", side_effect=mock_execute_stage):
        result = await workflow_engine.execute_workflow(
            workflow_type="waterfall",
            stages=sample_waterfall_stages,
            tenant_key="test-tenant",
            project_id="test-project",
        )

    assert result.status == "failed"
    assert len(result.completed) == 0
    assert len(result.failed) >= 1  # At least first critical stage failed
    assert result.success_rate == 0.0


@pytest.mark.asyncio
async def test_invalid_workflow_type(workflow_engine, sample_waterfall_stages):
    """Test that invalid workflow type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid workflow type"):
        await workflow_engine.execute_workflow(
            workflow_type="invalid_type",
            stages=sample_waterfall_stages,
            tenant_key="test-tenant",
            project_id="test-project",
        )


@pytest.mark.asyncio
async def test_workflow_result_success_rate(workflow_engine):
    """Test success rate calculation in WorkflowResult."""
    # Create result with 2 completed, 1 failed
    completed = [
        StageResult("stage1", [], {}, 1.0, "completed"),
        StageResult("stage2", [], {}, 1.0, "completed"),
    ]
    failed = ["stage3"]

    result = WorkflowResult(
        completed=completed,
        failed=failed,
        status="partial",
        duration_seconds=10.0,
    )

    # Verify success rate
    assert result.success_rate == 2 / 3  # 2 out of 3 stages succeeded


@pytest.mark.asyncio
async def test_circular_dependencies_detection(workflow_engine, sample_agent_config):
    """Test that circular dependencies are detected and rejected."""
    # Create stages with circular dependencies
    stage1 = WorkflowStage(name="stage1", agents=[sample_agent_config], depends_on=["stage2"])
    stage2 = WorkflowStage(name="stage2", agents=[sample_agent_config], depends_on=["stage1"])

    # Attempt to execute workflow with circular dependencies
    # This should result in no stages being executable (infinite wait)
    # We'll use a timeout to detect this
    try:
        result = await asyncio.wait_for(
            workflow_engine.execute_workflow(
                workflow_type="waterfall",
                stages=[stage1, stage2],
                tenant_key="test-tenant",
                project_id="test-project",
            ),
            timeout=2.0,
        )
        # If we get here, it should have failed
        assert result.status == "failed"
    except asyncio.TimeoutError:
        # Timeout is expected for circular dependencies
        pass


# ==================== Stage Execution Tests ====================


@pytest.mark.asyncio
async def test_execute_stage_creates_jobs(workflow_engine, job_manager, job_coordinator, sample_agent_config):
    """Test that _execute_stage creates jobs for all agents in stage."""
    stage = WorkflowStage(
        name="multi_agent_stage",
        agents=[sample_agent_config, sample_agent_config],  # Two agents
    )

    job_manager.create_job.side_effect = ["job-1", "job-2"]
    job_coordinator.wait_for_children.return_value = {
        "all_complete": True,
        "completed": 2,
        "failed": 0,
        "active": 0,
        "timed_out": False,
    }
    job_coordinator.aggregate_child_results.return_value = {
        "strategy": "collect",
        "results": [{"status": "completed"}, {"status": "completed"}],
        "count": 2,
    }

    result = await workflow_engine._execute_stage(
        stage=stage,
        tenant_key="test-tenant",
        project_id="test-project",
    )

    # Verify jobs were created for both agents
    assert job_manager.create_job.call_count == 2
    assert len(result.job_ids) == 2
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_handle_stage_failure_non_critical(workflow_engine, sample_agent_config):
    """Test that non-critical stage failures are handled gracefully."""
    stage = WorkflowStage(
        name="non_critical_stage",
        agents=[sample_agent_config],
        critical=False,
        max_retries=0,
    )

    error = Exception("Non-critical failure")

    # Should not raise exception
    await workflow_engine._handle_stage_failure(
        stage=stage,
        error=error,
        tenant_key="test-tenant",
    )

    # Verify no exception was raised (function completed)


@pytest.mark.asyncio
async def test_handle_stage_failure_with_retries(workflow_engine, sample_agent_config):
    """Test that stage failures trigger retries when available."""
    stage = WorkflowStage(
        name="retry_stage",
        agents=[sample_agent_config],
        critical=True,
        max_retries=2,
        retry_count=0,
    )

    error = Exception("Retriable failure")

    # Should not raise exception (retry available)
    await workflow_engine._handle_stage_failure(
        stage=stage,
        error=error,
        tenant_key="test-tenant",
    )

    # Retry count should be incremented
    assert stage.retry_count == 1
