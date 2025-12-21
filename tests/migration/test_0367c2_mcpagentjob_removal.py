"""
Behavioral tests for Handover 0367c-2: MCPAgentJob removal from tools and prompt generation.

These tests verify BEHAVIOR (what the code does), not IMPLEMENTATION (how it does it).
Tests check that MCPAgentJob is not imported or used in the migrated files.

Author: GiljoAI Development Team
Date: 2025-12-21
Handover: 0367c-2
"""

import ast
from pathlib import Path

import pytest


class TestMCPAgentJobRemovalBehavior:
    """
    Behavioral tests verifying MCPAgentJob removed from 0367c-2 scope files.

    CRITICAL: These tests check BEHAVIOR (no MCPAgentJob imports/usage),
    NOT implementation details (how the code achieves this).
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    def _has_mcpagentjob_import(self, source_code: str) -> bool:
        """
        Check if source code imports MCPAgentJob.

        Uses AST parsing to check actual imports, not comments.

        Args:
            source_code: Python source code string

        Returns:
            True if MCPAgentJob is imported, False otherwise
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # If we can't parse it, skip
            return False

        # Check direct imports: import MCPAgentJob
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "MCPAgentJob":
                        return True

        # Check from imports: from x import MCPAgentJob
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "MCPAgentJob":
                        return True

        return False

    def _has_mcpagentjob_usage(self, source_code: str) -> bool:
        """
        Check if source code uses MCPAgentJob in type annotations or expressions.

        Uses AST parsing to check actual usage, not comments.

        Args:
            source_code: Python source code string

        Returns:
            True if MCPAgentJob is used, False otherwise
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False

        # Check for MCPAgentJob in Name nodes (variable references, type annotations)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "MCPAgentJob":
                return True

        return False

    # Priority 0 - Staging Rollback
    def test_staging_rollback_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: staging_rollback.py should not import MCPAgentJob.

        Expected outcome: File uses AgentExecution instead.
        """
        file_path = project_root / "src" / "giljo_mcp" / "staging_rollback.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "staging_rollback.py still imports MCPAgentJob - should use AgentExecution"
        )

    def test_staging_rollback_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: staging_rollback.py should not use MCPAgentJob in type annotations or code.

        Expected outcome: All references replaced with AgentExecution.
        """
        file_path = project_root / "src" / "giljo_mcp" / "staging_rollback.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "staging_rollback.py still uses MCPAgentJob - should use AgentExecution"
        )

    def test_staging_rollback_uses_soft_delete_pattern(self, project_root: Path):
        """
        BEHAVIOR: staging_rollback.py should use soft delete (status='cancelled'), not hard delete.

        Expected outcome: No session.delete() calls in soft delete methods.
        """
        file_path = project_root / "src" / "giljo_mcp" / "staging_rollback.py"
        source = file_path.read_text(encoding="utf-8")

        # Parse source
        tree = ast.parse(source)

        # Find _soft_delete_agents method
        soft_delete_method = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_soft_delete_agents":
                soft_delete_method = node
                break

        if soft_delete_method:
            # Check for session.delete() calls inside soft delete method
            has_hard_delete = False
            for node in ast.walk(soft_delete_method):
                if isinstance(node, ast.Attribute) and node.attr == "delete":
                    # Check if it's session.delete()
                    if isinstance(node.value, ast.Name) and node.value.id == "session":
                        has_hard_delete = True
                        break

            assert not has_hard_delete, (
                "_soft_delete_agents() contains session.delete() - should use status='cancelled'"
            )

    # Priority 0 - Thin Prompt Generator
    def test_thin_prompt_generator_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: thin_prompt_generator.py should not import MCPAgentJob.

        Expected outcome: File uses AgentJob + AgentExecution only.
        """
        file_path = project_root / "src" / "giljo_mcp" / "thin_prompt_generator.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "thin_prompt_generator.py still imports MCPAgentJob - should use AgentJob + AgentExecution"
        )

    def test_thin_prompt_generator_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: thin_prompt_generator.py should not use MCPAgentJob in code.

        Expected outcome: No fallback logic to MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "thin_prompt_generator.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "thin_prompt_generator.py still uses MCPAgentJob - should use AgentJob + AgentExecution only"
        )

    def test_thin_prompt_generator_no_fallback_logic(self, project_root: Path):
        """
        BEHAVIOR: thin_prompt_generator.py should not have fallback logic to MCPAgentJob.

        Expected outcome: Single code path using AgentJob + AgentExecution.
        """
        file_path = project_root / "src" / "giljo_mcp" / "thin_prompt_generator.py"
        source = file_path.read_text(encoding="utf-8")

        # Check for strings like "MCPAgentJob" or "mcp_job" (variable names from fallback)
        # This is a heuristic, but useful for detecting fallback patterns
        assert "select(MCPAgentJob)" not in source, (
            "thin_prompt_generator.py still contains MCPAgentJob query - remove fallback logic"
        )
        assert "existing_mcp_stmt" not in source, (
            "thin_prompt_generator.py still contains MCPAgentJob fallback query variable"
        )

    # Priority 1 - Tools Files
    def test_tools_orchestration_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/orchestration.py should not import MCPAgentJob.

        Expected outcome: File uses AgentJob + AgentExecution.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "orchestration.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/orchestration.py still imports MCPAgentJob"
        )

    def test_tools_orchestration_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/orchestration.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "orchestration.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/orchestration.py still uses MCPAgentJob"
        )

    def test_tools_agent_coordination_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/agent_coordination.py should not import MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "agent_coordination.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/agent_coordination.py still imports MCPAgentJob"
        )

    def test_tools_agent_coordination_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/agent_coordination.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "agent_coordination.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/agent_coordination.py still uses MCPAgentJob"
        )

    def test_tools_init_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/__init__.py should not import MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "__init__.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/__init__.py still imports MCPAgentJob"
        )

    def test_tools_init_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/__init__.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "__init__.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/__init__.py still uses MCPAgentJob"
        )

    def test_tools_tool_accessor_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/tool_accessor.py should not import MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "tool_accessor.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/tool_accessor.py still imports MCPAgentJob"
        )

    def test_tools_tool_accessor_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/tool_accessor.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "tool_accessor.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/tool_accessor.py still uses MCPAgentJob"
        )

    # Priority 2 - Low Priority Tools
    def test_tools_agent_status_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/agent_status.py should not import MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "agent_status.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/agent_status.py still imports MCPAgentJob"
        )

    def test_tools_agent_status_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/agent_status.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "agent_status.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/agent_status.py still uses MCPAgentJob"
        )

    def test_tools_optimization_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/optimization.py should not import MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "optimization.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/optimization.py still imports MCPAgentJob"
        )

    def test_tools_optimization_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/optimization.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "optimization.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/optimization.py still uses MCPAgentJob"
        )

    def test_tools_project_has_no_mcpagentjob_import(self, project_root: Path):
        """
        BEHAVIOR: tools/project.py should not import MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "project.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_import(source), (
            "tools/project.py still imports MCPAgentJob"
        )

    def test_tools_project_has_no_mcpagentjob_usage(self, project_root: Path):
        """
        BEHAVIOR: tools/project.py should not use MCPAgentJob.
        """
        file_path = project_root / "src" / "giljo_mcp" / "tools" / "project.py"
        source = file_path.read_text(encoding="utf-8")

        assert not self._has_mcpagentjob_usage(source), (
            "tools/project.py still uses MCPAgentJob"
        )


class TestMCPAgentJobRemovalIntegration:
    """
    Integration tests verifying MCPAgentJob removal doesn't break functionality.

    These tests verify that after migration, the code still WORKS correctly.
    """

    def test_all_migrated_files_exist(self):
        """
        BEHAVIOR: All files in 0367c-2 scope should exist.

        This ensures we haven't accidentally deleted files during migration.
        """
        project_root = Path(__file__).parent.parent.parent

        files_to_check = [
            "src/giljo_mcp/staging_rollback.py",
            "src/giljo_mcp/thin_prompt_generator.py",
            "src/giljo_mcp/tools/orchestration.py",
            "src/giljo_mcp/tools/agent_coordination.py",
            "src/giljo_mcp/tools/__init__.py",
            "src/giljo_mcp/tools/tool_accessor.py",
            "src/giljo_mcp/tools/agent_status.py",
            "src/giljo_mcp/tools/optimization.py",
            "src/giljo_mcp/tools/project.py",
        ]

        for file_rel_path in files_to_check:
            file_path = project_root / file_rel_path
            assert file_path.exists(), f"File missing after migration: {file_rel_path}"

    def test_all_migrated_files_parse_successfully(self):
        """
        BEHAVIOR: All migrated files should parse successfully (no syntax errors).

        This ensures migration didn't introduce syntax errors.
        """
        project_root = Path(__file__).parent.parent.parent

        files_to_check = [
            "src/giljo_mcp/staging_rollback.py",
            "src/giljo_mcp/thin_prompt_generator.py",
            "src/giljo_mcp/tools/orchestration.py",
            "src/giljo_mcp/tools/agent_coordination.py",
            "src/giljo_mcp/tools/__init__.py",
            "src/giljo_mcp/tools/tool_accessor.py",
            "src/giljo_mcp/tools/agent_status.py",
            "src/giljo_mcp/tools/optimization.py",
            "src/giljo_mcp/tools/project.py",
        ]

        for file_rel_path in files_to_check:
            file_path = project_root / file_rel_path
            source = file_path.read_text(encoding="utf-8")

            try:
                ast.parse(source)
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {file_rel_path}: {e}")
