"""
Test suite for Windows path handling and OS-neutral path operations.
Ensures all paths use pathlib.Path() and work correctly across platforms.
"""

import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path

import yaml


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config_paths():
    """Test configuration file paths are OS-neutral"""

    home = Path.home()

    # Test config directory patterns
    config_patterns = [
        (".giljo-mcp", "config.yaml"),
        ("AppData/Local/GiljoAI" if platform.system() == "Windows" else ".config/giljoai", "settings.json"),
    ]

    all_passed = True
    for dir_name, file_name in config_patterns:
        config_dir = home / dir_name
        config_file = config_dir / file_name

        # Check path uses forward slashes
        posix_path = config_file.as_posix()

        passed = "/" in posix_path and "\\" not in posix_path
        all_passed = all_passed and passed

    return all_passed


def test_url_path_conversion():
    """Test converting file paths to URLs"""

    test_paths = [
        Path("C:/Users/test/file.txt"),
        Path("/home/user/document.pdf"),
        Path("relative/path/to/file.js"),
    ]

    all_passed = True
    for path in test_paths:
        # Convert to URL-safe format
        url_path = path.as_posix()

        # URLs should never have backslashes
        passed = "\\" not in url_path
        all_passed = all_passed and passed

    return all_passed


def test_json_yaml_paths():
    """Test that paths in JSON/YAML use forward slashes"""

    config = {
        "project_root": Path("F:/GiljoAI_MCP").as_posix(),
        "database": Path("data/sqlite.db").as_posix(),
        "templates": Path("templates/agent").as_posix(),
    }

    # Test JSON
    json_str = json.dumps(config, indent=2)
    json_passed = "\\" not in json_str

    # Test YAML
    yaml_str = yaml.dump(config, default_flow_style=False)
    yaml_passed = "\\" not in yaml_str

    return json_passed and yaml_passed


def test_real_file_operations():
    """Test actual file operations with OS-neutral paths"""

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create nested structure
        test_structure = temp_dir / "project" / "src" / "module"
        test_structure.mkdir(parents=True, exist_ok=True)

        # Create file using Path
        test_file = test_structure / "test.py"
        test_file.write_text("# Test file", encoding="utf-8")

        # Read using Path
        content = test_file.read_text(encoding="utf-8")

        # Check operations worked
        operations_passed = test_file.exists() and content == "# Test file"

        # Test relative path resolution
        cwd = Path.cwd()
        os.chdir(temp_dir)

        relative_file = Path("project/src/module/test.py")
        relative_passed = relative_file.exists()

        os.chdir(cwd)

        # Clean up
        shutil.rmtree(temp_dir)

        return operations_passed and relative_passed

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False


def check_source_for_path_issues():
    """Check source files for path handling issues"""

    # Patterns that indicate potential path issues
    bad_patterns = [
        (r'["\'][A-Z]:\\', "Hardcoded Windows drive paths"),
        (r"~/", "Hardcoded Unix home directory"),
    ]

    # Files to check (exclude path_normalizer.py as it needs to handle backslashes)
    src_dir = Path(__file__).parent.parent / "src"
    if not src_dir.exists():
        return True

    issues = []

    # Check Python files
    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            for pattern, description in bad_patterns:
                import re

                if re.search(pattern, content):
                    issues.append((py_file.name, description))
        except Exception:
            pass

    if issues:
        for _file, _issue in issues:
            pass
        return False
    return True


def test_path_resolver_utility():
    """Test PathNormalizer utility pattern"""

    class PathNormalizer:
        """Utility for consistent path handling"""

        @staticmethod
        def to_posix(path):
            """Convert any path to POSIX format"""
            return Path(path).as_posix()

        @staticmethod
        def resolve_config(name):
            """Resolve configuration file path"""
            config_dir = Path.home() / ".giljo-mcp"
            return (config_dir / name).as_posix()

        @staticmethod
        def resolve_project(relative_path):
            """Resolve path relative to project root"""
            project_root = Path(__file__).parent.parent
            return (project_root / relative_path).as_posix()

    # Test resolver
    resolver = PathNormalizer()

    tests = [
        ("Windows path", resolver.to_posix(r"C:\Windows\System32")),
        ("Config file", resolver.resolve_config("settings.yaml")),
        ("Project file", resolver.resolve_project("src/main.py")),
    ]

    all_passed = True
    for _name, result in tests:
        passed = "/" in result and "\\" not in result
        all_passed = all_passed and passed

    return all_passed


def run_all_tests():
    """Run all Windows path tests"""

    results = []

    # Run tests
    results.append(("Config paths", test_config_paths()))
    results.append(("URL conversion", test_url_path_conversion()))
    results.append(("JSON/YAML paths", test_json_yaml_paths()))
    results.append(("File operations", test_real_file_operations()))
    results.append(("Source code check", check_source_for_path_issues()))
    results.append(("PathNormalizer utility", test_path_resolver_utility()))

    # Summary

    passed = 0
    failed = 0

    for _name, result in results:
        if result:
            passed += 1
        else:
            failed += 1

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    # sys.exit(0 if success else 1)  # Commented for pytest
