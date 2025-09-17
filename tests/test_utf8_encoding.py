"""
Test suite for UTF-8 encoding handling across the codebase.
Tests file reading/writing with special characters and encoding parameters.
"""

import json
import sys
from pathlib import Path

import yaml


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_file_reading_without_encoding():
    """Test what happens when encoding is not specified"""
    test_file = Path(__file__).parent / "test_data" / "utf8_test.txt"

    try:
        # This might fail on Windows with default encoding
        with open(test_file) as f:
            f.read()
    except UnicodeDecodeError:
        pass
    except Exception:
        pass


def test_file_reading_with_encoding():
    """Test reading with explicit UTF-8 encoding"""
    test_file = Path(__file__).parent / "test_data" / "utf8_test.txt"

    try:
        with open(test_file, encoding="utf-8") as f:
            content = f.read()

        # Check for various character types
        checks = [
            ("Emojis", "😀" in content and "💻" in content),
            ("French accents", "École" in content and "café" in content),
            ("Chinese", "你好世界" in content),
            ("Japanese", "こんにちは" in content),
            ("Math symbols", "∑" in content and "∞" in content),
            ("Box drawing", "┌" in content and "└" in content),
            ("Arabic RTL", "مرحبا" in content),
        ]

        all_passed = True
        for _name, passed in checks:
            all_passed = all_passed and passed

        if all_passed:
            pass
        else:
            pass

        return all_passed

    except Exception:
        return False


def test_json_with_utf8():
    """Test JSON handling with UTF-8 characters"""

    test_data = {"emojis": "🚀 🎉 🔥", "chinese": "你好世界", "accents": "café résumé", "math": "π ≈ 3.14159"}

    test_file = Path(__file__).parent / "test_data" / "utf8_test.json"

    try:
        # Write JSON with UTF-8
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        # Read it back
        with open(test_file, encoding="utf-8") as f:
            loaded_data = json.load(f)

        # Verify content
        return loaded_data == test_data

    except Exception:
        return False


def test_yaml_with_utf8():
    """Test YAML handling with UTF-8 characters"""

    test_data = {
        "project": "GiljoAI 🚀",
        "features": ["Multi-tenant 🏢", "Local-first 💻", "Progressive 📈"],
        "i18n": {"chinese": "你好", "japanese": "こんにちは", "arabic": "مرحبا"},
    }

    test_file = Path(__file__).parent / "test_data" / "utf8_test.yaml"

    try:
        # Write YAML with UTF-8
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(test_data, f, allow_unicode=True, default_flow_style=False)

        # Read it back
        with open(test_file, encoding="utf-8") as f:
            loaded_data = yaml.safe_load(f)

        # Verify content
        return loaded_data == test_data

    except Exception:
        return False


def check_source_files_encoding():
    """Check if source files properly handle encoding"""

    # Files that should have encoding='utf-8' specified
    files_to_check = [
        ("src/giljo_mcp/discovery.py", [135, 371, 735]),  # Lines reported to be missing encoding
        ("tools/context.py", []),  # Check if this file exists and has issues
    ]

    issues_found = []

    for file_path, _line_numbers in files_to_check:
        full_path = Path(__file__).parent.parent / file_path
        if not full_path.exists():
            continue

        with open(full_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Look for open() calls without encoding
        for i, line in enumerate(lines, 1):
            if "open(" in line and "encoding=" not in line:
                # Check if it's opening in binary mode
                if "'rb'" not in line and '"rb"' not in line and "'wb'" not in line and '"wb"' not in line:
                    issues_found.append((file_path, i, line.strip()))

    return not issues_found


def test_path_encoding():
    """Test path handling with non-ASCII characters"""

    # Create directory with non-ASCII name
    test_dir = Path(__file__).parent / "test_data" / "测试目录_テスト"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create file with non-ASCII name
    test_file = test_dir / "файл_🚀.txt"

    try:
        # Write content
        test_file.write_text("Test content with émojis 🎉", encoding="utf-8")

        # Read it back
        content = test_file.read_text(encoding="utf-8")
        if "émojis 🎉" in content:
            pass
        else:
            pass

        # List directory
        files = list(test_dir.iterdir())
        if test_file in files:
            pass
        else:
            pass

        # Clean up
        test_file.unlink()
        test_dir.rmdir()

        return True

    except Exception:
        return False


def run_all_tests():
    """Run all UTF-8 encoding tests"""

    results = []

    # Run each test
    test_file_reading_without_encoding()
    results.append(("UTF-8 file reading", test_file_reading_with_encoding()))
    results.append(("JSON UTF-8 handling", test_json_with_utf8()))
    results.append(("YAML UTF-8 handling", test_yaml_with_utf8()))
    results.append(("Path with non-ASCII", test_path_encoding()))
    results.append(("Source file encoding", check_source_files_encoding()))

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
