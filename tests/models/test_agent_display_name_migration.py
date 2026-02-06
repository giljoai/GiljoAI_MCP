"""
Tests for agent_display_name → agent_display_name migration (Handover 0414b).

RED Phase (TDD): These tests define expected behavior AFTER migration.
Tests will FAIL because agent_display_name doesn't exist yet - agent_display_name is the current field.

Semantic Meaning:
- agent_name = NORTH STAR (template lookup key) - KEEP
- agent_display_name = UI LABEL (what humans see) - NEW NAME
- agent_display_name = OLD ambiguous name - WILL BE RENAMED

Migration Target:
- Database: agent_display_name column → agent_display_name column
- Model: AgentExecution.agent_display_name → AgentExecution.agent_display_name
- Keep: agent_name unchanged (template lookup key)

Expected Failures:
- AttributeError: 'AgentExecution' has no attribute 'agent_display_name'
- OperationalError: column agent_display_name does not exist
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession

# Import models - these tests will FAIL until GREEN phase
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


class TestAgentDisplayNameModelAttribute:
    """Test that AgentExecution model has agent_display_name attribute."""

    @pytest.mark.asyncio
    async def test_agent_execution_has_agent_display_name_attribute(self, db_session: AsyncSession):
        """
        Test that AgentExecution model has agent_display_name attribute.

        EXPECTED FAILURE: AttributeError - 'AgentExecution' object has no attribute 'agent_display_name'
        Reason: Field is currently named 'agent_display_name' in the model.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-display-name-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test migration",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution with NEW field name (will fail)
        execution = AgentExecution(
            agent_id="agent-display-001",
            job_id="job-display-name-001",
            tenant_key="tenant-abc",
            agent_display_name="System Architect",  # NEW FIELD NAME (will fail)            status="waiting"
        )
        db_session.add(execution)
        await db_session.commit()

        # Verify attribute exists
        assert hasattr(execution, "agent_display_name")
        assert execution.agent_display_name == "System Architect"

    @pytest.mark.asyncio
    async def test_agent_execution_does_not_have_agent_display_name_attribute(self, db_session: AsyncSession):
        """
        Test that AgentExecution model does NOT have agent_display_name attribute after migration.

        EXPECTED FAILURE: Test will pass NOW but should FAIL after migration
        Reason: agent_display_name currently exists but should be removed after migration.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-no-type-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test migration",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution
        execution = AgentExecution(
            agent_id="agent-no-type-001",
            job_id="job-no-type-001",
            tenant_key="tenant-abc",
            agent_display_name="Database Expert",  # NEW FIELD NAME            status="waiting"
        )
        db_session.add(execution)
        await db_session.commit()

        # Verify OLD attribute does NOT exist
        assert not hasattr(execution, "agent_display_name"), "agent_display_name should not exist after migration"

    @pytest.mark.asyncio
    async def test_agent_execution_agent_name_still_exists(self, db_session: AsyncSession):
        """
        Test that agent_name (NORTH STAR) is NOT affected by migration.

        This test should PASS both before and after migration.
        agent_name is the template lookup key and must remain unchanged.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-agent-name-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test agent_name preservation",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution with BOTH agent_name (template key) and agent_display_name (UI label)
        execution = AgentExecution(
            agent_id="agent-name-001",
            job_id="job-agent-name-001",
            tenant_key="tenant-abc",
            agent_name="system-architect",  # Template lookup key (KEEP)
            agent_display_name="System Architect",  # UI label (NEW)            status="waiting"
        )
        db_session.add(execution)
        await db_session.commit()

        # Verify BOTH fields exist
        assert hasattr(execution, "agent_name")
        assert hasattr(execution, "agent_display_name")
        assert execution.agent_name == "system-architect"
        assert execution.agent_display_name == "System Architect"


class TestAgentDisplayNameDatabaseColumn:
    """Test that database column is named agent_display_name."""

    @pytest.mark.asyncio
    async def test_database_column_named_agent_display_name(self, db_session: AsyncSession):
        """
        Test that database column is named agent_display_name, not agent_display_name.

        EXPECTED FAILURE: OperationalError - column agent_display_name does not exist
        Reason: Database column is currently named 'agent_display_name'.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-column-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test column name",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution
        execution = AgentExecution(
            agent_id="agent-column-001",
            job_id="job-column-001",
            tenant_key="tenant-abc",
            agent_display_name="TDD Implementor",            status="waiting"
        )
        db_session.add(execution)
        await db_session.commit()

        # Verify database column name via SQLAlchemy inspection
        inspector = inspect(db_session.bind)
        columns = [col["name"] for col in inspector.get_columns("agent_executions")]

        assert "agent_display_name" in columns, "Database should have agent_display_name column"
        assert "agent_display_name" not in columns, "Database should NOT have agent_display_name column after migration"

    @pytest.mark.asyncio
    async def test_agent_display_name_column_not_null_constraint(self, db_session: AsyncSession):
        """
        Test that agent_display_name column has NOT NULL constraint.

        EXPECTED FAILURE: OperationalError or IntegrityError
        Reason: Column doesn't exist yet, so NULL constraint can't be tested.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-not-null-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test NOT NULL",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Try to create execution WITHOUT agent_display_name (should fail)
        execution = AgentExecution(
            agent_id="agent-not-null-001",
            job_id="job-not-null-001",
            tenant_key="tenant-abc",
            # agent_display_name missing - should violate NOT NULL constraint            status="waiting"
        )
        db_session.add(execution)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_display_name_column_max_length(self, db_session: AsyncSession):
        """
        Test that agent_display_name column has VARCHAR(100) constraint (same as agent_display_name).

        EXPECTED FAILURE: Column doesn't exist yet
        Reason: Will fail on column access before constraint can be tested.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-maxlen-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test max length",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution with valid length
        execution = AgentExecution(
            agent_id="agent-maxlen-001",
            job_id="job-maxlen-001",
            tenant_key="tenant-abc",
            agent_display_name="A" * 100,  # Exactly 100 characters (should pass)            status="waiting"
        )
        db_session.add(execution)
        await db_session.commit()

        assert len(execution.agent_display_name) == 100


class TestAgentDisplayNameQueryOperations:
    """Test that queries work with agent_display_name field."""

    @pytest.mark.asyncio
    async def test_filter_by_agent_display_name(self, db_session: AsyncSession):
        """
        Test that we can filter executions by agent_display_name.

        EXPECTED FAILURE: OperationalError - no such column: agent_display_name
        Reason: Column is currently named agent_display_name.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-filter-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test filtering",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create multiple executions with different display names
        exec1 = AgentExecution(
            agent_id="agent-filter-001",
            job_id="job-filter-001",
            tenant_key="tenant-abc",
            agent_display_name="Orchestrator",            status="complete"
        )
        exec2 = AgentExecution(
            agent_id="agent-filter-002",
            job_id="job-filter-001",
            tenant_key="tenant-abc",
            agent_display_name="Implementor",            status="working"
        )
        db_session.add_all([exec1, exec2])
        await db_session.commit()

        # Query by agent_display_name
        result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.agent_display_name == "Orchestrator")
        )
        executions = result.scalars().all()

        assert len(executions) == 1
        assert executions[0].agent_display_name == "Orchestrator"

    @pytest.mark.asyncio
    async def test_order_by_agent_display_name(self, db_session: AsyncSession):
        """
        Test that we can order executions by agent_display_name.

        EXPECTED FAILURE: OperationalError - no such column: agent_display_name
        Reason: Column is currently named agent_display_name.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-order-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test ordering",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create executions (unordered insertion)
        exec_b = AgentExecution(
            agent_id="agent-order-b",
            job_id="job-order-001",
            tenant_key="tenant-abc",
            agent_display_name="Beta Agent",            status="waiting"
        )
        exec_a = AgentExecution(
            agent_id="agent-order-a",
            job_id="job-order-001",
            tenant_key="tenant-abc",
            agent_display_name="Alpha Agent",            status="waiting"
        )
        db_session.add_all([exec_b, exec_a])
        await db_session.commit()

        # Query with ORDER BY agent_display_name
        result = await db_session.execute(
            select(AgentExecution)
            .where(AgentExecution.tenant_key == "tenant-abc")
            .order_by(AgentExecution.agent_display_name)
        )
        executions = result.scalars().all()

        assert len(executions) >= 2
        # Find our test executions
        test_execs = [e for e in executions if e.job_id == "job-order-001"]
        assert test_execs[0].agent_display_name == "Alpha Agent"
        assert test_execs[1].agent_display_name == "Beta Agent"


class TestAgentDisplayNameReprMethod:
    """Test that __repr__ method uses agent_display_name."""

    @pytest.mark.asyncio
    async def test_repr_includes_agent_display_name(self, db_session: AsyncSession):
        """
        Test that AgentExecution.__repr__() includes agent_display_name, not agent_display_name.

        EXPECTED FAILURE: AttributeError - AgentExecution has no attribute 'agent_display_name'
        Reason: __repr__ currently uses agent_display_name field.
        """
        # Create parent job
        job = AgentJob(
            job_id="job-repr-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test repr",
            job_type="orchestrator",
            status="active"
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution
        execution = AgentExecution(
            agent_id="agent-repr-001",
            job_id="job-repr-001",
            tenant_key="tenant-abc",
            agent_display_name="Documentation Manager",            status="waiting"
        )
        db_session.add(execution)
        await db_session.commit()

        # Test __repr__ output
        repr_str = repr(execution)
        assert "agent_display_name=Documentation Manager" in repr_str
        assert "agent_display_name=" not in repr_str, "__repr__ should not include agent_display_name after migration"
