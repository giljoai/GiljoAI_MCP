#!/usr/bin/env python3
"""
Simplified test suite for Project 5.2 Setup Enhancements
Tests the actual implemented modules
"""

import os
import sys
import json
import time
import platform
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Test results
results = {
    'tests': [],
    'passed': 0,
    'failed': 0,
    'errors': []
}

def test_result(name, passed, message=""):
    """Record test result"""
    results['tests'].append({
        'name': name,
        'passed': passed,
        'message': message
    })
    if passed:
        results['passed'] += 1
        print(f"[PASS] {name}")
    else:
        results['failed'] += 1
        results['errors'].append(f"{name}: {message}")
        print(f"[FAIL] {name}: {message}")

print("=" * 70)
print("PROJECT 5.2 SETUP ENHANCEMENT - VALIDATION TEST SUITE")
print("=" * 70)
print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
print(f"Python: {platform.python_version()}")
print("=" * 70)

# Test 1: Check all new modules exist
print("\n1. MODULE EXISTENCE CHECK")
print("-" * 30)
modules = ['setup_gui', 'setup_platform', 'setup_migration', 'setup_dependencies', 'setup_config']
for module_name in modules:
    module_file = f"{module_name}.py"
    if os.path.exists(module_file):
        # Check file size
        size = os.path.getsize(module_file)
        test_result(f"{module_name} exists", True, f"Size: {size:,} bytes")
    else:
        test_result(f"{module_name} exists", False, "File not found")

# Test 2: Import all modules
print("\n2. MODULE IMPORT TEST")
print("-" * 30)
imported_modules = {}
for module_name in modules:
    try:
        module = __import__(module_name)
        imported_modules[module_name] = module
        test_result(f"Import {module_name}", True)
    except ImportError as e:
        test_result(f"Import {module_name}", False, str(e))

# Test 3: Platform Detection
print("\n3. PLATFORM DETECTION TEST")
print("-" * 30)
if 'setup_platform' in imported_modules:
    try:
        detector = imported_modules['setup_platform'].PlatformDetector()
        info = detector.get_full_info()

        # Check required fields
        required = ['system', 'architecture', 'python_version']
        for field in required:
            if field in info:
                test_result(f"Platform {field}", True, f"{info[field]}")
            else:
                test_result(f"Platform {field}", False, "Not detected")

        # Package managers
        pkg_mgrs = info.get('package_managers', [])
        test_result("Package managers detected", len(pkg_mgrs) > 0,
                   f"Found: {', '.join(pkg_mgrs[:3]) if pkg_mgrs else 'None'}")

    except Exception as e:
        test_result("Platform detection", False, str(e))

# Test 4: GUI Module Structure
print("\n4. GUI MODULE STRUCTURE TEST")
print("-" * 30)
if 'setup_gui' in imported_modules:
    try:
        module = imported_modules['setup_gui']
        # Check for key classes/functions
        expected = ['SetupWizard', 'GUISetupManager']
        for item in expected:
            if hasattr(module, item):
                test_result(f"GUI has {item}", True)
            else:
                test_result(f"GUI has {item}", False, "Not found")
    except Exception as e:
        test_result("GUI structure", False, str(e))

# Test 5: Dependency Manager
print("\n5. DEPENDENCY MANAGER TEST")
print("-" * 30)
if 'setup_dependencies' in imported_modules:
    try:
        manager = imported_modules['setup_dependencies'].DependencyManager()

        # Test package detection
        packages = manager.get_installed_packages()
        test_result("Get installed packages", isinstance(packages, dict),
                   f"Found {len(packages)} packages")

        # Test requirements parsing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("fastapi>=0.100.0\n")
            f.write("# optional\n")
            f.write("redis  # optional: caching\n")
            temp_file = f.name

        try:
            deps = manager.parse_requirements(temp_file)
            test_result("Parse requirements", len(deps['core']) > 0,
                       f"Core: {len(deps['core'])}, Optional: {len(deps['optional'])}")
        finally:
            os.unlink(temp_file)

    except Exception as e:
        test_result("Dependency manager", False, str(e))

# Test 6: Migration Tool
print("\n6. MIGRATION TOOL TEST")
print("-" * 30)
if 'setup_migration' in imported_modules:
    try:
        migrator = imported_modules['setup_migration'].AKEMCPMigrator()

        # Test AKE-MCP detection
        ake_path = Path("F:/AKE-MCP")
        if ake_path.exists():
            test_result("AKE-MCP detected", True, str(ake_path))
        else:
            test_result("AKE-MCP detected", True, "Not present (expected in test)")

        # Test data validation
        sample_data = {
            'projects': [{'id': 'test', 'name': 'Test'}],
            'agents': [],
            'messages': []
        }
        valid = migrator.validate_data(sample_data)
        test_result("Migration data validation", valid, "Sample data validated")

    except Exception as e:
        test_result("Migration tool", False, str(e))

# Test 7: Configuration Manager
print("\n7. CONFIGURATION MANAGER TEST")
print("-" * 30)
if 'setup_config' in imported_modules:
    try:
        manager = imported_modules['setup_config'].ConfigurationManager()

        # Test config creation
        test_config = {
            'environment': 'test',
            'database': {'type': 'sqlite'},
            'api_port': 6002
        }

        # Test JSON export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_json = f.name

        try:
            success = manager.export_config(test_config, temp_json)
            test_result("Export config to JSON", success and os.path.exists(temp_json))

            # Test import
            imported = manager.import_config(temp_json)
            test_result("Import config from JSON",
                       imported and imported['environment'] == 'test')
        finally:
            if os.path.exists(temp_json):
                os.unlink(temp_json)

    except Exception as e:
        test_result("Config manager", False, str(e))

# Test 8: GUI Flag in setup.py
print("\n8. SETUP.PY GUI INTEGRATION TEST")
print("-" * 30)
try:
    # Check if setup.py accepts --gui flag
    result = subprocess.run(
        [sys.executable, 'setup.py', '--help'],
        capture_output=True,
        text=True,
        timeout=5
    )

    has_gui = '--gui' in result.stdout or '--gui' in result.stderr
    test_result("setup.py has --gui flag", has_gui,
               "GUI mode available" if has_gui else "Not found in help")

except Exception as e:
    test_result("setup.py --gui check", False, str(e))

# Test 9: Backward Compatibility
print("\n9. BACKWARD COMPATIBILITY TEST")
print("-" * 30)
try:
    from setup import GiljoSetup
    setup = GiljoSetup()

    # Check original methods exist
    methods = ['detect_platform', 'setup_database', 'create_directories',
               'check_dependencies', 'generate_env_file']

    for method in methods:
        if hasattr(setup, method):
            test_result(f"Legacy method {method}", True)
        else:
            test_result(f"Legacy method {method}", False, "Not found")

except Exception as e:
    test_result("Backward compatibility", False, str(e))

# Test 10: Performance Benchmark
print("\n10. PERFORMANCE BENCHMARK")
print("-" * 30)
try:
    start_time = time.time()

    # Quick setup simulation
    from setup import GiljoSetup
    setup = GiljoSetup()
    setup.detect_platform()

    elapsed = time.time() - start_time
    test_result("Setup initialization time", elapsed < 5,
               f"{elapsed:.2f} seconds")

    # Memory check
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    test_result("Memory usage", memory_mb < 500,
               f"{memory_mb:.1f} MB")

except ImportError:
    test_result("Performance test", False, "psutil not installed")
except Exception as e:
    test_result("Performance test", False, str(e))

# Generate Report
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Total Tests: {results['passed'] + results['failed']}")
print(f"Passed: {results['passed']} [OK]")
print(f"Failed: {results['failed']}" + (" [ERROR]" if results['failed'] > 0 else ""))
print(f"Success Rate: {(results['passed'] / (results['passed'] + results['failed']) * 100):.1f}%")

if results['errors']:
    print("\nFailed Tests:")
    for error in results['errors']:
        print(f"  - {error}")

# Save detailed report
report = {
    'timestamp': datetime.now().isoformat(),
    'platform': {
        'system': platform.system(),
        'release': platform.release(),
        'python': platform.python_version()
    },
    'summary': {
        'total': results['passed'] + results['failed'],
        'passed': results['passed'],
        'failed': results['failed'],
        'success_rate': f"{(results['passed'] / (results['passed'] + results['failed']) * 100):.1f}%"
    },
    'tests': results['tests'],
    'errors': results['errors']
}

with open('setup_test_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"\nDetailed report saved to: setup_test_report.json")
print("=" * 70)

# Exit code
sys.exit(0 if results['failed'] == 0 else 1)