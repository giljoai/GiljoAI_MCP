# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Quick validation script to check for hardcoded paths in context.py
This will help verify the implementer's changes
"""

import re
from pathlib import Path


def check_hardcoded_paths():
    """Scan context.py for hardcoded paths"""
    context_file = Path("src/giljo_mcp/tools/context.py")

    if not context_file.exists():
        return False

    content = context_file.read_text()

    # Patterns to check for hardcoded paths
    hardcoded_patterns = [
        r'Path\(["\']docs/Vision["\']\)',
        r'Path\(["\']docs/Sessions["\']\)',
        r'Path\(["\']docs/devlog["\']\)',
        r'Path\(["\']CLAUDE\.md["\']\)',
        r'["\'"]docs/Vision["\'"]',
        r'["\'"]docs/Sessions["\'"]',
        r'["\'"]docs/devlog["\'"]',
    ]

    found_issues = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in hardcoded_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                found_issues.append(f"Line {i}: {line.strip()}")

    if found_issues:
        for _issue in found_issues:
            pass
        return False
    return True


def check_configuration_manager():
    """Check if ConfigurationManager exists"""
    config_manager_locations = [
        "src/giljo_mcp/tools/config_manager.py",
        "src/giljo_mcp/config_manager.py",
        "src/giljo_mcp/configuration.py",
    ]

    return any(Path(location).exists() for location in config_manager_locations)


def check_discovery_manager():
    """Check if DiscoveryManager exists"""
    discovery_locations = [
        "src/giljo_mcp/tools/discovery.py",
        "src/giljo_mcp/discovery.py",
        "src/giljo_mcp/tools/discovery_manager.py",
    ]

    return any(Path(location).exists() for location in discovery_locations)


if __name__ == "__main__":
    paths_ok = check_hardcoded_paths()

    config_ok = check_configuration_manager()

    discovery_ok = check_discovery_manager()

    if paths_ok and config_ok and discovery_ok:
        pass
    else:
        pass
