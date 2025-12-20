"""
Tests for MessageService with agent_id routing (Handover 0366b).

These tests are written FIRST (TDD RED phase) to define expected behavior:
1. Messages are sent to agent_id (executor), NOT job_id (work)
2. Agent receives messages addressed to its agent_id, NOT job_id
3. Succession: Messages go to NEW executor (not old one)
4. Agent type resolution: "orchestrator" → current executor agent_id

Test Coverage:
- send_message() uses agent_id parameter
- receive_messages() filters by agent_id
- Succession: Messages route to active execution
- Agent type resolution to agent_id
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message
from src.giljo_mcp.services.message_service_0366b import MessageService


@pytest_asyncio.fixture
async def test_project_0366b_msg(db_session):
    """Create test project for 0366b message tests."""
    project = Project(
        id="project-123",
        tenant_key="tenant-abc",
        name="Test Project 0366b Messages",
        description="Test project for agent identity message routing",
        mission="Build authentication system",
        status="active"
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest.mark.asyncio
async def test_send_message_uses_agent_id(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    Messages are sent to agent_id (executor), NOT job_id (work).

    This is the core semantic change for messaging:
    - OLD: to_agents=[job_id] (ambiguous - which executor?)
    - NEW: to_agents=[agent_id] (precise - specific executor)
    """
    # Setup: Create job with two executions
    job = AgentJob(
        job_id="job-messaging",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

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
    db_session.add_all([sender, receiver])
    await db_session.commit()

    # Act: Send message using agent_id
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
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
async def test_receive_messages_filters_by_agent_id(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    Agent receives messages addressed to its agent_id, NOT job_id.

    Scenario: Two executions on SAME job (succession).
    Messages sent to exec2 should NOT be received by exec1.
    """
    # Setup: Create two executions on SAME job
    job = AgentJob(
        job_id="job-shared",
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
    db_session.add_all([exec1, exec2])
    await db_session.commit()

    # Act: Send message to exec2 only
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
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


@pytest.mark.asyncio
async def test_agent_type_resolution_to_agent_id(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    Sending to agent_type string resolves to current executor agent_id.

    Scenario: send_message(to_agents=["orchestrator"]) should resolve to
    the ACTIVE orchestrator execution (not the job).
    """
    # Setup: Create job with active execution
    job = AgentJob(
        job_id="job-resolution",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec_active = AgentExecution(
        agent_id="agent-active",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working"  # Active
    )
    db_session.add(exec_active)
    await db_session.commit()

    # Act: Send message using agent_type string
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    result = await service.send_message(
        to_agents=["orchestrator"],  # Agent type string
        content="Status update",
        project_id="project-123",
        from_agent="system",
        tenant_key="tenant-abc"
    )

    # Assert: Resolved to agent_id of active execution
    assert result["success"] is True
    # The resolved agent_id should be agent-active
    # (implementation will resolve agent_type → agent_id)


@pytest.mark.asyncio
async def test_succession_messages_route_to_new_executor(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    After succession, messages sent to agent_type route to NEW executor.

    Scenario:
    1. exec1 (orchestrator) is complete
    2. exec2 (orchestrator) is active (successor)
    3. Message sent to "orchestrator" → should go to exec2 (NOT exec1)
    """
    # Setup: Create succession chain
    job = AgentJob(
        job_id="job-succession-routing",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-old",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete",  # Old executor (decommissioned)
        succeeded_by="agent-new"
    )
    exec2 = AgentExecution(
        agent_id="agent-new",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=2,
        status="working",  # New executor (active)
        spawned_by="agent-old"
    )
    db_session.add_all([exec1, exec2])
    await db_session.commit()

    # Act: Send message to "orchestrator" (should resolve to active exec2)
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    await service.send_message(
        to_agents=["orchestrator"],  # Agent type (not agent_id)
        content="Continue work",
        project_id="project-123",
        from_agent="system",
        tenant_key="tenant-abc"
    )

    # Assert: Message delivered to exec2 (NOT exec1)
    messages_exec2 = await service.receive_messages(
        agent_id="agent-new",
        tenant_key="tenant-abc"
    )
    messages_exec1 = await service.receive_messages(
        agent_id="agent-old",
        tenant_key="tenant-abc"
    )

    assert messages_exec2["count"] == 1  # Active executor received
    assert messages_exec1["count"] == 0  # Old executor did NOT receive


@pytest.mark.asyncio
async def test_broadcast_to_all_active_executors(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    Broadcasting to all agents targets active executions only.

    Scenario: Project has 3 jobs, each with 2 executions (succession).
    Broadcast should go to 3 active executions (not all 6).
    """
    # Setup: Create project with multiple jobs and executions
    job1 = AgentJob(
        job_id="job-1",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Task 1",
        job_type="analyzer",
        status="active"
    )
    exec1_old = AgentExecution(
        agent_id="exec1-old",
        job_id=job1.job_id,
        tenant_key="tenant-abc",
        agent_type="analyzer",
        instance_number=1,
        status="complete"
    )
    exec1_new = AgentExecution(
        agent_id="exec1-new",
        job_id=job1.job_id,
        tenant_key="tenant-abc",
        agent_type="analyzer",
        instance_number=2,
        status="working"  # Active
    )

    job2 = AgentJob(
        job_id="job-2",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Task 2",
        job_type="implementer",
        status="active"
    )
    exec2_active = AgentExecution(
        agent_id="exec2-active",
        job_id=job2.job_id,
        tenant_key="tenant-abc",
        agent_type="implementer",
        instance_number=1,
        status="working"  # Active
    )

    job3 = AgentJob(
        job_id="job-3",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Task 3",
        job_type="tester",
        status="active"
    )
    exec3_active = AgentExecution(
        agent_id="exec3-active",
        job_id=job3.job_id,
        tenant_key="tenant-abc",
        agent_type="tester",
        instance_number=1,
        status="working"  # Active
    )

    db_session.add_all([job1, job2, job3, exec1_old, exec1_new, exec2_active, exec3_active])
    await db_session.commit()

    # Act: Broadcast to all agents in project
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    result = await service.broadcast_to_project(
        project_id="project-123",
        content="Project-wide announcement",
        from_agent="orchestrator",
        tenant_key="tenant-abc"
    )

    # Assert: Only 3 active executions received (not all 4)
    assert result["success"] is True
    assert result["count"] == 3  # Only active executions


@pytest.mark.asyncio
async def test_multi_tenant_isolation_messaging(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    Messages respect multi-tenant isolation.

    Scenario: Two tenants with similar agent_type.
    Message to tenant-a should NOT be received by tenant-b.
    """
    # Create projects for two tenants
    project_a = Project(
        id="project-a",
        tenant_key="tenant-a",
        name="Project A",
        description="Tenant A project",
        mission="Task A",
        status="active"
    )
    project_b = Project(
        id="project-b",
        tenant_key="tenant-b",
        name="Project B",
        description="Tenant B project",
        mission="Task B",
        status="active"
    )
    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Setup: Create executions for two tenants
    job_tenant_a = AgentJob(
        job_id="job-tenant-a",
        tenant_key="tenant-a",
        project_id="project-a",
        mission="Task A",
        job_type="orchestrator",
        status="active"
    )
    exec_tenant_a = AgentExecution(
        agent_id="exec-a",
        job_id=job_tenant_a.job_id,
        tenant_key="tenant-a",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )

    job_tenant_b = AgentJob(
        job_id="job-tenant-b",
        tenant_key="tenant-b",
        project_id="project-b",
        mission="Task B",
        job_type="orchestrator",
        status="active"
    )
    exec_tenant_b = AgentExecution(
        agent_id="exec-b",
        job_id=job_tenant_b.job_id,
        tenant_key="tenant-b",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )

    db_session.add_all([job_tenant_a, job_tenant_b, exec_tenant_a, exec_tenant_b])
    await db_session.commit()

    # Act: Send message to tenant-a only
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    await service.send_message(
        to_agents=["exec-a"],
        content="Tenant A message",
        project_id="project-a",
        from_agent="system",
        tenant_key="tenant-a"
    )

    # Assert: Only tenant-a receives message
    messages_a = await service.receive_messages(
        agent_id="exec-a",
        tenant_key="tenant-a"
    )
    messages_b = await service.receive_messages(
        agent_id="exec-b",
        tenant_key="tenant-b"
    )

    assert messages_a["count"] == 1  # Received
    assert messages_b["count"] == 0  # Did NOT receive


@pytest.mark.asyncio
async def test_message_acknowledgment_by_agent_id(db_session, db_manager, tenant_manager, test_project_0366b_msg):
    """
    Message acknowledgment uses agent_id (not job_id).

    Scenario: Agent acknowledges message using its agent_id.
    """
    # Setup: Create execution and message
    job = AgentJob(
        job_id="job-ack",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id="agent-ack",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )
    db_session.add(execution)
    await db_session.commit()

    # Send message
    service = MessageService(db_manager, tenant_manager, test_session=db_session)
    send_result = await service.send_message(
        to_agents=["agent-ack"],
        content="Task assignment",
        project_id="project-123",
        from_agent="system",
        tenant_key="tenant-abc"
    )

    message_id = send_result["message_id"]

    # Act: Acknowledge message using agent_id
    ack_result = await service.acknowledge_message(
        message_id=message_id,
        agent_id="agent-ack",  # Uses agent_id (not job_id)
        tenant_key="tenant-abc"
    )

    # Assert: Message acknowledged
    assert ack_result["success"] is True
    assert ack_result["acknowledged"] is True
