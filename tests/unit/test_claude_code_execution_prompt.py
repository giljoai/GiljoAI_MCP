"""
Unit tests for Claude Code execution prompt generation.

Tests for _build_claude_code_execution_prompt() method in ThinClientPromptGenerator.
Validates all 7 required sections per Handover 0337 Task 3.

Handover: 0337 Task 3
Priority: P0 (Critical blocker - agent_display_name field missing)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


class TestClaudeCodeExecutionPrompt:
    """Test suite for Claude Code execution prompt generation."""

    @pytest.fixture
    def generator(self):
        """Create ThinClientPromptGenerator instance."""
        mock_db = Mock()  # Mock database session
        return ThinClientPromptGenerator(db=mock_db, tenant_key="test-tenant-123")

    @pytest.fixture
    def mock_project(self):
        """Mock project object."""
        project = Mock()
        project.id = "proj-123"
        project.product_id = "prod-456"
        project.name = "Test Project"
        return project

    @pytest.fixture
    def mock_agent_jobs(self):
        """Mock agent jobs list."""
        job1 = Mock()
        job1.job_id = "job-abc-123"
        job1.agent_display_name = "implementer"  # CRITICAL: This field must be present
        job1.agent_name = "Folder Structure Implementer"
        job1.status = "waiting"
        job1.mission = "Create project folder structure with src/, tests/, docs/ directories"

        job2 = Mock()
        job2.job_id = "job-def-456"
        job2.agent_display_name = "tester"
        job2.agent_name = "Unit Test Developer"
        job2.status = "waiting"
        job2.mission = "Write comprehensive unit tests for folder structure validator"

        return [job1, job2]

    def test_section_1_context_recap_present(self, generator, mock_project, mock_agent_jobs):
        """
        Section 1: Context Recap

        MUST include:
        - "Who You Are" heading
        - "PREVIOUS session" language
        - "Current State" heading
        - Reference to staging completion
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Context recap headers
        assert "## Who You Are" in prompt, "Missing 'Who You Are' section"
        assert "## What You've Already Done" in prompt, "Missing 'What You've Already Done' section"
        assert "## Current State" in prompt, "Missing 'Current State' section"

        # PREVIOUS session language
        assert "PREVIOUS session" in prompt, "Missing 'PREVIOUS session' language"
        assert "completed staging" in prompt, "Missing staging completion reference"

        # Identity information
        assert "orch-789" in prompt, "Missing orchestrator ID"
        assert "test-tenant-123" in prompt, "Missing tenant key"

    def test_section_2_agent_display_name_field_present(self, generator, mock_project, mock_agent_jobs):
        """
        Section 2: Agent Jobs List (CRITICAL P0 BLOCKER)

        MUST include agent_display_name field for each job:
        - Agent Type: `implementer` (matches .claude/agents/implementer.md)
        - Job ID: job-abc-123
        - Status: waiting
        - Mission Summary: ...

        WITHOUT agent_display_name: Task tool cannot spawn agents (blocker)
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # CRITICAL: agent_display_name field must be present
        assert "Agent Type:" in prompt, "CRITICAL BLOCKER: Missing 'Agent Type:' field"
        assert "`implementer`" in prompt, "Missing agent_display_name value for first job"
        assert "`tester`" in prompt, "Missing agent_display_name value for second job"

        # Template file reference
        assert ".claude/agents/" in prompt, "Missing .claude/agents/ template file reference"

        # Job identifiers
        assert "job-abc-123" in prompt, "Missing job_id for first job"
        assert "job-def-456" in prompt, "Missing job_id for second job"

        # Status
        assert "waiting" in prompt, "Missing job status"

        # Agent names (display names)
        assert "Folder Structure Implementer" in prompt, "Missing agent_name for first job"
        assert "Unit Test Developer" in prompt, "Missing agent_name for second job"

    def test_section_2_agent_display_name_vs_agent_name_distinction(self, generator, mock_project, mock_agent_jobs):
        """
        Section 2: Verify agent_display_name vs agent_name distinction is clear.

        agent_display_name: Technical ID (e.g., "implementer") - matches .claude/agents/implementer.md
        agent_name: Display name (e.g., "Folder Structure Implementer")

        Task tool requires agent_display_name, NOT agent_name.
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Both should be present but clearly distinguished
        assert "Agent Type:" in prompt, "Missing agent_display_name field"
        assert "implementer" in prompt, "Missing agent_display_name value"
        assert "Folder Structure Implementer" in prompt, "Missing agent_name value"

        # Should reference that agent_display_name matches template file
        assert (
            ".claude/agents/implementer.md" in prompt or ".claude/agents/{agent_display_name}.md" in prompt
        ), "Missing template file naming convention reference"

    def test_section_3_task_tool_template_present(self, generator, mock_project, mock_agent_jobs):
        """
        Section 3: Task Tool Spawning Template

        MUST include:
        - Spawning template with exact syntax
        - Concrete example using real job_id
        - Parallel spawning instructions
        - get_agent_mission() call pattern
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Template section
        assert (
            "### Spawning Template" in prompt or "Task Tool Template" in prompt
        ), "Missing Task tool spawning template section"

        # Task() syntax
        assert "Task(" in prompt, "Missing Task() syntax reference"

        # Example with concrete job_id
        assert "job-abc-123" in prompt, "Missing concrete job_id in example"

        # Parallel spawning guidance
        assert "parallel" in prompt.lower(), "Missing parallel spawning guidance"

        # get_agent_mission() call
        assert "get_agent_mission" in prompt, "Missing get_agent_mission() reference"

    def test_section_4_monitoring_instructions_complete(self, generator, mock_project, mock_agent_jobs):
        """
        Section 4: Monitoring Instructions (Enhanced)

        MUST include:
        - get_workflow_status() with return value examples
        - Message handling instructions
        - Blocker detection and response
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Monitoring tools
        assert "get_workflow_status" in prompt, "Missing get_workflow_status() reference"

        # Message handling
        assert "message" in prompt.lower(), "Missing message handling instructions"

        # Blocker handling
        assert "blocker" in prompt.lower() or "blocked" in prompt.lower(), "Missing blocker handling instructions"

    def test_section_5_context_refresh_present(self, generator, mock_project, mock_agent_jobs):
        """
        Section 5: Context Refresh Capability

        MUST include:
        - get_orchestrator_instructions() call pattern
        - Explanation of when to refresh context
        - MCP tool usage for re-reading mission
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Context refresh capability
        assert (
            "get_orchestrator_instructions" in prompt or "refresh" in prompt.lower()
        ), "Missing context refresh capability"

        # MCP tool reference
        assert "MCP" in prompt or "mcp" in prompt, "Missing MCP tool reference"

    def test_section_6_cli_mode_constraints_present(self, generator, mock_project, mock_agent_jobs):
        """
        Section 6: CLI Mode Constraints (CRITICAL P0 BLOCKER)

        MUST include:
        - Template file warnings (.claude/agents/{agent_display_name}.md)
        - Exact naming requirements (agent_display_name vs agent_name)
        - MCP communication constraints
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # CLI Mode Constraints section
        assert "## CLI Mode Constraints" in prompt or "CLI Mode" in prompt, "Missing CLI Mode Constraints section"

        # Template file warnings
        assert ".claude/agents/" in prompt, "Missing template file path reference"
        assert "WARNING" in prompt or "Warning" in prompt, "Missing warning language"

        # Naming conventions
        assert "agent_display_name" in prompt, "Missing agent_display_name naming reference"
        assert "agent_name" in prompt or "agent name" in prompt.lower(), "Missing agent_name distinction"

        # MCP communication
        assert "MCP" in prompt or "mcp" in prompt, "Missing MCP communication reference"

    def test_section_7_completion_instructions_present(self, generator, mock_project, mock_agent_jobs):
        """
        Section 7: Completion Instructions

        MUST include:
        - Sub-agent completion verification
        - Orchestrator job completion (complete_job)
        - Handover protocol if needed
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Completion instructions
        assert "complete_job" in prompt or "completion" in prompt.lower(), "Missing completion instructions"

        # Sub-agent verification
        assert "sub-agent" in prompt.lower() or "agent" in prompt.lower(), "Missing sub-agent reference"

    def test_all_sections_present_integration(self, generator, mock_project, mock_agent_jobs):
        """
        Integration test: Verify all 7 sections are present in correct order.

        Expected structure:
        1. Context Recap
        2. Agent Jobs List
        3. Task Tool Spawning
        4. Monitoring Instructions
        5. Context Refresh
        6. CLI Mode Constraints
        7. Completion Instructions
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # All critical sections present
        required_sections = [
            "Who You Are",  # Section 1
            "Agent Type:",  # Section 2 (P0 blocker)
            "Task(",  # Section 3
            "get_workflow_status",  # Section 4
            "CLI Mode",  # Section 6 (P0 blocker)
        ]

        for section in required_sections:
            assert section in prompt, f"Missing critical section: {section}"

    def test_empty_agent_jobs_list(self, generator, mock_project):
        """
        Edge case: Empty agent jobs list should not crash.

        Should show appropriate message about no agents spawned yet.
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=[]
        )

        assert (
            "No agents spawned" in prompt or "no agents" in prompt.lower()
        ), "Missing handling for empty agent jobs list"

        # Should still have core sections
        assert "Who You Are" in prompt, "Missing context recap even with no agents"

    def test_long_mission_truncation(self, generator, mock_project):
        """
        Test that long missions are truncated in the jobs list.

        Full mission should not be in the summary (use "..." for truncation).
        """
        job = Mock()
        job.job_id = "job-123"
        job.agent_display_name = "implementer"
        job.agent_name = "Test Agent"
        job.status = "waiting"
        job.mission = "A" * 500  # Very long mission

        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=[job]
        )

        # Should show truncation indicator
        assert "..." in prompt, "Missing mission truncation for long missions"

        # Full mission should not be present (would be 500+ chars)
        assert "A" * 500 not in prompt, "Long mission not truncated"

    def test_tenant_key_propagation(self, generator, mock_project, mock_agent_jobs):
        """
        Verify tenant_key is included in all relevant sections.

        Critical for multi-tenant isolation.
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Tenant key should appear in:
        # 1. Identity section
        assert "test-tenant-123" in prompt, "Missing tenant_key in prompt"

        # Should appear in MCP tool call examples
        assert "tenant_key" in prompt.lower(), "Missing tenant_key parameter in tool calls"

    def test_orchestrator_id_consistency(self, generator, mock_project, mock_agent_jobs):
        """
        Verify orchestrator_id is consistently referenced throughout prompt.
        """
        orchestrator_id = "orch-xyz-789"

        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id=orchestrator_id, project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Orchestrator ID should appear at least once
        assert orchestrator_id in prompt, "Missing orchestrator_id in prompt"

    def test_project_metadata_included(self, generator, mock_project, mock_agent_jobs):
        """
        Verify project metadata is included in identity section.

        Should include: project_id, product_id, project_name
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # Project metadata
        assert "proj-123" in prompt, "Missing project_id"
        assert "prod-456" in prompt, "Missing product_id"
        assert "Test Project" in prompt, "Missing project name"

    def test_p0_blockers_all_fixed(self, generator, mock_project, mock_agent_jobs):
        """
        Master test: Verify all P0 blockers are resolved.

        P0 Blockers (from Deep Researcher analysis):
        1. agent_display_name field in Section 2
        2. Section 1 (Context Recap)
        3. Section 3 (Task Tool Template)
        4. Section 6 (CLI Mode Constraints)
        """
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-789", project=mock_project, agent_jobs=mock_agent_jobs
        )

        # P0 Blocker #1: agent_display_name field
        assert "Agent Type:" in prompt, "P0 BLOCKER #1: Missing agent_display_name field"
        assert "`implementer`" in prompt, "P0 BLOCKER #1: Missing agent_display_name value"

        # P0 Blocker #2: Context Recap
        assert "Who You Are" in prompt, "P0 BLOCKER #2: Missing Context Recap section"
        assert "PREVIOUS session" in prompt, "P0 BLOCKER #2: Missing PREVIOUS session language"

        # P0 Blocker #3: Task Tool Template
        assert "Task(" in prompt, "P0 BLOCKER #3: Missing Task tool template"
        assert "job-abc-123" in prompt, "P0 BLOCKER #3: Missing concrete example"

        # P0 Blocker #4: CLI Mode Constraints
        assert "CLI Mode" in prompt, "P0 BLOCKER #4: Missing CLI Mode Constraints section"
        assert ".claude/agents/" in prompt, "P0 BLOCKER #4: Missing template file reference"
