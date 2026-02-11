"""
Test suite for Handover 0702: Utils & Config Cleanup
Verifies naming collision resolution and orphan file deletion.
"""

import sys
from pathlib import Path

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_discovery_path_resolver_still_exists():
    """Test that discovery.PathResolver is unchanged"""
    from src.giljo_mcp.discovery import PathResolver

    assert PathResolver is not None
    # Should have different methods than PathNormalizer
    assert hasattr(PathResolver, "resolve_path")
    assert hasattr(PathResolver, "DEFAULT_PATHS")


def test_old_path_resolver_module_deleted():
    """Test that old path_resolver.py module is deleted"""
    old_path = Path(__file__).parent.parent / "src" / "giljo_mcp" / "utils" / "path_resolver.py"
    assert not old_path.exists(), "Old path_resolver.py should be deleted"


def test_download_utils_deleted():
    """Test that download_utils.py is deleted"""
    download_utils_path = Path(__file__).parent.parent / "src" / "giljo_mcp" / "tools" / "download_utils.py"
    assert not download_utils_path.exists(), "download_utils.py should be deleted"


def test_task_helpers_deleted():
    """Test that task_helpers.py is deleted"""
    task_helpers_path = Path(__file__).parent.parent / "src" / "giljo_mcp" / "api_helpers" / "task_helpers.py"
    assert not task_helpers_path.exists(), "task_helpers.py should be deleted"


def test_api_helpers_init_updated():
    """Test that api_helpers __init__.py is updated to remove task_helpers imports"""
    init_path = Path(__file__).parent.parent / "src" / "giljo_mcp" / "api_helpers" / "__init__.py"

    if init_path.exists():
        content = init_path.read_text()
        assert "task_helpers" not in content, "task_helpers should not be imported in __init__.py"


def test_test_api_integration_fix_deleted():
    """Test that test_api_integration_fix.py is deleted"""
    test_path = Path(__file__).parent.parent / "tests" / "test_api_integration_fix.py"
    assert not test_path.exists(), "test_api_integration_fix.py should be deleted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
