"""
Unit tests for Handover 0351 - agent_name as Single Source of Truth.

Tests that orchestrators receive agent NAME constraints (not agent_display_name) and that
spawn_agent_job validates agent_name against available template names.

HANDOVER 0351 CHANGES:
- allowed_agent_display_names → allowed_agent_names in CLI constraints
- Validation checks agent_name (not agent_display_name) against template names
- agent_name is now the SINGLE SOURCE OF TRUTH for template matching

Test Coverage:
1. CLI mode: Response includes allowed_agent_names (not allowed_agent_display_names)
2. Constraint structure validation (mode, allowed_agent_names, instruction)
3. allowed_agent_names matches available template names
4. spawn_agent_job accepts valid agent names
5. spawn_agent_job rejects invalid/invented agent names with helpful error
6. Error messages reference agent_name field (not agent_display_name)

TDD PHASE: RED - These tests should FAIL initially.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate, Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.utils.tools_helpers import ToolsTestHelper, MockMCPToolRegistrar


class TestOrchestratorInstructionsConstraintAgentName:
    """
    Phase 1: Test allowed_agent_names in get_orchestrator_instructions response
    (replacing allowed_agent_display_names per Handover 0351)
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
                name="Test Product - Agent Name Validation",
                description="Product for agent name validation tests",
                tenant_key=self.tenant_key,
            )
            session.add(self.product)

            # Create test project with CLI execution mode
            self.project = Project(
                id=str(uuid.uuid4()),
                name="Agent Name Validation Project",
                description="Test project for agent name validation",
                mission="Test mission for agent name validation",  # Required field
                tenant_key=self.tenant_key,
                product_id=self.product.id,
                status="active",
                execution_mode="claude_code_cli",  # Set CLI mode on Project (Handover 0346)
            )
            session.add(self.project)
            await session.commit()

            # Create active agent templates (these should be discoverable by NAME)
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
                    system_instructions="# Implementer Agent\n\nImplements code features.",
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
                    system_instructions="# Tester Agent\n\nWrites tests.",
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
                    system_instructions="# Reviewer Agent\n\nReviews code.",
                ),
            ]
            for template in self.agent_templates:
                session.add(template)
            await session.commit()

            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_cli_mode_includes_allowed_agent_names_not_types(self):
        """
        HANDOVER 0351: get_orchestrator_instructions in CLI mode MUST
        include allowed_agent_names (NOT allowed_agent_display_names).

        agent_name is the SINGLE SOURCE OF TRUTH for template matching.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create orchestrator with CLI execution_mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_display_name="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                tool_type="claude-code",
                job_metadata={
                    "field_priorities": {},
                    # execution_mode read from Project.execution_mode (Handover 0346)
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
                "CLI mode MUST include agent_spawning_constraint"
            )

            constraint = result["agent_spawning_constraint"]

            # ASSERTION 2: allowed_agent_names is present (NEW)
            assert "allowed_agent_names" in constraint, (
                "Handover 0351: Constraint must use allowed_agent_names (not allowed_agent_display_names)"
            )

            # ASSERTION 3: allowed_agent_display_names should NOT be present (OLD)
            assert "allowed_agent_display_names" not in constraint, (
                "Handover 0351: allowed_agent_display_names is DEPRECATED, must use allowed_agent_names"
            )

            # ASSERTION 4: allowed_agent_names is a list
            assert isinstance(constraint["allowed_agent_names"], list), (
                "allowed_agent_names must be a list of template names"
            )

            # ASSERTION 5: allowed_agent_names matches available template names
            from src.giljo_mcp.tools.agent_discovery import get_available_agents

            agents_result = await get_available_agents(
                session, self.tenant_key, depth="type_only"
            )

            expected_names = [t["name"] for t in agents_result["data"]["agents"]]
            assert set(constraint["allowed_agent_names"]) == set(expected_names), (
                f"allowed_agent_names must match available template names. "
                f"Expected: {expected_names}, Got: {constraint['allowed_agent_names']}"
            )

    @pytest.mark.asyncio
    async def test_cli_mode_instruction_references_agent_name_field(self):
        """
        HANDOVER 0351: Instruction text must reference agent_name field
        (not agent_display_name) as the validation field.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create orchestrator in CLI mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_display_name="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                job_metadata={},  # execution_mode read from Project.execution_mode (Handover 0346)
            )
            session.add(orchestrator)
            await session.commit()

            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            constraint = result["agent_spawning_constraint"]
            instruction = constraint["instruction"]

            # ASSERTION 1: Instruction mentions agent_name field
            assert "agent_name" in instruction, (
                "Handover 0351: Instruction must reference agent_name field"
            )

            # ASSERTION 2: Instruction should NOT mention agent_display_name as validation field
            # (agent_display_name may be mentioned for other purposes, but not as the SSOT)
            instruction_lower = instruction.lower()
            assert "agent_name parameter must" in instruction_lower or "agent_name must" in instruction_lower, (
                f"Instruction should specify agent_name as the validated parameter. Got: {instruction}"
            )

            # ASSERTION 3: Instruction includes allowed agent names
            assert "implementer" in instruction or str(constraint["allowed_agent_names"]) in instruction, (
                "Instruction should list allowed agent names"
            )

    @pytest.mark.asyncio
    async def test_constraint_includes_all_active_template_names(self):
        """
        HANDOVER 0351: allowed_agent_names must include ALL active template names.
        """
        from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Create orchestrator in CLI mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_display_name="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                job_metadata={},  # execution_mode read from Project.execution_mode (Handover 0346)
            )
            session.add(orchestrator)
            await session.commit()

            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            constraint = result["agent_spawning_constraint"]
            allowed_names = constraint["allowed_agent_names"]

            # ASSERTION: All template names present
            expected_names = ["implementer", "tester", "reviewer"]
            assert set(allowed_names) == set(expected_names), (
                f"Constraint must include all active template names. "
                f"Expected: {expected_names}, Got: {allowed_names}"
            )

    @pytest.mark.asyncio
    async def test_constraint_excludes_inactive_template_names(self):
        """
        HANDOVER 0351: allowed_agent_names must EXCLUDE inactive template names.
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
                system_instructions="# Deprecated Agent\n\nOld agent.",
            )
            session.add(inactive_template)
            await session.commit()

            # Create orchestrator
            orchestrator = AgentExecution(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_display_name="orchestrator",
                agent_name="CLI Orchestrator",
                status="waiting",
                mission="Test mission",
                job_metadata={},  # execution_mode read from Project.execution_mode (Handover 0346)
            )
            session.add(orchestrator)
            await session.commit()

            result = await get_orchestrator_instructions(
                orchestrator_id=orchestrator.job_id,
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            constraint = result["agent_spawning_constraint"]
            allowed_names = constraint["allowed_agent_names"]

            # ASSERTION: Inactive template NOT in allowed names
            assert "deprecated_agent" not in allowed_names, (
                "Inactive templates must NOT be in allowed_agent_names"
            )

            # ASSERTION: Only active templates present
            assert set(allowed_names) == {"implementer", "tester", "reviewer"}, (
                f"Only active template names should be allowed. Got: {allowed_names}"
            )


class TestSpawnAgentJobValidationAgentName:
    """
    Phase 2: Test spawn_agent_job agent_name validation against template names
    (replacing agent_display_name validation per Handover 0351)
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
                name="Spawn Validation Product - Agent Name",
                description="Product for spawn validation with agent_name",
                tenant_key=self.tenant_key,
            )
            session.add(self.product)

            # Create test project
            self.project = Project(
                id=str(uuid.uuid4()),
                name="Spawn Validation Project - Agent Name",
                description="Test project for spawn validation via agent_name",
                mission="Test mission for spawn validation",  # Required field
                tenant_key=self.tenant_key,
                product_id=self.product.id,
                status="active",
            )
            session.add(self.project)
            await session.commit()

            # Create active agent templates (valid agent names)
            self.agent_templates = [
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="implementer",
                    role="Code Implementation Specialist",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    system_instructions="# Implementer\n\nImplements code.",
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="tester",
                    role="Testing Specialist",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    version="1.0.0",
                    system_instructions="# Tester\n\nWrites tests.",
                ),
            ]
            for template in self.agent_templates:
                session.add(template)
            await session.commit()

    @pytest.mark.asyncio
    async def test_valid_agent_name_accepted(self):
        """
        HANDOVER 0351: spawn_agent_job should ACCEPT valid agent names that match
        active template names.

        agent_name is the SINGLE SOURCE OF TRUTH for template matching.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn agent with valid agent_name
        result = await spawn_agent_job(
            agent_display_name="worker",  # agent_display_name is still used for job categorization
            agent_name="implementer",  # SSOT: Must match template name
            mission="Implement feature X",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Spawn succeeds
        assert result["success"] is True, (
            f"Valid agent_name 'implementer' should be accepted. Error: {result.get('error')}"
        )

        # ASSERTION: Agent job created
        assert "job_id" in result, "Successful spawn must return job_id"
        assert "agent_prompt" in result, "Successful spawn must return agent_prompt"

        # ASSERTION: No error message
        assert "error" not in result, "Successful spawn should not have error field"

    @pytest.mark.asyncio
    async def test_all_valid_agent_names_accepted(self):
        """
        HANDOVER 0351: spawn_agent_job should accept ALL valid agent names from template names.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Test each valid agent name
        for agent_name in ["implementer", "tester"]:
            result = await spawn_agent_job(
                agent_display_name="worker",
                agent_name=agent_name,  # SSOT: Match template name
                mission=f"Test mission for {agent_name}",
                project_id=str(self.project.id),
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            # ASSERTION: Each valid name accepted
            assert result["success"] is True, (
                f"Valid agent_name '{agent_name}' should be accepted. "
                f"Error: {result.get('error')}"
            )

    @pytest.mark.asyncio
    async def test_invalid_agent_name_rejected(self):
        """
        HANDOVER 0351: spawn_agent_job should REJECT invented agent names that don't
        match any active template name.

        Error message must reference agent_name field (not agent_display_name).
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn agent with invented agent_name
        result = await spawn_agent_job(
            agent_display_name="worker",
            agent_name="backend-tester-for-api-validation",  # INVALID (doesn't match template)
            mission="Validate APIs",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION 1: Spawn fails
        assert result["success"] is False, (
            "Invalid agent_name should be rejected"
        )

        # ASSERTION 2: Error message present
        assert "error" in result, "Rejected spawn must include error message"

        # ASSERTION 3: Error mentions invalid agent_name (NOT agent_display_name)
        error_msg = result["error"]
        assert "Invalid agent_name" in error_msg or "agent_name" in error_msg.lower(), (
            f"Handover 0351: Error message should mention 'agent_name' field. Got: {error_msg}"
        )
        assert "backend-tester-for-api-validation" in error_msg, (
            f"Error message should include the invalid name. Got: {error_msg}"
        )

        # ASSERTION 4: Error lists valid agent names (not types)
        assert "implementer" in error_msg, (
            f"Error should list valid agent names. Got: {error_msg}"
        )
        assert "tester" in error_msg, (
            f"Error should list valid agent names. Got: {error_msg}"
        )

        # ASSERTION 5: Hint field present
        assert "hint" in result, (
            "Rejected spawn should include 'hint' field to guide orchestrator"
        )

    @pytest.mark.asyncio
    async def test_extended_descriptive_name_rejected(self):
        """
        HANDOVER 0351: spawn_agent_job should reject extended descriptive names
        that don't match template names.

        Orchestrators must use exact template names in agent_name field.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with extended descriptive name (common mistake)
        result = await spawn_agent_job(
            agent_display_name="worker",
            agent_name="Backend Tester Agent",  # WRONG (descriptive, doesn't match template)
            mission="Test backend APIs",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION 1: Spawn fails
        assert result["success"] is False, (
            "Extended descriptive names should be rejected if not matching template"
        )

        # ASSERTION 2: Error present
        assert "error" in result

        # ASSERTION 3: Error references agent_name field
        error_lower = result["error"].lower()
        assert "agent_name" in error_lower, (
            "Handover 0351: Error should reference agent_name field"
        )

        # ASSERTION 4: Hint explains exact template name requirement
        assert "hint" in result, "Hint field must be present for guidance"

        hint = result["hint"]
        assert "agent_name" in hint, "Hint should mention agent_name field"
        assert any(word in hint.lower() for word in ["exact", "match", "template"]), (
            f"Hint should explain exact template name matching. Got: {hint}"
        )

    @pytest.mark.asyncio
    async def test_case_sensitive_agent_name_validation(self):
        """
        HANDOVER 0351: spawn_agent_job should enforce EXACT case-sensitive matching
        of agent_name against template names.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with wrong case
        result = await spawn_agent_job(
            agent_display_name="worker",
            agent_name="Implementer",  # WRONG CASE (should be lowercase "implementer")
            mission="Implement feature",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Case mismatch rejected
        assert result["success"] is False, (
            "Agent name matching must be case-sensitive. 'Implementer' != 'implementer'"
        )

        # ASSERTION: Error mentions case sensitivity
        assert "error" in result
        error_msg = result["error"]
        assert "Implementer" in error_msg, (
            f"Error should show the invalid name. Got: {error_msg}"
        )

    @pytest.mark.asyncio
    async def test_inactive_template_name_rejected(self):
        """
        HANDOVER 0351: spawn_agent_job should reject agent names that match inactive
        template names.

        Only active template names are spawnable.
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
                system_instructions="# Deprecated\n\nOld agent.",
            )
            session.add(inactive_template)
            await session.commit()

            # Try to spawn using inactive template name
            result = await spawn_agent_job(
                agent_display_name="worker",
                agent_name="deprecated",  # Template exists but INACTIVE
                mission="Test mission",
                project_id=str(self.project.id),
                tenant_key=self.tenant_key,
                db_manager=self.db_manager,
            )

            # ASSERTION: Inactive template rejected
            assert result["success"] is False, (
                "Inactive template names should be rejected"
            )

            # ASSERTION: Error explains template is inactive
            assert "error" in result
            # Should list only active template names
            assert "implementer" in result["error"], (
                "Error should list active template names only"
            )

    @pytest.mark.asyncio
    async def test_error_message_includes_valid_names_list(self):
        """
        HANDOVER 0351: spawn_agent_job error messages must include list of valid
        agent names (template names) to guide orchestrator.

        Error messages should be actionable.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with invalid name
        result = await spawn_agent_job(
            agent_display_name="worker",
            agent_name="nonexistent",
            mission="Test mission",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Error includes valid names
        error_msg = result["error"]

        # Should list all valid names
        assert "implementer" in error_msg, "Error should list 'implementer'"
        assert "tester" in error_msg, "Error should list 'tester'"

        # Should use list format (e.g., "Must be one of: [...]")
        assert "Must be one of" in error_msg or "one of:" in error_msg, (
            f"Error should use 'Must be one of' format. Got: {error_msg}"
        )

    @pytest.mark.asyncio
    async def test_hint_explains_exact_template_name_requirement(self):
        """
        HANDOVER 0351: spawn_agent_job hint field must explain that agent_name
        must EXACTLY match a template name.

        This is the CRITICAL change from Handover 0351.
        """
        from src.giljo_mcp.tools.orchestration import spawn_agent_job

        # Spawn with invalid name
        result = await spawn_agent_job(
            agent_display_name="worker",
            agent_name="custom-backend-agent",
            mission="Develop backend",
            project_id=str(self.project.id),
            tenant_key=self.tenant_key,
            db_manager=self.db_manager,
        )

        # ASSERTION: Hint field present
        assert "hint" in result, "Rejected spawn must include 'hint' field"

        hint = result["hint"]

        # ASSERTION: Hint explains agent_name requirement
        assert "agent_name" in hint, "Hint should mention agent_name field"

        # ASSERTION: Hint mentions template name requirement
        hint_lower = hint.lower()
        assert "template" in hint_lower, "Hint should mention template"
        assert any(word in hint_lower for word in ["exact", "match", "must match"]), (
            f"Handover 0351: Hint should explain agent_name must EXACTLY match template name. Got: {hint}"
        )
