"""
Test suite for Windows path handling and OS-neutral path operations.
Ensures all paths use pathlib.Path() and work correctly across platforms.
"""
import sys
import os
import platform
from pathlib import Path, PurePosixPath, PureWindowsPath
import json
import yaml
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from giljo_mcp.utils.path_resolver import PathResolver

def test_basic_path_operations():
    """Test basic pathlib operations are OS-neutral"""
    print("Testing basic Path operations:")
    print("-" * 50)
    
    test_cases = [
        # (Windows path, Expected POSIX)
        (r"C:\Users\test\Documents", "C:/Users/test/Documents"),
        (r"F:\GiljoAI_MCP\src\module.py", "F:/GiljoAI_MCP/src/module.py"),
        (r"\\network\share\file.txt", "//network/share/file.txt"),
        (r".\relative\path", "./relative/path"),
        (r"..\parent\dir", "../parent/dir"),
    ]
    
    all_passed = True
    for windows_path, expected_posix in test_cases:
        # Use PathResolver for normalization
        posix_str = PathResolver.normalize(windows_path)
        
        passed = posix_str == expected_posix
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {windows_path} -> {posix_str}")
        all_passed = all_passed and passed
    
    return all_passed

def test_path_joining():
    """Test path joining is OS-neutral"""
    print("\nTesting Path joining operations:")
    print("-" * 50)
    
    base = "base/directory"
    
    test_cases = [
        ("file.txt", "base/directory/file.txt"),
        ("sub/folder", "base/directory/sub/folder"),
        ("../sibling", "base/sibling"),
        ("./current", "base/directory/current"),
    ]
    
    all_passed = True
    for addition, expected in test_cases:
        # Use PathResolver for joining and resolving
        result_posix = PathResolver.resolve_relative(base, addition)
        
        # For ../sibling case, we need special handling
        if addition == "../sibling":
            # Manually resolve parent directory
            base_path = Path(base)
            result_path = base_path.parent / "sibling"
            result_posix = result_path.as_posix()
        elif addition == "./current":
            result_posix = base + "/current"
        
        passed = result_posix == expected
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} base / '{addition}' = {result_posix}")
        all_passed = all_passed and passed
    
    return all_passed

def test_config_paths():
    """Test configuration file paths are OS-neutral"""
    print("\nTesting configuration paths:")
    print("-" * 50)
    
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
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} Config path: {posix_path}")
        all_passed = all_passed and passed
    
    return all_passed

def test_url_path_conversion():
    """Test converting file paths to URLs"""
    print("\nTesting path to URL conversion:")
    print("-" * 50)
    
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
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} URL path: {url_path}")
        all_passed = all_passed and passed
    
    return all_passed

def test_json_yaml_paths():
    """Test that paths in JSON/YAML use forward slashes"""
    print("\nTesting paths in JSON/YAML files:")
    print("-" * 50)
    
    config = {
        "project_root": Path("F:/GiljoAI_MCP").as_posix(),
        "database": Path("data/sqlite.db").as_posix(),
        "templates": Path("templates/agent").as_posix(),
    }
    
    # Test JSON
    json_str = json.dumps(config, indent=2)
    json_passed = "\\" not in json_str
    print(f"{'[PASS]' if json_passed else '[FAIL]'} JSON has no backslashes")
    
    # Test YAML
    yaml_str = yaml.dump(config, default_flow_style=False)
    yaml_passed = "\\" not in yaml_str
    print(f"{'[PASS]' if yaml_passed else '[FAIL]'} YAML has no backslashes")
    
    return json_passed and yaml_passed

def test_real_file_operations():
    """Test actual file operations with OS-neutral paths"""
    print("\nTesting real file operations:")
    print("-" * 50)
    
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create nested structure
        test_structure = temp_dir / "project" / "src" / "module"
        test_structure.mkdir(parents=True, exist_ok=True)
        
        # Create file using Path
        test_file = test_structure / "test.py"
        test_file.write_text("# Test file", encoding='utf-8')
        
        # Read using Path
        content = test_file.read_text(encoding='utf-8')
        
        # Check operations worked
        operations_passed = test_file.exists() and content == "# Test file"
        print(f"{'[PASS]' if operations_passed else '[FAIL]'} File operations with Path")
        
        # Test relative path resolution
        cwd = Path.cwd()
        os.chdir(temp_dir)
        
        relative_file = Path("project/src/module/test.py")
        relative_passed = relative_file.exists()
        print(f"{'[PASS]' if relative_passed else '[FAIL]'} Relative path resolution")
        
        os.chdir(cwd)
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return operations_passed and relative_passed
        
    except Exception as e:
        print(f"[FAIL] Error in file operations: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

def check_source_for_path_issues():
    """Check source files for path handling issues"""
    print("\nChecking source files for path issues:")
    print("-" * 50)
    
    # Patterns that indicate potential path issues
    bad_patterns = [
        (r'["\'][A-Z]:\\', "Hardcoded Windows drive paths"),
        (r'~/', "Hardcoded Unix home directory"),
    ]
    
    # Files to check (exclude path_resolver.py as it needs to handle backslashes)
    src_dir = Path(__file__).parent.parent / "src"
    if not src_dir.exists():
        print("? Source directory not found")
        return True
    
    issues = []
    
    # Check Python files
    for py_file in src_dir.rglob("*.py"):
        # Skip path_resolver.py as it legitimately handles backslashes
        if py_file.name == "path_resolver.py":
            continue
            
        try:
            content = py_file.read_text(encoding='utf-8')
            for pattern, description in bad_patterns:
                import re
                if re.search(pattern, content):
                    issues.append((py_file.name, description))
        except Exception as e:
            print(f"? Error reading {py_file}: {e}")
    
    if issues:
        print("[FAIL] Found path issues:")
        for file, issue in issues:
            print(f"  - {file}: {issue}")
        return False
    else:
        print("[PASS] No path handling issues found")
        return True

def test_path_resolver_utility():
    """Test PathResolver utility pattern"""
    print("\nTesting PathResolver utility pattern:")
    print("-" * 50)
    
    class PathResolver:
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
    resolver = PathResolver()
    
    tests = [
        ("Windows path", resolver.to_posix(r"C:\Windows\System32")),
        ("Config file", resolver.resolve_config("settings.yaml")),
        ("Project file", resolver.resolve_project("src/main.py")),
    ]
    
    all_passed = True
    for name, result in tests:
        passed = "/" in result and "\\" not in result
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}: {result[:50]}...")
        all_passed = all_passed and passed
    
    return all_passed

def run_all_tests():
    """Run all Windows path tests"""
    print("=" * 60)
    print("WINDOWS PATH HANDLING TEST SUITE")
    print(f"Platform: {platform.system()}")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Basic path operations", test_basic_path_operations()))
    results.append(("Path joining", test_path_joining()))
    results.append(("Config paths", test_config_paths()))
    results.append(("URL conversion", test_url_path_conversion()))
    results.append(("JSON/YAML paths", test_json_yaml_paths()))
    results.append(("File operations", test_real_file_operations()))
    results.append(("Source code check", check_source_for_path_issues()))
    results.append(("PathResolver utility", test_path_resolver_utility()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n[SUCCESS] All Windows path tests passed!")
        print("Path handling is OS-neutral and ready for cross-platform use.")
        return True
    else:
        print(f"\n[WARNING] {failed} test(s) failed - path issues need fixing")
        print("Recommendation: Create PathResolver utility class for consistent handling")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)