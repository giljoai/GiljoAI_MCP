"""
Test suite for UTF-8 encoding handling across the codebase.
Tests file reading/writing with special characters and encoding parameters.
"""
import sys
import os
from pathlib import Path
import json
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_file_reading_without_encoding():
    """Test what happens when encoding is not specified"""
    test_file = Path(__file__).parent / "test_data" / "utf8_test.txt"
    
    print("Testing file reading WITHOUT encoding='utf-8':")
    print("-" * 50)
    
    try:
        # This might fail on Windows with default encoding
        with open(test_file, 'r') as f:
            content = f.read()
        print("[FAIL] WARNING: File read without encoding succeeded (may fail on some systems)")
        print(f"  First 100 chars: {content[:100]}")
    except UnicodeDecodeError as e:
        print(f"[PASS] Expected error without encoding: {e}")
    except Exception as e:
        print(f"? Unexpected error: {e}")

def test_file_reading_with_encoding():
    """Test reading with explicit UTF-8 encoding"""
    test_file = Path(__file__).parent / "test_data" / "utf8_test.txt"
    
    print("\nTesting file reading WITH encoding='utf-8':")
    print("-" * 50)
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for various character types
        checks = [
            ("Emojis", "😀" in content and "💻" in content),
            ("French accents", "École" in content and "café" in content),
            ("Chinese", "你好世界" in content),
            ("Japanese", "こんにちは" in content),
            ("Math symbols", "∑" in content and "∞" in content),
            ("Box drawing", "┌" in content and "└" in content),
            ("Arabic RTL", "مرحبا" in content)
        ]
        
        all_passed = True
        for name, passed in checks:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {name}: {'Found' if passed else 'Missing'}")
            all_passed = all_passed and passed
        
        if all_passed:
            print("[PASS] All UTF-8 characters read correctly!")
        else:
            print("[FAIL] Some UTF-8 characters missing!")
        
        return all_passed
        
    except Exception as e:
        print(f"[FAIL] Error reading with UTF-8 encoding: {e}")
        return False

def test_json_with_utf8():
    """Test JSON handling with UTF-8 characters"""
    print("\nTesting JSON with UTF-8 characters:")
    print("-" * 50)
    
    test_data = {
        "emojis": "🚀 🎉 🔥",
        "chinese": "你好世界",
        "accents": "café résumé",
        "math": "π ≈ 3.14159"
    }
    
    test_file = Path(__file__).parent / "test_data" / "utf8_test.json"
    
    try:
        # Write JSON with UTF-8
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        print("[PASS] JSON written with UTF-8 encoding")
        
        # Read it back
        with open(test_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        # Verify content
        if loaded_data == test_data:
            print("[PASS] JSON round-trip successful with UTF-8 characters")
            return True
        else:
            print("[FAIL] JSON data mismatch after round-trip")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error with JSON UTF-8 handling: {e}")
        return False

def test_yaml_with_utf8():
    """Test YAML handling with UTF-8 characters"""
    print("\nTesting YAML with UTF-8 characters:")
    print("-" * 50)
    
    test_data = {
        "project": "GiljoAI 🚀",
        "features": ["Multi-tenant 🏢", "Local-first 💻", "Progressive 📈"],
        "i18n": {
            "chinese": "你好",
            "japanese": "こんにちは",
            "arabic": "مرحبا"
        }
    }
    
    test_file = Path(__file__).parent / "test_data" / "utf8_test.yaml"
    
    try:
        # Write YAML with UTF-8
        with open(test_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_data, f, allow_unicode=True, default_flow_style=False)
        print("[PASS] YAML written with UTF-8 encoding")
        
        # Read it back
        with open(test_file, 'r', encoding='utf-8') as f:
            loaded_data = yaml.safe_load(f)
        
        # Verify content
        if loaded_data == test_data:
            print("[PASS] YAML round-trip successful with UTF-8 characters")
            return True
        else:
            print("[FAIL] YAML data mismatch after round-trip")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error with YAML UTF-8 handling: {e}")
        return False

def check_source_files_encoding():
    """Check if source files properly handle encoding"""
    print("\nChecking source files for encoding issues:")
    print("-" * 50)
    
    # Files that should have encoding='utf-8' specified
    files_to_check = [
        ("src/giljo_mcp/discovery.py", [135, 371, 735]),  # Lines reported to be missing encoding
        ("tools/context.py", []),  # Check if this file exists and has issues
    ]
    
    issues_found = []
    
    for file_path, line_numbers in files_to_check:
        full_path = Path(__file__).parent.parent / file_path
        if not full_path.exists():
            print(f"? File not found: {file_path}")
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"\nChecking {file_path}:")
        
        # Look for open() calls without encoding
        for i, line in enumerate(lines, 1):
            if 'open(' in line and 'encoding=' not in line:
                # Check if it's opening in binary mode
                if "'rb'" not in line and '"rb"' not in line and "'wb'" not in line and '"wb"' not in line:
                    issues_found.append((file_path, i, line.strip()))
                    print(f"  Line {i}: Missing encoding parameter")
                    print(f"    {line.strip()[:80]}...")
    
    if issues_found:
        print(f"\n[FAIL] Found {len(issues_found)} file operations missing encoding='utf-8'")
        return False
    else:
        print("\n[PASS] No encoding issues found in checked files")
        return True

def test_path_encoding():
    """Test path handling with non-ASCII characters"""
    print("\nTesting paths with non-ASCII characters:")
    print("-" * 50)
    
    # Create directory with non-ASCII name
    test_dir = Path(__file__).parent / "test_data" / "测试目录_テスト"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create file with non-ASCII name
    test_file = test_dir / "файл_🚀.txt"
    
    try:
        # Write content
        test_file.write_text("Test content with émojis 🎉", encoding='utf-8')
        print("[PASS] Created file with non-ASCII path")
        
        # Read it back
        content = test_file.read_text(encoding='utf-8')
        if "émojis 🎉" in content:
            print("[PASS] Read content from non-ASCII path")
        else:
            print("[FAIL] Content mismatch from non-ASCII path")
        
        # List directory
        files = list(test_dir.iterdir())
        if test_file in files:
            print("[PASS] Non-ASCII filename listed correctly")
        else:
            print("[FAIL] Non-ASCII filename not found in directory listing")
        
        # Clean up
        test_file.unlink()
        test_dir.rmdir()
        print("[PASS] Cleaned up test files")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error with non-ASCII paths: {e}")
        return False

def run_all_tests():
    """Run all UTF-8 encoding tests"""
    print("=" * 60)
    print("UTF-8 ENCODING TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run each test
    test_file_reading_without_encoding()
    results.append(("UTF-8 file reading", test_file_reading_with_encoding()))
    results.append(("JSON UTF-8 handling", test_json_with_utf8()))
    results.append(("YAML UTF-8 handling", test_yaml_with_utf8()))
    results.append(("Path with non-ASCII", test_path_encoding()))
    results.append(("Source file encoding", check_source_files_encoding()))
    
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
        print("\n[SUCCESS] All UTF-8 encoding tests passed!")
        return True
    else:
        print(f"\n[WARNING] {failed} test(s) failed - encoding issues need fixing")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)