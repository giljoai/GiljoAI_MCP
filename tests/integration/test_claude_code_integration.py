"""
Integration Tests for Claude Code Integration System

Tests validate the findings from system-architect analysis:
1. ✅ Prompt generation works (manual workflow support)
2. ✅ Agent tracking works (logging infrastructure)
3. ❌ NO automatic sub-agent spawning (automation gap)
4. ❌ NO Task tool client implementation
5. ❌ NO process management for Claude Code

This test suite provides evidence for Handover 0012 Phase 2 validation.
"""

import pytest
pytest.skip("TODO(0127a-2): Comprehensive refactoring needed for MCPAgentJob model", allow_module_level=True)
from pathlib import Path

import pytest
from sqlalchemy import select

# TODO(0127a): from src.giljo_mcp.models import Agent, AgentInteraction
# from src.giljo_mcp.models import MCPAgentJob  # Use this instead
from src.giljo_mcp.tools.agent import (
    _ensure_agent,
)
from src.giljo_mcp.tools.claude_code_integration import (
    CLAUDE_CODE_AGENT_TYPES,
    generate_agent_spawn_instructions,
    generate_orchestrator_prompt,
    get_claude_code_agent_type,
)


class TestPromptGeneration:
    """Test the prompt generation infrastructure (manual workflow support)"""

    def test_agent_type_mapping_database(self):
        """Test mapping MCP role 'database' to Claude Code type"""
        # VALIDATION: Prompt generation infrastructure exists
        result = get_claude_code_agent_type("database")
        assert result == "database-expert"

    def test_agent_type_mapping_backend(self):
        """Test mapping MCP role 'backend' to Claude Code type"""
        result = get_claude_code_agent_type("backend")
        assert result == "tdd-implementor"

    def test_agent_type_mapping_tester(self):
        """Test mapping MCP role 'tester' to Claude Code type"""
        result = get_claude_code_agent_type("tester")
        assert result == "backend-integration-tester"

    def test_agent_type_mapping_architect(self):
        """Test mapping MCP role 'architect' to Claude Code type"""
        result = get_claude_code_agent_type("architect")
        assert result == "system-architect"

    def test_agent_type_mapping_case_insensitive(self):
        """Test role mapping is case-insensitive"""
        assert get_claude_code_agent_type("DATABASE") == "database-expert"
        assert get_claude_code_agent_type("Backend") == "tdd-implementor"

    def test_agent_type_mapping_with_spaces(self):
        """Test role mapping handles spaces"""
        assert get_claude_code_agent_type("database expert") == "database-expert"
        assert get_claude_code_agent_type("system architect") == "system-architect"

    def test_agent_type_mapping_unknown_defaults_to_general(self):
        """Test unknown roles default to 'general-purpose'"""
        result = get_claude_code_agent_type("unknown_role")
        assert result == "general-purpose"

    def test_agent_type_mapping_completeness(self):
        """Test all mapped agent types are valid Claude Code types"""
        # VALIDATION: Mapping dictionary exists and is complete
        assert len(CLAUDE_CODE_AGENT_TYPES) > 0
        unique_types = set(CLAUDE_CODE_AGENT_TYPES.values())

        # Verify expected agent types are present
        expected_types = {
            "database-expert",
            "tdd-implementor",
            "backend-integration-tester",
            "system-architect",
            "orchestrator-coordinator",
            "deep-researcher",
            "ux-designer",
            "network-security-engineer",
            "documentation-manager",
            "general-purpose",
        }
        assert expected_types.issubset(unique_types)

    def test_generate_agent_spawn_instructions_project_not_found(self):
        """Test error handling when project doesn't exist"""
        result = generate_agent_spawn_instructions(project_id="nonexistent-project", tenant_key="nonexistent-tenant")

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_generate_agent_spawn_instructions_success(self, db_session, test_project):
        """Test successful generation of agent spawn instructions"""
        # VALIDATION: Prompt generation infrastructure works

        # Create test agents
        agent1 = Agent(
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            name="database-agent",
            role="database",
            status="active",
            mission="Design database schema",
        )
        agent2 = Agent(
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            name="backend-agent",
            role="backend",
            status="active",
            mission="Implement API endpoints",
        )
        db_session.add_all([agent1, agent2])
        await db_session.commit()

        # Generate instructions (synchronous function)
        result = generate_agent_spawn_instructions(project_id=str(test_project.id), tenant_key=test_project.tenant_key)

        # Validate structure
        assert result["project_id"] == str(test_project.id)
        assert result["project_name"] == test_project.name
        assert result["total_agents"] == 2
        assert len(result["agents"]) == 2

        # Validate agent mapping
        db_agent = next(a for a in result["agents"] if a["mcp_role"] == "database")
        assert db_agent["claude_code_type"] == "database-expert"
        assert db_agent["mission"] == "Design database schema"

        backend_agent = next(a for a in result["agents"] if a["mcp_role"] == "backend")
        assert backend_agent["claude_code_type"] == "tdd-implementor"
        assert backend_agent["mission"] == "Implement API endpoints"

    @pytest.mark.asyncio
    async def test_generate_agent_spawn_instructions_no_agents(self, db_session, test_project):
        """Test generation with no active agents"""
        result = generate_agent_spawn_instructions(project_id=str(test_project.id), tenant_key=test_project.tenant_key)

        assert result["total_agents"] == 0
        assert result["agents"] == []

    @pytest.mark.asyncio
    async def test_generate_orchestrator_prompt_structure(self, db_session, test_project):
        """Test orchestrator prompt has correct structure for manual use"""
        # VALIDATION: Prompt is designed for manual copy-paste workflow

        # Create test agent
        agent = Agent(
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            name="test-agent",
            role="database",
            status="active",
            mission="Test mission",
        )
        db_session.add(agent)
        await db_session.commit()

        # Generate prompt
        prompt = generate_orchestrator_prompt(project_id=str(test_project.id), tenant_key=test_project.tenant_key)

        # Validate prompt structure (for manual use)
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Non-trivial prompt

        # Check for key sections
        assert "GiljoAI MCP Orchestration Request" in prompt
        assert "Project Details" in prompt
        assert "Project ID" in prompt
        assert str(test_project.id) in prompt
        assert test_project.name in prompt

        # Check for agent information
        assert "Agents to Spawn" in prompt
        assert "test-agent" in prompt
        assert "database-expert" in prompt
        assert "Test mission" in prompt

        # Check for workflow instructions (manual steps)
        assert "Workflow" in prompt
        assert "mcp__giljo-mcp__list_agents" in prompt  # Manual MCP tool call
        assert "Task" in prompt  # References Task tool (but doesn't spawn automatically)

    @pytest.mark.asyncio
    async def test_generate_orchestrator_prompt_context_budget(self, db_session, test_project):
        """Test prompt includes context budget information"""
        # Create agent with custom context budget
        agent = Agent(
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            name="test-agent",
            role="database",
            status="active",
            mission="Test mission",
            meta_data={"context_budget": 75000},
        )
        db_session.add(agent)
        await db_session.commit()

        prompt = generate_orchestrator_prompt(project_id=str(test_project.id), tenant_key=test_project.tenant_key)

        assert "75000" in prompt
        assert "Context Budget" in prompt

    @pytest.mark.asyncio
    async def test_generate_orchestrator_prompt_default_context_budget(self, db_session, test_project):
        """Test prompt uses default context budget when not specified"""
        agent = Agent(
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            name="test-agent",
            role="database",
            status="active",
            mission="Test mission",
        )
        db_session.add(agent)
        await db_session.commit()

        prompt = generate_orchestrator_prompt(project_id=str(test_project.id), tenant_key=test_project.tenant_key)

        assert "50000" in prompt  # Default budget


class TestAgentTrackingInfrastructure:
    """Test the agent tracking and logging system (what DOES exist)"""

    @pytest.mark.asyncio
    async def test_agent_interaction_model_exists(self, db_session):
        """Test AgentInteraction database model exists and is properly configured"""
        # VALIDATION: Tracking infrastructure exists

        # Verify model is importable and has correct structure
# TODO(0127a): from src.giljo_mcp.models import AgentInteraction
# from src.giljo_mcp.models import MCPAgentJob  # Use this instead

        # Check model has required fields
        assert hasattr(AgentInteraction, "id")
        assert hasattr(AgentInteraction, "tenant_key")
        assert hasattr(AgentInteraction, "project_id")
        assert hasattr(AgentInteraction, "parent_agent_id")
        assert hasattr(AgentInteraction, "sub_agent_name")
        assert hasattr(AgentInteraction, "interaction_type")
        assert hasattr(AgentInteraction, "mission")
        assert hasattr(AgentInteraction, "start_time")
        assert hasattr(AgentInteraction, "end_time")
        assert hasattr(AgentInteraction, "duration_seconds")
        assert hasattr(AgentInteraction, "tokens_used")
        assert hasattr(AgentInteraction, "result")
        assert hasattr(AgentInteraction, "error_message")

    @pytest.mark.asyncio
    async def test_spawn_and_log_sub_agent_creates_interaction(self, db_session, test_project):
        """Test spawn_and_log_sub_agent creates AgentInteraction record"""
        # VALIDATION: Manual tracking workflow works

        # Create parent agent
        parent_result = await _ensure_agent(
            project_id=str(test_project.id), agent_name="orchestrator", mission="Coordinate project", session=db_session
        )
        assert parent_result["success"]
        parent_agent_id = parent_result["agent_id"]

        # Import the spawn function
        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager()

        # Use MCP tool to log sub-agent spawn
        async with db_manager.get_session_async() as session:
            from fastmcp import FastMCP

            from src.giljo_mcp.tenant import TenantManager
            from src.giljo_mcp.tools.agent import register_agent_tools

            mcp = FastMCP("test-server")
            tenant_manager = TenantManager()
            register_agent_tools(mcp, db_manager, tenant_manager)

            # Get the tool function
            spawn_tool = None
            for tool in mcp.list_tools():
                if tool.name == "spawn_and_log_sub_agent":
                    spawn_tool = mcp._tools[tool.name]
                    break

            assert spawn_tool is not None, "spawn_and_log_sub_agent tool not registered"

            # Call the tool
            result = await spawn_tool(
                project_id=str(test_project.id),
                parent_agent_name="orchestrator",
                sub_agent_name="database-expert",
                mission="Design schema",
                meta_data={"test": "data"},
            )

            assert result["success"]
            assert result["sub_agent"] == "database-expert"
            assert result["mission"] == "Design schema"
            assert "interaction_id" in result

            # Verify interaction record was created
            interaction_query = select(AgentInteraction).where(AgentInteraction.id == result["interaction_id"])
            interaction_result = await session.execute(interaction_query)
            interaction = interaction_result.scalar_one_or_none()

            assert interaction is not None
            assert interaction.sub_agent_name == "database-expert"
            assert interaction.mission == "Design schema"
            assert interaction.interaction_type == "SPAWN"
            assert interaction.start_time is not None
            assert interaction.end_time is None  # Not completed yet
            assert interaction.meta_data == {"test": "data"}

    @pytest.mark.asyncio
    async def test_log_sub_agent_completion_updates_interaction(self, db_session, test_project):
        """Test log_sub_agent_completion updates AgentInteraction record"""
        # VALIDATION: Completion tracking works

        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            from fastmcp import FastMCP

            from src.giljo_mcp.tenant import TenantManager
            from src.giljo_mcp.tools.agent import register_agent_tools

            mcp = FastMCP("test-server")
            tenant_manager = TenantManager()
            register_agent_tools(mcp, db_manager, tenant_manager)

            # First, spawn a sub-agent
            spawn_tool = mcp._tools["spawn_and_log_sub_agent"]
            spawn_result = await spawn_tool(
                project_id=str(test_project.id),
                parent_agent_name="orchestrator",
                sub_agent_name="tester",
                mission="Run integration tests",
            )

            interaction_id = spawn_result["interaction_id"]

            # Now complete it
            complete_tool = mcp._tools["log_sub_agent_completion"]
            complete_result = await complete_tool(
                interaction_id=interaction_id, result="All tests passed", tokens_used=15000
            )

            assert complete_result["success"]
            assert complete_result["status"] == "completed"
            assert complete_result["tokens_used"] == 15000

            # Verify interaction was updated
            interaction_query = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
            interaction_result = await session.execute(interaction_query)
            interaction = interaction_result.scalar_one_or_none()

            assert interaction.end_time is not None
            assert interaction.duration_seconds is not None
            assert interaction.tokens_used == 15000
            assert interaction.result == "All tests passed"
            assert interaction.interaction_type == "COMPLETE"

    @pytest.mark.asyncio
    async def test_log_sub_agent_error(self, db_session, test_project):
        """Test logging sub-agent errors"""
        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            from fastmcp import FastMCP

            from src.giljo_mcp.tenant import TenantManager
            from src.giljo_mcp.tools.agent import register_agent_tools

            mcp = FastMCP("test-server")
            tenant_manager = TenantManager()
            register_agent_tools(mcp, db_manager, tenant_manager)

            # Spawn sub-agent
            spawn_result = await mcp._tools["spawn_and_log_sub_agent"](
                project_id=str(test_project.id),
                parent_agent_name="orchestrator",
                sub_agent_name="buggy-agent",
                mission="Fail spectacularly",
            )

            interaction_id = spawn_result["interaction_id"]

            # Log error
            error_result = await mcp._tools["log_sub_agent_completion"](
                interaction_id=interaction_id, error_message="Database connection failed", tokens_used=5000
            )

            assert error_result["success"]
            assert error_result["status"] == "error"

            # Verify error was logged
            interaction_query = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
            interaction_result = await session.execute(interaction_query)
            interaction = interaction_result.scalar_one_or_none()

            assert interaction.interaction_type == "ERROR"
            assert interaction.error_message == "Database connection failed"
            assert interaction.tokens_used == 5000


class TestAutomationGapValidation:
    """Test to CONFIRM the absence of automation infrastructure"""

    def test_no_task_tool_class_exists(self):
        """NEGATIVE TEST: Verify TaskTool class does NOT exist"""
        # VALIDATION: Automation gap confirmed

        try:
            from src.giljo_mcp.tools.claude_code_integration import TaskTool

            pytest.fail("TaskTool class should NOT exist - automation gap not confirmed")
        except ImportError:
            pass  # Expected - class doesn't exist
        except AttributeError:
            pass  # Expected - class doesn't exist

    def test_no_claude_code_client_exists(self):
        """NEGATIVE TEST: Verify ClaudeCodeClient does NOT exist"""
        # VALIDATION: Automation gap confirmed

        try:
            from src.giljo_mcp.tools.claude_code_integration import ClaudeCodeClient

            pytest.fail("ClaudeCodeClient should NOT exist - automation gap not confirmed")
        except ImportError:
            pass  # Expected - class doesn't exist
        except AttributeError:
            pass  # Expected - class doesn't exist

    def test_no_spawn_claude_code_agent_function(self):
        """NEGATIVE TEST: Verify spawn_claude_code_agent function does NOT exist"""
        # VALIDATION: Automation gap confirmed

        try:
            from src.giljo_mcp.tools.claude_code_integration import spawn_claude_code_agent

            pytest.fail("spawn_claude_code_agent should NOT exist - automation gap not confirmed")
        except ImportError:
            pass  # Expected - function doesn't exist
        except AttributeError:
            pass  # Expected - function doesn't exist

    def test_no_subprocess_spawning_in_integration_module(self):
        """NEGATIVE TEST: Verify no subprocess spawning in claude_code_integration.py"""
        # VALIDATION: No process management for Claude Code

        integration_file = (
            Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "tools" / "claude_code_integration.py"
        )
        content = integration_file.read_text()

        # Verify no subprocess imports or calls
        assert "import subprocess" not in content
        assert "from subprocess" not in content
        assert "subprocess.Popen" not in content
        assert "subprocess.run" not in content
        assert "subprocess.call" not in content

    def test_no_automated_spawning_in_agent_module(self):
        """NEGATIVE TEST: Verify agent.py only has LOGGING functions, not spawning"""
        # VALIDATION: Only manual tracking, no automation

        agent_file = Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "tools" / "agent.py"
        content = agent_file.read_text()

        # Verify tracking functions exist
        assert "spawn_and_log_sub_agent" in content
        assert "log_sub_agent_completion" in content

        # Verify NO automation infrastructure
        assert "TaskTool" not in content
        assert "ClaudeCodeClient" not in content
        assert "subprocess.Popen" not in content  # No process spawning

        # The functions should ONLY create database records, not spawn processes
        assert "AgentInteraction" in content  # Database model usage

    def test_manual_workflow_only(self):
        """POSITIVE TEST: Confirm system supports MANUAL workflow only"""
        # VALIDATION: Manual workflow infrastructure exists, automation doesn't

        from src.giljo_mcp.tools.claude_code_integration import generate_orchestrator_prompt, get_claude_code_agent_type

        # These functions exist (manual workflow)
        assert callable(generate_orchestrator_prompt)
        assert callable(get_claude_code_agent_type)

        # But they return prompts/mappings, not spawn agents
        result = get_claude_code_agent_type("database")
        assert isinstance(result, str)  # Just a string mapping, not an agent object


class TestManualWorkflowDocumentation:
    """Test that the system is designed for manual developer workflow"""

    @pytest.mark.asyncio
    async def test_orchestrator_prompt_instructs_manual_mcp_calls(self, db_session, test_project):
        """Test that generated prompts instruct developers to make manual MCP calls"""
        # VALIDATION: System is designed for manual operation

        agent = Agent(
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            name="test-agent",
            role="database",
            status="active",
            mission="Test",
        )
        db_session.add(agent)
        await db_session.commit()

        prompt = generate_orchestrator_prompt(project_id=str(test_project.id), tenant_key=test_project.tenant_key)

        # Verify prompt contains instructions for MANUAL workflow
        assert "Read full agent details from MCP" in prompt
        assert "using `mcp__giljo-mcp__list_agents`" in prompt

        # Verify it mentions Task tool (for manual use by developer)
        assert "Task" in prompt

        # But does NOT provide automation code or scripts
        assert "#!/usr/bin/env python" not in prompt  # No script
        assert "subprocess" not in prompt  # No automation
        assert "automatically spawn" not in prompt.lower()  # No automation claims

    def test_tracking_functions_require_manual_invocation(self):
        """Test that tracking functions must be called manually by developers"""
        # VALIDATION: No automatic invocation mechanism

        from src.giljo_mcp.tools import agent

        # These functions exist but have no automatic trigger
        assert hasattr(agent, "register_agent_tools")

        # No scheduler, no event loop, no automatic invocation
        source = Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "tools" / "agent.py"
        content = source.read_text()

        assert "threading.Timer" not in content
        assert "asyncio.create_task" not in content  # No background tasks
        assert "celery" not in content  # No task queue
        assert "schedule.every" not in content  # No scheduler


class TestContextBudgetTracking:
    """Test context budget tracking in manual workflow"""

    @pytest.mark.asyncio
    async def test_context_budget_tracked_on_completion(self, db_session, test_project):
        """Test that token usage is tracked when sub-agent completes"""
        # VALIDATION: Manual tracking works correctly

        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            from fastmcp import FastMCP

            from src.giljo_mcp.tenant import TenantManager
            from src.giljo_mcp.tools.agent import register_agent_tools

            mcp = FastMCP("test-server")
            tenant_manager = TenantManager()
            register_agent_tools(mcp, db_manager, tenant_manager)

            # Create parent agent
            parent = Agent(
                project_id=test_project.id,
                tenant_key=test_project.tenant_key,
                name="orchestrator",
                role="orchestrator",
                status="active",
                context_used=0,
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)

            # Spawn and complete sub-agent with token usage
            spawn_result = await mcp._tools["spawn_and_log_sub_agent"](
                project_id=str(test_project.id),
                parent_agent_name="orchestrator",
                sub_agent_name="worker",
                mission="Do work",
            )

            # Get parent agent's initial context
            await session.refresh(parent)
            initial_context = parent.context_used

            # Complete with token usage
            await mcp._tools["log_sub_agent_completion"](
                interaction_id=spawn_result["interaction_id"], tokens_used=20000, result="Work completed"
            )

            # Verify parent agent context was updated
            await session.refresh(parent)
            assert parent.context_used == initial_context + 20000

    @pytest.mark.asyncio
    async def test_project_description_budget_updated(self, db_session, test_project):
        """Test that project-level context budget is updated"""
        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            from fastmcp import FastMCP

            from src.giljo_mcp.tenant import TenantManager
            from src.giljo_mcp.tools.agent import register_agent_tools

            mcp = FastMCP("test-server")
            tenant_manager = TenantManager()
            register_agent_tools(mcp, db_manager, tenant_manager)

            # Create parent agent
            parent = Agent(
                project_id=test_project.id,
                tenant_key=test_project.tenant_key,
                name="orchestrator",
                role="orchestrator",
                status="active",
            )
            session.add(parent)
            await session.commit()

            initial_project_description = test_project.context_used

            # Spawn and complete sub-agent
            spawn_result = await mcp._tools["spawn_and_log_sub_agent"](
                project_id=str(test_project.id),
                parent_agent_name="orchestrator",
                sub_agent_name="worker",
                mission="Do work",
            )

            await mcp._tools["log_sub_agent_completion"](
                interaction_id=spawn_result["interaction_id"], tokens_used=15000, result="Done"
            )

            # Refresh project and verify context updated
            await session.refresh(test_project)
            assert test_project.context_used == initial_project_description + 15000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
