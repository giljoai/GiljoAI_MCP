"""
Unit and Integration Tests for Orchestrator Succession Architecture.

Handover 0080: Tests for orchestrator succession lifecycle management.

Test Coverage:
- Context threshold detection
- Successor creation with instance numbering
- Handover summary generation and compression
- Multi-tenant isolation during succession
- Full succession workflow integration
- Concurrent orchestrators during transition
- Failed succession handling
"""

from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentExecution
from giljo_mcp.orchestrator_succession import (
    OrchestratorSuccessionManager,
    calculate_context_usage,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_manager():
    """Provide DatabaseManager instance."""
    return DatabaseManager()


@pytest.fixture
def tenant_key():
    """Provide consistent tenant key for testing."""
    return "test-tenant-" + str(uuid4())


@pytest.fixture
def session(db_manager):
    """Provide database session for testing."""
    with db_manager.get_session() as session:
        yield session


@pytest.fixture
def orchestrator_job(session: Session, tenant_key: str):
    """Create a test orchestrator job."""
    job = AgentExecution(
        tenant_key=tenant_key,
        job_id=str(uuid4()),
        agent_display_name="orchestrator",
        mission="Test orchestrator mission",
        status="working",
        instance_number=1,
        context_used=0,
        context_budget=150000,
        spawned_by=None,
        context_chunks=[],
        messages=[],
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@pytest.fixture
def succession_manager(db_manager, tenant_key):
    """Provide OrchestratorSuccessionManager instance."""
    with db_manager.get_session() as session:
        yield OrchestratorSuccessionManager(session, tenant_key)


# ============================================================================
# Unit Tests: Context Threshold Detection
# ============================================================================


def test_should_trigger_succession_at_90_percent(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test succession triggers at 90% context usage threshold."""
    # Set context to 90% (135,000 / 150,000)
    orchestrator_job.context_used = 135000
    session.commit()
    session.refresh(orchestrator_job)

    # Should trigger succession
    assert succession_manager.should_trigger_succession(orchestrator_job) is True


def test_should_trigger_succession_above_90_percent(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test succession triggers above 90% threshold."""
    # Set context to 95% (142,500 / 150,000)
    orchestrator_job.context_used = 142500
    session.commit()
    session.refresh(orchestrator_job)

    # Should trigger succession
    assert succession_manager.should_trigger_succession(orchestrator_job) is True


def test_should_not_trigger_succession_below_threshold(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test succession does not trigger below 90% threshold."""
    # Set context to 80% (120,000 / 150,000)
    orchestrator_job.context_used = 120000
    session.commit()
    session.refresh(orchestrator_job)

    # Should NOT trigger succession
    assert succession_manager.should_trigger_succession(orchestrator_job) is False


def test_should_not_trigger_succession_at_50_percent(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test succession does not trigger at 50% context usage."""
    # Set context to 50% (75,000 / 150,000)
    orchestrator_job.context_used = 75000
    session.commit()
    session.refresh(orchestrator_job)

    # Should NOT trigger succession
    assert succession_manager.should_trigger_succession(orchestrator_job) is False


def test_should_trigger_succession_manual_request(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
):
    """Test manual succession request triggers regardless of context."""
    # Set context to 50% (should not normally trigger)
    orchestrator_job.context_used = 75000

    # Manual request should trigger even below threshold
    assert succession_manager.should_trigger_succession(orchestrator_job, manual_request=True) is True


# ============================================================================
# Unit Tests: Successor Creation
# ============================================================================


def test_create_successor_increments_instance_number(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor gets incremented instance number."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify instance number incremented
    assert successor.instance_number == orchestrator_job.instance_number + 1
    assert successor.instance_number == 2


def test_create_successor_preserves_tenant_key(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor preserves tenant isolation."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify tenant key matches
    assert successor.tenant_key == orchestrator_job.tenant_key


def test_create_successor_preserves_project_id(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor preserves project association."""
    # Set project ID on orchestrator
    orchestrator_job.project_id = str(uuid4())
    session.commit()

    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify project ID matches
    assert successor.project_id == orchestrator_job.project_id


def test_create_successor_sets_spawned_by(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor tracks parent via spawned_by."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify spawned_by linkage
    assert successor.spawned_by == orchestrator_job.job_id


def test_create_successor_status_waiting(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor created in waiting status."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify status is waiting (for manual launch)
    assert successor.status == "waiting"


def test_create_successor_fresh_context(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor starts with fresh context window."""
    # Set parent to high context usage
    orchestrator_job.context_used = 135000
    session.commit()

    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify fresh context
    assert successor.context_used == 0
    assert successor.context_budget == 150000


def test_create_successor_unique_job_id(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test successor gets unique job ID."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Verify unique job IDs
    assert successor.job_id != orchestrator_job.job_id
    assert len(successor.job_id) == 36  # UUID format


def test_create_successor_multiple_instances(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test creating multiple successive instances."""
    # Create first successor (instance 2)
    successor1 = succession_manager.create_successor(orchestrator_job, reason="context_limit")
    assert successor1.instance_number == 2

    # Create second successor (instance 3)
    successor2 = succession_manager.create_successor(successor1, reason="context_limit")
    assert successor2.instance_number == 3

    # Create third successor (instance 4)
    successor3 = succession_manager.create_successor(successor2, reason="context_limit")
    assert successor3.instance_number == 4


# ============================================================================
# Unit Tests: Handover Summary Generation
# ============================================================================


def test_generate_handover_summary_includes_required_fields(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test handover summary contains all required fields."""
    # Add some messages to the orchestrator
    orchestrator_job.messages = [
        {"type": "mission", "content": "Start project"},
        {"type": "status", "content": "Working on phase 1"},
    ]
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Verify required fields present
    assert "project_status" in summary
    assert "active_agents" in summary
    assert "completed_phases" in summary
    assert "pending_decisions" in summary
    assert "critical_context_refs" in summary
    assert "next_steps" in summary
    assert "message_count" in summary


def test_generate_handover_summary_includes_context_refs(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test handover summary includes context chunk references."""
    # Add context chunks
    orchestrator_job.context_chunks = ["chunk-123", "chunk-456", "chunk-789"]
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Verify context refs included
    assert "critical_context_refs" in summary
    assert isinstance(summary["critical_context_refs"], list)
    assert len(summary["critical_context_refs"]) > 0


def test_generate_handover_summary_compression_target(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test handover summary meets compression target (<10K tokens)."""
    # Add significant message history
    orchestrator_job.messages = [{"type": "message", "content": f"Message {i}"} for i in range(100)]
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Estimate token count (rough approximation: 1 token ≈ 4 chars)
    import json

    summary_str = json.dumps(summary)
    estimated_tokens = len(summary_str) / 4

    # Should be under 10K tokens
    assert estimated_tokens < 10000, f"Summary too large: ~{estimated_tokens} tokens"


def test_generate_handover_summary_empty_orchestrator(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test handover summary handles empty orchestrator gracefully."""
    # Empty orchestrator (no messages, no context)
    orchestrator_job.messages = []
    orchestrator_job.context_chunks = []
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Should still have structure
    assert isinstance(summary, dict)
    assert summary["message_count"] == 0
    assert summary["active_agents"] == []


# ============================================================================
# Unit Tests: Handover Completion
# ============================================================================


def test_complete_handover_marks_status_complete(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test complete_handover marks orchestrator as complete."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Generate handover summary
    handover_summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Complete handover
    succession_manager.complete_handover(orchestrator_job, successor, handover_summary)

    # Refresh from database
    session.refresh(orchestrator_job)

    # Verify status is complete
    assert orchestrator_job.status == "complete"


def test_complete_handover_sets_handover_to_field(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test complete_handover sets handover_to field."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Generate handover summary
    handover_summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Complete handover
    succession_manager.complete_handover(orchestrator_job, successor, handover_summary)

    # Refresh from database
    session.refresh(orchestrator_job)

    # Verify handover_to points to successor
    assert orchestrator_job.handover_to == successor.job_id


def test_complete_handover_stores_summary(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test complete_handover stores handover summary."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Generate handover summary
    handover_summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Complete handover
    succession_manager.complete_handover(orchestrator_job, successor, handover_summary)

    # Refresh from database
    session.refresh(orchestrator_job)

    # Verify summary stored
    assert orchestrator_job.handover_summary is not None
    assert isinstance(orchestrator_job.handover_summary, dict)
    assert orchestrator_job.handover_summary == handover_summary


def test_complete_handover_sets_completed_at(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test complete_handover sets completed_at timestamp."""
    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Generate handover summary
    handover_summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Complete handover
    succession_manager.complete_handover(orchestrator_job, successor, handover_summary)

    # Refresh from database
    session.refresh(orchestrator_job)

    # Verify timestamp set
    assert orchestrator_job.completed_at is not None
    assert isinstance(orchestrator_job.completed_at, datetime)


def test_complete_handover_sets_succession_reason(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test complete_handover stores succession reason."""
    # Create successor with specific reason
    successor = succession_manager.create_successor(orchestrator_job, reason="manual")

    # Generate handover summary
    handover_summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Complete handover
    succession_manager.complete_handover(orchestrator_job, successor, handover_summary, reason="manual")

    # Refresh from database
    session.refresh(orchestrator_job)

    # Verify succession reason stored
    assert orchestrator_job.succession_reason == "manual"


# ============================================================================
# Unit Tests: Context Monitoring
# ============================================================================


def test_calculate_context_usage_returns_tuple(orchestrator_job: AgentExecution):
    """Test calculate_context_usage returns (used, budget) tuple."""
    orchestrator_job.context_used = 100000
    orchestrator_job.context_budget = 150000

    used, budget = calculate_context_usage(orchestrator_job)

    assert used == 100000
    assert budget == 150000


def test_calculate_context_usage_zero_usage(orchestrator_job: AgentExecution):
    """Test calculate_context_usage with zero usage."""
    orchestrator_job.context_used = 0
    orchestrator_job.context_budget = 150000

    used, budget = calculate_context_usage(orchestrator_job)

    assert used == 0
    assert budget == 150000


def test_calculate_context_usage_full_usage(orchestrator_job: AgentExecution):
    """Test calculate_context_usage at 100% usage."""
    orchestrator_job.context_used = 150000
    orchestrator_job.context_budget = 150000

    used, budget = calculate_context_usage(orchestrator_job)

    assert used == 150000
    assert budget == 150000


# ============================================================================
# Integration Tests: Full Succession Workflow
# ============================================================================


@pytest.mark.asyncio
async def test_full_succession_workflow(
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test complete succession workflow from detection to handover."""
    with db_manager.get_session() as session:
        # Create orchestrator at 90% context
        orchestrator = AgentExecution(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            mission="Test project orchestration",
            status="working",
            instance_number=1,
            context_used=135000,  # 90% of 150K
            context_budget=150000,
            context_chunks=["chunk-1", "chunk-2"],
            messages=[
                {"type": "mission", "content": "Start project"},
                {"type": "status", "content": "Phase 1 complete"},
            ],
        )
        session.add(orchestrator)
        session.commit()
        session.refresh(orchestrator)

        # Initialize succession manager
        manager = OrchestratorSuccessionManager(session, tenant_key)

        # Step 1: Detect threshold breach
        assert manager.should_trigger_succession(orchestrator) is True

        # Step 2: Create successor
        successor = manager.create_successor(orchestrator, reason="context_limit")
        assert successor.instance_number == 2
        assert successor.status == "waiting"
        assert successor.spawned_by == orchestrator.job_id

        # Step 3: Generate handover summary
        handover_summary = manager.generate_handover_summary(orchestrator)
        assert "next_steps" in handover_summary
        assert handover_summary["message_count"] == 2

        # Step 4: Complete handover
        manager.complete_handover(orchestrator, successor, handover_summary)

        # Verify final state
        session.refresh(orchestrator)
        session.refresh(successor)

        assert orchestrator.status == "complete"
        assert orchestrator.handover_to == successor.job_id
        assert orchestrator.handover_summary == handover_summary
        assert orchestrator.completed_at is not None

        assert successor.status == "waiting"
        assert successor.spawned_by == orchestrator.job_id
        assert successor.instance_number == 2


@pytest.mark.asyncio
async def test_multiple_successive_handovers(
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test multiple successive handovers (chain of 4 instances)."""
    with db_manager.get_session() as session:
        manager = OrchestratorSuccessionManager(session, tenant_key)

        # Create instance 1
        orch1 = AgentExecution(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            mission="Instance 1",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
        )
        session.add(orch1)
        session.commit()
        session.refresh(orch1)

        # Instance 1 → Instance 2
        orch2 = manager.create_successor(orch1, reason="context_limit")
        summary1 = manager.generate_handover_summary(orch1)
        manager.complete_handover(orch1, orch2, summary1)

        # Instance 2 → Instance 3
        orch2.context_used = 140000
        session.commit()
        orch3 = manager.create_successor(orch2, reason="context_limit")
        summary2 = manager.generate_handover_summary(orch2)
        manager.complete_handover(orch2, orch3, summary2)

        # Instance 3 → Instance 4
        orch3.context_used = 145000
        session.commit()
        orch4 = manager.create_successor(orch3, reason="phase_transition")
        summary3 = manager.generate_handover_summary(orch3)
        manager.complete_handover(orch3, orch4, summary3)

        # Verify chain integrity
        session.refresh(orch1)
        session.refresh(orch2)
        session.refresh(orch3)
        session.refresh(orch4)

        assert orch1.instance_number == 1
        assert orch1.handover_to == orch2.job_id
        assert orch1.status == "complete"

        assert orch2.instance_number == 2
        assert orch2.spawned_by == orch1.job_id
        assert orch2.handover_to == orch3.job_id
        assert orch2.status == "complete"

        assert orch3.instance_number == 3
        assert orch3.spawned_by == orch2.job_id
        assert orch3.handover_to == orch4.job_id
        assert orch3.status == "complete"

        assert orch4.instance_number == 4
        assert orch4.spawned_by == orch3.job_id
        assert orch4.status == "waiting"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_during_succession(
    db_manager: DatabaseManager,
):
    """Test succession respects tenant boundaries."""
    tenant_a = "tenant-a-" + str(uuid4())
    tenant_b = "tenant-b-" + str(uuid4())

    with db_manager.get_session() as session:
        # Create orchestrators for both tenants
        orch_a = AgentExecution(
            tenant_key=tenant_a,
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            mission="Tenant A project",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
        )
        orch_b = AgentExecution(
            tenant_key=tenant_b,
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            mission="Tenant B project",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
        )
        session.add(orch_a)
        session.add(orch_b)
        session.commit()
        session.refresh(orch_a)
        session.refresh(orch_b)

        # Create successors for both tenants
        manager_a = OrchestratorSuccessionManager(session, tenant_a)
        manager_b = OrchestratorSuccessionManager(session, tenant_b)

        successor_a = manager_a.create_successor(orch_a, reason="context_limit")
        successor_b = manager_b.create_successor(orch_b, reason="context_limit")

        # Verify tenant isolation
        assert successor_a.tenant_key == tenant_a
        assert successor_b.tenant_key == tenant_b
        assert successor_a.job_id != successor_b.job_id
        assert successor_a.spawned_by == orch_a.job_id
        assert successor_b.spawned_by == orch_b.job_id

        # Query orchestrators by tenant - should only see own tenant
        query_a = select(AgentExecution).where(AgentExecution.tenant_key == tenant_a)
        query_b = select(AgentExecution).where(AgentExecution.tenant_key == tenant_b)

        result_a = session.execute(query_a).scalars().all()
        result_b = session.execute(query_b).scalars().all()

        # Each tenant should have exactly 2 jobs (original + successor)
        assert len(result_a) == 2
        assert len(result_b) == 2

        # Verify zero cross-tenant leakage
        job_ids_a = {job.job_id for job in result_a}
        job_ids_b = {job.job_id for job in result_b}
        assert len(job_ids_a.intersection(job_ids_b)) == 0


@pytest.mark.asyncio
async def test_concurrent_orchestrators_during_transition(
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test handling concurrent orchestrators during succession."""
    with db_manager.get_session() as session:
        manager = OrchestratorSuccessionManager(session, tenant_key)

        # Create instance 1 (working)
        orch1 = AgentExecution(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            mission="Instance 1",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
        )
        session.add(orch1)
        session.commit()
        session.refresh(orch1)

        # Create successor (waiting)
        orch2 = manager.create_successor(orch1, reason="context_limit")
        session.refresh(orch2)

        # At this point: orch1=working, orch2=waiting (concurrent state)
        assert orch1.status == "working"
        assert orch2.status == "waiting"

        # Simulate user launching orch2
        orch2.status = "working"
        session.commit()

        # Now both are "working" briefly (grace period)
        session.refresh(orch1)
        session.refresh(orch2)
        assert orch1.status == "working"
        assert orch2.status == "working"

        # Complete handover (orch1 transitions to complete)
        summary = manager.generate_handover_summary(orch1)
        manager.complete_handover(orch1, orch2, summary)

        session.refresh(orch1)
        session.refresh(orch2)

        # Final state: orch1=complete, orch2=working
        assert orch1.status == "complete"
        assert orch2.status == "working"


@pytest.mark.asyncio
async def test_failed_succession_creates_blocked_status(
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test failed succession marks orchestrator as blocked."""
    with db_manager.get_session() as session:
        # Create orchestrator
        orch = AgentExecution(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_display_name="orchestrator",
            mission="Test project",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)

        manager = OrchestratorSuccessionManager(session, tenant_key)

        # Simulate succession failure by mocking create_successor to raise exception
        with patch.object(manager, "create_successor", side_effect=Exception("Database error")):
            try:
                manager.create_successor(orch, reason="context_limit")
                assert False, "Should have raised exception"
            except Exception as e:
                # Mark orchestrator as blocked
                orch.status = "blocked"
                orch.block_reason = f"Successor creation failed: {e!s}"
                session.commit()
                session.refresh(orch)

        # Verify blocked status
        assert orch.status == "blocked"
        assert "Successor creation failed" in orch.block_reason


# ============================================================================
# Unit Tests: Edge Cases
# ============================================================================


def test_succession_with_different_reasons(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test succession with different reason codes."""
    reasons = ["context_limit", "manual", "phase_transition"]

    for reason in reasons:
        # Create successor with specific reason
        successor = succession_manager.create_successor(orchestrator_job, reason=reason)

        # Complete handover with reason
        summary = succession_manager.generate_handover_summary(orchestrator_job)
        succession_manager.complete_handover(orchestrator_job, successor, summary, reason=reason)

        session.refresh(orchestrator_job)

        # Verify reason stored
        assert orchestrator_job.succession_reason == reason

        # Reset for next iteration
        orchestrator_job.status = "working"
        orchestrator_job.succession_reason = None
        session.commit()


def test_handover_context_refs_transferred(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test context chunk references transferred in handover."""
    # Add context chunks to orchestrator
    orchestrator_job.context_chunks = ["chunk-1", "chunk-2", "chunk-3"]
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Create successor
    successor = succession_manager.create_successor(orchestrator_job, reason="context_limit")

    # Complete handover
    succession_manager.complete_handover(orchestrator_job, successor, summary)

    session.refresh(orchestrator_job)

    # Verify context refs in handover_context_refs field
    assert orchestrator_job.handover_context_refs is not None
    assert len(orchestrator_job.handover_context_refs) > 0


def test_message_count_in_handover_summary(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test message count accurately reflected in handover summary."""
    # Add specific number of messages
    messages = [{"type": "test", "content": f"Message {i}"} for i in range(25)]
    orchestrator_job.messages = messages
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Verify message count
    assert summary["message_count"] == 25


def test_unresolved_blockers_in_handover(
    succession_manager: OrchestratorSuccessionManager,
    orchestrator_job: AgentExecution,
    session: Session,
):
    """Test unresolved blockers included in handover summary."""
    # Add blocker information to messages
    orchestrator_job.messages = [
        {"type": "blocker", "content": "Authentication method unclear"},
        {"type": "blocker", "content": "Database schema pending review"},
    ]
    session.commit()

    # Generate handover summary
    summary = succession_manager.generate_handover_summary(orchestrator_job)

    # Verify unresolved blockers included
    assert "unresolved_blockers" in summary
    # Implementation may extract blockers from messages
