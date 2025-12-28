"""
Unit tests for orchestrator agent spawning validation (Handover 0260 Phase 5).

Tests that orchestrators receive agent type constraints in CLI mode and that
spawn_agent_job validates agent types against available templates.

Phase 5a: get_orchestrator_instructions includes agent_spawning_constraint in CLI mode
Phase 5b: spawn_agent_job validates agent_type against available templates

Test Coverage:
1. Multi-terminal mode: No agent_spawning_constraint in response
2. Claude Code CLI mode: Response includes agent_spawning_constraint
3. Constraint structure validation (mode, allowed_agent_types, instruction)
4. allowed_agent_types matches available templates from get_available_agents()
5. spawn_agent_job accepts valid agent types
6. spawn_agent_job rejects invalid/invented agent types with helpful error
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate, Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.utils.tools_helpers import ToolsTestHelper, MockMCPToolRegistrar


class TestOrchestratorInstructionsConstraint:
    """
    Phase 5a: Test agent_spawning_constraint in get_orchestrator_instructions response
    """

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Generate valid tenant key
        self.tenant_key = TenantManager.generate_tenant_key()

        # Create test data
        async with self.db_manager.get_session_async() as session:
            # Create test product
            self.product = Product(
                id=str(uuid.uuid4()),
                name="Test Product",
                description="Product for agent validation tests",
                tenant_key=self.tenant_key,
            )
            session.add(self.product)

            # Create test project
            self.project = Project(
                id=str(uuid.uuid4()),
                name="Agent Validation Test Project",
                description="Test project for agent validation",
                mission="Test mission for agent validation",  # Required field
                tenant_key=self.tenant_key,
                product_id=self.product.id,
                status="active",
            )
            session.add(self.project)
            await session.commit()

            # Create active agent templates (these should be discoverable)
            self.agent_templates = [
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="implementer",
                    role="Code Implementation Specialist",
                    description="Implements features using TDD",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    template_content="# Implementer Agent\n\nImplements code features.",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="tester",
                    role="Testing Specialist",
                    description="Writes comprehensive tests",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    template_content="# Tester Agent\n\nWrites tests.",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="reviewer",
                    role="Code Review Specialist",
                    description="Reviews code for quality",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    template_content="# Reviewer Agent\n\nReviews code.",
                ),
            ]
            for template in self.agent_templates:
                session.add(template)
            await session.commit()

            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_multi_terminal_mode_excludes_spawning_constraint(self):
        """
        PHASE 5a: get_orchestrator_instructions in multi-terminal mode should NOT
        include agent_spawning_constraint.

        Multi-terminal mode allows orchestrator to spawn any agent types since
        agents are manually launched in separate terminals.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create orchestrator with multi-terminal execution_mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="Multi-Terminal Orchestrator",
                status="waiting",
                mission="Test mission",
                tool_type="universal",
                job_metadata={
                    "field_priorities": {},
                    "execution_mode": "multi_terminal",  # Multi-terminal mode
                },
            )
            session.add(orchestrator)
            await session.commit()

            # Call get_orchestrator_instructions
            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            # ASSERTION: No agent_spawning_constraint in multi-terminal mode
            assert "agent_spawning_constraint" not in result, (
                "Multi-terminal mode should NOT include agent_spawning_constraint "
                "(agents are manually launched)"
            )

    @pytest.mark.asyncio
    async def test_cli_mode_includes_spawning_constraint(self):
        """
        PHASE 5a: get_orchestrator_instructions in claude_code_cli mode MUST
        include agent_spawning_constraint.

        CLI mode requires strict agent type validation since orchestrator spawns
        subagents via Task tool, which must use exact template names.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create orchestrator with CLI execution_mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                tool_type="claude-code",
                job_metadata={
                    "field_priorities": {},
                    "execution_mode": "claude_code_cli",  # CLI mode
                },
            )
            session.add(orchestrator)
            await session.commit()

            # Call get_orchestrator_instructions
            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            # ASSERTION 1: agent_spawning_constraint exists
            assert "agent_spawning_constraint" in result, (
                "CLI mode MUST include agent_spawning_constraint to enforce Task tool validation"
            )

            constraint = result["agent_spawning_constraint"]

            # ASSERTION 2: Constraint has correct structure
            assert "mode" in constraint, "Constraint must specify validation mode"
            assert "allowed_agent_types" in constraint, "Constraint must list allowed agent types"
            assert "instruction" in constraint, "Constraint must include instruction text"

            # ASSERTION 3: Mode is 'strict_task_tool'
            assert constraint["mode"] == "strict_task_tool", (
                "CLI mode must use 'strict_task_tool' validation mode"
            )

            # ASSERTION 4: allowed_agent_types is a list
            assert isinstance(constraint["allowed_agent_types"], list), (
                "allowed_agent_types must be a list of agent type strings"
            )

            # ASSERTION 5: allowed_agent_types matches available templates
            # Query available templates
            from src.giljo_mcp.tools.agent_discovery import get_available_agents

            agents_result = await get_available_agents(
                session, self.tenant_key, depth="type_only"
            )

            expected_types = [t["name"] for t in agents_result["data"]["agents"]]
            assert set(constraint["allowed_agent_types"]) == set(expected_types), (
                f"allowed_agent_types must match available templates. "
                f"Expected: {expected_types}, Got: {constraint['allowed_agent_types']}"
            )

            # ASSERTION 6: Instruction mentions Task tool requirement
            instruction_lower = constraint["instruction"].lower()
            assert "task tool" in instruction_lower, (
                "Instruction must mention Task tool requirement"
            )

    @pytest.mark.asyncio
    async def test_constraint_includes_all_active_templates(self):
        """
        PHASE 5a: agent_spawning_constraint.allowed_agent_types must include
        ALL active templates for the tenant.

        Tests that constraint accurately reflects database state.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create orchestrator in CLI mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                job_metadata={"execution_mode": "claude_code_cli"},
            )
            session.add(orchestrator)
            await session.commit()

            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            constraint = result["agent_spawning_constraint"]
            allowed_types = constraint["allowed_agent_types"]

            # ASSERTION: All template names present
            expected_names = ["implementer", "tester", "reviewer"]
            assert set(allowed_types) == set(expected_names), (
                f"Constraint must include all active templates. "
                f"Expected: {expected_names}, Got: {allowed_types}"
            )

    @pytest.mark.asyncio
    async def test_constraint_excludes_inactive_templates(self):
        """
        PHASE 5a: agent_spawning_constraint.allowed_agent_types must EXCLUDE
        inactive templates.

        Only active templates should be spawnable.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Add inactive template
        async with self.db_manager.get_session_async() as session:
            inactive_template = AgentTemplate(
                id=str(uuid.uuid4()),
                name="deprecated_agent",
                role="Deprecated Agent",
                description="Should not be spawnable",
                tenant_key=self.tenant_key,
                product_id=self.product.id,
                is_active=False,  # INACTIVE
                version="0.5.0",
                template_content="# Deprecated Agent\n\nOld agent.",
            )
            session.add(inactive_template)
            await session.commit()

            # Create orchestrator
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                job_metadata={"execution_mode": "claude_code_cli"},
            )
            session.add(orchestrator)
            await session.commit()

            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            constraint = result["agent_spawning_constraint"]
            allowed_types = constraint["allowed_agent_types"]

            # ASSERTION: Inactive template NOT in allowed types
            assert "deprecated_agent" not in allowed_types, (
                "Inactive templates must NOT be in allowed_agent_types"
            )

            # ASSERTION: Only active templates present
            assert set(allowed_types) == {"implementer", "tester", "reviewer"}, (
                f"Only active templates should be allowed. Got: {allowed_types}"
            )


class TestSpawnAgentJobValidation:
    """
    Phase 5b: Test spawn_agent_job agent_type validation against available templates
    """

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]

        # Generate valid tenant key
        self.tenant_key = TenantManager.generate_tenant_key()

        # Create test data
        async with self.db_manager.get_session_async() as session:
            # Create test product
            self.product = Product(
                id=str(uuid.uuid4()),
                name="Spawn Validation Product",
                description="Product for spawn validation tests",
                tenant_key=self.tenant_key,
            )
            session.add(self.product)

            # Create test project
            self.project = Project(
                id=str(uuid.uuid4()),
                name="Spawn Validation Project",
                description="Test project for spawn validation",
                mission="Test mission for spawn validation",  # Required field
                tenant_key=self.tenant_key,
                product_id=self.product.id,
                status="active",
            )
            session.add(self.project)
            await session.commit()

            # Create active agent templates (valid agent types)
            self.agent_templates = [
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="implementer",
                    role="Code Implementation Specialist",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    template_content="# Implementer\n\nImplements code.",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="tester",
                    role="Testing Specialist",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    template_content="# Tester\n\nWrites tests.",
                ),
            ]
            for template in self.agent_templates:
                session.add(template)
            await session.commit()

    @pytest.mark.asyncio
    async def test_valid_agent_type_accepted(self):
        """
        PHASE 5b: spawn_agent_job should ACCEPT valid agent types that match
        active templates.

        Tests the happy path: orchestrator spawns agent with valid type.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn agent with valid agent_type
        result = await spawn_agent_job(
            agent_type="implementer",  # Valid type (matches template)
            agent_name="Test Implementer",
            mission="Implement feature X",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Spawn succeeds
        assert result["success"] is True, (
            f"Valid agent_type 'implementer' should be accepted. Error: {result.get('error')}"
        )

        # ASSERTION: Agent job created
        assert "job_id" in result, "Successful spawn must return job_id"
        assert "agent_prompt" in result, "Successful spawn must return agent_prompt"

        # ASSERTION: No error message
        assert "error" not in result, "Successful spawn should not have error field"

    @pytest.mark.asyncio
    async def test_all_valid_agent_types_accepted(self):
        """
        PHASE 5b: spawn_agent_job should accept ALL valid agent types from templates.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Test each valid agent type
        for agent_type in ["implementer", "tester"]:
            result = await spawn_agent_job(
                agent_type=agent_type,
                agent_name=f"Test {agent_type.title()}",
                mission=f"Test mission for {agent_type}",
                project_id=str(self.project.id),
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            # ASSERTION: Each valid type accepted
            assert result["success"] is True, (
                f"Valid agent_type '{agent_type}' should be accepted. "
                f"Error: {result.get('error')}"
            )

    @pytest.mark.asyncio
    async def test_invalid_agent_type_rejected(self):
        """
        PHASE 5b: spawn_agent_job should REJECT invented agent types that don't
        match any active template.

        Tests error handling for invalid agent types.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn agent with invented agent_type
        result = await spawn_agent_job(
            agent_type="backend-tester-for-api-validation",  # INVALID (invented)
            agent_name="API Validator",
            mission="Validate APIs",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION 1: Spawn fails
        assert result["success"] is False, (
            "Invalid agent_type should be rejected"
        )

        # ASSERTION 2: Error message present
        assert "error" in result, "Rejected spawn must include error message"

        # ASSERTION 3: Error mentions invalid agent_type
        error_msg = result["error"]
        assert "Invalid agent_type" in error_msg, (
            f"Error message should mention 'Invalid agent_type'. Got: {error_msg}"
        )
        assert "backend-tester-for-api-validation" in error_msg, (
            f"Error message should include the invalid type name. Got: {error_msg}"
        )

        # ASSERTION 4: Error lists valid agent types
        assert "implementer" in error_msg, (
            f"Error should list valid agent types. Got: {error_msg}"
        )
        assert "tester" in error_msg, (
            f"Error should list valid agent types. Got: {error_msg}"
        )

        # ASSERTION 5: Hint field present
        assert "hint" in result, (
            "Rejected spawn should include 'hint' field to guide orchestrator"
        )

    @pytest.mark.asyncio
    async def test_extended_agent_name_as_type_rejected(self):
        """
        PHASE 5b: spawn_agent_job should reject extended descriptive names used
        as agent_type.

        Orchestrators sometimes use descriptive names (intended for agent_name)
        as agent_type. This should be rejected with helpful guidance.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with extended name as agent_type (common mistake)
        result = await spawn_agent_job(
            agent_type="Backend Tester Agent",  # WRONG (descriptive, should be agent_name)
            agent_name="API Tester",
            mission="Test backend APIs",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION 1: Spawn fails
        assert result["success"] is False, (
            "Extended names should be rejected as agent_type"
        )

        # ASSERTION 2: Error present
        assert "error" in result

        # ASSERTION 3: Hint explains agent_name vs agent_type
        assert "hint" in result, "Hint field must be present for guidance"

        hint_lower = result["hint"].lower()
        assert "agent_name" in hint_lower and "agent_type" in hint_lower, (
            f"Hint should explain agent_name vs agent_type distinction. Got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_case_sensitive_agent_type_validation(self):
        """
        PHASE 5b: spawn_agent_job should enforce EXACT case-sensitive matching
        of agent_type.

        Agent types must match template names exactly (lowercase).
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with wrong case
        result = await spawn_agent_job(
            agent_type="Implementer",  # WRONG CASE (should be lowercase "implementer")
            agent_name="Test Implementer",
            mission="Implement feature",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Case mismatch rejected
        assert result["success"] is False, (
            "Agent type matching must be case-sensitive. 'Implementer' != 'implementer'"
        )

        # ASSERTION: Error mentions case sensitivity
        assert "error" in result
        error_msg = result["error"]
        assert "Implementer" in error_msg, (
            f"Error should show the invalid type. Got: {error_msg}"
        )

    @pytest.mark.asyncio
    async def test_inactive_template_rejected(self):
        """
        PHASE 5b: spawn_agent_job should reject agent types that match inactive
        templates.

        Only active templates are spawnable.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Add inactive template
        async with self.db_manager.get_session_async() as session:
            inactive_template = AgentTemplate(
                id=str(uuid.uuid4()),
                name="deprecated",
                role="Deprecated Agent",
                tenant_key=self.tenant_key,
                product_id=self.product.id,
                is_active=False,  # INACTIVE
                template_content="# Deprecated\n\nOld agent.",
            )
            session.add(inactive_template)
            await session.commit()

            # Try to spawn inactive agent
            result = await spawn_agent_job(
                agent_type="deprecated",  # Exists but INACTIVE
                agent_name="Deprecated Agent",
                mission="Test mission",
                project_id=str(self.project.id),
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            # ASSERTION: Inactive template rejected
            assert result["success"] is False, (
                "Inactive templates should be rejected"
            )

            # ASSERTION: Error explains template is inactive
            assert "error" in result
            # Should list only active templates
            assert "implementer" in result["error"], (
                "Error should list active templates only"
            )

    @pytest.mark.asyncio
    async def test_error_message_includes_valid_types_list(self):
        """
        PHASE 5b: spawn_agent_job error messages must include list of valid
        agent types to guide orchestrator.

        Error messages should be actionable.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with invalid type
        result = await spawn_agent_job(
            agent_type="nonexistent",
            agent_name="Test Agent",
            mission="Test mission",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Error includes valid types
        error_msg = result["error"]

        # Should list all valid types
        assert "implementer" in error_msg, "Error should list 'implementer'"
        assert "tester" in error_msg, "Error should list 'tester'"

        # Should use list format (e.g., "Must be one of: [...]")
        assert "Must be one of" in error_msg or "one of:" in error_msg, (
            f"Error should use 'Must be one of' format. Got: {error_msg}"
        )

    @pytest.mark.asyncio
    async def test_hint_explains_agent_name_vs_agent_type(self):
        """
        PHASE 5b: spawn_agent_job hint field must explain the difference between
        agent_name (descriptive) and agent_type (exact template match).

        Common orchestrator mistake is confusing these fields.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with invalid type
        result = await spawn_agent_job(
            agent_type="custom-backend-agent",
            agent_name="Backend Developer",
            mission="Develop backend",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Hint field present
        assert "hint" in result, "Rejected spawn must include 'hint' field"

        hint = result["hint"]

        # ASSERTION: Hint explains agent_name usage
        assert "agent_name" in hint, "Hint should mention agent_name field"

        # ASSERTION: Hint explains agent_type requirement
        assert "agent_type" in hint, "Hint should mention agent_type field"

        # ASSERTION: Hint mentions exact match requirement
        hint_lower = hint.lower()
        assert any(word in hint_lower for word in ["exact", "match", "template"]), (
            f"Hint should explain exact matching requirement. Got: {hint}"
        )
