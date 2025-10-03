#!/usr/bin/env python3
"""
Cleanup test MCP registration from all CLI tools
Removes 'giljo-mcp-test' from Claude, Codex, and Gemini configs
"""

from pathlib import Path
from installer.universal_mcp_installer import UniversalMCPInstaller

def main():
    print("="*70)
    print("  Cleaning Up Test MCP Registrations")
    print("="*70)
    print()

    installer = UniversalMCPInstaller()

    # Unregister test server
    print("Removing 'giljo-mcp-test' from all CLI tools...")
    results = installer.unregister_all("giljo-mcp-test")
    print()

    for tool, success in results.items():
        status = "REMOVED" if success else "NOT FOUND"
        symbol = "[+]" if success else "[-]"
        print(f"  {symbol} {tool}: {status}")
    print()

    # Verify removal
    print("Verifying removal...")
    verified = installer.verify_all("giljo-mcp-test")
    print()

    for tool, still_exists in verified.items():
        status = "STILL EXISTS" if still_exists else "CONFIRMED REMOVED"
        symbol = "[!]" if still_exists else "[+]"
        print(f"  {symbol} {tool}: {status}")
    print()

    success_count = sum(1 for v in results.values() if v)
    verified_count = sum(1 for v in verified.values() if not v)  # Count removed

    if success_count > 0 and verified_count == len(verified):
        print("="*70)
        print("  CLEANUP COMPLETE!")
        print("="*70)
        print()
        print("All test MCP registrations have been removed.")
        print("Codex CLI and Gemini CLI remain installed.")
        return 0
    else:
        print("="*70)
        print("  CLEANUP INCOMPLETE")
        print("="*70)
        return 1

if __name__ == "__main__":
    exit(main())
