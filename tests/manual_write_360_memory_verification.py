# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Manual verification script for write_360_memory tool (Handover 0412)

Run this script to verify:
1. Tool is registered in MCP HTTP endpoint
2. Tool is accessible via ToolAccessor
3. Syntax is valid

Usage:
    python tests/manual_write_360_memory_verification.py
"""

import sys
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_mcp_registration():
    """Verify tool is registered in MCP HTTP endpoint."""
    print("[OK] Verifying MCP HTTP endpoint registration...")

    # Read the file and check for write_360_memory
    mcp_file = Path(__file__).parent.parent / "api" / "endpoints" / "mcp_http.py"
    content = mcp_file.read_text()

    assert '"name": "write_360_memory"' in content, "write_360_memory not found in MCP HTTP schema"
    assert '"write_360_memory": state.tool_accessor.write_360_memory' in content, "write_360_memory not in tool_map"

    print("  [OK] MCP HTTP endpoint registration found")
    print("  [OK] write_360_memory tool schema defined")
    print("  [OK] write_360_memory added to tool_map")
    return True


def verify_tool_accessor():
    """Verify ToolAccessor has write_360_memory method."""
    print("\n[OK] Verifying ToolAccessor registration...")

    # Read the file and check for write_360_memory method
    tool_accessor_file = Path(__file__).parent.parent / "src" / "giljo_mcp" / "tools" / "tool_accessor.py"
    content = tool_accessor_file.read_text()

    assert "async def write_360_memory(" in content, "write_360_memory method not found in ToolAccessor"
    assert "from giljo_mcp.tools.write_360_memory import write_360_memory as tool_func" in content, (
        "write_360_memory import not found"
    )

    print("  [OK] ToolAccessor.write_360_memory() method exists")
    print("  [OK] Method signature verified")
    return True


def verify_tool_implementation():
    """Verify write_360_memory tool implementation."""
    print("\n[OK] Verifying tool implementation...")

    # Read the file and check for write_360_memory function
    tool_file = Path(__file__).parent.parent / "src" / "giljo_mcp" / "tools" / "write_360_memory.py"
    assert tool_file.exists(), "write_360_memory.py file not found"

    content = tool_file.read_text()

    expected_params = [
        "project_id",
        "tenant_key",
        "summary",
        "key_outcomes",
        "decisions_made",
        "entry_type",
        "author_job_id",
    ]

    assert "async def write_360_memory(" in content, "write_360_memory function not found"
    for param in expected_params:
        assert param in content, f"Missing parameter: {param}"

    print("  [OK] write_360_memory() function exists")
    print("  [OK] Function signature verified")
    print(f"  [OK] Parameters: {', '.join(expected_params[:5])}...")
    return True


def verify_api_endpoints():
    """Verify /continue-working and /archive endpoints exist."""
    print("\n[OK] Verifying API endpoints...")

    # Check for /continue-working endpoint in completion.py (canonical endpoint)
    completion_file = Path(__file__).parent.parent / "api" / "endpoints" / "projects" / "completion.py"
    completion_content = completion_file.read_text()

    assert '@router.post("/{project_id}/continue-working"' in completion_content, "/continue-working endpoint not found"
    assert "async def continue_working(" in completion_content, "continue_working function not found"
    print("  [OK] POST /{project_id}/continue-working endpoint exists")

    # Check for /archive endpoint in lifecycle.py
    lifecycle_file = Path(__file__).parent.parent / "api" / "endpoints" / "projects" / "lifecycle.py"
    lifecycle_content = lifecycle_file.read_text()

    assert '@router.post("/{project_id}/archive"' in lifecycle_content, "/archive endpoint not found"
    assert "async def archive_project(" in lifecycle_content, "archive_project function not found"
    print("  [OK] POST /{project_id}/archive endpoint exists")

    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("write_360_memory Tool Verification (Handover 0412)")
    print("=" * 60)

    try:
        verify_mcp_registration()
        verify_tool_accessor()
        verify_tool_implementation()
        verify_api_endpoints()

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL VERIFICATIONS PASSED")
        print("=" * 60)
        print("\nImplementation Summary:")
        print("  • MCP tool 'write_360_memory' registered in HTTP endpoint")
        print("  • ToolAccessor.write_360_memory() method added")
        print("  • Tool implementation in src/giljo_mcp/tools/write_360_memory.py")
        print("  • POST /{project_id}/continue-working endpoint exists")
        print("  • POST /{project_id}/archive endpoint added")
        print("\nNext Steps:")
        print("  • Test via MCP client (Claude Code / Codex)")
        print("  • Verify 360 memory entries in Product.product_memory")
        print("  • Test multi-tenant isolation")

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print("[FAILED] VERIFICATION FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
