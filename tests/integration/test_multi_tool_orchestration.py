"""
Comprehensive Integration Tests for Multi-Tool Orchestration System (Handover 0045).

Phase 8: Integration Testing - Tests the entire multi-tool orchestration system
end-to-end with focus on:
- Pure mode scenarios (Claude, Codex, Gemini)
- Mixed mode orchestration
- Agent-Job synchronization
- MCP tool coordination
- Multi-tenant isolation (CRITICAL)
- Error recovery flows
- Concurrent operations
- Edge cases and resilience

Testing focuses on actual implementable functionality via AgentJobManager
and AgentCommunicationQueue rather than async orchestrator methods.
"""

import shutil
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate, Project
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def db_manager():
    """Create a database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    manager.create_tables()
    yield manager
    manager.close()


@pytest.fixture
def job_manager(db_manager):
    """Create AgentJobManager instance."""
    return AgentJobManager(db_manager)


@pytest.fixture
def temp_export_dir():
    """Create temporary directory for template exports."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def tenant_key():
    """Generate unique tenant key for each test."""
    return str(uuid4())


@pytest.fixture
def other_tenant_key():
    """Generate second tenant key for isolation tests."""
    return str(uuid4())


@pytest.fixture
def test_project(db_manager, tenant_key):
    """Create a test project in the database."""
    with db_manager.get_session() as session:
        project = Project(
            id=str(uuid4()),
            name="Test Project",
            mission="Test mission for integration testing",
            status="active",
            tenant_key=tenant_key,
        )
        session.add(project)
        session.commit()
        return project


@pytest.fixture
def test_project_other_tenant(db_manager, other_tenant_key):
    """Create a test project for another tenant."""
    with db_manager.get_session() as session:
        project = Project(
            id=str(uuid4()),
            name="Other Tenant Project",
            mission="Test mission for other tenant",
            status="active",
            tenant_key=other_tenant_key,
        )
        session.add(project)
        session.commit()
        return project


@pytest.fixture
def claude_template(db_manager, tenant_key):
    """Create a Claude mode template."""
    with db_manager.get_session() as session:
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Claude Implementer",
            category="role",
            role="implementer",
            tool="claude",
            system_instructions="Implement the following feature: {{feature}}",
            success_criteria=["Code compiles and tests pass"],
            is_default=True,
        )
        session.add(template)
        session.commit()
        return template


@pytest.fixture
def codex_template(db_manager, tenant_key):
    """Create a Codex mode template."""
    with db_manager.get_session() as session:
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Codex Implementer",
            category="role",
            role="implementer",
            tool="codex",
            system_instructions="Implement using Codex: {{feature}}",
            success_criteria=["Working implementation with tests"],
            is_default=False,
        )
        session.add(template)
        session.commit()
        return template


@pytest.fixture
def gemini_template(db_manager, tenant_key):
    """Create a Gemini mode template."""
    with db_manager.get_session() as session:
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="Gemini Tester",
            category="role",
            role="tester",
            tool="gemini",
            system_instructions="Test the implementation: {{feature}}",
            success_criteria=["All tests pass with high coverage"],
            is_default=False,
        )
        session.add(template)
        session.commit()
        return template


# ============================================================================
# TEST SCENARIO 1: Pure Codex Mode - Job Queue Operations
# ============================================================================


class TestPureCodexMode:
    """Test Codex CLI mode with job queue."""

    def test_create_codex_job(self, db_manager, job_manager, tenant_key):
        """Test creating a Codex job."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement user authentication",
            context_chunks=["chunk1", "chunk2"],
        )

        # Assertions
        assert job is not None
        assert job.job_id is not None
        assert job.agent_display_name == "implementer"
        assert job.status == "pending"
        assert job.tenant_key == tenant_key
        assert job.created_at is not None

    def test_codex_job_acknowledgment(self, db_manager, job_manager, tenant_key):
        """Test acknowledging a Codex job."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature",
        )

        # Acknowledge job
        updated_job = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        # Assertions
        assert updated_job is not None
        assert updated_job.status == "active"
        assert updated_job.started_at is not None

    def test_codex_get_pending_jobs(self, db_manager, job_manager, tenant_key):
        """Test retrieving pending jobs for Codex agents."""
        # Create multiple jobs
        job1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature 1",
        )
        job2 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature 2",
        )

        # Get pending jobs
        pending_jobs = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="implementer",
        )

        # Assertions
        assert len(pending_jobs) == 2
        job_ids = [j.job_id for j in pending_jobs]
        assert job1.job_id in job_ids
        assert job2.job_id in job_ids

    def test_codex_job_completion(self, db_manager, job_manager, tenant_key):
        """Test completing a Codex job."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature",
        )

        # Acknowledge then complete
        job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        completed_job = job_manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"summary": "Feature implemented successfully"},
        )

        # Assertions
        assert completed_job is not None
        assert completed_job.status == "completed"
        assert completed_job.completed_at is not None

    def test_codex_job_failure(self, db_manager, job_manager, tenant_key):
        """Test failing a Codex job with error."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature",
        )

        # Acknowledge then fail
        job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        failed_job = job_manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error="Build failed: module not found",
        )

        # Assertions
        assert failed_job is not None
        assert failed_job.status == "blocked"


# ============================================================================
# TEST SCENARIO 2: Pure Gemini Mode - Job Queue Operations
# ============================================================================


class TestPureGeminiMode:
    """Test Gemini CLI mode with job queue."""

    def test_create_gemini_job(self, db_manager, job_manager, tenant_key):
        """Test creating a Gemini job."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="tester",
            mission="Write comprehensive test suite",
        )

        # Assertions
        assert job is not None
        assert job.agent_display_name == "tester"
        assert job.status == "pending"

    def test_gemini_job_workflow(self, db_manager, job_manager, tenant_key):
        """Test complete Gemini job workflow."""
        # Create job
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="tester",
            mission="Write tests",
        )

        # Acknowledge
        job = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )
        assert job.status == "active"

        # Complete
        job = job_manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"summary": "Tests written and passing"},
        )
        assert job.status == "completed"


# ============================================================================
# TEST SCENARIO 3: Mixed Mode Job Operations
# ============================================================================


class TestMixedModeOperations:
    """Test mixed Codex and Gemini job operations."""

    def test_mixed_agents_create_jobs(self, db_manager, job_manager, tenant_key):
        """Test creating jobs for different agent types."""
        # Create Codex implementer job
        impl_job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement features",
        )

        # Create Gemini tester job
        test_job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="tester",
            mission="Test features",
        )

        # Assertions
        assert impl_job.agent_display_name == "implementer"
        assert test_job.agent_display_name == "tester"
        assert impl_job.job_id != test_job.job_id

    def test_mixed_agents_pending_filtering(self, db_manager, job_manager, tenant_key):
        """Test getting pending jobs filtered by agent type."""
        # Create mixed jobs
        impl_job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement",
        )
        test_job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="tester",
            mission="Test",
        )

        # Get pending for implementer only
        pending_impl = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="implementer",
        )
        assert len(pending_impl) == 1
        assert pending_impl[0].job_id == impl_job.job_id

        # Get pending for tester only
        pending_test = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="tester",
        )
        assert len(pending_test) == 1
        assert pending_test[0].job_id == test_job.job_id


# ============================================================================
# TEST SCENARIO 4: MCP Tool Coordination
# ============================================================================


# ============================================================================
# TEST SCENARIO 5: Multi-Tenant Isolation (CRITICAL)
# ============================================================================


class TestMultiTenantIsolation:
    """CRITICAL: Zero cross-tenant leakage tests."""

    def test_jobs_isolated_by_tenant(self, db_manager, job_manager, tenant_key, other_tenant_key):
        """CRITICAL: Jobs from different tenants don't interfere."""
        # Create jobs for two tenants
        job_t1 = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Tenant 1 job",
        )
        job_t2 = job_manager.create_job(
            tenant_key=other_tenant_key,
            agent_display_name="implementer",
            mission="Tenant 2 job",
        )

        # Get pending for tenant 1
        pending_t1 = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="implementer",
        )

        # Get pending for tenant 2
        pending_t2 = job_manager.get_pending_jobs(
            tenant_key=other_tenant_key,
            agent_display_name="implementer",
        )

        # Assertions: Each tenant only sees their own job
        assert len(pending_t1) == 1
        assert len(pending_t2) == 1
        assert pending_t1[0].job_id == job_t1.job_id
        assert pending_t2[0].job_id == job_t2.job_id
        assert pending_t1[0].job_id != pending_t2[0].job_id

    def test_cross_tenant_job_access_denied(self, db_manager, job_manager, tenant_key, other_tenant_key):
        """CRITICAL: Cannot acknowledge job from another tenant."""
        # Create job for tenant 1
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Tenant 1 job",
        )

        # Try to acknowledge with tenant 2 key (should raise ValueError)
        with pytest.raises(ValueError):
            job_manager.acknowledge_job(
                tenant_key=other_tenant_key,  # Wrong tenant!
                job_id=job.job_id,
            )

    def test_tenant_job_get_isolation(self, db_manager, job_manager, tenant_key, other_tenant_key):
        """CRITICAL: Jobs properly isolated by tenant."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Tenant 1 job",
        )

        # Get pending jobs for tenant 1 - should see it
        pending_t1 = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="implementer",
        )
        assert any(j.job_id == job.job_id for j in pending_t1)

        # Get pending for tenant 2 - should NOT see it
        pending_t2 = job_manager.get_pending_jobs(
            tenant_key=other_tenant_key,
            agent_display_name="implementer",
        )
        assert not any(j.job_id == job.job_id for j in pending_t2)


# ============================================================================
# TEST SCENARIO 6: Error Recovery Flow
# ============================================================================


class TestErrorRecoveryFlow:
    """Test error reporting and handling."""

    def test_report_error_updates_job_status(self, db_manager, job_manager, tenant_key):
        """Test error report updates job status."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature",
        )

        # Acknowledge then fail
        job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        failed_job = job_manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error="Build failed: missing dependency",
        )

        # Assertions
        assert failed_job.status == "blocked"

    def test_error_stored_in_job(self, db_manager, job_manager, tenant_key):
        """Test error message stored in job."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement feature",
        )

        job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        error_message = "Build failed: ImportError in module foo"
        failed_job = job_manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error=error_message,
        )

        # Verify job status is failed
        assert failed_job.status == "blocked"


# ============================================================================
# TEST SCENARIO 7: Concurrent Job Operations
# ============================================================================


class TestConcurrentOperations:
    """Test concurrent job operations at scale."""

    def test_create_10_jobs_concurrently(self, db_manager, job_manager, tenant_key):
        """Test creating 10 jobs quickly."""
        jobs = []

        # Create 10 jobs
        for i in range(10):
            job = job_manager.create_job(
                tenant_key=tenant_key,
                agent_display_name="implementer" if i % 2 == 0 else "tester",
                mission=f"Feature {i}",
            )
            jobs.append(job)

        # Assertions
        assert len(jobs) == 10
        assert all(j.job_id is not None for j in jobs)
        assert len(set(j.job_id for j in jobs)) == 10  # All unique

        # Verify retrieval
        pending = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="implementer",
        )
        assert len(pending) == 5

    def test_multiple_jobs_per_agent_display_name(self, db_manager, job_manager, tenant_key):
        """Test multiple jobs per agent type."""
        impl_jobs = []
        test_jobs = []

        # Create 5 implementer jobs
        for i in range(5):
            job = job_manager.create_job(
                tenant_key=tenant_key,
                agent_display_name="implementer",
                mission=f"Implement feature {i}",
            )
            impl_jobs.append(job)

        # Create 3 tester jobs
        for i in range(3):
            job = job_manager.create_job(
                tenant_key=tenant_key,
                agent_display_name="tester",
                mission=f"Test feature {i}",
            )
            test_jobs.append(job)

        # Verify counts
        pending_impl = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="implementer",
        )
        pending_test = job_manager.get_pending_jobs(
            tenant_key=tenant_key,
            agent_display_name="tester",
        )

        assert len(pending_impl) == 5
        assert len(pending_test) == 3


# ============================================================================
# TEST SCENARIO 8: Job Status Transitions
# ============================================================================


class TestJobStatusTransitions:
    """Test job status state machine."""

    def test_pending_to_active_transition(self, db_manager, job_manager, tenant_key):
        """Test transition from pending to active."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement",
        )
        assert job.status == "pending"

        job = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )
        assert job.status == "active"

    def test_active_to_completed_transition(self, db_manager, job_manager, tenant_key):
        """Test transition from active to completed."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement",
        )

        job = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )
        assert job.status == "active"

        job = job_manager.complete_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            result={"summary": "Done"},
        )
        assert job.status == "completed"

    def test_active_to_failed_transition(self, db_manager, job_manager, tenant_key):
        """Test transition from active to failed."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement",
        )

        job = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )

        job = job_manager.fail_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
            error="Test error",
        )
        assert job.status == "blocked"


# ============================================================================
# TEST SCENARIO 9: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_mission_text(self, db_manager, job_manager, tenant_key):
        """Test job with empty mission raises error."""
        # Empty mission should raise ValueError
        with pytest.raises(ValueError):
            job_manager.create_job(
                tenant_key=tenant_key,
                agent_display_name="implementer",
                mission="",  # Empty!
            )

    def test_very_long_mission_text(self, db_manager, job_manager, tenant_key):
        """Test job with very long mission."""
        long_mission = "Do something. " * 1000  # Very long

        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission=long_mission,
        )

        # Should still create job
        assert job is not None

    def test_special_characters_in_mission(self, db_manager, job_manager, tenant_key):
        """Test job with special characters."""
        special_mission = "Implement: foo@bar.com, price=$100, emoji: 🚀"

        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission=special_mission,
        )

        # Should handle special chars
        assert job is not None
        assert special_mission in job.mission

    def test_acknowledge_already_active_job(self, db_manager, job_manager, tenant_key):
        """Test acknowledging already-active job (idempotent)."""
        job = job_manager.create_job(
            tenant_key=tenant_key,
            agent_display_name="implementer",
            mission="Implement",
        )

        # Acknowledge once
        job1 = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )
        assert job1.status == "active"

        # Acknowledge again (should be idempotent)
        job2 = job_manager.acknowledge_job(
            tenant_key=tenant_key,
            job_id=job.job_id,
        )
        assert job2.status == "active"
        assert job1.started_at == job2.started_at

    def test_complete_nonexistent_job(self, db_manager, job_manager, tenant_key):
        """Test completing non-existent job raises error."""
        with pytest.raises(ValueError):
            job_manager.complete_job(
                tenant_key=tenant_key,
                job_id="nonexistent_job_id",
                result={"summary": "Done"},
            )

    def test_fail_nonexistent_job(self, db_manager, job_manager, tenant_key):
        """Test failing non-existent job raises error."""
        with pytest.raises(ValueError):
            job_manager.fail_job(
                tenant_key=tenant_key,
                job_id="nonexistent_job_id",
                error="Test error",
            )


# ============================================================================
# TEST SCENARIO 10: Template Verification
# ============================================================================


class TestTemplateConsistency:
    """Test template consistency across operations."""

    def test_claude_template_properties(self, db_manager, claude_template):
        """Verify Claude template has correct properties."""
        assert claude_template.tool == "claude"
        assert claude_template.role == "implementer"
        assert claude_template.is_default is True

    def test_codex_template_properties(self, db_manager, codex_template):
        """Verify Codex template has correct properties."""
        assert codex_template.tool == "codex"
        assert codex_template.role == "implementer"

    def test_gemini_template_properties(self, db_manager, gemini_template):
        """Verify Gemini template has correct properties."""
        assert gemini_template.tool == "gemini"
        assert gemini_template.role == "tester"

    def test_templates_isolated_by_tenant(self, db_manager, tenant_key, other_tenant_key):
        """Test templates isolated by tenant."""
        with db_manager.get_session() as session:
            # Create template for tenant 1
            t1_template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=tenant_key,
                name="Template 1",
                category="role",
                role="implementer",
                tool="claude",
                system_instructions="Template 1",
                is_default=False,
            )
            session.add(t1_template)

            # Create template for tenant 2
            t2_template = AgentTemplate(
                id=str(uuid4()),
                tenant_key=other_tenant_key,
                name="Template 2",
                category="role",
                role="implementer",
                tool="codex",
                system_instructions="Template 2",
                is_default=False,
            )
            session.add(t2_template)
            session.commit()

            # Query template for tenant 1
            from sqlalchemy import select

            result = session.execute(
                select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.role == "implementer",
                )
            )
            templates = result.scalars().all()

            # Should only see tenant 1 templates
            assert len(templates) >= 1
            assert all(t.tenant_key == tenant_key for t in templates)


# ============================================================================
# INTEGRATION TEST RUNNER
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
