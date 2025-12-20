"""
Tests for succession_tools.py with new identity model - TDD RED phase.

Handover 0366c Phase C: Tests for succession tools using agent_id (executor)
instead of job_id (work order).

These tests are EXPECTED TO FAIL initially because succession_tools.py
currently uses old parameter names (job_id instead of agent_id).

Test Coverage:
1. test_trigger_succession_uses_agent_id - Trigger succession using agent_id
2. test_succession_chain_validation - Validate spawned_by/succeeded_by chain
3. test_same_job_new_executor - Verify successor has SAME job_id, different agent_id
4. test_context_tracking_preserved - Ensure context tracking transfers correctly
5. test_multi_tenant_isolation - Verify tenant isolation during succession

Design Philosophy (Agent Identity Model):
- agent_id = executor UUID (the WHO - specific agent instance)
- job_id = work order UUID (the WHAT - persistent across succession)
- Succession creates NEW executor for SAME job
"""

import uuid

import pytest
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models import Product, Project


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def tenant_key():
    """Generate unique tenant key for test isolation."""
    return f"tenant-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def test_product(db_manager: DatabaseManager, tenant_key):
    """Create test product."""
    async with db_manager.get_session_async() as session:
        product = Product(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="Test Product",
            description="Product for succession testing",
            is_active=True,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


@pytest.fixture
async def test_project(db_manager: DatabaseManager, tenant_key, test_product):
    """Create test project."""
    async with db_manager.get_session_async() as session:
        project = Project(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            product_id=test_product.id,
            name="Test Project",
            description="Build authentication system",
            mission="Implement OAuth2 authentication",
            status="active",
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


@pytest.fixture
async def orchestrator_job_with_execution(
    db_manager: DatabaseManager, tenant_key, test_project
):
    """
    Create orchestrator job with execution at 90% context capacity.

    Returns tuple: (job, execution)
    """
    async with db_manager.get_session_async() as session:
        # Create persistent work order (job)
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=test_project.id,
            mission="Coordinate OAuth2 implementation across subagents",
            job_type="orchestrator",
            status="active",
            job_metadata={
                "field_priorities": {"vision_documents": 1, "architecture": 2},
                "depth_config": {"vision_documents": "light"},
            },
        )
        session.add(job)
        await session.flush()

        # Create executor instance (at 90% context capacity)
        execution = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="working",
            context_used=135000,  # 90% of 150K
            context_budget=150000,
            progress=75,
            current_task="Coordinating analyzer and implementer agents",
            spawned_by=None,  # Root orchestrator
            succeeded_by=None,  # Not yet succeeded
        )
        session.add(execution)
        await session.commit()
        await session.refresh(job)
        await session.refresh(execution)

        return job, execution


# ============================================================================
# Test Cases (TDD RED - These WILL FAIL Initially)
# ============================================================================


@pytest.mark.asyncio
async def test_trigger_succession_uses_agent_id(
    db_manager: DatabaseManager, tenant_key, orchestrator_job_with_execution
):
    """
    Test that trigger_succession identifies current executor by agent_id.

    Expected Behavior (NEW):
    - Tool uses agent_id parameter (not job_id)
    - Identifies current executor by agent_id
    - Creates successor with SAME job_id but different agent_id
    - Returns both current_agent_id and successor_agent_id

    WILL FAIL: succession_tools.py currently uses job_id parameter.
    """
    job, current_execution = orchestrator_job_with_execution

    # Import the tool (will fail because signature uses job_id)
    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    # Act: Trigger succession using agent_id (new signature)
    async with db_manager.get_session_async() as session:
        result = await _internal_trigger_succession(
            session=session,
            agent_id=current_execution.agent_id,  # NEW: agent_id instead of job_id
            tenant_key=tenant_key,
            reason="context_limit",
        )

    # Assert: Succession completed successfully
    assert result["success"] is True, "Succession should succeed"
    assert (
        "successor_agent_id" in result
    ), "Result should contain successor_agent_id (not successor_id)"
    assert (
        "current_agent_id" in result
    ), "Result should contain current_agent_id for clarity"
    assert (
        result["current_agent_id"] == current_execution.agent_id
    ), "Current agent_id should match input"
    assert (
        result["successor_agent_id"] != current_execution.agent_id
    ), "Successor should have different agent_id"
    assert (
        result["job_id"] == job.job_id
    ), "Work order (job_id) should remain the same"


@pytest.mark.asyncio
async def test_succession_chain_validation(
    db_manager: DatabaseManager, tenant_key, orchestrator_job_with_execution
):
    """
    Test that succession chain is correctly established.

    Validates:
    - current.succeeded_by == successor.agent_id
    - successor.spawned_by == current.agent_id
    - successor.job_id == current.job_id (SAME work order)
    - successor.instance_number == current.instance_number + 1

    WILL FAIL: Tool needs to use agent_id to identify current executor.
    """
    job, current_execution = orchestrator_job_with_execution

    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    # Trigger succession
    async with db_manager.get_session_async() as session:
        result = await _internal_trigger_succession(
            session=session,
            agent_id=current_execution.agent_id,  # NEW: Use agent_id
            tenant_key=tenant_key,
            reason="context_limit",
        )

    successor_agent_id = result["successor_agent_id"]

    # Validate succession chain in database
    async with db_manager.get_session_async() as session:
        # Fetch current execution
        current_result = await session.execute(
            select(AgentExecution).where(
                AgentExecution.agent_id == current_execution.agent_id
            )
        )
        current = current_result.scalar_one()

        # Fetch successor execution
        successor_result = await session.execute(
            select(AgentExecution).where(AgentExecution.agent_id == successor_agent_id)
        )
        successor = successor_result.scalar_one()

        # Assert: Chain correctly established
        assert (
            current.succeeded_by == successor.agent_id
        ), "Current executor should point to successor via succeeded_by"
        assert (
            successor.spawned_by == current.agent_id
        ), "Successor should point to current via spawned_by"
        assert (
            successor.job_id == current.job_id
        ), "Successor should work on SAME job (work order persists)"
        assert (
            successor.instance_number == current.instance_number + 1
        ), "Successor should increment instance number"


@pytest.mark.asyncio
async def test_same_job_new_executor(
    db_manager: DatabaseManager, tenant_key, orchestrator_job_with_execution
):
    """
    Test that succession creates new executor for SAME job.

    Semantic Contract:
    - job_id (work order) PERSISTS across succession
    - agent_id (executor) CHANGES on succession
    - Mission stored in job (not duplicated in execution)

    WILL FAIL: Need to query by agent_id to find current executor.
    """
    job, current_execution = orchestrator_job_with_execution

    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    # Trigger succession
    async with db_manager.get_session_async() as session:
        result = await _internal_trigger_succession(
            session=session,
            agent_id=current_execution.agent_id,  # Use agent_id
            tenant_key=tenant_key,
            reason="phase_transition",
        )

    # Validate: Job unchanged, execution created
    async with db_manager.get_session_async() as session:
        # Fetch job
        job_result = await session.execute(
            select(AgentJob).where(AgentJob.job_id == job.job_id)
        )
        job_after = job_result.scalar_one()

        # Fetch all executions for this job
        executions_result = await session.execute(
            select(AgentExecution)
            .where(AgentExecution.job_id == job.job_id)
            .order_by(AgentExecution.instance_number)
        )
        executions = executions_result.scalars().all()

        # Assert: Job unchanged
        assert job_after.mission == job.mission, "Job mission should not change"
        assert job_after.status == "active", "Job should remain active during succession"

        # Assert: Two executions exist for same job
        assert len(executions) == 2, "Should have 2 executions for same job"
        assert executions[0].agent_id == current_execution.agent_id, "First is original"
        assert (
            executions[1].agent_id == result["successor_agent_id"]
        ), "Second is successor"
        assert all(
            e.job_id == job.job_id for e in executions
        ), "All executions reference same job"


@pytest.mark.asyncio
async def test_context_tracking_preserved(
    db_manager: DatabaseManager, tenant_key, orchestrator_job_with_execution
):
    """
    Test that context tracking transfers correctly to successor.

    Validates:
    - Successor starts with context_used = 0 (fresh context)
    - Successor inherits context_budget from current
    - Handover summary contains context state

    WILL FAIL: Tool signature needs agent_id parameter.
    """
    job, current_execution = orchestrator_job_with_execution

    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    # Trigger succession
    async with db_manager.get_session_async() as session:
        result = await _internal_trigger_succession(
            session=session,
            agent_id=current_execution.agent_id,  # Use agent_id
            tenant_key=tenant_key,
            reason="context_limit",
        )

    # Validate context tracking
    async with db_manager.get_session_async() as session:
        successor_result = await session.execute(
            select(AgentExecution).where(
                AgentExecution.agent_id == result["successor_agent_id"]
            )
        )
        successor = successor_result.scalar_one()

        # Assert: Successor has fresh context
        assert (
            successor.context_used == 0
        ), "Successor should start with 0 context usage"
        assert (
            successor.context_budget == current_execution.context_budget
        ), "Successor should inherit context budget"

        # Assert: Handover summary exists
        assert (
            successor.handover_summary is not None
        ), "Successor should have handover summary"
        assert (
            "context_used" in successor.handover_summary
        ), "Handover should document context state"


@pytest.mark.asyncio
async def test_multi_tenant_isolation(
    db_manager: DatabaseManager, test_product, test_project
):
    """
    Test that succession respects multi-tenant isolation.

    Validates:
    - Cannot trigger succession for agent in different tenant
    - Successor created in same tenant as current
    - Queries filtered by tenant_key

    WILL FAIL: Need to use agent_id parameter with tenant filtering.
    """
    tenant_key_1 = f"tenant-1-{uuid.uuid4().hex[:8]}"
    tenant_key_2 = f"tenant-2-{uuid.uuid4().hex[:8]}"

    # Create job + execution in tenant 1
    async with db_manager.get_session_async() as session:
        job1 = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key_1,
            project_id=test_project.id,
            mission="Tenant 1 work",
            job_type="orchestrator",
            status="active",
        )
        session.add(job1)
        await session.flush()

        exec1 = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job1.job_id,
            tenant_key=tenant_key_1,
            agent_type="orchestrator",
            instance_number=1,
            status="working",
            context_used=135000,
            context_budget=150000,
        )
        session.add(exec1)
        await session.commit()

        agent_id_tenant_1 = exec1.agent_id

    # Attempt succession with wrong tenant_key
    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    with pytest.raises(ValueError, match="not found"):
        async with db_manager.get_session_async() as session:
            await _internal_trigger_succession(
                session=session,
                agent_id=agent_id_tenant_1,  # Tenant 1 agent
                tenant_key=tenant_key_2,  # Tenant 2 key (WRONG)
                reason="context_limit",
            )

    # Verify no succession occurred
    async with db_manager.get_session_async() as session:
        executions_result = await session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job1.job_id)
        )
        executions = executions_result.scalars().all()

        assert (
            len(executions) == 1
        ), "Should still have only 1 execution (succession blocked)"


@pytest.mark.asyncio
async def test_trigger_succession_tool_signature(
    db_manager: DatabaseManager, tenant_key, orchestrator_job_with_execution
):
    """
    Test that public MCP tool has correct signature.

    Expected signature:
    - trigger_succession(agent_id: str, reason: str, tenant_key: str)

    WILL FAIL: Tool currently named create_successor_orchestrator with job_id param.
    """
    job, current_execution = orchestrator_job_with_execution

    # Import public MCP tool (this import should succeed but signature is wrong)
    # Note: In Phase C, we'll rename create_successor_orchestrator → trigger_succession
    from src.giljo_mcp.tools import succession_tools

    # Check tool registration - NEW tool should exist
    # This test validates the tool exists with correct name
    assert hasattr(
        succession_tools, "register_succession_tools"
    ), "Module should have registration function"

    # TODO: Once tool is updated, validate signature includes agent_id parameter
    # For now, this test documents expected interface


# ============================================================================
# Additional Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_succession_for_completed_executor_fails(
    db_manager: DatabaseManager, tenant_key, test_project
):
    """
    Test that succession cannot be triggered for already-complete executor.

    WILL FAIL: Need agent_id parameter to check executor status.
    """
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=test_project.id,
            mission="Completed work",
            job_type="orchestrator",
            status="active",
        )
        session.add(job)
        await session.flush()

        completed_exec = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            instance_number=1,
            status="complete",  # Already complete
            context_used=100000,
            context_budget=150000,
        )
        session.add(completed_exec)
        await session.commit()

        agent_id = completed_exec.agent_id

    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    # Attempt succession on completed executor
    with pytest.raises(ValueError, match="already complete"):
        async with db_manager.get_session_async() as session:
            await _internal_trigger_succession(
                session=session,
                agent_id=agent_id,  # Use agent_id
                tenant_key=tenant_key,
                reason="manual",
            )


@pytest.mark.asyncio
async def test_succession_for_nonexistent_agent_fails(
    db_manager: DatabaseManager, tenant_key
):
    """
    Test that succession fails for non-existent agent_id.

    WILL FAIL: Tool needs to accept agent_id parameter.
    """
    from src.giljo_mcp.tools.succession_tools import _internal_trigger_succession

    fake_agent_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="not found"):
        async with db_manager.get_session_async() as session:
            await _internal_trigger_succession(
                session=session,
                agent_id=fake_agent_id,  # Non-existent
                tenant_key=tenant_key,
                reason="context_limit",
            )


@pytest.mark.asyncio
async def test_succession_manager_accepts_async_session(db_manager: DatabaseManager, tenant_key):
    """
    OrchestratorSuccessionManager should accept AsyncSession.
    
    Behavioral test verifying type hint fix from Session to AsyncSession.
    """
    from src.giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
    
    async with db_manager.get_session_async() as session:
        # Behavior: Should instantiate without type errors
        manager = OrchestratorSuccessionManager(
            db_session=session,  # This is AsyncSession
            tenant_key=tenant_key
        )
        
        assert manager is not None
        assert manager.tenant_key == tenant_key
        # Verify the session is properly stored
        assert manager.db_session is session
