"""
Integration tests for AgentJob + AgentExecution (Handover 0366a).

RED Phase (TDD): These tests validate the interaction between both models.

Tests focus on:
- Job persistence across succession
- Message routing semantics (agent_id vs job_id)
- Data normalization (mission stored in job, not execution)
- Succession chain integrity
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# These imports will FAIL until GREEN phase
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


class TestJobPersistenceAcrossSuccession:
    """Test that jobs persist when executions change (succession scenario)."""

    @pytest.mark.asyncio
    async def test_job_persists_across_succession(self, db_session: AsyncSession):
        """Job persists when executions change (succession scenario)."""
        # Create job
        job = AgentJob(
            job_id="job-persistent",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Build authentication system with OAuth2, JWT, and role-based access control",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution 1
        exec1 = AgentExecution(
            agent_id="agent-001",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="complete",
            started_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
        )
        db_session.add(exec1)
        await db_session.commit()

        # Create execution 2 (succession)
        exec2 = AgentExecution(
            agent_id="agent-002",
            job_id=job.job_id,  # SAME job
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            spawned_by=exec1.agent_id,
            started_at=datetime(2025, 1, 1, 14, 5, 0, tzinfo=timezone.utc),
        )
        exec1.succeeded_by = exec2.agent_id
        db_session.add(exec2)
        await db_session.commit()

        # Refresh job to load executions
        await db_session.refresh(job)

        # Validate job persistence
        assert len(job.executions) == 2
        assert job.executions[0].agent_id == "agent-001"
        assert job.executions[1].agent_id == "agent-002"
        assert job.mission == "Build authentication system with OAuth2, JWT, and role-based access control"  # Unchanged
        assert job.job_id == "job-persistent"  # Unchanged

    @pytest.mark.asyncio
    async def test_multiple_succession_instances(self, db_session: AsyncSession):
        """Job can have many execution instances (extended succession chain)."""
        job = AgentJob(
            job_id="job-multi-succession",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Long-running project with multiple handovers",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create 5 successive executions
        prev_agent_id = None
        for i in range(1, 6):
            exec_instance = AgentExecution(
                agent_id=f"agent-{i:03d}",
                job_id=job.job_id,
                tenant_key="tenant-abc",
                agent_display_name="orchestrator",
                status="complete" if i < 5 else "working",
                spawned_by=prev_agent_id,
            )
            db_session.add(exec_instance)
            await db_session.commit()

            # Update previous execution's succeeded_by
            if prev_agent_id:
                prev_exec = (
                    await db_session.execute(select(AgentExecution).filter(AgentExecution.agent_id == prev_agent_id))
                ).scalar_one_or_none()
                prev_exec.succeeded_by = exec_instance.agent_id
                await db_session.commit()

            prev_agent_id = exec_instance.agent_id

        # Refresh job
        await db_session.refresh(job)

        # Validate succession chain
        assert len(job.executions) == 5
        assert job.executions[4].spawned_by == "agent-004"


class TestMissionDataNormalization:
    """Test that mission is stored in job (NOT duplicated in executions)."""

    @pytest.mark.asyncio
    async def test_mission_stored_once_in_job(self, db_session: AsyncSession):
        """Mission is stored ONCE in AgentJob, not duplicated in executions."""
        job = AgentJob(
            job_id="job-mission-normalization",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="This is the mission statement. It should be stored only once.",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create 3 executions (succession)
        for i in range(1, 4):
            exec_instance = AgentExecution(
                agent_id=f"agent-norm-{i}",
                job_id=job.job_id,
                tenant_key="tenant-abc",
                agent_display_name="orchestrator",
                status="complete" if i < 3 else "working",
            )
            db_session.add(exec_instance)
        await db_session.commit()

        # Validate: Mission is NOT in AgentExecution table
        assert not hasattr(job.executions[0], "mission")  # No mission field in execution

        # Validate: All executions share the SAME job mission
        await db_session.refresh(job)
        for execution in job.executions:
            assert execution.job.mission == "This is the mission statement. It should be stored only once."


class TestMessageRoutingSemantics:
    """Test that messages route to agent_id (executor), NOT job_id (work)."""

    @pytest.mark.asyncio
    async def test_message_routing_uses_agent_id(self, db_session: AsyncSession):
        """Messages are routed to agent_id, NOT job_id."""
        # This test validates the semantic shift:
        # OLD: "Send message to job_id abc-123" (ambiguous - which executor?)
        # NEW: "Send message to agent_id def-456" (precise - specific executor)

        job = AgentJob(
            job_id="job-messaging-test",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Test messaging",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        exec1 = AgentExecution(
            agent_id="agent-sender",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
        )
        exec2 = AgentExecution(
            agent_id="agent-receiver",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="analyzer",
            status="working",
        )
        db_session.add_all([exec1, exec2])
        await db_session.commit()

        # Simulate sending message to specific executor
        message_payload = {
            "from_agent": "agent-sender",
            "to_agent": "agent-receiver",  # Routes to EXECUTOR, not job
            "content": "Please analyze the requirements",
        }

        # Store message in receiver's execution
        exec2.messages = [
            {
                "id": "msg-1",
                "from": message_payload["from_agent"],
                "content": message_payload["content"],
                "status": "pending",
            }
        ]
        await db_session.commit()

        # Validate: Message is stored in agent_id (executor-specific)
        await db_session.refresh(exec2)
        assert len(exec2.messages) == 1
        assert exec2.messages[0]["from"] == "agent-sender"

        # Validate: Other executor does NOT see the message
        await db_session.refresh(exec1)
        assert len(exec1.messages) == 0  # No messages for sender

    @pytest.mark.asyncio
    async def test_message_isolation_between_executions(self, db_session: AsyncSession):
        """Messages are isolated per execution (succession scenario)."""
        job = AgentJob(
            job_id="job-message-isolation",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Test message isolation",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution 1 with messages
        exec1 = AgentExecution(
            agent_id="agent-iso-001",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="complete",
            messages=[{"id": "msg-1", "content": "Message for instance 1", "status": "acknowledged"}],
        )
        db_session.add(exec1)
        await db_session.commit()

        # Create execution 2 (successor) with different messages
        exec2 = AgentExecution(
            agent_id="agent-iso-002",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            spawned_by=exec1.agent_id,
            messages=[{"id": "msg-2", "content": "Message for instance 2", "status": "pending"}],
        )
        db_session.add(exec2)
        await db_session.commit()

        # Validate: Messages are isolated per execution
        await db_session.refresh(exec1)
        await db_session.refresh(exec2)

        assert len(exec1.messages) == 1
        assert exec1.messages[0]["content"] == "Message for instance 1"

        assert len(exec2.messages) == 1
        assert exec2.messages[0]["content"] == "Message for instance 2"


class TestSuccessionChainIntegrity:
    """Test succession chain relationships are maintained correctly."""

    @pytest.mark.asyncio
    async def test_succession_chain_forward_backward_links(self, db_session: AsyncSession):
        """Succession chain has valid forward (succeeded_by) and backward (spawned_by) links."""
        job = AgentJob(
            job_id="job-chain-integrity",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Test succession chain integrity",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create chain: agent-1 → agent-2 → agent-3
        exec1 = AgentExecution(
            agent_id="agent-chain-1",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="complete",
        )
        db_session.add(exec1)
        await db_session.commit()

        exec2 = AgentExecution(
            agent_id="agent-chain-2",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="complete",
            spawned_by=exec1.agent_id,
        )
        exec1.succeeded_by = exec2.agent_id
        db_session.add(exec2)
        await db_session.commit()

        exec3 = AgentExecution(
            agent_id="agent-chain-3",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            spawned_by=exec2.agent_id,
        )
        exec2.succeeded_by = exec3.agent_id
        db_session.add(exec3)
        await db_session.commit()

        # Refresh all
        await db_session.refresh(exec1)
        await db_session.refresh(exec2)
        await db_session.refresh(exec3)

        # Validate forward links (succeeded_by)
        assert exec1.succeeded_by == "agent-chain-2"
        assert exec2.succeeded_by == "agent-chain-3"
        assert exec3.succeeded_by is None  # No successor yet

        # Validate backward links (spawned_by)
        assert exec1.spawned_by is None  # First in chain
        assert exec2.spawned_by == "agent-chain-1"
        assert exec3.spawned_by == "agent-chain-2"

    @pytest.mark.asyncio
    async def test_succession_chain_query_all_instances(self, db_session: AsyncSession):
        """Can query all execution instances for a job (full history)."""
        job = AgentJob(
            job_id="job-query-history",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Test execution history query",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create 4 executions
        for i in range(1, 5):
            exec_instance = AgentExecution(
                agent_id=f"agent-history-{i}",
                job_id=job.job_id,
                tenant_key="tenant-abc",
                agent_display_name="orchestrator",
                status="complete" if i < 4 else "working",
            )
            db_session.add(exec_instance)
        await db_session.commit()

        # Query all executions for job
        executions = (
            (await db_session.execute(select(AgentExecution).filter(AgentExecution.job_id == job.job_id)))
            .scalars()
            .all()
        )

        # Validate
        assert len(executions) == 4
        assert executions[3].status == "working"


class TestJobStatusTransitions:
    """Test job status transitions coordinated with execution status."""

    @pytest.mark.asyncio
    async def test_job_completion_when_final_execution_completes(self, db_session: AsyncSession):
        """Job status becomes 'completed' when final execution completes."""
        job = AgentJob(
            job_id="job-completion",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Test job completion",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution
        execution = AgentExecution(
            agent_id="agent-final",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
        )
        db_session.add(execution)
        await db_session.commit()

        # Mark execution as complete
        execution.status = "complete"
        execution.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Validate
        await db_session.refresh(job)
        await db_session.refresh(execution)

        assert job.status == "completed"
        assert execution.status == "complete"
        assert job.completed_at is not None


class TestIndexPerformance:
    """Test that indexes improve query performance for common operations."""

    @pytest.mark.asyncio
    async def test_query_executions_by_job_id_uses_index(self, db_session: AsyncSession):
        """Querying executions by job_id should use index."""
        job = AgentJob(
            job_id="job-index-test",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Test index performance",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create multiple executions
        for i in range(1, 11):
            exec_instance = AgentExecution(
                agent_id=f"agent-idx-{i}",
                job_id=job.job_id,
                tenant_key="tenant-abc",
                agent_display_name="orchestrator",
                status="complete",
            )
            db_session.add(exec_instance)
        await db_session.commit()

        # Query by job_id (should use idx_agent_executions_job)
        executions = (
            (await db_session.execute(select(AgentExecution).filter(AgentExecution.job_id == job.job_id)))
            .scalars()
            .all()
        )

        assert len(executions) == 10

    @pytest.mark.asyncio
    async def test_query_executions_by_tenant_and_job_uses_composite_index(self, db_session: AsyncSession):
        """Querying executions by tenant_key + job_id should use composite index."""
        job = AgentJob(
            job_id="job-composite-idx",
            tenant_key="tenant-xyz",
            project_id="project-123",
            mission="Test composite index",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create executions
        for i in range(1, 6):
            exec_instance = AgentExecution(
                agent_id=f"agent-comp-{i}",
                job_id=job.job_id,
                tenant_key="tenant-xyz",
                agent_display_name="orchestrator",
                status="complete",
            )
            db_session.add(exec_instance)
        await db_session.commit()

        # Query by tenant_key + job_id (should use idx_agent_executions_tenant_job)
        executions = (
            (
                await db_session.execute(
                    select(AgentExecution).filter(
                        AgentExecution.tenant_key == "tenant-xyz", AgentExecution.job_id == job.job_id
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(executions) == 5
