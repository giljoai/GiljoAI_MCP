"""
TDD tests for Handover 0431: Orchestrator Closeout Verification Protocol.

Purpose:
Test that write_360_memory() enforces pre-closeout verification,
blocking project closeouts when agents have unfinished work.

Verification Checks:
1. All agents have status == 'complete'
2. All agents have messages_waiting_count == 0
3. All agents have all AgentTodoItem.status == 'completed'
4. Orchestrator's own todos are completed

Test Coverage:
- CLOSEOUT_BLOCKED when agent still working
- CLOSEOUT_BLOCKED when agent has unread messages
- CLOSEOUT_BLOCKED when agent has incomplete todos
- CLOSEOUT_BLOCKED when orchestrator has incomplete todos
- Success when all checks pass
- Multiple blockers reported correctly
- Tenant isolation in verification
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.tools.write_360_memory import write_360_memory


# ========================================================================
# Test Fixtures
# ========================================================================


@pytest_asyncio.fixture
async def tenant_key():
    """Generate test tenant key."""
    return f"tk_test_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def other_tenant_key():
    """Generate separate tenant key for isolation tests."""
    return f"tk_other_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_product(db_session, tenant_key):
    """Create test product with empty JSONB product_memory."""
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product 0431",
        description="Test product for closeout verification",
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, tenant_key, test_product):
    """Create test project linked to product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Project 0431",
        description="Test project for closeout verification",
        product_id=test_product.id,
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_orchestrator_job(db_session, tenant_key, test_project):
    """Create orchestrator job for author tracking."""
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        job_type="orchestrator",
        mission="Orchestrator mission for closeout test",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_orchestrator_execution(db_session, tenant_key, test_orchestrator_job):
    """Create orchestrator execution for author tracking."""
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=test_orchestrator_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        agent_name="Test Orchestrator",
        status="working",
        progress=90,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        health_status="healthy",
        tool_type="universal",
        context_used=5000,
        context_budget=150000,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(execution)
    return execution


async def create_test_agent(
    db_session,
    project_id: str,
    tenant_key: str,
    status: str = "complete",
    messages_waiting_count: int = 0,
    agent_name: str = None,
    job_type: str = "implementer",
):
    """Helper to create test agent with job and execution."""
    job_id = str(uuid4())
    agent_id = str(uuid4())
    agent_name = agent_name or f"test-agent-{agent_id[:8]}"

    # Create AgentJob
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type=job_type,
        mission=f"Mission for {agent_name}",
        status="active" if status != "complete" else "completed",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job)

    # Create AgentExecution
    execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name=job_type,
        agent_name=agent_name,
        status=status,
        progress=100 if status == "complete" else 50,
        messages_sent_count=0,
        messages_waiting_count=messages_waiting_count,
        messages_read_count=0,
        health_status="healthy",
        tool_type="universal",
        context_used=5000,
        context_budget=150000,
    )
    db_session.add(execution)

    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)

    return job, execution


# ========================================================================
# Test Cases - CLOSEOUT_BLOCKED Scenarios
# ========================================================================


class TestCloseoutVerificationBlocking:
    """Tests for CLOSEOUT_BLOCKED scenarios."""

    @pytest.mark.asyncio
    async def test_blocks_when_agent_still_working(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should block closeout if any agent is still working."""
        # Create agent with status='working'
        job, execution = await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="working",
            tenant_key=tenant_key,
            agent_name="implementer-auth",
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for closeout",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert result["error"] == "CLOSEOUT_BLOCKED"
        assert "blockers" in result
        assert len(result["blockers"]) >= 1

        # Find the blocker for our agent
        blocker = next((b for b in result["blockers"] if b.get("agent_name") == "implementer-auth"), None)
        assert blocker is not None
        assert blocker["issue_type"] == "still_working"
        assert blocker["status"] == "working"

    @pytest.mark.asyncio
    async def test_blocks_when_unread_messages(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should block closeout if any agent has unread messages."""
        # Create completed agent with unread messages
        job, execution = await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            messages_waiting_count=3,
            tenant_key=tenant_key,
            agent_name="tester-unit",
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for closeout",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert result["error"] == "CLOSEOUT_BLOCKED"
        assert "blockers" in result

        blocker = next((b for b in result["blockers"] if b.get("agent_name") == "tester-unit"), None)
        assert blocker is not None
        assert blocker["issue_type"] == "unread_messages"
        assert blocker["messages_waiting"] == 3

    @pytest.mark.asyncio
    async def test_blocks_when_incomplete_todos(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should block closeout if any agent has incomplete todos."""
        # Create completed agent
        job, execution = await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            tenant_key=tenant_key,
            agent_name="reviewer-code",
        )

        # Add incomplete todos
        pending_todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=tenant_key,
            content="Review auth module",
            status="pending",
            sequence=0,
        )
        in_progress_todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=tenant_key,
            content="Check test coverage",
            status="in_progress",
            sequence=1,
        )
        db_session.add(pending_todo)
        db_session.add(in_progress_todo)
        await db_session.commit()

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for closeout",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert result["error"] == "CLOSEOUT_BLOCKED"
        assert "blockers" in result

        blocker = next((b for b in result["blockers"] if b.get("agent_name") == "reviewer-code"), None)
        assert blocker is not None
        assert blocker["issue_type"] == "incomplete_todos"
        assert blocker["pending_count"] == 1
        assert blocker["in_progress_count"] == 1
        assert "Review auth module" in blocker["incomplete_items"]
        assert "Check test coverage" in blocker["incomplete_items"]

    @pytest.mark.asyncio
    async def test_blocks_when_orchestrator_has_incomplete_todos(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should block closeout if orchestrator has incomplete todos."""
        # Add incomplete todo for orchestrator
        orch_todo = AgentTodoItem(
            job_id=test_orchestrator_job.job_id,
            tenant_key=tenant_key,
            content="Final verification",
            status="in_progress",
            sequence=0,
        )
        db_session.add(orch_todo)
        await db_session.commit()

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for closeout",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert result["error"] == "CLOSEOUT_BLOCKED"
        assert "blockers" in result

        blocker = next((b for b in result["blockers"] if b.get("issue_type") == "orchestrator_incomplete_todos"), None)
        assert blocker is not None
        assert "Final verification" in blocker["incomplete_items"]

    @pytest.mark.asyncio
    async def test_multiple_blockers_reported(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should report multiple blockers when multiple issues exist."""
        # Agent 1: Still working
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="working",
            tenant_key=tenant_key,
            agent_name="agent-1-working",
        )

        # Agent 2: Unread messages
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            messages_waiting_count=2,
            tenant_key=tenant_key,
            agent_name="agent-2-messages",
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for closeout",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert result["error"] == "CLOSEOUT_BLOCKED"
        assert len(result["blockers"]) >= 2

        # Verify summary includes counts
        assert "summary" in result
        assert result["summary"]["still_working"] >= 1
        assert result["summary"]["agents_with_unread"] >= 1


# ========================================================================
# Test Cases - Success Scenarios
# ========================================================================


class TestCloseoutVerificationSuccess:
    """Tests for successful closeout scenarios."""

    @pytest.mark.asyncio
    async def test_succeeds_when_all_ready(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should succeed when all agents complete, no unread, all todos done."""
        # Create completed agent with no issues
        job, execution = await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            messages_waiting_count=0,
            tenant_key=tenant_key,
            agent_name="implementer-complete",
        )

        # Add completed todo for agent
        agent_todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=tenant_key,
            content="Finished task",
            status="completed",
            sequence=0,
        )
        db_session.add(agent_todo)

        # Add completed todo for orchestrator
        orch_todo = AgentTodoItem(
            job_id=test_orchestrator_job.job_id,
            tenant_key=tenant_key,
            content="Orchestrator task",
            status="completed",
            sequence=0,
        )
        db_session.add(orch_todo)
        await db_session.commit()

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for successful closeout",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is True
        assert "entry_id" in result
        assert "verified" in result
        assert result["verified"]["all_complete"] is True
        assert result["verified"]["all_messages_read"] is True
        assert result["verified"]["all_todos_done"] is True

    @pytest.mark.asyncio
    async def test_succeeds_with_no_agents(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should succeed when project has no spawned agents (only orchestrator)."""
        # Add completed todo for orchestrator
        orch_todo = AgentTodoItem(
            job_id=test_orchestrator_job.job_id,
            tenant_key=tenant_key,
            content="Orchestrator task",
            status="completed",
            sequence=0,
        )
        db_session.add(orch_todo)
        await db_session.commit()

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary for closeout with no agents",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is True
        assert "entry_id" in result

    @pytest.mark.asyncio
    async def test_includes_verification_summary_on_success(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Success response should include verification summary."""
        # Create 2 completed agents
        for i in range(2):
            await create_test_agent(
                db_session=db_session,
                project_id=test_project.id,
                status="complete",
                messages_waiting_count=0,
                tenant_key=tenant_key,
                agent_name=f"agent-{i}",
            )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is True
        assert "verified" in result
        assert result["verified"]["agents_checked"] >= 2


# ========================================================================
# Test Cases - Edge Cases
# ========================================================================


class TestCloseoutVerificationEdgeCases:
    """Tests for edge cases in closeout verification."""

    @pytest.mark.asyncio
    async def test_skips_decommissioned_agents(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should skip decommissioned agents in verification."""
        # Create decommissioned agent (should be ignored)
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="decommissioned",
            tenant_key=tenant_key,
            agent_name="old-agent",
        )

        # Create completed agent
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            tenant_key=tenant_key,
            agent_name="current-agent",
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        # Should succeed - decommissioned agent doesn't block
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_skips_cancelled_agents(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should skip cancelled agents in verification."""
        # Create cancelled agent (should be ignored)
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="cancelled",
            tenant_key=tenant_key,
            agent_name="cancelled-agent",
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        # Should succeed - cancelled agent doesn't block
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_completed_todos_do_not_block(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Completed todos should not cause blocking."""
        # Create completed agent
        job, execution = await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            tenant_key=tenant_key,
            agent_name="agent-with-done-todos",
        )

        # Add ONLY completed todos
        for i in range(3):
            todo = AgentTodoItem(
                job_id=job.job_id,
                tenant_key=tenant_key,
                content=f"Completed task {i}",
                status="completed",
                sequence=i,
            )
            db_session.add(todo)
        await db_session.commit()

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is True


# ========================================================================
# Test Cases - Tenant Isolation
# ========================================================================


class TestCloseoutVerificationTenantIsolation:
    """Tests for multi-tenant isolation in verification."""

    @pytest.mark.asyncio
    async def test_ignores_other_tenant_agents(
        self,
        db_session,
        db_manager,
        tenant_key,
        other_tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Should not consider agents from other tenants."""
        # Create "problem" agent in OTHER tenant (should be ignored)
        other_project_id = str(uuid4())

        other_product = Product(
            id=str(uuid4()),
            tenant_key=other_tenant_key,
            name="Other Tenant Product",
            is_active=True,
            product_memory={},
        )
        db_session.add(other_product)

        other_project = Project(
            id=other_project_id,
            tenant_key=other_tenant_key,
            name="Other Project",
            description="Other project description",
            product_id=other_product.id,
            mission="Other mission",
            status="active",
        )
        db_session.add(other_project)
        await db_session.commit()

        # Create working agent in other tenant (should be ignored)
        await create_test_agent(
            db_session=db_session,
            project_id=other_project_id,
            status="working",
            tenant_key=other_tenant_key,
            agent_name="other-tenant-agent",
        )

        # Create completed agent in our tenant
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="complete",
            tenant_key=tenant_key,
            agent_name="our-tenant-agent",
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        # Should succeed - other tenant's working agent doesn't affect us
        assert result["success"] is True


# ========================================================================
# Test Cases - Blocked Response Schema
# ========================================================================


class TestCloseoutBlockedResponseSchema:
    """Tests for the CLOSEOUT_BLOCKED response schema."""

    @pytest.mark.asyncio
    async def test_blocked_response_contains_action_required(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Blocked response should contain action_required guidance."""
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="working",
            tenant_key=tenant_key,
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert "action_required" in result
        assert "report_error" in result["action_required"].lower() or "blocked" in result["action_required"].lower()

    @pytest.mark.asyncio
    async def test_blocked_response_contains_message(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Blocked response should contain descriptive message."""
        await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="working",
            tenant_key=tenant_key,
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert "message" in result
        assert "blockers" in result["message"].lower() or "unresolved" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_blocker_contains_job_id(
        self,
        db_session,
        db_manager,
        tenant_key,
        test_project,
        test_product,
        test_orchestrator_job,
        test_orchestrator_execution,
    ):
        """Each blocker should contain job_id for reference."""
        job, execution = await create_test_agent(
            db_session=db_session,
            project_id=test_project.id,
            status="working",
            tenant_key=tenant_key,
        )

        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            author_job_id=test_orchestrator_job.job_id,
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        blocker = result["blockers"][0]
        assert "job_id" in blocker
        assert blocker["job_id"] == job.job_id


# ========================================================================
# Test Cases - Backward Compatibility
# ========================================================================


class TestCloseoutBackwardCompatibility:
    """Tests to ensure no breaking changes to existing functionality."""

    @pytest.mark.asyncio
    async def test_still_validates_required_fields(self, db_session, db_manager, tenant_key, test_project):
        """Should still validate required fields before verification."""
        # Missing summary should still fail with validation error, not CLOSEOUT_BLOCKED
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            db_manager=db_manager,
            session=db_session,
        )

        assert result["success"] is False
        assert result["error"] != "CLOSEOUT_BLOCKED"
        assert "summary is required" in result["error"]

    @pytest.mark.asyncio
    async def test_author_job_id_still_optional_for_basic_write(
        self, db_session, db_manager, tenant_key, test_project, test_product
    ):
        """author_job_id should still be optional."""
        # No author_job_id provided - should still work
        result = await write_360_memory(
            project_id=test_project.id,
            tenant_key=tenant_key,
            summary="Test summary without author",
            key_outcomes=["Outcome 1"],
            decisions_made=["Decision 1"],
            # No author_job_id
            db_manager=db_manager,
            session=db_session,
        )

        # Should succeed since there are no agents to check
        assert result["success"] is True
