"""
Test suite for Handover 0702: Utils & Config Cleanup
Verifies naming collision resolution and orphan file deletion.
"""

import sys
from pathlib import Path

import pytest


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_path_normalizer_module_exists():
    """Test that PathNormalizer module exists at correct location"""
    from src.giljo_mcp.utils.path_normalizer import PathNormalizer

    assert PathNormalizer is not None


def test_path_normalizer_class_name():
    """Test that class is named PathNormalizer (not PathResolver)"""
    from src.giljo_mcp.utils.path_normalizer import PathNormalizer

    assert PathNormalizer.__name__ == "PathNormalizer"


def test_path_normalizer_convenience_functions():
    """Test that convenience functions exist and work"""
    from src.giljo_mcp.utils.path_normalizer import normalize_path, join_paths, resolve_relative_path

    # Test normalize_path
    result = normalize_path(r"C:\Windows\System32")
    assert result == "C:/Windows/System32"
    assert "\\" not in result

    # Test join_paths
    result = join_paths("base", "subdir", "file.txt")
    assert "base" in result
    assert "/" in result or result == "base/subdir/file.txt"

    # Test resolve_relative_path
    result = resolve_relative_path("base/dir", "file.txt")
    assert "file.txt" in result


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


def test_path_normalizer_normalization():
    """Test PathNormalizer normalizes paths correctly"""
    from src.giljo_mcp.utils.path_normalizer import PathNormalizer

    test_cases = [
        (r"C:\Users\test\Documents", "C:/Users/test/Documents"),
        (r"F:\GiljoAI_MCP\src\module.py", "F:/GiljoAI_MCP/src/module.py"),
        (r".\relative\path", "./relative/path"),
        (r"..\parent\dir", "../parent/dir"),
    ]

    for windows_path, expected in test_cases:
        result = PathNormalizer.normalize(windows_path)
        assert result == expected, f"Expected {expected}, got {result}"


def test_path_normalizer_joining():
    """Test PathNormalizer joins paths correctly"""
    from src.giljo_mcp.utils.path_normalizer import PathNormalizer

    result = PathNormalizer.join("base", "dir", "file.txt")
    assert "/" in result
    assert "\\" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
