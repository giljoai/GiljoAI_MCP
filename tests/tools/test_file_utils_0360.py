"""
TDD RED Phase - file_exists() Utility Tool

Tests for lightweight file/directory existence checking within tenant workspace.
These tests WILL FAIL initially - they define the expected behavior.

Handover 0360 Feature 3: File Existence Utility
"""

import pytest
from pathlib import Path
from uuid import uuid4
import tempfile
import os


@pytest.mark.asyncio
async def test_file_exists_returns_true_for_existing_file(db_manager):
    """
    Should return exists=True, is_file=True for existing file.

    Semantic: Simple existence check without reading file contents.
    """
    from src.giljo_mcp.tools.file_utils import file_exists

    tenant_key = f"tenant_{uuid4()}"

    # Create temporary file in workspace
    with tempfile.TemporaryDirectory() as workspace:
        test_file = Path(workspace) / "test_file.txt"
        test_file.write_text("test content")

        # TEST: Check file exists
        result = await file_exists(
            path=str(test_file.relative_to(workspace)),
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        # EXPECTED: File exists and is identified as file
        assert result["success"] is True
        assert result["exists"] is True
        assert result["is_file"] is True
        assert result["is_dir"] is False
        assert "path" in result


@pytest.mark.asyncio
async def test_file_exists_returns_true_for_existing_directory(db_manager):
    """
    Should return exists=True, is_dir=True for existing directory.

    Semantic: Distinguish between files and directories.
    """
    from src.giljo_mcp.tools.file_utils import file_exists

    tenant_key = f"tenant_{uuid4()}"

    # Create temporary directory in workspace
    with tempfile.TemporaryDirectory() as workspace:
        test_dir = Path(workspace) / "test_dir"
        test_dir.mkdir()

        # TEST: Check directory exists
        result = await file_exists(
            path="test_dir",
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        # EXPECTED: Directory exists and is identified as directory
        assert result["success"] is True
        assert result["exists"] is True
        assert result["is_file"] is False
        assert result["is_dir"] is True


@pytest.mark.asyncio
async def test_file_exists_returns_false_for_missing_path(db_manager):
    """
    Should return exists=False for non-existent path.

    Semantic: Graceful handling of missing paths without errors.
    """
    from src.giljo_mcp.tools.file_utils import file_exists

    tenant_key = f"tenant_{uuid4()}"

    with tempfile.TemporaryDirectory() as workspace:
        # TEST: Check non-existent path
        result = await file_exists(
            path="nonexistent_file.txt",
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        # EXPECTED: Path does not exist
        assert result["success"] is True
        assert result["exists"] is False
        assert result["is_file"] is False
        assert result["is_dir"] is False


@pytest.mark.asyncio
async def test_file_exists_respects_workspace_sandbox(db_manager):
    """
    Should not allow access outside tenant workspace.

    Semantic: Sandbox security - prevent path traversal attacks.
    """
    from src.giljo_mcp.tools.file_utils import file_exists

    tenant_key = f"tenant_{uuid4()}"

    with tempfile.TemporaryDirectory() as workspace:
        # TEST: Try to access path outside workspace using path traversal
        result = await file_exists(
            path="../../../etc/passwd",
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        # EXPECTED: Should fail with sandbox violation error
        assert result["success"] is False
        assert "error" in result
        assert "sandbox" in result["error"].lower() or "outside" in result["error"].lower()


@pytest.mark.asyncio
async def test_file_exists_handles_absolute_paths_within_workspace(db_manager):
    """
    Should handle absolute paths that resolve within workspace.

    Semantic: Allow absolute paths if they resolve to workspace.
    """
    from src.giljo_mcp.tools.file_utils import file_exists

    tenant_key = f"tenant_{uuid4()}"

    with tempfile.TemporaryDirectory() as workspace:
        test_file = Path(workspace) / "absolute_test.txt"
        test_file.write_text("content")

        # TEST: Use absolute path within workspace
        result = await file_exists(
            path=str(test_file),
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        # EXPECTED: Should work if path is within workspace
        assert result["success"] is True
        assert result["exists"] is True
        assert result["is_file"] is True


@pytest.mark.asyncio
async def test_file_exists_handles_nested_directories(db_manager):
    """
    Should correctly identify nested directory structures.

    Semantic: Support deep directory paths within workspace.
    """
    from src.giljo_mcp.tools.file_utils import file_exists

    tenant_key = f"tenant_{uuid4()}"

    with tempfile.TemporaryDirectory() as workspace:
        # Create nested structure
        nested_dir = Path(workspace) / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "deep_file.txt"
        nested_file.write_text("deep content")

        # TEST: Check nested directory
        result_dir = await file_exists(
            path="level1/level2/level3",
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        assert result_dir["success"] is True
        assert result_dir["exists"] is True
        assert result_dir["is_dir"] is True

        # TEST: Check nested file
        result_file = await file_exists(
            path="level1/level2/level3/deep_file.txt",
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        assert result_file["success"] is True
        assert result_file["exists"] is True
        assert result_file["is_file"] is True


@pytest.mark.asyncio
async def test_file_exists_cross_platform_paths(db_manager):
    """
    Should handle both forward slashes and platform-specific separators.

    Semantic: Cross-platform compatibility using pathlib.
    """
    from src.giljo_mcp.tools.file_exists import file_exists

    tenant_key = f"tenant_{uuid4()}"

    with tempfile.TemporaryDirectory() as workspace:
        # Create nested file
        nested = Path(workspace) / "sub" / "file.txt"
        nested.parent.mkdir(parents=True)
        nested.write_text("content")

        # TEST: Use forward slashes (should work on all platforms)
        result = await file_exists(
            path="sub/file.txt",
            tenant_key=tenant_key,
            workspace_root=workspace
        )

        # EXPECTED: Path should be normalized and found
        assert result["success"] is True
        assert result["exists"] is True
        assert result["is_file"] is True
