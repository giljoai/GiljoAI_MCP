"""
Regression tests for context_tools import structure.

Purpose: Prevent future import conflicts after fix in commit 56ad7cd.

Background:
- Original issue: Python namespace collision between context.py (file) and context/ (directory)
- Fix: Renamed context/ directory to context_tools/
- This test ensures the import structure remains correct

TDD Compliance: Written retroactively after fix to document expected behavior
and prevent regression.
"""

import pytest


class TestContextToolsImportStructure:
    """Verify context_tools directory structure and imports work correctly."""

    def test_register_context_tools_imports(self):
        """
        Test that register_context_tools can be imported from context.py.

        This is the critical import that was broken by the namespace collision.
        """
        from src.giljo_mcp.tools.context import register_context_tools

        assert callable(register_context_tools)
        assert register_context_tools.__name__ == "register_context_tools"

    def test_all_context_tools_importable_from_init(self):
        """
        Test that all 6 context tools can be imported from context_tools package.

        Verifies the __init__.py exports are correct after directory rename.
        """
        from src.giljo_mcp.tools.context_tools import (
            get_360_memory,
            get_agent_templates,
            get_architecture,
            get_git_history,
            get_tech_stack,
            get_vision_document,
        )

        # Verify all tools are callable functions
        tools = [
            get_vision_document,
            get_360_memory,
            get_git_history,
            get_agent_templates,
            get_tech_stack,
            get_architecture,
        ]

        for tool in tools:
            assert callable(tool), f"{tool.__name__} is not callable"
            assert hasattr(tool, "__name__"), f"{tool} has no __name__ attribute"

    def test_individual_context_tool_imports(self):
        """
        Test that each context tool can be imported individually from its module.

        Verifies the internal module structure is correct.
        """
        # Import each tool from its specific module
        from src.giljo_mcp.tools.context_tools.get_360_memory import get_360_memory
        from src.giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates
        from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture
        from src.giljo_mcp.tools.context_tools.get_git_history import get_git_history
        from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
        from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document

        # Verify each tool is callable
        assert callable(get_vision_document)
        assert callable(get_360_memory)
        assert callable(get_git_history)
        assert callable(get_agent_templates)
        assert callable(get_tech_stack)
        assert callable(get_architecture)

    def test_no_context_directory_exists(self):
        """
        Test that the old context/ directory no longer exists.

        Prevents accidental recreation of the namespace collision.
        """
        from pathlib import Path

        tools_dir = Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "tools"
        context_dir = tools_dir / "context"

        # Verify context.py file exists
        context_file = tools_dir / "context.py"
        assert context_file.exists(), "context.py file should exist"
        assert context_file.is_file(), "context should be a file, not a directory"

        # Verify old context/ directory does NOT exist
        if context_dir.exists():
            assert not context_dir.is_dir(), (
                "context/ directory should not exist (causes namespace collision). Use context_tools/ instead."
            )

    def test_context_tools_directory_structure(self):
        """
        Test that context_tools/ directory has the expected structure.

        Verifies:
        - Directory exists
        - __init__.py exists
        - All 6 tool modules exist
        """
        from pathlib import Path

        tools_dir = Path(__file__).parent.parent.parent / "src" / "giljo_mcp" / "tools"
        context_tools_dir = tools_dir / "context_tools"

        # Verify directory exists
        assert context_tools_dir.exists(), "context_tools/ directory should exist"
        assert context_tools_dir.is_dir(), "context_tools should be a directory"

        # Verify __init__.py exists
        init_file = context_tools_dir / "__init__.py"
        assert init_file.exists(), "context_tools/__init__.py should exist"

        # Verify all 6 tool modules exist
        expected_modules = [
            "get_vision_document.py",
            "get_360_memory.py",
            "get_git_history.py",
            "get_agent_templates.py",
            "get_tech_stack.py",
            "get_architecture.py",
        ]

        for module in expected_modules:
            module_path = context_tools_dir / module
            assert module_path.exists(), f"{module} should exist in context_tools/"
            assert module_path.is_file(), f"{module} should be a file"

    def test_context_tools_init_exports(self):
        """
        Test that context_tools/__init__.py exports match expected tools.

        Verifies the __all__ export list is correct.
        """
        from src.giljo_mcp.tools import context_tools

        # Check __all__ export list
        assert hasattr(context_tools, "__all__"), "context_tools should have __all__ attribute"

        expected_exports = [
            "get_vision_document",
            "get_360_memory",
            "get_git_history",
            "get_agent_templates",
            "get_tech_stack",
            "get_architecture",
            "get_product_context",
            "get_project",
            "get_testing",
        ]

        assert set(context_tools.__all__) == set(expected_exports), (
            f"context_tools.__all__ exports don't match expected. "
            f"Expected: {expected_exports}, Got: {context_tools.__all__}"
        )

    def test_structlog_dependency_available(self):
        """
        Test that structlog is importable (required by context tools).

        Regression test for missing structlog dependency that caused startup failure.
        """
        try:
            import structlog

            assert structlog is not None
        except ImportError as e:
            pytest.fail(f"structlog should be importable (added to requirements.txt): {e}")


class TestContextToolsFunctionSignatures:
    """Verify context tools have expected async function signatures."""

    def test_get_vision_document_is_async(self):
        """Test that get_vision_document is an async function."""
        import inspect

        from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document

        assert inspect.iscoroutinefunction(get_vision_document), "get_vision_document should be an async function"

    def test_get_360_memory_is_async(self):
        """Test that get_360_memory is an async function."""
        import inspect

        from src.giljo_mcp.tools.context_tools.get_360_memory import get_360_memory

        assert inspect.iscoroutinefunction(get_360_memory), "get_360_memory should be an async function"

    def test_all_context_tools_are_async(self):
        """Test that all 6 context tools are async functions."""
        import inspect

        from src.giljo_mcp.tools.context_tools import (
            get_360_memory,
            get_agent_templates,
            get_architecture,
            get_git_history,
            get_tech_stack,
            get_vision_document,
        )

        tools = [
            get_vision_document,
            get_360_memory,
            get_git_history,
            get_agent_templates,
            get_tech_stack,
            get_architecture,
        ]

        for tool in tools:
            assert inspect.iscoroutinefunction(tool), (
                f"{tool.__name__} should be an async function (uses DatabaseManager)"
            )
