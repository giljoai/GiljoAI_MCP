"""
Tests for orchestrator deduplication on project reactivation (Handover 0485 - Bug B)
Updated 0730d: Exception-based error handling patterns (no success wrappers).
Updated 0731c: Typed returns - launch_project returns ProjectLaunchResult.

Verifies that when a project is reactivated, the system does NOT create duplicate
orchestrators if one already exists in a non-decommissioned state (complete, blocked, etc.).
"""

import random
from contextlib import asynccontextmanager
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentExecution, AgentJob, Product, Project, User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.schemas.service_responses import ProjectLaunchResult
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
        is_active=True,
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


def create_project_service(db_session: AsyncSession, tenant_key: str) -> ProjectService:
    """Helper to create ProjectService with proper mocking."""

    @asynccontextmanager
    async def mock_get_session():
        yield db_session

    db_manager = MagicMock()
    db_manager.get_session_async = mock_get_session

    tenant_manager = TenantManager()
    tenant_manager.set_current_tenant(tenant_key)

    return ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


class TestOrchestratorDeduplication:
    """Test orchestrator deduplication when reactivating projects"""

    @pytest.mark.asyncio
    async def test_ensure_fixture_finds_completed_orchestrator(self, db_session, test_user):
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
            mission="Test mission for orchestrator dedup",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
            series_number=random.randint(1, 999999),
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
            status="complete",  # COMPLETE status - should be found
            progress=100,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        project_service = create_project_service(db_session, test_user.tenant_key)

        # Call _ensure_orchestrator_fixture
        result = await project_service._lifecycle._ensure_orchestrator_fixture(
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
    async def test_ensure_fixture_finds_blocked_orchestrator(self, db_session, test_user):
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
            mission="Test mission for blocked orchestrator",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
            series_number=random.randint(1, 999999),
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
            status="blocked",  # BLOCKED status - should be found
            progress=50,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        project_service = create_project_service(db_session, test_user.tenant_key)

        # Call _ensure_orchestrator_fixture
        result = await project_service._lifecycle._ensure_orchestrator_fixture(
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
    async def test_ensure_fixture_creates_when_decommissioned(self, db_session, test_user):
        """
        Test that _ensure_orchestrator_fixture() DOES create a new orchestrator
        when the existing one has "decommissioned" status (Fix 1).
        Handover 0491: failed -> decommissioned (only decommissioned is excluded by filter).
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
            description="Test project for decommissioned orchestrator",
            mission="Test mission for decommissioned orchestrator",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="inactive",
            series_number=random.randint(1, 999999),
        )
        db_session.add(project)
        await db_session.flush()

        # Create orchestrator with "decommissioned" status
        decommissioned_job_id = str(uuid4())
        decommissioned_agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=decommissioned_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=decommissioned_agent_id,
            job_id=decommissioned_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="decommissioned",  # DECOMMISSIONED status - should NOT be found
            progress=25,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        project_service = create_project_service(db_session, test_user.tenant_key)

        # Call _ensure_orchestrator_fixture
        result = await project_service._lifecycle._ensure_orchestrator_fixture(
            session=db_session,
            project=project,
            websocket_manager=None,
        )

        # ASSERT: Should return dict with new orchestrator IDs
        assert result is not None
        assert "job_id" in result
        assert "agent_id" in result
        assert result["job_id"] != decommissioned_job_id  # NEW orchestrator

        # Commit to ensure the new orchestrator is persisted
        await db_session.commit()

        # ASSERT: Should now have TWO orchestrators (decommissioned + new)
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
        assert "decommissioned" in statuses
        assert "waiting" in statuses  # New orchestrator should be "waiting"

    @pytest.mark.asyncio
    async def test_launch_project_skips_existing_orchestrator(self, db_session, test_user):
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
            mission="Test mission for launch dedup",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="active",
            series_number=random.randint(1, 999999),
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
            status="working",  # WORKING status - should be found
            progress=75,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ProjectService
        project_service = create_project_service(db_session, test_user.tenant_key)

        # Call launch_project
        # 0731c: launch_project returns ProjectLaunchResult typed model
        result = await project_service.launch_project(
            project_id=project.id,
            user_id=str(test_user.id),
            launch_config=None,
            websocket_manager=None,
        )

        # ASSERT: Should return typed ProjectLaunchResult and reuse existing orchestrator
        assert isinstance(result, ProjectLaunchResult)
        assert result.orchestrator_job_id == existing_job_id

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
