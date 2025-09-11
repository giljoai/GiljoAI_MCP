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
        print("❌ context.py not found")
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
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        for pattern in hardcoded_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                found_issues.append(f"Line {i}: {line.strip()}")
    
    if found_issues:
        print("[FAIL] Found hardcoded paths:")
        for issue in found_issues:
            print(f"  - {issue}")
        return False
    else:
        print("[PASS] No hardcoded paths found")
        return True


def check_configuration_manager():
    """Check if ConfigurationManager exists"""
    config_manager_locations = [
        "src/giljo_mcp/tools/config_manager.py",
        "src/giljo_mcp/config_manager.py",
        "src/giljo_mcp/configuration.py"
    ]
    
    for location in config_manager_locations:
        if Path(location).exists():
            print(f"[PASS] Configuration manager found at: {location}")
            return True
    
    print("[FAIL] No configuration manager found")
    return False


def check_discovery_manager():
    """Check if DiscoveryManager exists"""
    discovery_locations = [
        "src/giljo_mcp/tools/discovery.py",
        "src/giljo_mcp/discovery.py",
        "src/giljo_mcp/tools/discovery_manager.py"
    ]
    
    for location in discovery_locations:
        if Path(location).exists():
            print(f"[PASS] Discovery manager found at: {location}")
            return True
    
    print("[FAIL] No discovery manager found")
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("DYNAMIC DISCOVERY VALIDATION")
    print("=" * 60)
    
    print("\n1. Checking for hardcoded paths...")
    paths_ok = check_hardcoded_paths()
    
    print("\n2. Checking for configuration manager...")
    config_ok = check_configuration_manager()
    
    print("\n3. Checking for discovery manager...")
    discovery_ok = check_discovery_manager()
    
    print("\n" + "=" * 60)
    if paths_ok and config_ok and discovery_ok:
        print("[PASS] ALL CHECKS PASSED - Ready for testing!")
    else:
        print("[FAIL] Some checks failed - Implementation incomplete")
    print("=" * 60)