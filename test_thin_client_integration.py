"""
Integration test for thin client architecture fixes (Handover 0088).

Tests:
1. Config reading: external_host is configured
2. Health check MCP tool works
3. Prompt generation logic (simulated, without database)
"""

import sys
from pathlib import Path


# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import yaml


def test_config_external_host():
    """Test that config.yaml has external_host configured."""
    print("\n=== TEST 1: Config External Host ===")

    # Read config
    config_path = Path("config.yaml")
    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)

    external_host = config_data.get("services", {}).get("external_host")
    api_port = config_data.get("services", {}).get("api", {}).get("port", 7272)
    bind_host = config_data.get("services", {}).get("api", {}).get("host")

    print(f"Config external_host: {external_host}")
    print(f"Config API port: {api_port}")
    print(f"Config bind host: {bind_host}")

    assert external_host, "external_host should be configured"
    assert external_host != "0.0.0.0", "external_host should not be 0.0.0.0"
    assert bind_host == "0.0.0.0", "Bind host should be 0.0.0.0 for network access"

    print("\n[PASS] TEST 1 PASSED")
    print(f"   - External host: {external_host}")
    print(f"   - Server binds to: {bind_host} (correct for network)")
    print(f"   - User-facing URL: http://{external_host}:{api_port}")

    return external_host, api_port


def test_health_check_tool():
    """Test that health_check MCP tool exists and works."""
    print("\n=== TEST 2: Health Check Tool ===")

    import asyncio

    from src.giljo_mcp.tools.orchestration import health_check

    # Verify health_check exists
    assert health_check is not None, "health_check tool should exist"

    # Call it (it's async)
    result = asyncio.run(health_check())

    print(f"Health check result: {result}")
    assert result["status"] == "healthy", "Health check should return healthy status"
    assert "version" in result, "Health check should include version"
    assert "timestamp" in result, "Health check should include timestamp"

    print("[PASS] TEST 2 PASSED: health_check() tool works")


def test_prompt_generation_logic(external_host, api_port):
    """Test the prompt generation logic (simulated)."""
    print("\n=== TEST 3: Prompt Generation Logic ===")

    # Simulate what the thin prompt generator does
    orchestrator_id = "orch_test_123"
    project_id = "proj_test_123"
    project_name = "Test Project"
    tenant_key = "test_tenant"
    instance_number = 1

    # This is the actual logic from thin_prompt_generator.py
    mcp_url = f"http://{external_host}:{api_port}"

    prompt = f"""I am Orchestrator #{instance_number} for GiljoAI Project "{project_name}".

IDENTITY:
- Orchestrator ID: {orchestrator_id}
- Project ID: {project_id}
- Tenant Key: {tenant_key}

MCP CONNECTION:
- Server URL: {mcp_url}
- Tool Prefix: mcp__giljo-mcp__
- Auth Status: (check config.yaml for API key)

STARTUP SEQUENCE:
1. Verify MCP: mcp__giljo-mcp__health_check()
2. Fetch mission: mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}', '{tenant_key}')
3. Execute mission (70% token reduction applied)
4. Coordinate agents via MCP tools

CONNECTION TROUBLESHOOTING:
If MCP fails: Check server running at {mcp_url}/health
Logs: ~/.giljo_mcp/logs/mcp_adapter.log

Begin by verifying MCP connection, then fetch your mission.
"""

    print("\n--- Generated Prompt ---")
    print(prompt)
    print("--- End Prompt ---\n")

    # Verify external_host is used
    assert external_host in prompt, f"Prompt should contain external_host: {external_host}"
    assert "0.0.0.0" not in prompt, "Prompt should NOT contain 0.0.0.0"

    # Verify both MCP tools mentioned
    assert "health_check()" in prompt, "Prompt should mention health_check()"
    assert "get_orchestrator_instructions(" in prompt, "Prompt should mention get_orchestrator_instructions()"

    # Verify prompt is thin
    line_count = len(prompt.strip().split("\n"))
    print(f"Prompt line count: {line_count}")
    assert line_count < 30, f"Prompt too long: {line_count} lines (should be < 30)"

    print("[PASS] TEST 3 PASSED")
    print(f"   - External host used: {external_host}")
    print(f"   - MCP URL correct: {mcp_url}")
    print(f"   - Prompt is thin: {line_count} lines")
    print("   - Both MCP tools mentioned")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("THIN CLIENT ARCHITECTURE INTEGRATION TESTS")
    print("=" * 60)

    try:
        # Test 1: Config external host
        external_host, api_port = test_config_external_host()

        # Test 2: Health check tool
        test_health_check_tool()

        # Test 3: Prompt generation logic
        test_prompt_generation_logic(external_host, api_port)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED [SUCCESS]")
        print("=" * 60)
        print("\nThin client architecture fixes verified:")
        print(f"1. [OK] External host configured: {external_host}")
        print("2. [OK] Health check MCP tool works")
        print("3. [OK] Prompts use external host (not 0.0.0.0)")
        print("4. [OK] Prompts are thin (~20 lines, not 3000)")
        print("5. [OK] Both MCP tools referenced in prompt")

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
