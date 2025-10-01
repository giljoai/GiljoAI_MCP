#!/usr/bin/env python3
"""
Test script for universal MCP registration
Tests registration with Claude, Codex, and Gemini CLI tools
"""

from pathlib import Path
from installer.universal_mcp_installer import UniversalMCPInstaller

def main():
    print("="*70)
    print("  Testing Universal MCP Registration")
    print("="*70)
    print()

    # Initialize installer
    installer = UniversalMCPInstaller()

    # Detect installed tools
    print("[1/5] Detecting installed AI CLI tools...")
    installed = installer.detect_installed_tools()
    print(f"      Found: {', '.join(installed)}")
    print()

    # Configure test MCP server
    test_config = {
        "server_name": "giljo-mcp-test",
        "command": "python",
        "args": ["-m", "giljo_mcp"],
        "env": {
            "GILJO_SERVER_URL": "http://localhost:8000",
            "GILJO_MODE": "test"
        }
    }

    # Register with all tools
    print("[2/5] Registering MCP server with all detected tools...")
    results = installer.register_all(**test_config)
    print()

    for tool, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        symbol = "[+]" if success else "[X]"
        print(f"      {symbol} {tool}: {status}")
    print()

    # Verify registration
    print("[3/5] Verifying registration...")
    verified = installer.verify_all("giljo-mcp-test")
    print()

    for tool, is_verified in verified.items():
        status = "VERIFIED" if is_verified else "NOT FOUND"
        symbol = "[+]" if is_verified else "[X]"
        print(f"      {symbol} {tool}: {status}")
    print()

    # Show config file locations
    print("[4/5] Config file locations:")
    for tool_name, adapter in installer.adapters.items():
        if tool_name in installed:
            config_path = adapter.get_config_path()
            exists = "EXISTS" if config_path.exists() else "NOT FOUND"
            print(f"      {tool_name}: {config_path} ({exists})")
    print()

    # Summary
    print("[5/5] Test Summary:")
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"      Registered: {success_count}/{total_count} tools")

    verified_count = sum(1 for v in verified.values() if v)
    print(f"      Verified: {verified_count}/{total_count} tools")
    print()

    if success_count == total_count and verified_count == total_count:
        print("="*70)
        print("  ALL TESTS PASSED!")
        print("="*70)
        return 0
    else:
        print("="*70)
        print("  SOME TESTS FAILED")
        print("="*70)
        return 1

if __name__ == "__main__":
    exit(main())
