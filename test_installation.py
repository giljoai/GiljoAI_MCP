#!/usr/bin/env python3
"""
Test script to diagnose installation issues
"""

import sys
import subprocess
from pathlib import Path

def test_requirements():
    """Test if requirements can be installed"""
    print("Testing Python dependencies installation...")

    # Check Python version
    print(f"Python version: {sys.version}")

    # Check if pip is available
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                              capture_output=True, text=True)
        print(f"Pip version: {result.stdout.strip()}")
    except Exception as e:
        print(f"ERROR: pip not available: {e}")
        return False

    # Check if requirements.txt exists
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("ERROR: requirements.txt not found")
        return False
    print(f"Found requirements.txt ({req_file.stat().st_size} bytes)")

    # Try a dry run of pip install
    print("\nTesting pip install (dry run)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--dry-run", "-r", "requirements.txt"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("ERROR: pip install would fail")
        print("STDERR:", result.stderr[:1000])
        return False

    print("SUCCESS: pip install test passed")
    return True

def test_imports():
    """Test if critical imports work"""
    print("\nTesting critical imports...")

    critical_modules = {
        'src.giljo_mcp.models.base': 'Database models',
        'installer.health_checker': 'Health checker',
        'setup_config': 'Configuration manager'
    }

    for module, description in critical_modules.items():
        try:
            __import__(module)
            print(f"[OK] {description} ({module})")
        except ImportError as e:
            print(f"[FAIL] {description} ({module}): {e}")
        except Exception as e:
            print(f"[ERROR] {description} ({module}): Unexpected error: {e}")

def test_paths():
    """Test if required paths exist or can be created"""
    print("\nTesting paths...")

    paths_to_check = [
        "data",
        "logs",
        "src/giljo_mcp",
        "installer"
    ]

    for path_str in paths_to_check:
        path = Path(path_str)
        if path.exists():
            print(f"[OK] {path_str} exists")
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"[OK] {path_str} can be created")
                path.rmdir()  # Clean up test
            except Exception as e:
                print(f"[FAIL] {path_str} cannot be created: {e}")

def test_database():
    """Test database initialization"""
    print("\nTesting database initialization...")

    try:
        from src.giljo_mcp.models.base import init_database, get_database_url

        db_url = get_database_url()
        print(f"Database URL pattern: {db_url.split('://')[0]}://...")

        result = init_database()
        if result:
            print("[OK] Database initialization successful")
        else:
            print("[FAIL] Database initialization failed")
    except ImportError as e:
        print(f"[FAIL] Cannot import database modules: {e}")
    except Exception as e:
        print(f"[ERROR] Database initialization error: {e}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("GiljoAI MCP Installation Diagnostic")
    print("=" * 60)

    # Run tests
    test_requirements()
    test_imports()
    test_paths()
    test_database()

    print("\n" + "=" * 60)
    print("Diagnostic complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
