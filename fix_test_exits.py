#!/usr/bin/env python3
"""
Quick script to comment out sys.exit() calls in test files for pytest compatibility
"""

import os
import re


test_files_with_exits = [
    "tests/integration/test_database_integration.py",
    "tests/integration/test_message_queue_integration.py",
    "tests/integration/test_product_isolation_complete.py",
    "tests/run_websocket_tests.py",
    "tests/test_api_integration_fix.py",
    "tests/test_async_db.py",
    "tests/test_chunking_naming.py",
    "tests/test_integration_5_1_c.py",
    "tests/test_mcp_tools.py",
    "tests/test_product_isolation.py",
    "tests/test_serena_hooks.py",
    "tests/test_setup_enhancements.py",
    "tests/test_simple_integration.py",
    "tests/test_tools_simple.py",
    "tests/test_tool_api_integration_fixed.py",
    "tests/test_tool_registration.py",
    "tests/test_utf8_encoding.py",
    "tests/test_vision_chunking_comprehensive.py",
    "tests/test_websocket_events.py",
    "tests/test_windows_paths.py",
    "tests/test_ws_auth_simple.py",
]


def fix_file(filepath):
    """Comment out sys.exit() calls in a test file"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Replace sys.exit() patterns
        patterns = [
            (r"^(\s*)sys\.exit\((.*?)\)(.*)$", r"\1# sys.exit(\2)\3  # Commented for pytest"),
            (r"^(\s*)exit\((.*?)\)(.*)$", r"\1# exit(\2)\3  # Commented for pytest"),
        ]

        modified = False
        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if new_content != content:
                content = new_content
                modified = True

        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            pass

    except Exception:
        pass


if __name__ == "__main__":
    for filepath in test_files_with_exits:
        if os.path.exists(filepath):
            fix_file(filepath)
        else:
            pass
