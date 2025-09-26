#!/usr/bin/env python3
"""
Run coverage analysis on message_queue.py
"""

import os
import subprocess
import sys


def run_coverage():
    """Run coverage analysis on message queue tests"""

    # Change to project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_message_queue.py",
        "--cov=src.giljo_mcp.message_queue",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=0",  # Don't fail on low coverage yet
        "-v",
    ]

    print("Running coverage analysis...")
    print("Command:", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"Return code: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"Error running coverage: {e}")
        return False


if __name__ == "__main__":
    success = run_coverage()
    sys.exit(0 if success else 1)
