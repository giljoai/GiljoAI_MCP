"""
Tests for Dynamic Agent Discovery System (Handover TBD).

Tests the enhancement of get_orchestrator_instructions() MCP tool and
ThinClientPromptGenerator to support execution_mode parameter and dynamic
agent template discovery with launch_instructions.

Test Coverage:
- execution_mode parameter handling (claude-code, legacy, auto-inferred)
- Mode-specific instructions building
- Agent template formatting with launch_instructions
- Backward compatibility with existing orchestrators
- Default mode inference from tool_type
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate, MCPAgentJob, Product, Project
from tests.helpers import ToolsTestHelper
from tests.mock_mcp import MockMCPToolRegistrar


class TestDynamicAgentDiscovery:
    """Test class for Dynamic Agent Discovery System"""

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
                description="Test product for agent discovery",
                tenant_key=self.tenant_key,
                vision_type="inline",
                vision_document="# Test Vision\n\nTest product vision.",
                chunked=True,
            )
            session.add(self.product)

            # Create test project
            self.project = await ToolsTestHelper.create_test_project(
                session, "Agent Discovery Test Project"
            )
            self.project.tenant_key = self.tenant_key
            self.project.product_id = self.product.id
            await session.commit()

            # Create agent templates with launch_instructions
            self.agent_templates = [
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="implementer",
                    role="Backend implementation specialist",
                    description="Implements features using TDD",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    meta_data={
                        "capabilities": ["Python", "FastAPI", "PostgreSQL"],
                        "expertise": ["TDD", "REST APIs"],
                        "launch_instructions": "cd $PROJECT_PATH && claude-code --agent implementer",
                    },
                ),
                AgentTemplate(
                    id=str(uuid.uuid4()),
                    name="tester",
                    role="Testing specialist",
                    description="Writes comprehensive tests",
                    tenant_key=self.tenant_key,
                    product_id=self.product.id,
                    is_active=True,
                    meta_data={
                        "capabilities": ["pytest", "unittest"],
                        "expertise": ["Unit testing", "Integration testing"],
                        "launch_instructions": "cd $PROJECT_PATH && claude-code --agent tester",
                    },
                ),
            ]
            for template in self.agent_templates:
                session.add(template)
            await session.commit()

            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_with_claude_code_mode(self):
        """Test get_orchestrator_instructions with execution_mode='claude-code'"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create orchestrator with claude-code execution_mode in metadata
        async with self.db_manager.get_session_async() as session:
            orchestrator = MCPAgentJob(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="Orchestrator #1",
                status="waiting",
                mission="Test mission",
                tool_type="claude-code",
                job_metadata={
                    "field_priorities": {},
                    "execution_mode": "claude-code",  # NEW: execution mode
                },
            )
            session.add(orchestrator)
            await session.commit()

            register_orchestration_tools(mock_server, self.db_manager)
            get_instructions = registrar.get_registered_tool("get_orchestrator_instructions")

            result = await get_instructions(
                orchestrator_id=orchestrator.job_id, tenant_key=self.tenant_key
            )

            # Verify claude-code mode response
            assert isinstance(result, dict)
            assert "execution_mode" in result
            assert result["execution_mode"]["mode"] == "claude-code"
            assert "instructions" in result["execution_mode"]
            assert "agent_templates" in result

            # Verify agent templates include launch_instructions
            templates = result["agent_templates"]
            assert len(templates) == 2
            assert any(t["name"] == "implementer" for t in templates)

            # Find implementer template and check launch_instructions
            implementer = next(t for t in templates if t["name"] == "implementer")
            assert "launch_instructions" in implementer
            assert "claude-code" in implementer["launch_instructions"]
            assert "$PROJECT_PATH" in implementer["launch_instructions"]

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_with_legacy_mode(self):
        """Test get_orchestrator_instructions with execution_mode='legacy'"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create orchestrator with legacy execution_mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = MCPAgentJob(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="Orchestrator #1",
                status="waiting",
                mission="Test mission",
                tool_type="universal",
                job_metadata={
                    "field_priorities": {},
                    "execution_mode": "legacy",  # Legacy mode
                },
            )
            session.add(orchestrator)
            await session.commit()

            register_orchestration_tools(mock_server, self.db_manager)
            get_instructions = registrar.get_registered_tool("get_orchestrator_instructions")

            result = await get_instructions(
                orchestrator_id=orchestrator.job_id, tenant_key=self.tenant_key
            )

            # Verify legacy mode response
            assert isinstance(result, dict)
            assert "execution_mode" in result
            assert result["execution_mode"]["mode"] == "legacy"
            assert "instructions" in result["execution_mode"]

            # Legacy mode should still include templates but with different instructions
            assert "agent_templates" in result
            legacy_instructions = result["execution_mode"]["instructions"]
            assert "manual" in legacy_instructions.lower() or "copy" in legacy_instructions.lower()

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_auto_infers_mode_from_tool_type(self):
        """Test execution_mode auto-inference from tool_type when not specified"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create orchestrator WITHOUT execution_mode (should infer from tool_type)
        async with self.db_manager.get_session_async() as session:
            orchestrator = MCPAgentJob(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="Orchestrator #1",
                status="waiting",
                mission="Test mission",
                tool_type="claude-code",
                job_metadata={
                    "field_priorities": {},
                    # No execution_mode specified
                },
            )
            session.add(orchestrator)
            await session.commit()

            register_orchestration_tools(mock_server, self.db_manager)
            get_instructions = registrar.get_registered_tool("get_orchestrator_instructions")

            result = await get_instructions(
                orchestrator_id=orchestrator.job_id, tenant_key=self.tenant_key
            )

            # Should auto-infer claude-code mode from tool_type
            assert isinstance(result, dict)
            assert "execution_mode" in result
            assert result["execution_mode"]["mode"] == "claude-code"

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_backward_compatibility(self):
        """Test backward compatibility with existing orchestrators (no execution_mode)"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create OLD orchestrator WITHOUT tool_type or execution_mode
        async with self.db_manager.get_session_async() as session:
            orchestrator = MCPAgentJob(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="Orchestrator #1",
                status="waiting",
                mission="Test mission",
                tool_type=None,  # Old orchestrators might not have this
                job_metadata={},  # No execution_mode
            )
            session.add(orchestrator)
            await session.commit()

            register_orchestration_tools(mock_server, self.db_manager)
            get_instructions = registrar.get_registered_tool("get_orchestrator_instructions")

            result = await get_instructions(
                orchestrator_id=orchestrator.job_id, tenant_key=self.tenant_key
            )

            # Should default to legacy mode for backward compatibility
            assert isinstance(result, dict)
            assert "execution_mode" in result
            assert result["execution_mode"]["mode"] == "legacy"
            # Should still include basic fields
            assert "orchestrator_id" in result
            assert "project_id" in result
            assert "mission" in result

    @pytest.mark.asyncio
    async def test_thin_prompt_generator_with_execution_mode(self):
        """Test ThinClientPromptGenerator.generate() with execution_mode parameter"""
        from sqlalchemy.ext.asyncio import AsyncSession

        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        async with self.db_manager.get_session_async() as session:
            generator = ThinClientPromptGenerator(session, self.tenant_key)

            # Generate with claude-code mode
            result = await generator.generate(
                project_id=str(self.project.id),
                user_id=None,
                tool="claude-code",
                execution_mode="claude-code",  # NEW parameter
            )

            # Verify orchestrator created with execution_mode in metadata
            assert "orchestrator_id" in result
            assert "thin_prompt" in result

            # Check database for execution_mode in job_metadata
            from sqlalchemy import select

            stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == result["orchestrator_id"])
            db_result = await session.execute(stmt)
            orchestrator = db_result.scalar_one()

            assert orchestrator.job_metadata is not None
            assert "execution_mode" in orchestrator.job_metadata
            assert orchestrator.job_metadata["execution_mode"] == "claude-code"

    @pytest.mark.asyncio
    async def test_thin_prompt_generator_defaults_execution_mode_from_tool(self):
        """Test ThinClientPromptGenerator auto-infers execution_mode from tool parameter"""
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        async with self.db_manager.get_session_async() as session:
            generator = ThinClientPromptGenerator(session, self.tenant_key)

            # Generate WITHOUT explicit execution_mode (should infer from tool)
            result = await generator.generate(
                project_id=str(self.project.id),
                user_id=None,
                tool="claude-code",
                # No execution_mode specified
            )

            # Check database for inferred execution_mode
            from sqlalchemy import select

            stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == result["orchestrator_id"])
            db_result = await session.execute(stmt)
            orchestrator = db_result.scalar_one()

            # Should infer claude-code from tool parameter
            assert orchestrator.job_metadata.get("execution_mode") == "claude-code"

    @pytest.mark.asyncio
    async def test_api_endpoint_accepts_execution_mode(self):
        """Test API endpoint accepts execution_mode in request schema"""
        from api.schemas.prompt import OrchestratorPromptRequest

        # Test schema validation with execution_mode
        request = OrchestratorPromptRequest(
            project_id=str(self.project.id),
            tool="claude-code",
            instance_number=1,
            execution_mode="claude-code",  # NEW field
        )

        assert request.project_id == str(self.project.id)
        assert request.tool == "claude-code"
        assert request.execution_mode == "claude-code"

    @pytest.mark.asyncio
    async def test_mode_specific_instructions_claude_code(self):
        """Test mode-specific instructions for claude-code mode"""
        from src.giljo_mcp.tools.orchestration import _build_mode_instructions

        instructions = _build_mode_instructions("claude-code", self.agent_templates[:1])

        # Claude Code mode should mention Task tool and subagent spawning
        assert "Task" in instructions or "sub-agent" in instructions
        assert "claude-code" in instructions.lower()

    @pytest.mark.asyncio
    async def test_mode_specific_instructions_legacy(self):
        """Test mode-specific instructions for legacy mode"""
        from src.giljo_mcp.tools.orchestration import _build_mode_instructions

        instructions = _build_mode_instructions("legacy", self.agent_templates[:1])

        # Legacy mode should mention manual launches and terminal
        assert "manual" in instructions.lower() or "terminal" in instructions.lower()

    @pytest.mark.asyncio
    async def test_agent_template_formatting_includes_launch_instructions(self):
        """Test agent template formatting includes launch_instructions"""
        from src.giljo_mcp.tools.orchestration import _format_agent_templates

        formatted = _format_agent_templates(
            self.agent_templates, execution_mode="claude-code"
        )

        # Should include launch_instructions for each template
        assert "implementer" in formatted
        assert "launch_instructions" in formatted.lower()
        assert "claude-code" in formatted

    @pytest.mark.asyncio
    async def test_execution_mode_validation(self):
        """Test execution_mode parameter validation"""
        from api.schemas.prompt import OrchestratorPromptRequest
        from pydantic import ValidationError

        # Valid modes
        for mode in ["claude-code", "legacy"]:
            request = OrchestratorPromptRequest(
                project_id=str(self.project.id),
                tool="claude-code",
                execution_mode=mode,
            )
            assert request.execution_mode == mode

        # Invalid mode should raise validation error
        with pytest.raises(ValidationError):
            OrchestratorPromptRequest(
                project_id=str(self.project.id),
                tool="claude-code",
                execution_mode="invalid-mode",
            )

    @pytest.mark.asyncio
    async def test_orchestrator_instructions_includes_all_required_fields(self):
        """Test get_orchestrator_instructions returns all required fields with execution_mode"""
        from src.giljo_mcp.tools.orchestration import register_orchestration_tools

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        async with self.db_manager.get_session_async() as session:
            orchestrator = MCPAgentJob(
                job_id=str(uuid.uuid4()),
                project_id=self.project.id,
                tenant_key=self.tenant_key,
                agent_type="orchestrator",
                agent_name="Orchestrator #1",
                status="waiting",
                mission="Test mission",
                tool_type="claude-code",
                job_metadata={"execution_mode": "claude-code"},
            )
            session.add(orchestrator)
            await session.commit()

            register_orchestration_tools(mock_server, self.db_manager)
            get_instructions = registrar.get_registered_tool("get_orchestrator_instructions")

            result = await get_instructions(
                orchestrator_id=orchestrator.job_id, tenant_key=self.tenant_key
            )

            # Verify all required fields present
            required_fields = [
                "orchestrator_id",
                "project_id",
                "project_name",
                "mission",
                "agent_templates",
                "execution_mode",
            ]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

            # Verify execution_mode structure
            exec_mode = result["execution_mode"]
            assert "mode" in exec_mode
            assert "instructions" in exec_mode
