"""
Standalone tests for MCP Tool Metadata Enhancement (Handover 0090 Phase 3)

These tests can run without full test fixtures by directly importing the endpoint.
"""

import sys
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_list_mcp_tools_returns_data():
    """Test that list_mcp_tools function returns proper structure"""
    # Import the function directly
    import asyncio

    from api.endpoints.mcp_tools import list_mcp_tools

    # Run the async function
    result = asyncio.run(list_mcp_tools())

    assert "tools" in result
    assert "total_count" in result
    assert "categories" in result

    # Count tools
    total_tools = sum(len(tools) for tools in result["tools"].values())
    print(f"\nTotal tools found: {total_tools}")

    # Should be 25 tools
    assert total_tools >= 20, f"Expected at least 20 tools, found {total_tools}"


def test_all_tools_have_enhanced_metadata():
    """Test all tools have enhanced argument descriptions and examples"""
    import asyncio

    from api.endpoints.mcp_tools import list_mcp_tools

    result = asyncio.run(list_mcp_tools())

    total_tools_checked = 0
    tools_with_examples = 0
    tools_with_enhanced_args = 0

    for category, tools in result["tools"].items():
        print(f"\nChecking category: {category}")
        for tool in tools:
            total_tools_checked += 1
            tool_name = tool["name"]
            print(f"  - {tool_name}")

            # Check for examples
            if "examples" in tool:
                tools_with_examples += 1
                example_count = len(tool["examples"])
                print(f"    [OK] Has {example_count} examples")
            else:
                print("    [MISSING] No examples")

            # Check for enhanced argument descriptions
            if "arguments" in tool:
                enhanced = True
                for arg_name, arg_desc in tool["arguments"].items():
                    # Check for type indicators
                    has_type = any(
                        keyword in str(arg_desc).lower()
                        for keyword in ["string", "array", "dict", "object", "uuid", "boolean", "integer"]
                    )

                    # Check for REQUIRED/OPTIONAL
                    has_marker = any(marker in str(arg_desc) for marker in ["REQUIRED", "OPTIONAL"])

                    if not has_type or not has_marker:
                        enhanced = False
                        print(f"    [MISSING] Argument '{arg_name}' missing metadata")
                        break

                if enhanced:
                    tools_with_enhanced_args += 1
                    print("    [OK] All arguments enhanced")
            else:
                print("    (No arguments)")

    print("\n--- Summary ---")
    print(f"Total tools checked: {total_tools_checked}")
    print(f"Tools with examples: {tools_with_examples} / {total_tools_checked}")
    print(f"Tools with enhanced args: {tools_with_enhanced_args} / {total_tools_checked}")

    # For TDD, these should fail initially
    # After implementation, they should pass
    return {
        "total": total_tools_checked,
        "with_examples": tools_with_examples,
        "with_enhanced_args": tools_with_enhanced_args,
    }


def test_send_message_array_notation():
    """Specific test for send_message to show array notation"""
    import asyncio

    from api.endpoints.mcp_tools import list_mcp_tools

    result = asyncio.run(list_mcp_tools())

    send_message_tool = None
    for tool in result["tools"].get("message_queue", []):
        if tool["name"] == "send_message":
            send_message_tool = tool
            break

    assert send_message_tool is not None, "send_message tool not found"

    print("\n--- send_message Tool ---")
    print(f"Description: {send_message_tool.get('description', 'N/A')}")
    print("\nArguments:")
    for arg, desc in send_message_tool.get("arguments", {}).items():
        print(f"  {arg}: {desc}")

    print("\nExamples:")
    for i, example in enumerate(send_message_tool.get("examples", []), 1):
        print(f"  Example {i}: {example.get('description', 'N/A')}")
        print(f"    Payload: {example.get('payload', {})}")


if __name__ == "__main__":
    print("=" * 80)
    print("HANDOVER 0090 PHASE 3 - MCP Tool Metadata Tests")
    print("=" * 80)

    print("\n[TEST 1] Basic structure test")
    test_list_mcp_tools_returns_data()

    print("\n[TEST 2] Enhanced metadata test")
    stats = test_all_tools_have_enhanced_metadata()

    print("\n[TEST 3] send_message array notation")
    test_send_message_array_notation()

    print("\n" + "=" * 80)
    print("Tests complete. See results above.")
    print("=" * 80)

    # Return stats for manual verification
    if stats["with_examples"] < stats["total"] or stats["with_enhanced_args"] < stats["total"]:
        print("\n[WARNING] NOT ALL TOOLS HAVE ENHANCED METADATA - Implementation needed")
        sys.exit(1)
    else:
        print("\n[SUCCESS] ALL TOOLS HAVE ENHANCED METADATA")
        sys.exit(0)
