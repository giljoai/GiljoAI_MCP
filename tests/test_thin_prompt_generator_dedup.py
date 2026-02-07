"""
Tests for ThinClientPromptGenerator orchestrator deduplication (Handover 0485 - Bug B)

Verifies that ThinClientPromptGenerator.generate() uses the same expanded
status filter as _ensure_orchestrator_fixture().
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import AgentExecution, AgentJob, Product, Project, User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.tenant import TenantManager
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


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


class TestThinPromptGeneratorDeduplication:
    """Test ThinClientPromptGenerator orchestrator deduplication"""

    @pytest.mark.asyncio
    async def test_generate_finds_completed_orchestrator(self, db_session, test_user):
        """
        Test that ThinClientPromptGenerator.generate() finds a "complete" orchestrator
        and reuses it (Fix 2).
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
            description="Test project for thin prompt generator dedup",
            product_id=product.id,
            tenant_key=test_user.tenant_key,
            status="active",
        )
        db_session.add(project)
        await db_session.flush()

        # Create orchestrator with "complete" status
        complete_job_id = str(uuid4())
        complete_agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=complete_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=complete_agent_id,
            job_id=complete_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="complete",  # COMPLETE status - should be found
            progress=100,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ThinClientPromptGenerator
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock

        @asynccontextmanager
        async def mock_get_session():
            yield db_session

        db_manager = MagicMock()
        db_manager.get_session_async = mock_get_session

        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=test_user.tenant_key,
        )

        # Call generate()
        result = await generator.generate(
            project_id=str(project.id),
            user_id=str(test_user.id),
            tool="universal",
        )

        # ASSERT: Should reuse existing orchestrator
        assert result["orchestrator_id"] == complete_job_id

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
        assert executions[0].job_id == complete_job_id

    @pytest.mark.asyncio
    async def test_generate_finds_blocked_orchestrator(self, db_session, test_user):
        """
        Test that ThinClientPromptGenerator.generate() finds a "blocked" orchestrator
        and reuses it (Fix 2).
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
            status="active",
        )
        db_session.add(project)
        await db_session.flush()

        # Create orchestrator with "blocked" status
        blocked_job_id = str(uuid4())
        blocked_agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=blocked_job_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=blocked_agent_id,
            job_id=blocked_job_id,
            tenant_key=test_user.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="blocked",  # BLOCKED status - should be found
            progress=50,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ThinClientPromptGenerator
        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=test_user.tenant_key,
        )

        # Call generate()
        result = await generator.generate(
            project_id=str(project.id),
            user_id=str(test_user.id),
            tool="universal",
        )

        # ASSERT: Should reuse existing orchestrator
        assert result["orchestrator_id"] == blocked_job_id

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
    async def test_generate_creates_when_failed(self, db_session, test_user):
        """
        Test that ThinClientPromptGenerator.generate() creates a NEW orchestrator
        when the existing one has "failed" status (Fix 2).
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
            status="active",
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
            status="failed",  # FAILED status - should NOT be found
            progress=25,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Create ThinClientPromptGenerator
        generator = ThinClientPromptGenerator(
            db=db_session,
            tenant_key=test_user.tenant_key,
        )

        # Call generate()
        result = await generator.generate(
            project_id=str(project.id),
            user_id=str(test_user.id),
            tool="universal",
        )

        # ASSERT: Should create NEW orchestrator (not reuse failed one)
        assert result["orchestrator_id"] != failed_job_id

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

        # Verify statuses
        statuses = {ex.status for ex in executions}
        assert "failed" in statuses
        assert "waiting" in statuses  # New orchestrator should be "waiting"
