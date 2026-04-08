# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test runner for authentication and user management integration tests.

This script runs all auth-related integration tests and provides a summary report.
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run authentication integration tests."""

    test_files = [
        "tests/integration/test_wizard_flow_comprehensive.py",
        "tests/integration/test_user_management_flow.py",
        "tests/integration/test_api_key_manager.py",
    ]

    print("=" * 80)
    print("Running Authentication & User Management Integration Tests")
    print("=" * 80)
    print()

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for test_file in test_files:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_file}")
        print(f"{'=' * 80}\n")

        # Run pytest with verbose output
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--color=yes",
                "-x",  # Stop on first failure
            ],
            check=False,
            capture_output=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        if result.returncode != 0:
            print(f"\n❌ Tests failed in {test_file}")
            total_failed += 1
        else:
            print(f"\n✅ All tests passed in {test_file}")
            total_passed += 1

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Test Files Passed: {total_passed}")
    print(f"Test Files Failed: {total_failed}")
    print()

    if total_failed > 0:
        print("❌ Some tests failed. Please review the output above.")
        sys.exit(1)
    else:
        print("✅ All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
