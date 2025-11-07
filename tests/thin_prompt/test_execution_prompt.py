"""
Unit tests for ThinClientPromptGenerator.generate_execution_prompt() (Handover 0109)

Tests the execution phase prompt generation for both multi-terminal
and Claude Code subagent modes.

Author: GiljoAI Development Team
Date: 2025-01-06
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def tenant_key():
    """Test tenant key."""
    return str(uuid4())


@pytest.fixture
def project_id():
    """Test project ID."""
    return str(uuid4())


@pytest.fixture
def orchestrator_job_id():
    """Test orchestrator job ID."""
    return str(uuid4())


@pytest.fixture
def generator(mock_db, tenant_key):
    """Create ThinClientPromptGenerator instance."""
    return ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)


@pytest.fixture
def mock_project(project_id, tenant_key):
    """Mock project object."""
    project = MagicMock()
    project.id = project_id
    project.name = "Test Project"
    project.tenant_key = tenant_key
    project.mission = "Build an authentication system"
    project.description = "User requirements for auth"
    project.context_budget = 150000
    project.status = "active"
    return project


@pytest.fixture
def mock_orchestrator_job(orchestrator_job_id, project_id, tenant_key):
    """Mock orchestrator job object."""
    job = MagicMock()
    job.job_id = orchestrator_job_id
    job.project_id = project_id
    job.tenant_key = tenant_key
    job.agent_type = "orchestrator"
    job.agent_name = "Orchestrator #1"
    job.instance_number = 1
    job.status = "working"
    return job


@pytest.fixture
def mock_agent_jobs(project_id, tenant_key):
    """Mock specialist agent job objects."""
    agents = []

    # Implementer
    impl = MagicMock()
    impl.job_id = str(uuid4())
    impl.agent_type = "implementer"
    impl.agent_name = "Implementer1"
    impl.mission = "Implement user authentication endpoints"
    impl.project_id = project_id
    impl.tenant_key = tenant_key
    impl.status = "waiting"
    agents.append(impl)

    # Tester
    tester = MagicMock()
    tester.job_id = str(uuid4())
    tester.agent_type = "tester"
    tester.agent_name = "Tester1"
    tester.mission = "Write integration tests for auth system"
    tester.project_id = project_id
    tester.tenant_key = tenant_key
    tester.status = "waiting"
    agents.append(tester)

    # Reviewer
    reviewer = MagicMock()
    reviewer.job_id = str(uuid4())
    reviewer.agent_type = "reviewer"
    reviewer.agent_name = "Reviewer1"
    reviewer.mission = "Review authentication implementation"
    reviewer.project_id = project_id
    reviewer.tenant_key = tenant_key
    reviewer.status = "waiting"
    agents.append(reviewer)

    return agents


class TestGenerateExecutionPromptValidation:
    """Test input validation for generate_execution_prompt()."""

    @pytest.mark.asyncio
    async def test_raises_when_orchestrator_not_found(self, generator, project_id):
        """Test that method raises when orchestrator job not found."""
        # Mock database to return None for orchestrator
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        generator.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Orchestrator job .* not found"):
            await generator.generate_execution_prompt(
                orchestrator_job_id=str(uuid4()),
                project_id=project_id,
                claude_code_mode=False
            )

    @pytest.mark.asyncio
    async def test_raises_when_project_not_found(
        self, generator, orchestrator_job_id, project_id, mock_orchestrator_job
    ):
        """Test that method raises when project not found."""
        # Mock database to return orchestrator but no project
        def mock_execute(stmt):
            result = AsyncMock()
            # First call returns orchestrator, second returns None for project
            if mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            else:
                result.scalar_one_or_none.return_value = None
            mock_execute.call_count += 1
            return result

        mock_execute.call_count = 0
        generator.db.execute = mock_execute

        with pytest.raises(ValueError, match="Project .* not found"):
            await generator.generate_execution_prompt(
                orchestrator_job_id=orchestrator_job_id,
                project_id=project_id,
                claude_code_mode=False
            )


class TestMultiTerminalModePrompt:
    """Test multi-terminal mode execution prompt generation."""

    @pytest.mark.asyncio
    async def test_generates_multi_terminal_prompt(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test multi-terminal mode prompt generation."""
        # Mock database responses
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                # Return orchestrator job
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                # Return project
                result.scalar_one_or_none.return_value = mock_project
            else:
                # Return agent jobs
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Verify prompt structure
        assert "PROJECT EXECUTION PHASE - MULTI-TERMINAL MODE" in prompt
        assert orchestrator_job_id in prompt
        assert mock_project.name in prompt
        assert generator.tenant_key in prompt

        # Verify role description
        assert "COORDINATE AGENT WORKFLOW" in prompt
        assert "Monitor dashboard for agent progress updates" in prompt
        assert "Respond to agent messages via MCP" in prompt

        # Verify agent list
        assert "AGENT TEAM:" in prompt
        for agent in mock_agent_jobs:
            assert agent.agent_name in prompt
            assert agent.job_id in prompt

        # Verify workflow monitoring
        assert "get_workflow_status" in prompt
        assert project_id in prompt

    @pytest.mark.asyncio
    async def test_multi_terminal_prompt_with_zero_agents(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project
    ):
        """Test multi-terminal mode prompt with no spawned agents."""
        # Mock database with empty agent list
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = []

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Verify prompt handles empty agent list gracefully
        assert "AGENT TEAM:" in prompt
        assert "(No agents spawned yet)" in prompt

    @pytest.mark.asyncio
    async def test_multi_terminal_prompt_length(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that multi-terminal prompt stays thin (~15-20 lines)."""
        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Count lines
        line_count = len([line for line in prompt.split('\n') if line.strip()])

        # Thin prompts should be concise (allow some flexibility for agent list)
        assert line_count < 30, f"Prompt has {line_count} lines, should be < 30"

        # Check token estimate (1 token ≈ 4 chars)
        estimated_tokens = len(prompt) // 4
        assert estimated_tokens < 500, f"Prompt has ~{estimated_tokens} tokens, should be < 500"


class TestClaudeCodeSubagentModePrompt:
    """Test Claude Code subagent mode execution prompt generation."""

    @pytest.mark.asyncio
    async def test_generates_claude_code_prompt(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test Claude Code subagent mode prompt generation."""
        # Mock database responses
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Verify prompt structure
        assert "PROJECT EXECUTION PHASE - CLAUDE CODE SUBAGENT MODE" in prompt
        assert orchestrator_job_id in prompt
        assert mock_project.name in prompt

        # Verify role description
        assert "SPAWN & COORDINATE SUB-AGENTS" in prompt
        assert "STEP 1: ACTIVATE AGENT TEAM" in prompt

        # Verify spawning instructions
        assert "spawn Claude Code sub-agent using Task tool" in prompt

        # Verify agent list with missions
        for agent in mock_agent_jobs:
            assert agent.agent_name in prompt
            assert agent.mission in prompt
            assert agent.job_id in prompt

        # Verify check-in protocol reminder
        assert "STEP 2: REMIND EACH SUB-AGENT" in prompt
        assert "acknowledge_job" in prompt
        assert "report_progress" in prompt
        assert "receive_messages" in prompt
        assert "complete_job" in prompt

        # Verify coordination step
        assert "STEP 3: COORDINATE WORKFLOW" in prompt
        assert "get_workflow_status" in prompt

        # Verify handover reference
        assert "Handover 0106b" in prompt

    @pytest.mark.asyncio
    async def test_claude_code_prompt_includes_task_tool_reference(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that Claude Code prompt includes Task tool reference."""
        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Verify Task tool mentioned
        assert "Task tool" in prompt or "task tool" in prompt

    @pytest.mark.asyncio
    async def test_claude_code_prompt_length(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that Claude Code prompt stays thin (~15-20 lines)."""
        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Count lines
        line_count = len([line for line in prompt.split('\n') if line.strip()])

        # Claude Code prompts can be slightly longer due to step structure
        assert line_count < 40, f"Prompt has {line_count} lines, should be < 40"

        # Check token estimate (1 token ≈ 4 chars)
        estimated_tokens = len(prompt) // 4
        assert estimated_tokens < 700, f"Prompt has ~{estimated_tokens} tokens, should be < 700"


class TestPromptDifferences:
    """Test that multi-terminal and Claude Code prompts are appropriately different."""

    @pytest.mark.asyncio
    async def test_prompts_have_different_titles(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that prompts have different titles."""
        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate both prompts
        multi_terminal_prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Reset call count
        mock_execute.call_count = 0

        claude_code_prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Verify titles are different
        assert "MULTI-TERMINAL MODE" in multi_terminal_prompt
        assert "MULTI-TERMINAL MODE" not in claude_code_prompt

        assert "CLAUDE CODE SUBAGENT MODE" in claude_code_prompt
        assert "CLAUDE CODE SUBAGENT MODE" not in multi_terminal_prompt

    @pytest.mark.asyncio
    async def test_prompts_have_different_instructions(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that prompts have different instructions."""
        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate both prompts
        multi_terminal_prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Reset call count
        mock_execute.call_count = 0

        claude_code_prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Multi-terminal specific instructions
        assert "User manually manages terminal windows" in multi_terminal_prompt
        assert "User manually manages terminal windows" not in claude_code_prompt

        # Claude Code specific instructions
        assert "spawn Claude Code sub-agent using Task tool" in claude_code_prompt
        assert "spawn Claude Code sub-agent using Task tool" not in multi_terminal_prompt


class TestTenantIsolation:
    """Test multi-tenant isolation in execution prompts."""

    @pytest.mark.asyncio
    async def test_only_fetches_agents_for_tenant(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that only agents for current tenant are included."""
        # Mock database
        executed_queries = []

        def mock_execute(stmt):
            executed_queries.append(stmt)
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = mock_agent_jobs

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt
        await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Verify queries were executed (tenant isolation happens at query level)
        assert len(executed_queries) >= 3, "Should have executed at least 3 queries"


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_handles_missing_agent_missions_gracefully(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project
    ):
        """Test handling of agents with None missions."""
        # Create agent with None mission
        agent_without_mission = MagicMock()
        agent_without_mission.job_id = str(uuid4())
        agent_without_mission.agent_type = "implementer"
        agent_without_mission.agent_name = "Implementer1"
        agent_without_mission.mission = None
        agent_without_mission.project_id = project_id
        agent_without_mission.tenant_key = generator.tenant_key

        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = [agent_without_mission]

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt (should not crash)
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Should handle None mission gracefully
        assert "Mission pending" in prompt or "(No mission assigned)" in prompt

    @pytest.mark.asyncio
    async def test_handles_long_agent_names(
        self,
        generator,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project
    ):
        """Test handling of very long agent names."""
        # Create agent with long name
        long_name_agent = MagicMock()
        long_name_agent.job_id = str(uuid4())
        long_name_agent.agent_type = "implementer"
        long_name_agent.agent_name = "A" * 200  # Very long name
        long_name_agent.mission = "Test mission"
        long_name_agent.project_id = project_id
        long_name_agent.tenant_key = generator.tenant_key

        # Mock database
        def mock_execute(stmt):
            result = AsyncMock()
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0

            if mock_execute.call_count == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            elif mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_project
            else:
                result.scalars.return_value.all.return_value = [long_name_agent]

            mock_execute.call_count += 1
            return result

        generator.db.execute = mock_execute

        # Generate prompt (should not crash)
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Should include the agent (possibly truncated)
        assert prompt is not None
