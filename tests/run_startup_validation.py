#!/usr/bin/env python3
"""
Quick test runner for startup validation - runs tests and generates report
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run startup validation tests and generate report"""
    print("=" * 80)
    print("GiljoAI MCP Production Startup Validation")
    print("=" * 80)
    print()

    test_file = Path(__file__).parent / "test_startup_validation.py"

    # Run tests without coverage
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "--no-cov",
            "--tb=short",
            "-q"
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    print()
    print("=" * 80)
    if result.returncode == 0:
        print("ALL TESTS PASSED - PRODUCTION READY")
    else:
        print(f"TESTS FAILED - Exit code: {result.returncode}")
    print("=" * 80)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
