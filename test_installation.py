#!/usr/bin/env python3
"""
Test Installation Components for GiljoAI MCP

Tests launcher creator and config generator
"""

import sys
from pathlib import Path

# Add installers to path
sys.path.insert(0, str(Path.cwd() / 'installers'))

def test_config_generator():
    """Test configuration generator"""
    print("Testing Configuration Generator...")
    print("-" * 40)

    from config_generator import ConfigGenerator
    generator = ConfigGenerator()

    # Test directory creation
    success, msg = generator.create_required_directories()
    print(f"[{'OK' if success else 'FAIL'}] {msg}")

    # Test config creation
    success, msg = generator.create_config_file()
    print(f"[{'OK' if success else 'FAIL'}] {msg}")

    # Test validation
    if Path('config.yaml').exists():
        valid, msg = generator.validate_config()
        print(f"[{'OK' if valid else 'FAIL'}] Validation: {msg}")

    print()

def test_launcher_creator():
    """Test launcher creator"""
    print("Testing Launcher Creator...")
    print("-" * 40)

    from launcher_creator import LauncherCreator
    creator = LauncherCreator()

    # Test creating all launchers
    results = creator.create_all_launchers()

    # Print results
    for name, (success, msg) in results.items():
        print(f"[{'OK' if success else 'FAIL'}] {name}: {msg}")

    print()

def main():
    """Main test function"""
    print("=" * 50)
    print("GiljoAI MCP Installation Component Test")
    print("=" * 50)
    print()

    # Test config generator
    test_config_generator()

    # Test launcher creator
    test_launcher_creator()

    print("=" * 50)
    print("Test Complete!")
    print("=" * 50)

    # Show what's been created
    print("\nCreated files:")
    files = [
        'config.yaml',
        'start_giljo.bat',
        'stop_giljo.bat',
        'open_dashboard.bat'
    ]

    for file in files:
        path = Path(file)
        if path.exists():
            print(f"  [OK] {file}")
        else:
            print(f"  [MISSING] {file}")

if __name__ == "__main__":
    main()