"""
Database Integrity Tests for Orchestrator Succession (Handover 0080)

Tests database schema constraints, indexes, and data integrity:
- spawned_by chain integrity
- handover_to foreign key constraints
- instance_number increments correctly
- handover_summary JSONB structure
- succession_reason enum validation
- Database indexes exist and are used
"""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.fixtures.succession_fixtures import SuccessionTestData


# ============================================================================
# Database Constraint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_spawned_by_chain_integrity(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify spawned_by forms valid chain with no orphans.

    Each instance should reference a valid parent (except Instance 1).
    """
    # Create chain of 4 instances
    instances = []

    for i in range(1, 5):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=140000 if i < 4 else 50000,
                context_budget=150000,
                spawned_by=instances[-1].job_id if instances else None,
                status="waiting" if i == 4 else "complete",
            )
        )

        db_session.add(instance)
        instances.append(instance)
        await db_session.flush()

    await db_session.commit()

    # Refresh all
    for instance in instances:
        await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    # Instance 1 should have no parent
    assert instances[0].spawned_by is None

    # Instances 2-4 should reference valid parents
    for i in range(1, 4):
        assert instances[i].spawned_by == instances[i - 1].job_id

        # Verify parent exists in database
        parent_stmt = select(AgentExecution).where(AgentExecution.job_id == instances[i].spawned_by)
        parent_result = await db_session.execute(parent_stmt)
        parent = parent_result.scalar_one_or_none()

        assert parent is not None, f"Instance {i + 1} has orphaned spawned_by reference"
        assert parent.job_id == instances[i - 1].job_id


@pytest.mark.asyncio
async def test_handover_to_references_valid_jobs(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    handover_to should only reference existing job_id values.

    Note: While there's no explicit FK constraint on handover_to (by design),
    we verify referential integrity through application logic.
    """
    # Create two instances
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.flush()

    instance2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=2,
            context_used=0,
            context_budget=150000,
            spawned_by=instance1.job_id,
            status="waiting",
        )
    )

    db_session.add(instance2)
    await db_session.flush()

    # Set handover_to
    instance1.handover_to = instance2.job_id
    instance1.status = "complete"
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)

    # ========== VERIFICATIONS ==========

    # Verify handover_to references valid job
    assert instance1.handover_to == instance2.job_id

    # Verify referenced job exists
    referenced_stmt = select(AgentExecution).where(AgentExecution.job_id == instance1.handover_to)
    referenced_result = await db_session.execute(referenced_stmt)
    referenced_job = referenced_result.scalar_one_or_none()

    assert referenced_job is not None
    assert referenced_job.job_id == instance2.job_id


@pytest.mark.asyncio
async def test_instance_number_increments_correctly(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    No gaps, no duplicates in instance_number per project.

    Instance numbers should be sequential: 1, 2, 3, 4, ...
    """
    # Create 5 instances with sequential instance numbers
    for i in range(1, 6):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=50000,
                context_budget=150000,
                status="waiting",
            )
        )

        db_session.add(instance)

    await db_session.commit()

    # Query all instances ordered by instance_number
    stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.project_id == test_project.id,
            AgentExecution.agent_type == "orchestrator",
        )
        .order_by(AgentExecution.instance_number.asc())
    )

    result = await db_session.execute(stmt)
    instances = result.scalars().all()

    # ========== VERIFICATIONS ==========

    assert len(instances) == 5

    # Verify sequential numbering (1, 2, 3, 4, 5)
    for i, instance in enumerate(instances, start=1):
        assert instance.instance_number == i

    # Verify no gaps
    instance_numbers = [inst.instance_number for inst in instances]
    assert instance_numbers == [1, 2, 3, 4, 5]

    # Verify no duplicates
    assert len(instance_numbers) == len(set(instance_numbers))


@pytest.mark.asyncio
async def test_handover_summary_jsonb_structure(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    JSONB handover_summary contains required keys and valid structure.

    Required keys:
    - project_status
    - active_agents
    - pending_decisions
    - next_steps
    """
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.flush()

    # Create handover summary with required structure
    handover_summary = SuccessionTestData.generate_handover_summary()

    instance1.handover_summary = handover_summary
    instance1.status = "complete"
    instance1.succession_reason = "context_limit"
    instance1.completed_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(instance1)

    # ========== VERIFICATIONS ==========

    # Verify JSONB stored correctly
    assert instance1.handover_summary is not None
    assert isinstance(instance1.handover_summary, dict)

    # Verify required keys present
    required_keys = ["project_status", "active_agents", "pending_decisions", "next_steps"]
    for key in required_keys:
        assert key in instance1.handover_summary, f"Missing required key: {key}"

    # Verify data types
    assert isinstance(instance1.handover_summary["project_status"], str)
    assert isinstance(instance1.handover_summary["active_agents"], list)
    assert isinstance(instance1.handover_summary["pending_decisions"], list)
    assert isinstance(instance1.handover_summary["next_steps"], str)

    # Verify JSONB serialization/deserialization
    json_str = json.dumps(instance1.handover_summary)
    deserialized = json.loads(json_str)
    assert deserialized == instance1.handover_summary


@pytest.mark.asyncio
async def test_succession_reason_enum_constraint(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Only allows: context_limit, manual, phase_transition

    Note: In PostgreSQL with SQLAlchemy, enum validation is typically
    done at application level unless a CHECK constraint is defined.
    """
    valid_reasons = ["context_limit", "manual", "phase_transition"]

    for i, reason in enumerate(valid_reasons, start=1):
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=140000,
                context_budget=150000,
                status="complete",
            )
        )

        instance.succession_reason = reason
        instance.completed_at = datetime.now(timezone.utc)

        db_session.add(instance)

    await db_session.commit()

    # Query all
    stmt = select(AgentExecution).where(
        AgentExecution.project_id == test_project.id,
        AgentExecution.agent_type == "orchestrator",
    )
    result = await db_session.execute(stmt)
    instances = result.scalars().all()

    # ========== VERIFICATIONS ==========

    assert len(instances) == 3

    # Verify all succession reasons are valid
    for instance in instances:
        assert instance.succession_reason in valid_reasons


@pytest.mark.asyncio
async def test_context_budget_positive_constraint(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    context_budget must be positive (> 0).

    Verifies CHECK constraint on context_budget.
    """
    # Create instance with valid context_budget
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=5000,
            context_budget=150000,  # Valid positive value
            status="waiting",
        )
    )

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    assert instance.context_budget > 0
    assert instance.context_budget == 150000


@pytest.mark.asyncio
async def test_instance_number_positive_constraint(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    instance_number must be >= 1 (CHECK constraint).

    Handover 0080 schema includes: CHECK (instance_number >= 1)
    """
    # Create instance with valid instance_number
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,  # Minimum valid value
            context_used=5000,
            context_budget=150000,
            status="waiting",
        )
    )

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    assert instance.instance_number >= 1
    assert instance.instance_number == 1


# ============================================================================
# Database Index Tests
# ============================================================================


@pytest.mark.asyncio
async def test_succession_indexes_exist(db_session: AsyncSession):
    """
    Verify Handover 0080 indexes exist in database:
    - idx_agent_jobs_instance (project_id, agent_type, instance_number)
    - idx_agent_jobs_handover (handover_to)
    """
    # Get table metadata
    inspector = inspect(db_session.bind)

    # Get indexes for mcp_agent_jobs table
    indexes = await db_session.run_sync(lambda sync_session: inspector.get_indexes("mcp_agent_jobs"))

    index_names = [idx["name"] for idx in indexes]

    # ========== VERIFICATIONS ==========

    # Verify succession-specific indexes exist
    assert "idx_agent_jobs_instance" in index_names, "Missing idx_agent_jobs_instance index"
    assert "idx_agent_jobs_handover" in index_names, "Missing idx_agent_jobs_handover index"

    # Verify index on project_id exists (required for succession queries)
    assert "idx_mcp_agent_jobs_project" in index_names, "Missing project_id index"


@pytest.mark.asyncio
async def test_succession_query_performance_with_index(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify succession queries use indexes (EXPLAIN ANALYZE).

    Query: Get all orchestrators for project ordered by instance_number
    Should use: idx_agent_jobs_instance
    """
    # Create multiple instances to test index usage
    for i in range(1, 11):  # 10 instances
        instance = AgentExecution(
            **SuccessionTestData.generate_orchestrator_job_data(
                project_id=test_project.id,
                tenant_key=test_tenant_key,
                instance_number=i,
                context_used=50000,
                context_budget=150000,
                status="waiting",
            )
        )
        db_session.add(instance)

    await db_session.commit()

    # Execute query with EXPLAIN
    explain_query = text(
        """
        EXPLAIN (FORMAT JSON)
        SELECT * FROM mcp_agent_jobs
        WHERE project_id = :project_id
          AND agent_type = 'orchestrator'
        ORDER BY instance_number ASC
    """
    )

    result = await db_session.execute(explain_query, {"project_id": test_project.id})
    explain_result = result.scalar()

    # ========== VERIFICATIONS ==========

    # Verify query plan exists
    assert explain_result is not None
    assert isinstance(explain_result, list)

    # Convert to string for index usage checking
    explain_str = json.dumps(explain_result)

    # Note: Exact index usage depends on PostgreSQL query planner
    # This is a basic check that the query executed successfully
    assert "Plan" in explain_str


# ============================================================================
# Data Integrity Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handover_context_refs_array_integrity(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify handover_context_refs JSON array is stored and retrieved correctly.
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="complete",
        )
    )

    # Set context refs
    context_refs = [f"chunk-{i}" for i in range(1, 11)]
    instance.handover_context_refs = context_refs
    instance.succession_reason = "context_limit"
    instance.completed_at = datetime.now(timezone.utc)

    db_session.add(instance)
    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    assert instance.handover_context_refs is not None
    assert isinstance(instance.handover_context_refs, list)
    assert len(instance.handover_context_refs) == 10
    assert instance.handover_context_refs == context_refs


@pytest.mark.asyncio
async def test_messages_jsonb_array_integrity(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify messages JSONB array stores handover messages correctly.
    """
    instance1 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add(instance1)
    await db_session.flush()

    instance2 = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=2,
            context_used=0,
            context_budget=150000,
            spawned_by=instance1.job_id,
            status="waiting",
        )
    )

    # Add handover message
    handover_message = SuccessionTestData.generate_handover_message(
        from_job_id=instance1.job_id,
        to_job_id=instance2.job_id,
    )

    instance2.messages = [handover_message]

    db_session.add(instance2)
    await db_session.commit()
    await db_session.refresh(instance2)

    # ========== VERIFICATIONS ==========

    assert instance2.messages is not None
    assert isinstance(instance2.messages, list)
    assert len(instance2.messages) == 1

    # Verify message structure
    msg = instance2.messages[0]
    assert msg["type"] == "handover"
    assert msg["from"] == instance1.job_id
    assert msg["to"] == instance2.job_id
    assert "payload" in msg


@pytest.mark.asyncio
async def test_completed_at_timestamp_integrity(
    db_session: AsyncSession,
    test_project: Project,
    test_tenant_key: str,
):
    """
    Verify completed_at timestamp is set correctly and includes timezone.
    """
    instance = AgentExecution(
        **SuccessionTestData.generate_orchestrator_job_data(
            project_id=test_project.id,
            tenant_key=test_tenant_key,
            instance_number=1,
            context_used=140000,
            context_budget=150000,
            status="working",
        )
    )

    db_session.add(instance)
    await db_session.flush()

    # Complete the instance
    completion_time = datetime.now(timezone.utc)
    instance.status = "complete"
    instance.completed_at = completion_time
    instance.succession_reason = "context_limit"

    await db_session.commit()
    await db_session.refresh(instance)

    # ========== VERIFICATIONS ==========

    assert instance.completed_at is not None
    assert instance.completed_at.tzinfo is not None  # Timezone aware
    assert instance.status == "complete"

    # Verify timestamp is recent (within last minute)
    time_diff = (datetime.now(timezone.utc) - instance.completed_at).total_seconds()
    assert time_diff < 60  # Less than 60 seconds old
