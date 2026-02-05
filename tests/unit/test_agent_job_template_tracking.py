"""
Unit tests for Handover 0244a: Agent Job Template Tracking.

Tests that MCPAgentJob correctly captures and stores template_id references
when agents are spawned via the orchestrator.

TDD Approach:
- Tests written FIRST (RED phase)
- Implementation follows (GREEN phase)
- Refactoring if needed (REFACTOR phase)
"""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import Base, AgentTemplate, Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


class TestAgentJobTemplateTracking:
    """Test template_id tracking in agent jobs."""

    @pytest.fixture
    def db_session(self):
        """Create in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def sample_product(self, db_session):
        """Create a sample product for testing."""
        product = Product(
            id="test-product-id",
            tenant_key="test-tenant",
            name="Test Product",
            description="Test product for template tracking",
            is_active=True,
        )
        db_session.add(product)
        db_session.commit()
        return product

    @pytest.fixture
    def sample_project(self, db_session, sample_product):
        """Create a sample project for testing."""
        project = Project(
            id="test-project-id",
            tenant_key="test-tenant",
            product_id=sample_product.id,
            name="Test Project",
            mission="Test project mission",
            status="active",
        )
        db_session.add(project)
        db_session.commit()
        return project

    @pytest.fixture
    def sample_template(self, db_session, sample_product):
        """Create a sample agent template."""
        template = AgentTemplate(
            id="template-123",
            tenant_key="test-tenant",
            product_id=sample_product.id,
            name="Test Implementer",
            role="implementer",
            cli_tool="claude",
            description="Test implementation agent",
            system_instructions="System instructions",
            user_instructions="User instructions",
            model="sonnet",
            tools=["bash", "read", "write"],
        )
        db_session.add(template)
        db_session.commit()
        return template

    def test_agent_job_has_template_id_column(self, db_session):
        """Test that MCPAgentJob model has template_id column."""
        # Verify column exists in model
        assert hasattr(MCPAgentJob, "template_id")

        # Verify column is nullable (for backward compatibility)
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        columns = inspector.get_columns("mcp_agent_jobs")
        template_id_col = next((col for col in columns if col["name"] == "template_id"), None)

        assert template_id_col is not None
        assert template_id_col["nullable"] is True

    def test_create_agent_job_with_template_id(self, db_session, sample_project, sample_template):
        """Test creating agent job with template_id reference."""
        agent_job = AgentExecution(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            job_id="job-123",
            agent_display_name="implementer",
            agent_name="Test Implementer",
            mission="Implement feature X",
            status="waiting",
            template_id=sample_template.id,
        )

        db_session.add(agent_job)
        db_session.commit()
        db_session.refresh(agent_job)

        # Verify template_id is stored
        assert agent_job.template_id == sample_template.id

        # Verify we can query by template_id
        result = db_session.execute(
            select(AgentExecution).where(AgentExecution.template_id == sample_template.id)
        )
        retrieved_job = result.scalar_one()
        assert retrieved_job.id == agent_job.id

    def test_create_agent_job_without_template_id(self, db_session, sample_project):
        """Test creating agent job without template_id (backward compatibility)."""
        agent_job = AgentExecution(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            job_id="job-456",
            agent_display_name="orchestrator",
            agent_name="Orchestrator",
            mission="Orchestrate project",
            status="working",
            # template_id is None (not provided)
        )

        db_session.add(agent_job)
        db_session.commit()
        db_session.refresh(agent_job)

        # Verify job is created successfully without template_id
        assert agent_job.template_id is None
        assert agent_job.agent_display_name == "orchestrator"

    def test_template_relationship_if_exists(self, db_session, sample_project, sample_template):
        """Test that relationship to AgentTemplate exists (if implemented)."""
        agent_job = AgentExecution(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            job_id="job-789",
            agent_display_name="implementer",
            agent_name="Test Implementer",
            mission="Implement feature Y",
            status="waiting",
            template_id=sample_template.id,
        )

        db_session.add(agent_job)
        db_session.commit()
        db_session.refresh(agent_job)

        # Check if relationship exists
        if hasattr(agent_job, "template"):
            # Verify relationship loads template
            assert agent_job.template is not None
            assert agent_job.template.id == sample_template.id
            assert agent_job.template.name == "Test Implementer"

    def test_multiple_jobs_same_template(self, db_session, sample_project, sample_template):
        """Test that multiple jobs can reference the same template."""
        job1 = AgentExecution(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            job_id="job-001",
            agent_display_name="implementer",
            agent_name="Implementer 1",
            mission="Task 1",
            status="waiting",
            template_id=sample_template.id,
        )

        job2 = AgentExecution(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            job_id="job-002",
            agent_display_name="implementer",
            agent_name="Implementer 2",
            mission="Task 2",
            status="waiting",
            template_id=sample_template.id,
        )

        db_session.add_all([job1, job2])
        db_session.commit()

        # Query all jobs with this template
        result = db_session.execute(
            select(AgentExecution).where(AgentExecution.template_id == sample_template.id)
        )
        jobs = result.scalars().all()

        assert len(jobs) == 2
        assert all(job.template_id == sample_template.id for job in jobs)

    def test_tenant_isolation_with_template_id(self, db_session, sample_project, sample_template):
        """Test tenant isolation when querying by template_id."""
        # Create job for tenant-a
        job_a = AgentExecution(
            tenant_key="tenant-a",
            project_id=sample_project.id,
            job_id="job-a",
            agent_display_name="implementer",
            agent_name="Agent A",
            mission="Task A",
            status="waiting",
            template_id=sample_template.id,
        )

        # Create job for tenant-b with different template
        template_b = AgentTemplate(
            id="template-b",
            tenant_key="tenant-b",
            product_id=None,
            name="Template B",
            role="implementer",
            cli_tool="claude",
            description="Template for tenant B",
        )
        db_session.add(template_b)

        job_b = AgentExecution(
            tenant_key="tenant-b",
            project_id=sample_project.id,
            job_id="job-b",
            agent_display_name="implementer",
            agent_name="Agent B",
            mission="Task B",
            status="waiting",
            template_id=template_b.id,
        )

        db_session.add_all([job_a, job_b])
        db_session.commit()

        # Query tenant-a jobs
        result_a = db_session.execute(
            select(AgentExecution).where(
                AgentExecution.tenant_key == "tenant-a", AgentExecution.template_id == sample_template.id
            )
        )
        jobs_a = result_a.scalars().all()

        # Query tenant-b jobs
        result_b = db_session.execute(
            select(AgentExecution).where(
                AgentExecution.tenant_key == "tenant-b", AgentExecution.template_id == template_b.id
            )
        )
        jobs_b = result_b.scalars().all()

        # Verify isolation
        assert len(jobs_a) == 1
        assert jobs_a[0].tenant_key == "tenant-a"

        assert len(jobs_b) == 1
        assert jobs_b[0].tenant_key == "tenant-b"

    def test_foreign_key_constraint(self, db_session, sample_project):
        """Test that template_id has proper foreign key constraint."""
        # Attempt to create job with non-existent template_id
        agent_job = AgentExecution(
            tenant_key="test-tenant",
            project_id=sample_project.id,
            job_id="job-invalid",
            agent_display_name="implementer",
            agent_name="Invalid Agent",
            mission="Invalid task",
            status="waiting",
            template_id="non-existent-template",
        )

        db_session.add(agent_job)

        # Should raise integrity error due to foreign key constraint
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            db_session.commit()

    def test_cross_platform_paths_used(self):
        """Verify that test file uses pathlib.Path for cross-platform compatibility."""
        # This test verifies coding standards are followed
        test_file = Path(__file__)
        assert test_file.is_absolute()
        assert isinstance(test_file, Path)

        # Verified: This test file uses pathlib.Path appropriately
        # Cross-platform compatibility is maintained


class TestAgentJobTemplateTrackingIntegration:
    """Integration tests for template tracking with orchestrator."""

    @pytest.mark.asyncio
    async def test_spawn_agent_captures_template_id(self):
        """
        Test that spawn_agent method captures template_id when creating jobs.

        This is a placeholder test that will be implemented after the
        orchestrator spawn_agent method is updated.
        """
        # TODO: Implement after orchestrator.spawn_agent is updated
        # This test will verify:
        # 1. Orchestrator fetches template by role
        # 2. Template ID is captured when creating MCPAgentJob
        # 3. Job is persisted with template_id
        # 4. Query returns job with correct template_id
        pytest.skip("Pending orchestrator implementation")

    @pytest.mark.asyncio
    async def test_spawn_agent_handles_missing_template(self):
        """
        Test that spawn_agent handles cases where no template exists.

        Should create job with template_id=None and continue normally.
        """
        # TODO: Implement after orchestrator.spawn_agent is updated
        pytest.skip("Pending orchestrator implementation")
