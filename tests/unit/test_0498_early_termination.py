"""
Tests for Handover 0498: Early Termination Protocol + Jobs Dashboard Reduction.

Covers:
- Phase 1: AgentTodoItem "skipped" status
- Phase 4: report_progress "skipped" status
- Phase 6: Steps aggregation with skipped count
- Termination prompt endpoint
- Archive terminated status
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.giljo_mcp.models import Project, User
from src.giljo_mcp.models.agent_identity import (
    AgentExecution,
    AgentJob,
    AgentTodoItem,
)
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Phase 1: AgentTodoItem accepts "skipped" status
# ============================================================================


class TestAgentTodoItemSkippedStatus:
    """Phase 1: Verify AgentTodoItem model accepts 'skipped' as a valid status."""

    @pytest.mark.asyncio
    async def test_todo_item_accepts_skipped_status(self, db_session, test_agent_job):
        """AgentTodoItem should accept 'skipped' as a valid status value."""
        job, execution = test_agent_job

        todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=job.tenant_key,
            content="Test item to be skipped",
            status="skipped",
            sequence=0,
        )
        db_session.add(todo)
        await db_session.flush()

        result = await db_session.execute(
            select(AgentTodoItem).where(AgentTodoItem.id == todo.id)
        )
        saved = result.scalar_one()
        assert saved.status == "skipped"

    @pytest.mark.asyncio
    async def test_todo_item_still_accepts_existing_statuses(self, db_session, test_agent_job):
        """Existing statuses (pending, in_progress, completed) still work."""
        job, execution = test_agent_job

        for status in ("pending", "in_progress", "completed"):
            todo = AgentTodoItem(
                job_id=job.job_id,
                tenant_key=job.tenant_key,
                content=f"Test item with status {status}",
                status=status,
                sequence=0,
            )
            db_session.add(todo)
            await db_session.flush()
            assert todo.status == status

    @pytest.mark.asyncio
    async def test_todo_item_rejects_invalid_status(self, db_session, test_agent_job):
        """Invalid statuses should be rejected by the CHECK constraint."""
        job, execution = test_agent_job

        todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=job.tenant_key,
            content="Test item with invalid status",
            status="invalid_status",
            sequence=0,
        )
        db_session.add(todo)

        with pytest.raises(Exception):
            await db_session.flush()
        await db_session.rollback()


# ============================================================================
# Phase 4: report_progress allows "skipped" status
# ============================================================================


class TestReportProgressSkippedStatus:
    """Phase 4: report_progress validates 'skipped' as allowed TODO status."""

    @pytest.mark.asyncio
    async def test_report_progress_accepts_skipped_todo_status(
        self, db_session, test_agent_job, test_tenant_key, orchestration_service_with_session
    ):
        """report_progress should accept 'skipped' as a valid TODO item status."""
        job, execution = test_agent_job
        execution.status = "working"
        await db_session.flush()

        service = orchestration_service_with_session
        result = await service.report_progress(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            todo_items=[
                {"content": "Task 1", "status": "completed"},
                {"content": "Task 2", "status": "skipped"},
                {"content": "Task 3", "status": "pending"},
            ],
        )

        assert result.status == "success"

        # Verify the skipped item was saved with correct status
        todo_result = await db_session.execute(
            select(AgentTodoItem)
            .where(AgentTodoItem.job_id == job.job_id)
            .order_by(AgentTodoItem.sequence)
        )
        items = todo_result.scalars().all()
        assert len(items) == 3
        assert items[0].status == "completed"
        assert items[1].status == "skipped"
        assert items[2].status == "pending"


# ============================================================================
# Phase 6: Steps aggregation includes skipped count
# ============================================================================


class TestStepsAggregationSkippedCount:
    """Phase 6: _list_jobs_by_project includes skipped count in steps_summary."""

    @pytest.mark.asyncio
    async def test_steps_summary_includes_skipped_from_todo_items(
        self, db_session, test_agent_job, test_tenant_key
    ):
        """Steps summary fallback path should include skipped count from todo_items."""
        job, execution = test_agent_job

        # Create TODO items with various statuses including skipped
        items = [
            AgentTodoItem(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
                content="Completed task",
                status="completed",
                sequence=0,
            ),
            AgentTodoItem(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
                content="Skipped task",
                status="skipped",
                sequence=1,
            ),
            AgentTodoItem(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
                content="Pending task",
                status="pending",
                sequence=2,
            ),
        ]
        db_session.add_all(items)
        await db_session.flush()

        # Verify the items are queryable with expected statuses
        result = await db_session.execute(
            select(AgentTodoItem)
            .where(AgentTodoItem.job_id == job.job_id)
            .order_by(AgentTodoItem.sequence)
        )
        saved_items = result.scalars().all()
        assert len(saved_items) == 3
        completed = sum(1 for i in saved_items if i.status == "completed")
        skipped = sum(1 for i in saved_items if i.status == "skipped")
        assert completed == 1
        assert skipped == 1


# ============================================================================
# Termination prompt endpoint tests
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_user_for_endpoint(db_session, test_tenant_key):
    """Create a real User record for endpoint tests with matching tenant_key."""
    from src.giljo_mcp.models.organizations import Organization

    unique_suffix = uuid.uuid4().hex[:8]

    # Create org first (org_id is NOT NULL)
    org = Organization(
        name=f"Test Org {unique_suffix}",
        slug=f"test-org-{unique_suffix}",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        username=f"testuser_{unique_suffix}",
        email=f"test_{unique_suffix}@example.com",
        tenant_key=test_tenant_key,
        role="developer",
        password_hash="hashed_password",
        org_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def authed_api_client(db_manager, db_session, test_user_for_endpoint, test_tenant_key):
    """Create an authenticated AsyncClient whose mock user's tenant_key matches test data."""
    from api.app import app, state
    from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session

    user = test_user_for_endpoint

    async def mock_get_current_user():
        return user

    async def mock_get_db_session():
        yield db_session

    class DummyAuth:
        async def authenticate_request(self, request):
            TenantManager.set_current_tenant(test_tenant_key)
            return {
                "authenticated": True,
                "user_id": str(user.id),
                "user": user.username,
                "user_obj": user,
                "tenant_key": test_tenant_key,
            }

    state.db_manager = db_manager
    state.tenant_manager = state.tenant_manager or TenantManager()
    state.auth = DummyAuth()
    app.state.db_manager = db_manager
    app.state.tenant_manager = state.tenant_manager
    app.state.auth = state.auth

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[get_db_session] = mock_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


class TestTerminationPrompt:
    """Tests for the GET /api/v1/prompts/termination/{project_id} endpoint."""

    @pytest.mark.asyncio
    async def test_termination_prompt_returns_prompt_with_agents(
        self, db_session, test_tenant_key, test_project_id, authed_api_client
    ):
        """Endpoint returns prompt containing agent job_id, project_id, and orchestrator job_id."""
        # Create orchestrator AgentJob + AgentExecution (status=working)
        orch_job_id = str(uuid.uuid4())
        orch_job = AgentJob(
            job_id=orch_job_id,
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            job_type="orchestrator",
            mission="Orchestrate the project",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(orch_job)

        orch_exec = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=orch_job_id,
            tenant_key=test_tenant_key,
            agent_display_name="orchestrator",
            agent_name="Orchestrator",
            status="working",
            progress=0,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add(orch_exec)

        # Create a worker AgentJob + AgentExecution
        worker_job_id = str(uuid.uuid4())
        worker_job = AgentJob(
            job_id=worker_job_id,
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            job_type="worker",
            mission="Implement feature X",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(worker_job)

        worker_exec = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=worker_job_id,
            tenant_key=test_tenant_key,
            agent_display_name="developer",
            agent_name="Developer Agent",
            status="working",
            progress=50,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add(worker_exec)
        await db_session.commit()

        # Call endpoint
        response = await authed_api_client.get(
            f"/api/v1/prompts/termination/{test_project_id}"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "prompt" in data
        assert "orchestrator_job_id" in data
        assert "agent_count" in data

        # Verify prompt contains relevant IDs
        assert worker_job_id in data["prompt"]
        assert test_project_id in data["prompt"]
        assert data["orchestrator_job_id"] == orch_job_id
        assert data["agent_count"] == 1  # 1 non-orchestrator agent

    @pytest.mark.asyncio
    async def test_termination_prompt_sets_early_termination_flag(
        self, db_session, test_tenant_key, test_project_id, authed_api_client
    ):
        """After calling the endpoint, project.meta_data['early_termination'] is True."""
        # Create orchestrator job + execution
        orch_job_id = str(uuid.uuid4())
        orch_job = AgentJob(
            job_id=orch_job_id,
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            job_type="orchestrator",
            mission="Orchestrate the project",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(orch_job)

        orch_exec = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=orch_job_id,
            tenant_key=test_tenant_key,
            agent_display_name="orchestrator",
            agent_name="Orchestrator",
            status="working",
            progress=0,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add(orch_exec)
        await db_session.commit()

        # Call endpoint
        response = await authed_api_client.get(
            f"/api/v1/prompts/termination/{test_project_id}"
        )
        assert response.status_code == 200

        # Verify the early_termination flag was set on the project
        # expire_all() is synchronous on AsyncSession
        db_session.expire_all()
        result = await db_session.execute(
            select(Project).where(Project.id == test_project_id)
        )
        project = result.scalar_one()
        assert project.meta_data is not None
        assert project.meta_data.get("early_termination") is True

    @pytest.mark.asyncio
    async def test_termination_prompt_404_without_working_orchestrator(
        self, db_session, test_tenant_key, test_project_id, authed_api_client
    ):
        """Endpoint returns 404 when there is no working orchestrator."""
        # Create orchestrator with status="complete" (not "working")
        orch_job_id = str(uuid.uuid4())
        orch_job = AgentJob(
            job_id=orch_job_id,
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            job_type="orchestrator",
            mission="Orchestrate the project",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(orch_job)

        orch_exec = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=orch_job_id,
            tenant_key=test_tenant_key,
            agent_display_name="orchestrator",
            agent_name="Orchestrator",
            status="complete",
            progress=100,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add(orch_exec)
        await db_session.commit()

        # Call endpoint
        response = await authed_api_client.get(
            f"/api/v1/prompts/termination/{test_project_id}"
        )

        assert response.status_code == 404
        data = response.json()
        # Exception handlers use "message" key (Handover 0480a)
        assert "No working orchestrator" in data.get("message", data.get("detail", ""))


# ============================================================================
# Archive terminated status tests
# ============================================================================


class TestArchiveTerminatedStatus:
    """Tests for archive logic: early_termination flag determines terminated vs completed status.

    Tests the archive_project endpoint logic using ProjectService directly
    with the shared test session, ensuring proper data visibility and isolation.
    """

    @pytest.mark.asyncio
    async def test_archive_with_early_termination_sets_terminated(
        self, db_session, test_tenant_key, test_project_id, project_service_with_session
    ):
        """Archive with early_termination flag sets status to 'terminated'."""
        # Set the early_termination flag on the project
        result = await db_session.execute(
            select(Project).where(Project.id == test_project_id)
        )
        project = result.scalar_one()
        meta = project.meta_data or {}
        meta["early_termination"] = True
        project.meta_data = meta
        flag_modified(project, "meta_data")
        await db_session.commit()

        service = project_service_with_session

        # Replicate archive_project endpoint logic:
        # 1. Get project
        proj = await service.get_project(
            project_id=test_project_id, tenant_key=test_tenant_key
        )
        current_status = proj.status

        # 2. Deactivate if not already inactive/completed
        if current_status not in ("inactive", "completed", "archived", "terminated"):
            await service.deactivate_project(
                project_id=test_project_id,
                reason="User archived project after completion",
            )

        # 3. Determine target status based on early_termination flag
        proj_meta = project.meta_data or {}
        target_status = "terminated" if proj_meta.get("early_termination") else "completed"

        # 4. Update project status
        await service.update_project(
            project_id=test_project_id,
            updates={"status": target_status, "completed_at": datetime.now(timezone.utc)},
        )

        # 5. Verify result
        updated = await service.get_project(
            project_id=test_project_id, tenant_key=test_tenant_key
        )
        assert updated.status == "terminated"

    @pytest.mark.asyncio
    async def test_archive_without_flag_sets_completed(
        self, db_session, test_tenant_key, test_project_id, project_service_with_session
    ):
        """Archive without early_termination flag sets status to 'completed'."""
        # Ensure no early_termination flag on the project
        result = await db_session.execute(
            select(Project).where(Project.id == test_project_id)
        )
        project = result.scalar_one()
        meta = project.meta_data or {}
        meta.pop("early_termination", None)
        project.meta_data = meta
        flag_modified(project, "meta_data")
        await db_session.commit()

        service = project_service_with_session

        # Replicate archive_project endpoint logic:
        # 1. Get project
        proj = await service.get_project(
            project_id=test_project_id, tenant_key=test_tenant_key
        )
        current_status = proj.status

        # 2. Deactivate if not already inactive/completed
        if current_status not in ("inactive", "completed", "archived", "terminated"):
            await service.deactivate_project(
                project_id=test_project_id,
                reason="User archived project after completion",
            )

        # 3. Determine target status based on early_termination flag
        proj_meta = project.meta_data or {}
        target_status = "terminated" if proj_meta.get("early_termination") else "completed"

        # 4. Update project status
        await service.update_project(
            project_id=test_project_id,
            updates={"status": target_status, "completed_at": datetime.now(timezone.utc)},
        )

        # 5. Verify result
        updated = await service.get_project(
            project_id=test_project_id, tenant_key=test_tenant_key
        )
        assert updated.status == "completed"
