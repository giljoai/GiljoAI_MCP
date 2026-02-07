"""
Unit Tests for Project execution_mode Field - Handover 0260 Phase 2 (TDD RED)

Tests cover:
- Default value assignment (multi_terminal)
- Setting execution_mode to claude_code_cli
- Setting execution_mode to multi_terminal
- Invalid execution_mode values rejected
- Database persistence and retrieval
- Model-level validation

These tests should FAIL initially until the Project model is updated
with the execution_mode column.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.giljo_mcp.models.projects import Project


class TestProjectExecutionModeModel:
    """Test execution_mode field on Project model."""

    def test_project_defaults_to_multi_terminal(self):
        """New projects should default to 'multi_terminal' execution mode."""
        project = Project(
            name="Test Project",
            description="Test project description",
            mission="Test mission for project",
            tenant_key=str(uuid4()),
        )

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert hasattr(project, "execution_mode"), "Project model missing execution_mode field"
        assert project.execution_mode == "multi_terminal", (
            f"Expected default 'multi_terminal', got {project.execution_mode}"
        )

    def test_project_accepts_claude_code_cli_mode(self):
        """Projects can be created with 'claude_code_cli' execution mode."""
        project = Project(
            name="CLI Project",
            description="Test project for CLI mode",
            mission="Test mission",
            tenant_key=str(uuid4()),
            execution_mode="claude_code_cli",
        )

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert hasattr(project, "execution_mode"), "Project model missing execution_mode field"
        assert project.execution_mode == "claude_code_cli", f"Expected 'claude_code_cli', got {project.execution_mode}"

    def test_project_accepts_multi_terminal_explicitly(self):
        """Projects can be explicitly set to 'multi_terminal' execution mode."""
        project = Project(
            name="Multi-Terminal Project",
            description="Test project for multi-terminal mode",
            mission="Test mission",
            tenant_key=str(uuid4()),
            execution_mode="multi_terminal",
        )

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert hasattr(project, "execution_mode"), "Project model missing execution_mode field"
        assert project.execution_mode == "multi_terminal", f"Expected 'multi_terminal', got {project.execution_mode}"

    def test_execution_mode_field_is_not_nullable(self):
        """Execution mode should not be nullable (has default)."""
        project = Project(
            name="Test Project", description="Test description", mission="Test mission", tenant_key=str(uuid4())
        )

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert hasattr(project, "execution_mode"), "Project model missing execution_mode field"
        assert project.execution_mode is not None, "execution_mode should not be None"

    @pytest.mark.asyncio
    async def test_execution_mode_persists_in_database(self, db_session):
        """Execution mode should persist through database roundtrip."""
        tenant_key = str(uuid4())

        # Create project with claude_code_cli mode
        project = Project(
            id=str(uuid4()),
            name="Persistence Test Project",
            description="Test database persistence",
            mission="Test mission",
            tenant_key=tenant_key,
            execution_mode="claude_code_cli",
        )

        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        project_id = project.id

        # Clear session to force fresh read from database
        await db_session.close()

        # Re-open session and fetch project
        from sqlalchemy import select

        async with db_session.begin():
            result = await db_session.execute(select(Project).where(Project.id == project_id))
            fetched_project = result.scalar_one()

            # EXPECTED TO FAIL: execution_mode column doesn't exist yet
            assert hasattr(fetched_project, "execution_mode"), "Fetched project missing execution_mode field"
            assert fetched_project.execution_mode == "claude_code_cli", (
                f"Expected 'claude_code_cli' after persistence, got {fetched_project.execution_mode}"
            )

    @pytest.mark.asyncio
    async def test_execution_mode_can_be_updated(self, db_session):
        """Execution mode can be changed after creation."""
        tenant_key = str(uuid4())

        # Create project with default mode
        project = Project(
            id=str(uuid4()),
            name="Update Test Project",
            description="Test updating execution_mode",
            mission="Test mission",
            tenant_key=tenant_key,
        )

        db_session.add(project)
        await db_session.commit()

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert project.execution_mode == "multi_terminal", (
            f"Expected default 'multi_terminal', got {project.execution_mode}"
        )

        # Update to claude_code_cli
        project.execution_mode = "claude_code_cli"
        await db_session.commit()
        await db_session.refresh(project)

        assert project.execution_mode == "claude_code_cli", (
            f"Expected 'claude_code_cli' after update, got {project.execution_mode}"
        )

    @pytest.mark.asyncio
    async def test_execution_mode_switch_back_to_multi_terminal(self, db_session):
        """Execution mode can be switched back to multi_terminal."""
        tenant_key = str(uuid4())

        # Create project with CLI mode
        project = Project(
            id=str(uuid4()),
            name="Switch Back Test Project",
            description="Test switching back to multi_terminal",
            mission="Test mission",
            tenant_key=tenant_key,
            execution_mode="claude_code_cli",
        )

        db_session.add(project)
        await db_session.commit()

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert project.execution_mode == "claude_code_cli"

        # Switch back to multi_terminal
        project.execution_mode = "multi_terminal"
        await db_session.commit()
        await db_session.refresh(project)

        assert project.execution_mode == "multi_terminal", (
            f"Expected 'multi_terminal' after switch, got {project.execution_mode}"
        )

    @pytest.mark.asyncio
    async def test_multiple_projects_different_execution_modes(self, db_session):
        """Multiple projects can have different execution modes."""
        tenant_key = str(uuid4())

        # Create two projects with different modes
        project1 = Project(
            id=str(uuid4()),
            name="Multi-Terminal Project",
            description="Uses multi-terminal mode",
            mission="Test mission 1",
            tenant_key=tenant_key,
            execution_mode="multi_terminal",
        )

        project2 = Project(
            id=str(uuid4()),
            name="CLI Project",
            description="Uses Claude Code CLI mode",
            mission="Test mission 2",
            tenant_key=tenant_key,
            execution_mode="claude_code_cli",
        )

        db_session.add(project1)
        db_session.add(project2)
        await db_session.commit()

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert project1.execution_mode == "multi_terminal"
        assert project2.execution_mode == "claude_code_cli"

    def test_execution_mode_field_length_limit(self):
        """Execution mode field should have VARCHAR(20) constraint."""
        # This test verifies the column definition
        # Column is String(20), so values >20 chars should fail validation

        project = Project(
            name="Length Test Project",
            description="Test field length",
            mission="Test mission",
            tenant_key=str(uuid4()),
            execution_mode="x" * 25,  # 25 characters - should exceed limit
        )

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        # When column exists, this should raise an error during commit
        # For now, just checking the field exists
        assert hasattr(project, "execution_mode"), "Project model missing execution_mode field"


class TestProjectExecutionModeValidation:
    """Test validation of execution_mode values."""

    def test_only_valid_modes_accepted(self):
        """Only 'claude_code_cli' and 'multi_terminal' should be valid."""
        valid_modes = ["claude_code_cli", "multi_terminal"]

        for mode in valid_modes:
            project = Project(
                name=f"Test {mode}",
                description="Test project",
                mission="Test mission",
                tenant_key=str(uuid4()),
                execution_mode=mode,
            )

            # EXPECTED TO FAIL: execution_mode column doesn't exist yet
            assert hasattr(project, "execution_mode"), f"Project model missing execution_mode field for mode {mode}"
            assert project.execution_mode == mode

    @pytest.mark.asyncio
    async def test_invalid_execution_mode_rejected(self, db_session):
        """Invalid execution_mode values should be rejected at database level."""
        # Note: Database-level validation requires a CHECK constraint or enum
        # This test documents expected behavior

        tenant_key = str(uuid4())
        invalid_modes = ["invalid_mode", "cli_only", "terminal", "", "CLAUDE_CODE_CLI"]

        for invalid_mode in invalid_modes:
            project = Project(
                id=str(uuid4()),
                name=f"Invalid Mode Test {invalid_mode}",
                description="Test invalid mode rejection",
                mission="Test mission",
                tenant_key=tenant_key,
                execution_mode=invalid_mode,
            )

            db_session.add(project)

            # EXPECTED TO FAIL: validation doesn't exist yet
            # When implemented, should raise IntegrityError or ValidationError
            # For now, just documenting the expectation
            try:
                await db_session.commit()
                # If we get here, validation is not implemented
                pytest.fail(
                    f"Invalid execution_mode '{invalid_mode}' was accepted "
                    "(validation not implemented yet - expected failure)"
                )
            except (IntegrityError, ValueError):
                # This is expected when validation is implemented
                await db_session.rollback()
                assert True  # Test passes when validation works


class TestProjectExecutionModeMultiTenant:
    """Test multi-tenant isolation for execution_mode."""

    @pytest.mark.asyncio
    async def test_different_tenants_different_execution_modes(self, db_session):
        """Different tenants can have projects with different execution modes."""
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        # Tenant A uses multi_terminal
        project_a = Project(
            id=str(uuid4()),
            name="Tenant A Project",
            description="Tenant A's project",
            mission="Test mission A",
            tenant_key=tenant_a,
            execution_mode="multi_terminal",
        )

        # Tenant B uses claude_code_cli
        project_b = Project(
            id=str(uuid4()),
            name="Tenant B Project",
            description="Tenant B's project",
            mission="Test mission B",
            tenant_key=tenant_b,
            execution_mode="claude_code_cli",
        )

        db_session.add(project_a)
        db_session.add(project_b)
        await db_session.commit()

        # EXPECTED TO FAIL: execution_mode column doesn't exist yet
        assert project_a.execution_mode == "multi_terminal"
        assert project_b.execution_mode == "claude_code_cli"

        # Verify tenant isolation - each project retains its own mode
        assert project_a.tenant_key != project_b.tenant_key
        assert project_a.execution_mode != project_b.execution_mode
