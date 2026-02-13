"""
Tests for /gil_add slash command functionality.

This module tests direct task mode (with --task flag), direct project mode
(with --project flag), and interactive mode (type routing and Q&A flow)
for the gil_add command.

TDD Red Phase: These tests should FAIL initially.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGilAddDirectTaskMode:
    """Tests for direct task mode: /gil_add --task --name "X" --priority high --category backend"""

    @pytest.mark.asyncio
    async def test_direct_task_mode_creates_task_with_all_flags(self):
        """Direct task mode with all flags creates task immediately via MCP tool."""
        # Arrange
        arguments = '--task --name "Refactor auth service" --priority high --category backend'
        expected_params = {
            "title": "Refactor auth service",
            "description": "Refactor auth service",  # Same as title for direct mode
            "priority": "high",
            "category": "backend",
        }

        # Mock MCP tool call
        mock_create_task = AsyncMock(return_value={"success": True, "task_id": "task-123"})

        # Act
        with patch("mcp__giljo-mcp__create_task", mock_create_task):
            result = await execute_gil_add_command(arguments)

        # Assert
        mock_create_task.assert_called_once_with(**expected_params)
        assert result["success"] is True
        assert "task-123" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_direct_task_mode_uses_defaults_for_missing_flags(self):
        """Direct task mode uses default values when optional flags are missing."""
        # Arrange
        arguments = '--task --name "Fix bug in login"'
        expected_params = {
            "title": "Fix bug in login",
            "description": "Fix bug in login",
            "priority": "medium",  # Default
            "category": "general",  # Default
        }

        # Mock MCP tool call
        mock_create_task = AsyncMock(return_value={"success": True, "task_id": "task-456"})

        # Act
        with patch("mcp__giljo-mcp__create_task", mock_create_task):
            await execute_gil_add_command(arguments)  # Result checked via mock

        # Assert
        mock_create_task.assert_called_once()
        call_kwargs = mock_create_task.call_args.kwargs
        assert call_kwargs["title"] == expected_params["title"]
        assert call_kwargs["priority"] == expected_params["priority"]
        assert call_kwargs["category"] == expected_params["category"]

    @pytest.mark.asyncio
    async def test_direct_task_mode_validates_priority_values(self):
        """Direct task mode validates priority must be low/medium/high/critical."""
        # Arrange
        arguments = '--task --name "Task X" --priority invalid'

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid priority"):
            await execute_gil_add_command(arguments)

    @pytest.mark.asyncio
    async def test_direct_task_mode_validates_category_values(self):
        """Direct task mode validates category must be from allowed list.

        Valid categories: frontend, backend, database, infra, docs, general
        """
        # Arrange
        arguments = '--task --name "Task X" --category invalid_category'

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid category"):
            await execute_gil_add_command(arguments)

    @pytest.mark.asyncio
    async def test_direct_task_mode_requires_name_flag(self):
        """Direct task mode fails if --name flag is missing."""
        # Arrange
        arguments = "--task --priority high --category backend"

        # Act & Assert
        with pytest.raises(ValueError, match="--name is required"):
            await execute_gil_add_command(arguments)


class TestGilAddDirectProjectMode:
    """Tests for direct project mode: /gil_add --project --name "X" """

    @pytest.mark.asyncio
    async def test_direct_project_mode_creates_project_with_name(self):
        """Direct project mode with --name creates project via MCP tool."""
        # Arrange
        arguments = '--project --name "Authentication Overhaul"'
        expected_params = {
            "name": "Authentication Overhaul",
            "description": "Authentication Overhaul",  # Defaults to name
        }

        # Mock MCP tool call
        mock_create_project = AsyncMock(
            return_value={"success": True, "project_id": "proj-001"}
        )

        # Act
        with patch("mcp__giljo-mcp__create_project", mock_create_project):
            result = await execute_gil_add_command(arguments)

        # Assert
        mock_create_project.assert_called_once_with(**expected_params)
        assert result["success"] is True
        assert "proj-001" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_direct_project_mode_with_description(self):
        """Direct project mode passes description when provided."""
        # Arrange
        arguments = (
            '--project --name "Dashboard Redesign" '
            '--description "Redesign the admin dashboard with responsive layout"'
        )

        # Mock MCP tool call
        mock_create_project = AsyncMock(
            return_value={"success": True, "project_id": "proj-002"}
        )

        # Act
        with patch("mcp__giljo-mcp__create_project", mock_create_project):
            result = await execute_gil_add_command(arguments)

        # Assert
        mock_create_project.assert_called_once()
        call_kwargs = mock_create_project.call_args.kwargs
        assert call_kwargs["name"] == "Dashboard Redesign"
        assert "Redesign the admin dashboard" in call_kwargs["description"]
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_direct_project_mode_requires_name_flag(self):
        """Direct project mode fails if --name flag is missing."""
        # Arrange
        arguments = '--project --description "Some description"'

        # Act & Assert
        with pytest.raises(ValueError, match="--name is required"):
            await execute_gil_add_command(arguments)


class TestGilAddInteractiveMode:
    """Tests for interactive mode: /gil_add (no args) with type routing"""

    @pytest.mark.asyncio
    async def test_interactive_mode_asks_for_type(self):
        """Interactive mode asks user whether to create a task or project."""
        # Arrange
        arguments = ""  # No arguments = interactive mode
        conversation_context = [{"role": "user", "content": "Some work item"}]

        # Act
        result = await execute_gil_add_command(arguments, conversation_context)

        # Assert
        assert "type" in result["questions_asked"]
        type_options = result["questions_asked"]["type"]
        assert "task" in type_options.lower() or "Task" in type_options
        assert "project" in type_options.lower() or "Project" in type_options

    @pytest.mark.asyncio
    async def test_interactive_mode_task_route_summarizes_conversation(self):
        """Interactive mode (task route) summarizes the last concept discussed."""
        # Arrange
        conversation_context = [
            {"role": "user", "content": "We should refactor the authentication service to use JWT tokens"},
            {"role": "assistant", "content": "That's a good idea for better security..."},
        ]
        arguments = ""
        user_responses = {"type": "task"}

        # Mock conversation summary
        mock_summarizer = MagicMock(
            return_value={
                "title": "Refactor authentication service to use JWT tokens",
                "description": (
                    "Refactor the authentication service to implement JWT "
                    "token-based authentication for improved security"
                ),
            }
        )

        # Act
        with patch("summarize_conversation", mock_summarizer):
            result = await execute_gil_add_command(arguments, conversation_context, user_responses)

        # Assert
        mock_summarizer.assert_called_once_with(conversation_context)
        assert "Refactor authentication service" in result["summary_shown_to_user"]

    @pytest.mark.asyncio
    async def test_interactive_mode_task_route_asks_for_scope(self):
        """Interactive mode (task route) asks user for scope (product or unscoped)."""
        # Arrange
        arguments = ""
        conversation_context = [{"role": "user", "content": "Some task"}]
        user_responses = {"type": "task"}

        # Act
        result = await execute_gil_add_command(arguments, conversation_context, user_responses)

        # Assert
        assert "scope" in result["questions_asked"]
        assert "Active product" in result["questions_asked"]["scope"]
        assert "All Tasks (unscoped)" in result["questions_asked"]["scope"]

    @pytest.mark.asyncio
    async def test_interactive_mode_task_route_asks_for_category(self):
        """Interactive mode (task route) asks user for category selection."""
        # Arrange
        arguments = ""
        conversation_context = [{"role": "user", "content": "Some task"}]
        user_responses = {"type": "task"}

        # Act
        result = await execute_gil_add_command(arguments, conversation_context, user_responses)

        # Assert
        assert "category" in result["questions_asked"]
        categories = result["questions_asked"]["category"]
        expected_categories = ["frontend", "backend", "database", "infra", "docs", "general"]
        for cat in expected_categories:
            assert cat in categories

    @pytest.mark.asyncio
    async def test_interactive_mode_task_route_asks_for_priority(self):
        """Interactive mode (task route) asks user for priority selection."""
        # Arrange
        arguments = ""
        conversation_context = [{"role": "user", "content": "Some task"}]
        user_responses = {"type": "task"}

        # Act
        result = await execute_gil_add_command(arguments, conversation_context, user_responses)

        # Assert
        assert "priority" in result["questions_asked"]
        priorities = result["questions_asked"]["priority"]
        expected_priorities = ["low", "medium", "high", "critical"]
        for priority in expected_priorities:
            assert priority in priorities

    @pytest.mark.asyncio
    async def test_interactive_mode_task_route_creates_task(self):
        """Interactive mode (task route) creates task after collecting all responses."""
        # Arrange
        arguments = ""
        conversation_context = [{"role": "user", "content": "Refactor auth"}]
        user_responses = {
            "type": "task",
            "scope": "unscoped",
            "category": "backend",
            "priority": "high",
        }

        # Mock MCP tool call
        mock_create_task = AsyncMock(return_value={"success": True, "task_id": "task-789"})

        # Act
        with patch("mcp__giljo-mcp__create_task", mock_create_task):
            result = await execute_gil_add_command(arguments, conversation_context, user_responses)

        # Assert
        mock_create_task.assert_called_once()
        call_kwargs = mock_create_task.call_args.kwargs
        assert call_kwargs["category"] == "backend"
        assert call_kwargs["priority"] == "high"
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_interactive_mode_project_route_creates_project(self):
        """Interactive mode (project route) creates project after collecting responses."""
        # Arrange
        arguments = ""
        conversation_context = [
            {"role": "user", "content": "We need a full dashboard redesign"},
        ]
        user_responses = {
            "type": "project",
            "name": "Dashboard Redesign",
            "description": "Complete redesign of the admin dashboard",
        }

        # Mock MCP tool call
        mock_create_project = AsyncMock(
            return_value={"success": True, "project_id": "proj-100"}
        )

        # Act
        with patch("mcp__giljo-mcp__create_project", mock_create_project):
            result = await execute_gil_add_command(arguments, conversation_context, user_responses)

        # Assert
        mock_create_project.assert_called_once()
        call_kwargs = mock_create_project.call_args.kwargs
        assert call_kwargs["name"] == "Dashboard Redesign"
        assert result["success"] is True


class TestGilAddMCPIntegration:
    """Tests for MCP tool integration (tasks and projects)"""

    @pytest.mark.asyncio
    async def test_task_mcp_tool_receives_correct_parameters(self):
        """Verify create_task MCP tool receives all expected parameters."""
        # Arrange
        arguments = '--task --name "Test Task" --priority high --category backend --description "Detailed desc"'

        # Mock MCP tool
        mock_create_task = AsyncMock(return_value={"success": True, "task_id": "task-abc"})

        # Act
        with patch("mcp__giljo-mcp__create_task", mock_create_task):
            await execute_gil_add_command(arguments)

        # Assert
        call_kwargs = mock_create_task.call_args.kwargs
        assert "title" in call_kwargs
        assert "description" in call_kwargs
        assert "priority" in call_kwargs

    @pytest.mark.asyncio
    async def test_task_mcp_tool_error_handling(self):
        """Verify error handling when create_task MCP tool fails."""
        # Arrange
        arguments = '--task --name "Test Task"'
        mock_create_task = AsyncMock(
            return_value={"success": False, "error": "Database connection failed"}
        )

        # Act
        with patch("mcp__giljo-mcp__create_task", mock_create_task):
            result = await execute_gil_add_command(arguments)

        # Assert
        assert result["success"] is False
        assert "Database connection failed" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_project_mcp_tool_receives_correct_parameters(self):
        """Verify create_project MCP tool receives all expected parameters."""
        # Arrange
        arguments = '--project --name "New Project" --description "Project description"'

        # Mock MCP tool
        mock_create_project = AsyncMock(
            return_value={"success": True, "project_id": "proj-abc"}
        )

        # Act
        with patch("mcp__giljo-mcp__create_project", mock_create_project):
            await execute_gil_add_command(arguments)

        # Assert
        call_kwargs = mock_create_project.call_args.kwargs
        assert "name" in call_kwargs
        assert "description" in call_kwargs

    @pytest.mark.asyncio
    async def test_project_mcp_tool_error_handling(self):
        """Verify error handling when create_project MCP tool fails."""
        # Arrange
        arguments = '--project --name "New Project"'
        mock_create_project = AsyncMock(
            return_value={"success": False, "error": "Product not found"}
        )

        # Act
        with patch("mcp__giljo-mcp__create_project", mock_create_project):
            result = await execute_gil_add_command(arguments)

        # Assert
        assert result["success"] is False
        assert "Product not found" in result.get("error", "")


class TestGilAddCommandFile:
    """Tests for the .claude/commands/gil_add.md file structure"""

    def test_command_file_exists(self):
        """Verify gil_add.md command file exists in .claude/commands/"""
        command_file = Path(".claude/commands/gil_add.md")
        assert command_file.exists(), "gil_add.md command file must exist"

    def test_command_file_has_frontmatter(self):
        """Verify command file has proper frontmatter with description."""
        command_file = Path(".claude/commands/gil_add.md")
        content = command_file.read_text()

        assert content.startswith("---"), "Command file must start with frontmatter"
        assert "description:" in content, "Command file must have description in frontmatter"

    def test_command_file_uses_arguments_variable(self):
        """Verify command file uses $ARGUMENTS for parameter passing."""
        command_file = Path(".claude/commands/gil_add.md")
        content = command_file.read_text()

        assert "$ARGUMENTS" in content, "Command file must use $ARGUMENTS variable"


# Helper function placeholder (to be implemented)
async def execute_gil_add_command(
    arguments: str,
    conversation_context: list | None = None,
    user_responses: dict | None = None,
) -> dict:
    """
    Execute the gil_add command with given arguments.

    This is a placeholder that will be replaced by the actual implementation
    from the .claude/commands/gil_add.md skill file.

    Args:
        arguments: Command-line style arguments
            (e.g., '--task --name "X" --priority high')
        conversation_context: Optional conversation history for summarization
        user_responses: Optional pre-filled user responses for testing

    Returns:
        dict with success status and result/error details
    """
    # Suppress unused variable warnings - parameters used in tests via mocking
    _ = (arguments, conversation_context, user_responses)
    raise NotImplementedError("gil_add command not yet implemented")
