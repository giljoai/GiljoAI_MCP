"""
Tests for orchestrator deduplication on project reactivation (Handover 0485 - Bug B)

Verifies that when a project is reactivated, the system does NOT create duplicate
orchestrators if one already exists in a non-failed state (complete, blocked, etc.).
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models import Project, AgentJob, AgentExecution, Product, User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create test user with tenant"""
    unique_suffix = uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()

    # Create org first (0424m: org_id is NOT NULL, tenant_key required)
    org = Organization(
        name=f"Test User Org {unique_suffix}",
        slug=f"test-user-org-{unique_suffix}",
        tenant_key=tenant_key,
        is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        username=f"testuser_{unique_suffix}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=tenant_key,
        role="developer",
        password_hash="hashed_password",
        org_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestOrchestratorDeduplication:
    """Test orchestrator deduplication when reactivating projects"""

    @pytest.mark.asyncio
    async def test_ensure_fixture_finds_completed_orchestrator(
        self, db_session, test_user
    ):
        """
        Test that _ensure_orchestrator_fixture() finds a "complete" orchestrator
        and does NOT create a new one (Fix 1).
        """
        # Create product and project
        product = Product(
            name=f"Test Product {uuid4().hex[:8]}",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        project = Project(
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for orchestrator dedup",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
        )
        db_session.add(project)
        await db_session.flush()

        # Create orchestrator with "complete" status
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="complete",  # COMPLETE status - should be found
            progress=100,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        from unittest.mock import MagicMock
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)

        project_service = ProjectService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Call _ensure_orchestrator_fixture
        result = await project_service._ensure_orchestrator_fixture(
            session=db_session,
            project=project,
            websocket_manager=None,
        )

        # ASSERT: Should return None (no new orchestrator created)
        assert result is None

        # ASSERT: Should still have only ONE orchestrator
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_user.tenant_key,
            )
        )
        exec_result = await db_session.execute(stmt)
        executions = exec_result.scalars().all()

        assert len(executions) == 1
        assert executions[0].status == "complete"
        assert executions[0].job_id == job_id

    @pytest.mark.asyncio
    async def test_ensure_fixture_finds_blocked_orchestrator(
        self, db_session, test_user
    ):
        """
        Test that _ensure_orchestrator_fixture() finds a "blocked" orchestrator
        and does NOT create a new one (Fix 1).
        """
        # Create product and project
        product = Product(
            name=f"Test Product {uuid4().hex[:8]}",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        project = Project(
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for blocked orchestrator",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
        )
        db_session.add(project)
        await db_session.flush()

        # Create orchestrator with "blocked" status
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="blocked",  # BLOCKED status - should be found
            progress=50,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        from unittest.mock import MagicMock
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)

        project_service = ProjectService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Call _ensure_orchestrator_fixture
        result = await project_service._ensure_orchestrator_fixture(
            session=db_session,
            project=project,
            websocket_manager=None,
        )

        # ASSERT: Should return None (no new orchestrator created)
        assert result is None

        # ASSERT: Should still have only ONE orchestrator
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_user.tenant_key,
            )
        )
        exec_result = await db_session.execute(stmt)
        executions = exec_result.scalars().all()

        assert len(executions) == 1
        assert executions[0].status == "blocked"

    @pytest.mark.asyncio
    async def test_ensure_fixture_creates_when_failed(
        self, db_session, test_user
    ):
        """
        Test that _ensure_orchestrator_fixture() DOES create a new orchestrator
        when the existing one has "failed" status (Fix 1).
        """
        # Create product and project
        product = Product(
            name=f"Test Product {uuid4().hex[:8]}",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        project = Project(
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for failed orchestrator",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
        )
        db_session.add(project)
        await db_session.flush()

        # Create orchestrator with "failed" status
        failed_job_id = str(uuid4())
        failed_agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=failed_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=failed_agent_id,
            job_id=failed_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="failed",  # FAILED status - should NOT be found
            progress=25,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        from unittest.mock import MagicMock
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)

        project_service = ProjectService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Call _ensure_orchestrator_fixture
        result = await project_service._ensure_orchestrator_fixture(
            session=db_session,
            project=project,
            websocket_manager=None,
        )

        # ASSERT: Should return dict with new orchestrator IDs
        assert result is not None
        assert "job_id" in result
        assert "agent_id" in result
        assert result["job_id"] != failed_job_id  # NEW orchestrator

        # ASSERT: Should now have TWO orchestrators (failed + new)
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_user.tenant_key,
            )
        )
        exec_result = await db_session.execute(stmt)
        executions = exec_result.scalars().all()

        assert len(executions) == 2

        # Verify instance numbers
        statuses = {ex.status for ex in executions}
        assert "failed" in statuses
        assert "waiting" in statuses  # New orchestrator should be "waiting"

    @pytest.mark.asyncio
    async def test_launch_project_skips_existing_orchestrator(
        self, db_session, test_user
    ):
        """
        Test that launch_project() does NOT create a duplicate orchestrator
        if one already exists for the project (Fix 3).
        """
        # Create product and project
        product = Product(
            name=f"Test Product {uuid4().hex[:8]}",
            tenant_key=test_user.tenant_key,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        project = Project(
            name=f"Test Project {uuid4().hex[:8]}",
            description="Test project for launch dedup",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="active",
        )
        db_session.add(project)
        await db_session.flush()

        # Create existing orchestrator with "working" status
        existing_job_id = str(uuid4())
        existing_agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=existing_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=existing_agent_id,
            job_id=existing_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            instance_number=1,
            status="working",  # WORKING status - should be found
            progress=75,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        from unittest.mock import MagicMock
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(test_user.tenant_key)

        project_service = ProjectService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Call launch_project
        result = await project_service.launch_project(
            project_id=project.id,
            user_id=str(test_user.id),
            launch_config=None,
            websocket_manager=None,
        )

        # ASSERT: Should reuse existing orchestrator (NOT create new one)
        assert result["orchestrator_job_id"] == existing_job_id

        # ASSERT: Should still have only ONE orchestrator
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_user.tenant_key,
            )
        )
        exec_result = await db_session.execute(stmt)
        executions = exec_result.scalars().all()

        assert len(executions) == 1
        assert executions[0].status == "working"
        assert executions[0].job_id == existing_job_id
