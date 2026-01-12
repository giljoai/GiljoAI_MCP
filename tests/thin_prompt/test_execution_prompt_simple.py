"""
Simplified unit tests for ThinClientPromptGenerator.generate_execution_prompt() (Handover 0109)

Tests the execution phase prompt generation for both multi-terminal
and Claude Code subagent modes with simplified mocking.

Author: GiljoAI Development Team
Date: 2025-01-06
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


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
def mock_orchestrator_job(orchestrator_job_id, project_id, tenant_key):
    """Mock orchestrator job object."""
    job = MagicMock()
    job.job_id = orchestrator_job_id
    job.project_id = project_id
    job.tenant_key = tenant_key
    job.agent_display_name = "orchestrator"
    job.agent_name = "Orchestrator #1"
    job.instance_number = 1
    job.status = "working"
    return job


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
def mock_agent_jobs(project_id, tenant_key):
    """Mock specialist agent job objects."""
    agents = []

    # Implementer
    impl = MagicMock()
    impl.job_id = str(uuid4())
    impl.agent_display_name = "implementer"
    impl.agent_name = "Implementer1"
    impl.mission = "Implement user authentication endpoints"
    impl.project_id = project_id
    impl.tenant_key = tenant_key
    impl.status = "waiting"
    agents.append(impl)

    # Tester
    tester = MagicMock()
    tester.job_id = str(uuid4())
    tester.agent_display_name = "tester"
    tester.agent_name = "Tester1"
    tester.mission = "Write integration tests for auth system"
    tester.project_id = project_id
    tester.tenant_key = tenant_key
    tester.status = "waiting"
    agents.append(tester)

    return agents


def create_async_db_mock(orchestrator, project, agents):
    """Create async database mock."""
    call_count = [0]

    async def mock_execute(stmt):
        result = MagicMock()
        if call_count[0] == 0:
            result.scalar_one_or_none.return_value = orchestrator
        elif call_count[0] == 1:
            result.scalar_one_or_none.return_value = project
        else:
            scalars_result = MagicMock()
            scalars_result.all.return_value = agents
            result.scalars.return_value = scalars_result
        call_count[0] += 1
        return result

    return mock_execute


class TestMultiTerminalPrompt:
    """Test multi-terminal mode prompt generation."""

    @pytest.mark.asyncio
    async def test_generates_multi_terminal_prompt(
        self,
        tenant_key,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test multi-terminal mode prompt generation."""
        # Create generator
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)

        # Mock database
        generator.db.execute = create_async_db_mock(
            orchestrator=mock_orchestrator_job,
            project=mock_project,
            agents=mock_agent_jobs
        )

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
        assert tenant_key in prompt

        # Verify role description
        assert "COORDINATE AGENT WORKFLOW" in prompt

        # Verify agent list
        assert "AGENT TEAM:" in prompt
        for agent in mock_agent_jobs:
            assert agent.agent_name in prompt

    @pytest.mark.asyncio
    async def test_multi_terminal_prompt_with_no_agents(
        self,
        tenant_key,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project
    ):
        """Test multi-terminal mode with no agents."""
        # Create generator
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)

        # Mock database with empty agent list
        generator.db.execute = create_async_db_mock(
            orchestrator=mock_orchestrator_job,
            project=mock_project,
            agents=[]
        )

        # Generate prompt
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Verify prompt handles empty agent list
        assert "(No agents spawned yet)" in prompt


class TestClaudeCodePrompt:
    """Test Claude Code subagent mode prompt generation."""

    @pytest.mark.asyncio
    async def test_generates_claude_code_prompt(
        self,
        tenant_key,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test Claude Code subagent mode prompt generation.

        NOTE: generate_execution_prompt() is deprecated and now returns staging prompt.
        This test verifies the deprecated method still works (for backward compatibility)
        and that outdated references are removed (Issue 0361).
        """
        # Create generator
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)

        # Mock database
        generator.db.execute = create_async_db_mock(
            orchestrator=mock_orchestrator_job,
            project=mock_project,
            agents=mock_agent_jobs
        )

        # Generate prompt (deprecated method now returns staging prompt)
        prompt = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Verify basic structure (staging prompt format)
        assert orchestrator_job_id in prompt
        assert "staging" in prompt.lower() or "STAGING" in prompt

        # Verify 0106b reference NOT present (Issue 0361)
        assert "Handover 0106b" not in prompt
        assert "0106b" not in prompt


class TestPromptValidation:
    """Test validation and error handling."""

    @pytest.mark.asyncio
    async def test_raises_when_orchestrator_not_found(
        self,
        tenant_key,
        project_id
    ):
        """Test that method raises when orchestrator not found."""
        # Create generator
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)

        # Mock database to return None
        async def mock_execute(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            return result

        generator.db.execute = mock_execute

        # Should raise ValueError
        with pytest.raises(ValueError, match="Orchestrator job .* not found"):
            await generator.generate_execution_prompt(
                orchestrator_job_id=str(uuid4()),
                project_id=project_id,
                claude_code_mode=False
            )

    @pytest.mark.asyncio
    async def test_raises_when_project_not_found(
        self,
        tenant_key,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job
    ):
        """Test that method raises when project not found."""
        # Create generator
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)

        # Mock database: orchestrator exists, project does not
        call_count = [0]

        async def mock_execute(stmt):
            result = MagicMock()
            if call_count[0] == 0:
                result.scalar_one_or_none.return_value = mock_orchestrator_job
            else:
                result.scalar_one_or_none.return_value = None
            call_count[0] += 1
            return result

        generator.db.execute = mock_execute

        # Should raise ValueError
        with pytest.raises(ValueError, match="Project .* not found"):
            await generator.generate_execution_prompt(
                orchestrator_job_id=orchestrator_job_id,
                project_id=project_id,
                claude_code_mode=False
            )


class TestPromptDifferences:
    """Test that prompts are appropriately different."""

    @pytest.mark.asyncio
    async def test_prompts_have_different_modes(
        self,
        tenant_key,
        orchestrator_job_id,
        project_id,
        mock_orchestrator_job,
        mock_project,
        mock_agent_jobs
    ):
        """Test that multi-terminal and Claude Code prompts differ."""
        # Create generator
        mock_db = MagicMock()
        generator = ThinClientPromptGenerator(db=mock_db, tenant_key=tenant_key)

        # Generate multi-terminal prompt
        generator.db.execute = create_async_db_mock(
            orchestrator=mock_orchestrator_job,
            project=mock_project,
            agents=mock_agent_jobs
        )
        multi_terminal = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=False
        )

        # Generate Claude Code prompt
        generator.db.execute = create_async_db_mock(
            orchestrator=mock_orchestrator_job,
            project=mock_project,
            agents=mock_agent_jobs
        )
        claude_code = await generator.generate_execution_prompt(
            orchestrator_job_id=orchestrator_job_id,
            project_id=project_id,
            claude_code_mode=True
        )

        # Verify differences
        assert "MULTI-TERMINAL MODE" in multi_terminal
        assert "CLAUDE CODE SUBAGENT MODE" in claude_code

        assert "User manually manages terminal windows" in multi_terminal
        assert "spawn Claude Code sub-agent using Task tool" in claude_code

        assert "Task tool" in claude_code
        assert "Task tool" not in multi_terminal
