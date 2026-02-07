"""
Integration test to verify complete removal of fetch_* tools.

Tests that:
1. No fetch_* tool definitions exist in context.py
2. No fetch_* references in mcp_tool_catalog.py
3. No fetch_* imports in test files
4. Documentation either deleted or shows deprecation notice

Handover 0281: Complete fetch_* tool cleanup after monolithic context migration.
"""

import re
from pathlib import Path

import pytest


class TestFetchToolsCleanup:
    """Verify fetch_* tools are completely removed from codebase."""

    def test_no_fetch_tools_in_context_py(self):
        """Verify context.py has no fetch_* tool definitions."""
        context_file = Path("F:/GiljoAI_MCP/src/giljo_mcp/tools/context.py")

        if not context_file.exists():
            pytest.skip("context.py does not exist")

        content = context_file.read_text(encoding="utf-8")

        # Should NOT have any of these function definitions
        fetch_tools = [
            "fetch_vision_document",
            "fetch_360_memory",
            "fetch_git_history",
            "fetch_agent_templates",
            "fetch_tech_stack",
            "fetch_architecture",
            "fetch_product_context",
            "fetch_project_description",
            "fetch_testing_config",
        ]

        for tool_name in fetch_tools:
            # Look for function definition (async def fetch_...)
            pattern = rf"async\s+def\s+{tool_name}\s*\("
            assert not re.search(pattern, content), f"Found {tool_name} definition in context.py - should be removed"

    def test_no_fetch_tools_in_mcp_tool_catalog(self):
        """Verify mcp_tool_catalog.py has no fetch_* tool definitions."""
        catalog_file = Path("F:/GiljoAI_MCP/src/giljo_mcp/prompt_generation/mcp_tool_catalog.py")

        if not catalog_file.exists():
            pytest.skip("mcp_tool_catalog.py does not exist")

        content = catalog_file.read_text(encoding="utf-8")

        # Should NOT have fetch_product_context or fetch_architecture in TOOLS dict
        assert '"fetch_product_context"' not in content, (
            "fetch_product_context found in mcp_tool_catalog.py - should be removed"
        )
        assert '"fetch_architecture"' not in content, (
            "fetch_architecture found in mcp_tool_catalog.py - should be removed"
        )

        # Should NOT have fetch_* in agent mappings
        assert '"context.fetch_product_context"' not in content, (
            "context.fetch_product_context found in agent mappings - should be removed"
        )
        assert '"context.fetch_architecture"' not in content, (
            "context.fetch_architecture found in agent mappings - should be removed"
        )

    def test_no_fetch_tool_imports_in_orchestrator_priority_filtering_test(self):
        """Verify test file does not import fetch_* tools."""
        test_file = Path("F:/GiljoAI_MCP/tests/integration/test_orchestrator_priority_filtering.py")

        if not test_file.exists():
            pytest.skip("test_orchestrator_priority_filtering.py does not exist")

        content = test_file.read_text(encoding="utf-8")

        # Should NOT import fetch_* tools
        fetch_tools = [
            "fetch_vision_document",
            "fetch_tech_stack",
            "fetch_architecture",
            "fetch_git_history",
            "fetch_360_memory",
        ]

        for tool_name in fetch_tools:
            # Look for import statement
            pattern = rf"from\s+src\.giljo_mcp\.tools\.context\s+import.*{tool_name}"
            assert not re.search(pattern, content), f"Found import of {tool_name} in test file - should be removed"

    def test_no_fetch_test_functions_in_orchestrator_priority_filtering_test(self):
        """Verify test file has no test functions for fetch_* tools."""
        test_file = Path("F:/GiljoAI_MCP/tests/integration/test_orchestrator_priority_filtering.py")

        if not test_file.exists():
            pytest.skip("test_orchestrator_priority_filtering.py does not exist")

        content = test_file.read_text(encoding="utf-8")

        # Should NOT have test functions for fetch_* tools
        assert "test_fetch_vision_excluded_when_priority_4" not in content, (
            "Found test_fetch_vision_excluded_when_priority_4 - should be removed"
        )
        assert "test_fetch_360_excluded_when_priority_4" not in content, (
            "Found test_fetch_360_excluded_when_priority_4 - should be removed"
        )

    def test_context_tools_documentation_deprecated_or_deleted(self):
        """Verify context_tools.md is either deleted or shows deprecation notice."""
        docs_file = Path("F:/GiljoAI_MCP/docs/api/context_tools.md")

        if not docs_file.exists():
            # PASS - file deleted is valid
            return

        content = docs_file.read_text(encoding="utf-8")

        # If file exists, it MUST have deprecation notice
        assert "DEPRECATED" in content, (
            "context_tools.md exists but has no DEPRECATED notice - either delete file or add deprecation"
        )
        assert "Handover 0280" in content or "Handover 0281" in content, (
            "context_tools.md deprecation notice missing handover reference"
        )

    def test_grep_returns_zero_fetch_tool_references(self):
        """
        Verify grep finds NO fetch_* tool references in source code.

        This validates that the monolithic context architecture is complete.
        Excludes deprecated test fixtures and test files that will be removed separately.
        """
        import subprocess

        # Run grep to find any fetch_* tool references in source code ONLY
        cmd = [
            "grep",
            "-r",
            r"fetch_vision_document\|fetch_360_memory\|fetch_git_history\|fetch_agent_templates\|fetch_tech_stack\|fetch_architecture\|fetch_product_context\|fetch_project_description\|fetch_testing_config",
            "F:/GiljoAI_MCP/src/",
            "--include=*.py",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

            # Filter out lines with "# DEPRECATED" or ".pyc" or comments
            lines = [
                line
                for line in result.stdout.splitlines()
                if "# DEPRECATED" not in line and ".pyc" not in line and "# NOTE:" not in line and "REMOVED" not in line
            ]

            # Should have ZERO results in source code
            assert len(lines) == 0, f"Found {len(lines)} fetch_* tool references in source code:\n" + "\n".join(
                lines[:10]
            )

        except FileNotFoundError:
            pytest.skip("grep command not available")


# ============================================================================
# Test Summary
# ============================================================================
#
# These tests verify complete removal of fetch_* tools from the codebase:
#
# 1. ✅ No fetch_* tool definitions in context.py
# 2. ✅ No fetch_* tool definitions in mcp_tool_catalog.py
# 3. ✅ No fetch_* tool references in agent mappings
# 4. ✅ No fetch_* imports in test files
# 5. ✅ No fetch_* test functions
# 6. ✅ Documentation either deleted or deprecated
# 7. ✅ Grep returns 0 results for fetch_* in source code
#
# Expected Final State:
# - 0 fetch_* tool definitions in source code
# - 0 fetch_* references in active code paths
# - 0 fetch_* test functions
# - Clean documentation (deleted or deprecation notice)
#
# ============================================================================
