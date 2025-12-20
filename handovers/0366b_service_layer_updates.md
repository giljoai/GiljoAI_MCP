# Handover 0366b: Agent Identity Refactor - Phase B (Service Layer Updates)

**Date**: 2025-12-19
**Phase**: B of 4
**Status**: Ready for Execution
**Estimated Duration**: 16-20 hours
**TDD Approach**: RED → GREEN → REFACTOR
**Dependencies**: Phase A (0366a) MUST be complete

---

## Prerequisites & Reference Documents

**MUST READ before starting this phase:**

1. **Master Roadmap**: `handovers/0366_agent_identity_refactor_roadmap.md`
   - Executive summary, phase dependencies, success criteria

2. **Phase A Completion**: `handovers/0366a_schema_and_models.md`
   - Verify AgentJob + AgentExecution models are implemented
   - Migration script completed successfully

3. **UUID Index**: `handovers/Reference_docs/UUID_INDEX_0366.md`
   - Service files to modify (orchestration_service, message_service, etc.)

4. **Database Schema Map**: `handovers/Reference_docs/DATABASE_SCHEMA_MAP_0366.md`
   - New schema relationships for service queries

5. **Project Context**: `F:\GiljoAI_MCP\CLAUDE.md`
   - Service layer patterns, multi-tenant isolation requirements

---

## Objective

Update all service layer components to work with the new dual-model architecture (AgentJob + AgentExecution). This phase rewires the backend logic to:
1. Create jobs separately from executions
2. Handle succession by creating new executions (NOT new jobs)
3. Route messages to agent_id (executor) instead of job_id (work)
4. Maintain semantic clarity: job_id = work, agent_id = worker

---

## Services to Update

### 1. **OrchestrationService** (`src/giljo_mcp/orchestrator_succession.py`)
**Current Behavior**: Creates new MCPAgentJob on succession (new job_id)
**New Behavior**: Creates new AgentExecution on succession (SAME job_id, new agent_id)

### 2. **MessageService** (`src/giljo_mcp/services/message_service.py`)
**Current Behavior**: Routes messages to job_id (ambiguous)
**New Behavior**: Routes messages to agent_id (precise executor)

### 3. **ProjectService** (`src/giljo_mcp/services/project_service.py`)
**Current Behavior**: Queries MCPAgentJob for project agents
**New Behavior**: Queries AgentExecution JOIN AgentJob for project agents

### 4. **AgentJobManager** (`src/giljo_mcp/services/agent_job_manager.py`)
**Current Behavior**: CRUD operations on MCPAgentJob
**New Behavior**: Coordinated CRUD on AgentJob + AgentExecution

---

## TDD Approach (MANDATORY)

### Phase 1: RED (30-40% of time) - Write Failing Tests FIRST

#### `tests/services/test_orchestration_service_0366b.py`
```python
"""
Tests for orchestration service with new identity model.
These tests MUST be written FIRST (TDD RED phase).
"""
import pytest
from datetime import datetime, timezone
from src.giljo_mcp.models import AgentJob, AgentExecution
from src.giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager

@pytest.mark.asyncio
async def test_succession_creates_new_execution_same_job(db_session):
    """Succession creates new execution on SAME job (not new job)."""
    # Setup: Create job and first execution
    job = AgentJob(
        job_id="job-persistent",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build authentication system",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete",
        context_used=135000,  # 90% of 150K budget - triggers succession
        context_budget=150000
    )
    db_session.add(exec1)
    await db_session.commit()

    # Act: Trigger succession
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    exec2 = await manager.create_successor(exec1, "context_limit")

    # Assert: New execution, SAME job
    assert exec2.agent_id != exec1.agent_id  # Different executor
    assert exec2.job_id == exec1.job_id  # SAME work order
    assert exec2.instance_number == 2  # Incremented
    assert exec2.spawned_by == exec1.agent_id  # Lineage preserved
    assert exec1.succeeded_by == exec2.agent_id  # Succession chain

@pytest.mark.asyncio
async def test_succession_preserves_mission(db_session):
    """Mission is NOT duplicated - stored in job, shared by executions."""
    # Setup
    job = AgentJob(
        job_id="job-mission-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Original mission: Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete"
    )
    db_session.add(exec1)
    await db_session.commit()

    # Act: Create successor
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    exec2 = await manager.create_successor(exec1, "manual")

    # Assert: Mission stored ONCE in job (not duplicated in executions)
    assert job.mission == "Original mission: Build auth"
    assert exec2.job.mission == job.mission  # Accessed via relationship
    # Executions do NOT have mission field (data normalization)

@pytest.mark.asyncio
async def test_handover_summary_generation(db_session):
    """Handover summary stored in execution, NOT job."""
    # Setup
    job = AgentJob(
        job_id="job-handover-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working",
        messages=[
            {"id": "msg-1", "type": "status", "content": "75% complete"},
            {"id": "msg-2", "type": "blocker", "content": "Database schema issue"}
        ]
    )
    db_session.add(exec1)
    await db_session.commit()

    # Act: Generate handover summary
    manager = OrchestratorSuccessionManager(db_session, "tenant-abc")
    summary = manager.generate_handover_summary(exec1)

    # Assert: Summary contains execution-specific state
    assert "project_status" in summary
    assert summary["project_status"] == "75% complete"
    assert len(summary["unresolved_blockers"]) > 0
    # Summary stored in execution, NOT job (execution-specific state)
```

#### `tests/services/test_message_service_0366b.py`
```python
"""
Tests for message service with agent_id routing.
These tests MUST be written FIRST (TDD RED phase).
"""
import pytest
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.models import AgentJob, AgentExecution

@pytest.mark.asyncio
async def test_send_message_uses_agent_id(db_manager, tenant_manager):
    """Messages are sent to agent_id (executor), NOT job_id (work)."""
    # Setup: Create job with two executions
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id="job-messaging",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Build auth",
            job_type="orchestrator",
            status="active"
        )
        session.add(job)

        sender = AgentExecution(
            agent_id="agent-sender",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=1,
            status="working"
        )
        receiver = AgentExecution(
            agent_id="agent-receiver",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="analyzer",
            instance_number=1,
            status="working"
        )
        session.add_all([sender, receiver])
        await session.commit()

    # Act: Send message using agent_id
    service = MessageService(db_manager, tenant_manager)
    result = await service.send_message(
        to_agents=["agent-receiver"],  # Uses agent_id (NOT job_id)
        content="Please review code",
        project_id="project-123",
        from_agent="agent-sender",
        tenant_key="tenant-abc"
    )

    # Assert: Message delivered to specific executor
    assert result["success"] is True
    assert "agent-receiver" in result["to_agents"]

@pytest.mark.asyncio
async def test_receive_messages_filters_by_agent_id(db_manager, tenant_manager):
    """Agent receives messages addressed to its agent_id, NOT job_id."""
    # Setup: Create two executions on SAME job
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id="job-shared",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Build auth",
            job_type="orchestrator",
            status="active"
        )
        session.add(job)

        exec1 = AgentExecution(
            agent_id="agent-001",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=1,
            status="complete"
        )
        exec2 = AgentExecution(
            agent_id="agent-002",
            job_id=job.job_id,  # SAME job
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=2,
            status="working"
        )
        session.add_all([exec1, exec2])
        await session.commit()

    # Act: Send message to exec2 only
    service = MessageService(db_manager, tenant_manager)
    await service.send_message(
        to_agents=["agent-002"],  # Only to successor
        content="Continue from where exec1 left off",
        project_id="project-123",
        from_agent="orchestrator-coordinator",
        tenant_key="tenant-abc"
    )

    # Assert: Only exec2 receives message (exec1 does NOT)
    messages_exec2 = await service.receive_messages(
        agent_id="agent-002",
        tenant_key="tenant-abc"
    )
    messages_exec1 = await service.receive_messages(
        agent_id="agent-001",
        tenant_key="tenant-abc"
    )

    assert messages_exec2["count"] == 1  # Received
    assert messages_exec1["count"] == 0  # Did NOT receive
```

#### `tests/services/test_agent_job_manager_0366b.py`
```python
"""
Tests for AgentJobManager with dual-model CRUD.
These tests MUST be written FIRST (TDD RED phase).
"""
import pytest
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.models import AgentJob, AgentExecution

@pytest.mark.asyncio
async def test_spawn_agent_creates_job_and_execution(db_manager, tenant_manager):
    """Spawning an agent creates BOTH job and execution."""
    # Act: Spawn new agent
    manager = AgentJobManager(db_manager, tenant_manager)
    result = await manager.spawn_agent(
        project_id="project-123",
        agent_type="analyzer",
        mission="Analyze codebase for security vulnerabilities",
        tenant_key="tenant-abc"
    )

    # Assert: Both job and execution created
    assert result["success"] is True
    assert "job_id" in result  # Work order ID
    assert "agent_id" in result  # Executor ID
    assert result["job_id"] != result["agent_id"]  # Different UUIDs

    # Validate database
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        job = await session.execute(
            select(AgentJob).where(AgentJob.job_id == result["job_id"])
        )
        job = job.scalar_one()

        execution = await session.execute(
            select(AgentExecution).where(AgentExecution.agent_id == result["agent_id"])
        )
        execution = execution.scalar_one()

        assert job.mission == "Analyze codebase for security vulnerabilities"
        assert execution.job_id == job.job_id  # Linked
        assert execution.instance_number == 1  # First instance

@pytest.mark.asyncio
async def test_update_execution_status_not_job_status(db_manager, tenant_manager):
    """Updating execution status does NOT change job status."""
    # Setup: Create job + execution
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id="job-status-test",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Build auth",
            job_type="orchestrator",
            status="active"  # Job is active
        )
        session.add(job)

        execution = AgentExecution(
            agent_id="agent-001",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=1,
            status="working"
        )
        session.add(execution)
        await session.commit()

    # Act: Update execution status to "complete"
    manager = AgentJobManager(db_manager, tenant_manager)
    await manager.update_agent_status(
        agent_id="agent-001",
        status="complete",
        tenant_key="tenant-abc"
    )

    # Assert: Execution complete, job STILL active (awaiting next execution)
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        job = await session.execute(
            select(AgentJob).where(AgentJob.job_id == "job-status-test")
        )
        job = job.scalar_one()

        execution = await session.execute(
            select(AgentExecution).where(AgentExecution.agent_id == "agent-001")
        )
        execution = execution.scalar_one()

        assert execution.status == "complete"
        assert job.status == "active"  # Job persists

@pytest.mark.asyncio
async def test_complete_job_marks_all_executions_decommissioned(db_manager, tenant_manager):
    """Completing a job decommissions all its executions."""
    # Setup: Create job with 3 executions (succession chain)
    async with db_manager.get_session_async() as session:
        job = AgentJob(
            job_id="job-complete-test",
            tenant_key="tenant-abc",
            project_id="project-123",
            mission="Build auth",
            job_type="orchestrator",
            status="active"
        )
        session.add(job)

        exec1 = AgentExecution(
            agent_id="agent-001",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=1,
            status="complete"
        )
        exec2 = AgentExecution(
            agent_id="agent-002",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=2,
            status="complete"
        )
        exec3 = AgentExecution(
            agent_id="agent-003",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_type="orchestrator",
            instance_number=3,
            status="complete"
        )
        session.add_all([exec1, exec2, exec3])
        await session.commit()

    # Act: Complete the job
    manager = AgentJobManager(db_manager, tenant_manager)
    await manager.complete_job(
        job_id="job-complete-test",
        tenant_key="tenant-abc"
    )

    # Assert: Job completed, all executions decommissioned
    async with db_manager.get_session_async() as session:
        from sqlalchemy import select
        job = await session.execute(
            select(AgentJob).where(AgentJob.job_id == "job-complete-test")
        )
        job = job.scalar_one()

        executions = await session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job.job_id)
        )
        executions = executions.scalars().all()

        assert job.status == "completed"
        for execution in executions:
            assert execution.status == "decommissioned"
```

### Phase 2: GREEN (40-50% of time) - Implement Service Updates

#### Update `orchestrator_succession.py`
```python
# KEY CHANGES:
# 1. create_successor() creates AgentExecution (not MCPAgentJob)
# 2. Succession preserves job_id (SAME work order)
# 3. spawned_by/succeeded_by point to agent_id (not job_id)

class OrchestratorSuccessionManager:
    """Manages orchestrator succession with dual-model architecture."""

    async def create_successor(
        self,
        current_execution: AgentExecution,  # Changed from MCPAgentJob
        reason: str,
    ) -> AgentExecution:  # Returns execution, not job
        """Create successor execution for handover."""

        # Get parent job
        job = current_execution.job  # Via relationship

        # Create NEW execution on SAME job
        successor_execution = AgentExecution(
            agent_id=str(uuid4()),  # New executor ID
            job_id=job.job_id,  # SAME work order
            tenant_key=self.tenant_key,
            agent_type=current_execution.agent_type,
            instance_number=current_execution.instance_number + 1,
            status="waiting",
            spawned_by=current_execution.agent_id,  # Points to agent, not job
            context_used=0,
            context_budget=current_execution.context_budget,
        )

        # Update current execution succession chain
        current_execution.succeeded_by = successor_execution.agent_id
        current_execution.succession_reason = reason

        # Add to session
        self.db_session.add(successor_execution)
        await self.db_session.commit()

        return successor_execution
```

#### Update `message_service.py`
```python
# KEY CHANGES:
# 1. to_agents parameter accepts agent_id (not job_id)
# 2. receive_messages() filters by agent_id
# 3. Resolution logic converts agent_type → agent_id lookup

async def send_message(
    self,
    to_agents: list[str],  # Now expects agent_id UUIDs
    content: str,
    project_id: str,
    from_agent: Optional[str] = None,  # Can be agent_id or agent_type
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """Send message to specific agent executors."""

    # Resolve agent_type strings to agent_id UUIDs
    resolved_to_agents = []
    for agent_ref in to_agents:
        if len(agent_ref) == 36 and '-' in agent_ref:
            # Already an agent_id UUID
            resolved_to_agents.append(agent_ref)
        else:
            # Agent type string - resolve to current executor
            result = await session.execute(
                select(AgentExecution).where(
                    AgentExecution.project_id == project_id,
                    AgentExecution.agent_type == agent_ref,
                    AgentExecution.status.in_(['waiting', 'working'])  # Active only
                ).order_by(AgentExecution.instance_number.desc()).limit(1)
            )
            execution = result.scalar_one_or_none()
            if execution:
                resolved_to_agents.append(execution.agent_id)

    # Create message with agent_id references
    message = Message(
        to_agents=resolved_to_agents,  # agent_id UUIDs
        content=content,
        # ...
    )
```

#### Update `agent_job_manager.py`
```python
# NEW FILE: Coordinated CRUD for AgentJob + AgentExecution

class AgentJobManager:
    """Manages agent job lifecycle with dual-model architecture."""

    async def spawn_agent(
        self,
        project_id: str,
        agent_type: str,
        mission: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """Spawn new agent (creates job + execution)."""

        # Create job (work order)
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project_id,
            mission=mission,
            job_type=agent_type,
            status="active",
        )

        # Create execution (first executor)
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type=agent_type,
            instance_number=1,
            status="waiting",
        )

        # Save both
        async with self.db_manager.get_session_async() as session:
            session.add(job)
            session.add(execution)
            await session.commit()

        return {
            "success": True,
            "job_id": job.job_id,
            "agent_id": execution.agent_id,
        }

    async def complete_job(
        self,
        job_id: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """Complete job and decommission all executions."""

        async with self.db_manager.get_session_async() as session:
            # Get job
            result = await session.execute(
                select(AgentJob).where(
                    AgentJob.job_id == job_id,
                    AgentJob.tenant_key == tenant_key
                )
            )
            job = result.scalar_one()

            # Mark job complete
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)

            # Decommission all executions
            for execution in job.executions:
                execution.status = "decommissioned"
                execution.decommissioned_at = datetime.now(timezone.utc)

            await session.commit()

        return {"success": True, "job_id": job_id}
```

### Phase 3: REFACTOR (10-20% of time) - Polish and Optimize

- Update relationship loading (use `selectinload` for efficiency)
- Add service-level validation (job exists before creating execution)
- Update error messages (distinguish job vs execution errors)
- Add logging (track job_id AND agent_id in all log messages)

---

## Validation Checklist

Before marking Phase B complete:

- [ ] All tests in `test_orchestration_service_0366b.py` pass
- [ ] All tests in `test_message_service_0366b.py` pass
- [ ] All tests in `test_agent_job_manager_0366b.py` pass
- [ ] Integration test: Spawn agent → succession → message delivery
- [ ] No breaking changes to existing API responses (backward compat)
- [ ] Performance benchmarks (query time for common operations)
- [ ] Error handling tested (job not found, execution not found, etc.)
- [ ] Logging verified (job_id + agent_id in all messages)

---

## Kickoff Prompt

Copy and paste this prompt to start a fresh session for Phase B:

---

**Mission**: Implement Handover 0366b - Update service layer for dual-model architecture

**Context**: You are the Backend Integration Tester Agent working on GiljoAI MCP Server. Phase A (0366a) is complete - AgentJob and AgentExecution models exist. Your mission is to update all service layer code to use the new dual-model architecture.

**TDD Approach** (MANDATORY):
1. **RED** (30-40% time): Write ALL service tests FIRST
2. **GREEN** (40-50% time): Update services to pass tests
3. **REFACTOR** (10-20% time): Optimize queries, add logging, polish

**Services to Update**:
1. `orchestrator_succession.py` - Succession creates new execution (not new job)
2. `message_service.py` - Route messages to agent_id (not job_id)
3. `project_service.py` - Query AgentExecution JOIN AgentJob
4. `agent_job_manager.py` - Coordinated CRUD on job + execution

**Test Files to Create** (RED phase):
- `tests/services/test_orchestration_service_0366b.py`
- `tests/services/test_message_service_0366b.py`
- `tests/services/test_agent_job_manager_0366b.py`

**Success Criteria**:
- All tests pass (>80% coverage)
- Succession creates new execution on SAME job
- Messages route to agent_id (precise delivery)
- No breaking API changes

**Reference**: Read `handovers/0366b_service_layer_updates.md` for complete specifications.

**Environment**:
- PostgreSQL 18 with Phase A schema (agent_jobs + agent_executions tables)
- Python 3.11+
- pytest-asyncio for async testing

**First Step**: Create `tests/services/test_orchestration_service_0366b.py` with failing tests (RED phase).

---

**Estimated Duration**: 16-20 hours
**Priority**: HIGH - Blocks Phase C and D
**Status**: Ready for execution (after Phase A complete)
