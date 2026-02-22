"""Tests for git closeout commit prompt injection.

Verifies that the structured closeout commit instruction is conditionally
injected into orchestrator prompts based on git integration toggle.

Covers both prompt paths:
- CLI mode: _build_claude_code_execution_prompt()
- Multi-terminal mode: build_retirement_prompt()
"""

from unittest.mock import MagicMock

import pytest

from src.giljo_mcp.thin_prompt_generator import build_retirement_prompt


# ---------------------------------------------------------------------------
# build_retirement_prompt (multi-terminal mode)
# ---------------------------------------------------------------------------


class TestRetirementPromptGitCloseout:
    """Tests for git closeout commit in retirement prompt."""

    def test_git_disabled_no_closeout_instruction(self):
        """When git_enabled=False, no closeout commit instruction appears."""
        prompt = build_retirement_prompt(
            project_id="proj-123",
            agent_id="agent-456",
            job_id="job-789",
            project_name="Auth System",
            git_enabled=False,
        )
        assert "closeout(" not in prompt
        assert "git commit" not in prompt

    def test_git_enabled_includes_closeout_instruction(self):
        """When git_enabled=True, closeout commit instruction appears."""
        prompt = build_retirement_prompt(
            project_id="proj-123",
            agent_id="agent-456",
            job_id="job-789",
            project_name="Auth System",
            git_enabled=True,
            project_taxonomy="FE-0042a",
        )
        assert "closeout(FE-0042a)" in prompt
        assert "git commit --allow-empty" in prompt
        assert "Auth System" in prompt
        assert 'git log --grep="closeout"' in prompt
        assert 'git log --grep="FE-0042a"' in prompt

    def test_git_enabled_falls_back_to_project_name(self):
        """When taxonomy is empty, falls back to project_name."""
        prompt = build_retirement_prompt(
            project_id="proj-123",
            agent_id="agent-456",
            job_id="job-789",
            project_name="Auth System",
            git_enabled=True,
            project_taxonomy="",
        )
        assert "closeout(Auth System)" in prompt

    def test_git_enabled_falls_back_to_project_id(self):
        """When both taxonomy and name are empty, falls back to project_id prefix."""
        prompt = build_retirement_prompt(
            project_id="abcdef12-3456-7890",
            agent_id="agent-456",
            job_id="job-789",
            git_enabled=True,
        )
        assert "closeout(abcdef12)" in prompt

    def test_closeout_appears_before_360_memory_write(self):
        """Git closeout instruction should appear before the 360 memory write."""
        prompt = build_retirement_prompt(
            project_id="proj-123",
            agent_id="agent-456",
            job_id="job-789",
            project_name="Auth System",
            git_enabled=True,
            project_taxonomy="FE-0042a",
        )
        closeout_pos = prompt.index("closeout(FE-0042a)")
        memory_pos = prompt.index("write_360_memory")
        assert closeout_pos < memory_pos, "Closeout commit must precede 360 memory write"

    def test_retirement_prompt_still_contains_360_memory(self):
        """Git closeout doesn't break existing 360 memory instructions."""
        prompt = build_retirement_prompt(
            project_id="proj-123",
            agent_id="agent-456",
            job_id="job-789",
            project_name="Auth System",
            git_enabled=True,
            project_taxonomy="FE-0042a",
        )
        assert "write_360_memory" in prompt
        assert "entry_type=\"session_handover\"" in prompt
        assert "Do NOT call complete_job()" in prompt


# ---------------------------------------------------------------------------
# _build_claude_code_execution_prompt (CLI mode)
# ---------------------------------------------------------------------------


def _make_mock_project(name="Auth System", taxonomy="FE-0042a"):
    """Create a mock project with taxonomy_alias."""
    project = MagicMock()
    project.name = name
    project.id = "proj-123"
    project.product_id = "prod-456"
    project.taxonomy_alias = taxonomy
    return project


def _make_mock_product(git_enabled=True):
    """Create a mock product with git_integration config."""
    product = MagicMock()
    product.product_memory = {
        "git_integration": {"enabled": git_enabled},
    }
    return product


class TestCLIModeGitCloseout:
    """Tests for git closeout commit in CLI execution prompt."""

    def _build_prompt(self, product=None, project=None):
        """Build CLI execution prompt with mocked dependencies."""
        from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

        generator = ThinClientPromptGenerator.__new__(ThinClientPromptGenerator)
        proj = project or _make_mock_project()
        return generator._build_claude_code_execution_prompt(
            orchestrator_id="orch-001",
            project=proj,
            agent_jobs=[],
            product=product,
        )

    def test_no_product_no_closeout(self):
        """When product is None, no closeout commit instruction."""
        prompt = self._build_prompt(product=None)
        assert "closeout(" not in prompt

    def test_git_disabled_no_closeout(self):
        """When git_integration.enabled=False, no closeout commit."""
        prompt = self._build_prompt(product=_make_mock_product(git_enabled=False))
        assert "closeout(" not in prompt

    def test_git_enabled_includes_closeout(self):
        """When git_integration.enabled=True, closeout commit appears."""
        prompt = self._build_prompt(product=_make_mock_product(git_enabled=True))
        assert "closeout(FE-0042a)" in prompt
        assert "git commit --allow-empty" in prompt
        assert "Auth System" in prompt

    def test_closeout_before_complete_job(self):
        """Git closeout instruction appears before complete_job call."""
        prompt = self._build_prompt(product=_make_mock_product(git_enabled=True))
        closeout_pos = prompt.index("Git Closeout Commit")
        complete_pos = prompt.index("Complete Your Orchestrator Job")
        assert closeout_pos < complete_pos

    def test_product_without_product_memory(self):
        """Product with no product_memory doesn't crash."""
        product = MagicMock()
        product.product_memory = None
        prompt = self._build_prompt(product=product)
        assert "closeout(" not in prompt
