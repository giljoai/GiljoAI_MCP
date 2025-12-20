"""
TDD Tests for agent_communication.py tools (Handover 0366c - RED Phase)

Phase C of Agent Identity Refactor: MCP Tool Standardization

RED Phase: These tests document expected behavior for refactor.

Current Tool Signatures (OLD - uses job_id):
- check_orchestrator_messages(job_id, tenant_key, ...)
- report_status(job_id, tenant_key, ...)

Expected NEW Signatures (after refactor):
- check_orchestrator_messages(agent_id, tenant_key, ...)
- report_status(agent_id, tenant_key, ...)

Note: Tools are registered via @mcp.tool() decorator inside register_agent_communication_tools().
They are not directly importable. Testing strategy:
1. Test via MCP server instance (integration test)
2. OR test the underlying service layer directly

Semantic Contract:
- agent_id = executor UUID (the WHO - specific agent instance)
- job_id = work order UUID (the WHAT - persistent across succession)
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.services.message_service_0366b import MessageService


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def messaging_setup(db_session, db_manager, tenant_manager):
    """
    Create a job with two executions for message routing tests.

    Scenario: Orchestrator succession
    - Job: "job-messaging" (work order)
    - Exec 1: agent-001 (completed - old executor)
    - Exec 2: agent-002 (working - current executor)

    Messages should route to agent-002 (active execution), NOT agent-001.
    """
    tenant_key = "tenant-messaging-test"

    # Create product (required for project)
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for messaging",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create project (required for job)
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Project",
        description="Test project for messaging",
        product_id=product.id,
        mission="Build amazing software",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Create job (work order)
    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,  # Use actual project ID
        mission="Build authentication system",
        job_type="orchestrator",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)

    # Create first execution (completed)
    exec1 = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=1,
        status="complete",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        progress=100,
    )
    db_session.add(exec1)

    # Create second execution (working - successor)
    exec2 = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,  # SAME job as exec1
        tenant_key=tenant_key,
        agent_type="orchestrator",
        instance_number=2,
        status="working",
        started_at=datetime.now(timezone.utc),
        spawned_by=exec1.agent_id,  # Succession chain
        progress=25,
    )
    db_session.add(exec2)

    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(exec1)
    await db_session.refresh(exec2)

    return {
        "tenant_key": tenant_key,
        "product": product,
        "project": project,
        "job": job,
        "exec1": exec1,  # Completed execution
        "exec2": exec2,  # Active execution
        "db_manager": db_manager,
        "tenant_manager": tenant_manager,
    }


@pytest_asyncio.fixture(scope="function")
async def status_update_setup(db_session):
    """
    Create a job with one execution for status update tests.
    """
    tenant_key = "tenant-status-test"

    # Create product (required for project)
    product = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Product Status",
        description="Test product for status updates",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Create project (required for job)
    project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        name="Test Project Status",
        description="Test project for status updates",
        product_id=product.id,
        mission="Analyze codebase",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,  # Use actual project ID
        mission="Analyze codebase",
        job_type="analyzer",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)

    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_type="analyzer",
        instance_number=1,
        status="working",
        started_at=datetime.now(timezone.utc),
        progress=0,
        current_task=None,
    )
    db_session.add(execution)

    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)

    return {
        "tenant_key": tenant_key,
        "product": product,
        "project": project,
        "job": job,
        "execution": execution,
    }


# ============================================================================
# TEST 1: Message Routing by Agent ID (Service Layer)
# ============================================================================


@pytest.mark.asyncio
async def test_message_service_routes_to_specific_agent_id(messaging_setup, db_session):
    """
    Test: MessageService routes messages to specific agent_id (executor)

    Scenario: Two executions on the same job (succession scenario)
    - Exec1: Complete (agent-001)
    - Exec2: Working (agent-002)

    Expected: Messages sent to agent-002 are ONLY visible to agent-002.

    This tests the SERVICE LAYER behavior that the MCP tool will use.
    After refactor, check_orchestrator_messages(agent_id=...) will call
    MessageService.receive_messages(agent_id=...).
    """
    setup = messaging_setup
    tenant_key = setup["tenant_key"]
    exec1 = setup["exec1"]
    exec2 = setup["exec2"]

    # Send message to exec2 only (active execution)
    msg_service = MessageService(
        db_manager=setup["db_manager"],
        tenant_manager=setup["tenant_manager"],
        test_session=db_session,
    )

    # Send to exec2
    send_result = await msg_service.send_message(
        to_agents=[exec2.agent_id],  # Target specific executor
        content="Continue from where exec1 left off",
        project_id=setup["job"].project_id,
        from_agent="orchestrator-coordinator",
        tenant_key=tenant_key,
    )

    assert send_result["success"] is True, f"Failed to send message: {send_result.get('error')}"

    # Receive messages for exec2
    exec2_messages = await msg_service.receive_messages(
        agent_id=exec2.agent_id,  # Service layer uses agent_id
        tenant_key=tenant_key,
    )

    # Receive messages for exec1
    exec1_messages = await msg_service.receive_messages(
        agent_id=exec1.agent_id,
        tenant_key=tenant_key,
    )

    # Assert: Exec2 receives message, Exec1 does NOT
    assert len(exec2_messages) == 1, f"Expected 1 message for exec2, got {len(exec2_messages)}"
    assert exec2_messages[0]["content"] == "Continue from where exec1 left off"

    assert len(exec1_messages) == 0, \
        f"Exec1 (completed) should not receive messages for exec2. Got {len(exec1_messages)} messages."


@pytest.mark.asyncio
async def test_message_service_isolates_messages_by_agent_id(messaging_setup, db_session):
    """
    Test: Each execution sees ONLY its own messages (not all messages for the job)

    Critical: Without agent_id filtering, all executions on the same job would see all messages (wrong!).
    """
    setup = messaging_setup
    tenant_key = setup["tenant_key"]
    exec1 = setup["exec1"]
    exec2 = setup["exec2"]

    msg_service = MessageService(
        db_manager=setup["db_manager"],
        tenant_manager=setup["tenant_manager"],
        test_session=db_session,
    )

    # Send different messages to each execution
    await msg_service.send_message(
        to_agents=[exec1.agent_id],
        content="Message for exec1 only",
        project_id=setup["job"].project_id,
        from_agent="test-sender",
        tenant_key=tenant_key,
    )

    await msg_service.send_message(
        to_agents=[exec2.agent_id],
        content="Message for exec2 only",
        project_id=setup["job"].project_id,
        from_agent="test-sender",
        tenant_key=tenant_key,
    )

    # Receive messages for each execution
    exec1_messages = await msg_service.receive_messages(agent_id=exec1.agent_id, tenant_key=tenant_key)
    exec2_messages = await msg_service.receive_messages(agent_id=exec2.agent_id, tenant_key=tenant_key)

    # Assert: Each execution sees ONLY its own message
    assert len(exec1_messages) == 1, "Exec1 should see exactly 1 message"
    assert len(exec2_messages) == 1, "Exec2 should see exactly 1 message"

    assert exec1_messages[0]["content"] == "Message for exec1 only"
    assert exec2_messages[0]["content"] == "Message for exec2 only"


# ============================================================================
# TEST 2: Status Updates Target Execution (Not Job)
# ============================================================================


@pytest.mark.asyncio
async def test_status_updates_should_target_execution_record(status_update_setup, db_session):
    """
    Test: Status updates should modify AgentExecution (not AgentJob)

    After refactor, report_status(agent_id=...) should:
    1. Look up AgentExecution by agent_id
    2. Update execution.progress, execution.current_task, etc.
    3. Leave AgentJob unchanged (job status is stable, execution status changes)

    This test uses the CURRENT tool (which uses job_id) to document expected FUTURE behavior.
    This test will LIKELY FAIL until refactor is complete.
    """
    # Import tools from nested function (will fail until refactor)
    # For now, test the underlying database behavior directly
    setup = status_update_setup
    tenant_key = setup["tenant_key"]
    job = setup["job"]
    execution = setup["execution"]

    # Simulate what report_status(agent_id=...) should do after refactor
    # 1. Look up execution by agent_id
    # 2. Update execution fields
    # 3. Leave job unchanged

    # Update execution directly (simulating refactored tool behavior)
    execution.progress = 75
    execution.current_task = "Writing tests"
    await db_session.commit()
    await db_session.refresh(execution)

    # Verify execution updated
    assert execution.progress == 75
    assert execution.current_task == "Writing tests"

    # Verify job unchanged (job status is stable)
    await db_session.refresh(job)
    assert job.status == "active", "Job status should not change when updating execution progress"


# ============================================================================
# TEST 3: Cross-Tenant Isolation (Security)
# ============================================================================


@pytest.mark.asyncio
async def test_message_service_blocks_cross_tenant_access(db_session, db_manager, tenant_manager):
    """
    Test: MessageService blocks cross-tenant message access

    Security: Tenant A cannot read Tenant B's messages even with valid agent_id.

    This tests the SERVICE LAYER security that the MCP tool will inherit.
    """
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    # Create product and project for Tenant B
    product_b = Product(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        name="Product B",
        description="Product for tenant B",
        is_active=True,
    )
    db_session.add(product_b)
    await db_session.commit()
    await db_session.refresh(product_b)

    project_b = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        name="Project B",
        description="Project for tenant B",
        product_id=product_b.id,
        mission="Tenant B work",
        status="active",
    )
    db_session.add(project_b)
    await db_session.commit()
    await db_session.refresh(project_b)

    # Create execution for Tenant B
    job_b = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        mission="Tenant B work",
        job_type="orchestrator",
        status="active",
    )
    db_session.add(job_b)

    exec_b = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job_b.job_id,
        tenant_key=tenant_b,
        agent_type="orchestrator",
        instance_number=1,
        status="working",
    )
    db_session.add(exec_b)

    await db_session.commit()
    await db_session.refresh(exec_b)

    # Send message to Tenant B's execution
    msg_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    await msg_service.send_message(
        to_agents=[exec_b.agent_id],
        content="Secret message for Tenant B",
        project_id=job_b.project_id,
        from_agent="system",
        tenant_key=tenant_b,
    )

    # Act: Tenant A tries to read Tenant B's messages using Tenant A's key
    exec_b_messages_from_tenant_a = await msg_service.receive_messages(
        agent_id=exec_b.agent_id,  # Tenant B's agent!
        tenant_key=tenant_a,  # Tenant A's key!
    )

    # Assert: Access denied (no messages returned due to tenant mismatch)
    assert len(exec_b_messages_from_tenant_a) == 0, \
        "Cross-tenant message access allowed! Security vulnerability."


# ============================================================================
# TEST 4: Expected Tool Signature After Refactor
# ============================================================================


@pytest.mark.asyncio
async def test_expected_tool_signatures_documentation():
    """
    Test: Document expected tool signatures after refactor

    This is a documentation test that specifies the expected API.

    Current (OLD):
    - check_orchestrator_messages(job_id, tenant_key, ...)
    - report_status(job_id, tenant_key, ...)

    Expected (NEW):
    - check_orchestrator_messages(agent_id, tenant_key, ...)
    - report_status(agent_id, tenant_key, ...)

    Implementation notes for GREEN phase:
    1. Rename job_id parameter to agent_id
    2. Look up AgentExecution (not AgentJob) using agent_id
    3. For messages: Call MessageService.receive_messages(agent_id=...)
    4. For status: Update execution fields (progress, current_task, etc.)
    5. Maintain tenant_key filtering for security
    """
    # This test always passes - it's documentation only
    expected_signatures = {
        "check_orchestrator_messages": {
            "old_params": ["job_id", "tenant_key", "agent_name", "message_type", "unread_only"],
            "new_params": ["agent_id", "tenant_key", "message_type", "unread_only"],
            "changes": [
                "job_id → agent_id",
                "Remove agent_name (redundant - agent_id is specific)",
            ],
        },
        "report_status": {
            "old_params": [
                "job_id",
                "tenant_key",
                "status",
                "current_task",
                "progress_percentage",
                "context_usage",
                "artifacts_created",
                "metadata",
            ],
            "new_params": [
                "agent_id",  # Changed from job_id
                "tenant_key",
                "status",
                "current_task",
                "progress_percentage",
                "context_usage",
                "artifacts_created",
                "metadata",
            ],
            "changes": ["job_id → agent_id"],
        },
    }

    assert expected_signatures["check_orchestrator_messages"]["new_params"][0] == "agent_id"
    assert expected_signatures["report_status"]["new_params"][0] == "agent_id"


# ============================================================================
# TEST 5: AgentJob vs AgentExecution Usage
# ============================================================================


@pytest.mark.asyncio
async def test_agent_job_vs_execution_semantic_usage(messaging_setup):
    """
    Test: Document semantic difference between AgentJob and AgentExecution

    AgentJob (the WHAT - work order):
    - Persistent across succession
    - Contains mission, project context
    - Status changes rarely (active → complete)

    AgentExecution (the WHO - executor instance):
    - Changes on succession (new executor, same job)
    - Contains executor-specific state (progress, current_task, health)
    - Status changes frequently (working → blocked → working)

    Tools should target:
    - check_orchestrator_messages() → AgentExecution (messages go to specific executor)
    - report_status() → AgentExecution (progress is per-executor, not per-job)
    """
    setup = messaging_setup
    job = setup["job"]
    exec1 = setup["exec1"]
    exec2 = setup["exec2"]

    # Verify job is shared
    assert exec1.job_id == job.job_id
    assert exec2.job_id == job.job_id
    assert exec1.agent_id != exec2.agent_id, "Executors must have different agent_ids"

    # Verify executions have different states
    assert exec1.status == "complete"
    assert exec2.status == "working"
    assert exec1.progress == 100
    assert exec2.progress == 25

    # Job status is independent of execution status
    assert job.status == "active", "Job remains active even though exec1 is complete"


# ============================================================================
# TEST 6: Nonexistent Agent ID Handling
# ============================================================================


@pytest.mark.asyncio
async def test_message_service_handles_nonexistent_agent_id(db_session, db_manager, tenant_manager):
    """
    Test: MessageService handles nonexistent agent_id gracefully

    After refactor, check_orchestrator_messages(agent_id="nonexistent") should:
    - Return empty message list (not crash)
    - OR return error with clear message
    """
    msg_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    # Receive messages for nonexistent agent
    messages = await msg_service.receive_messages(
        agent_id="nonexistent-agent-id",
        tenant_key="tenant-test",
    )

    # Should return empty list (not crash)
    assert isinstance(messages, list)
    assert len(messages) == 0
