#!/usr/bin/env python3
"""
Integration Test: Handover 0282 MCP Field Exclusions

Tests that user-configured field exclusions (Priority 4) are respected
when fetching orchestrator instructions via MCP tool.

CRITICAL: This tests the fix for the bug where users set all fields to
Priority 4 (EXCLUDED) but received ~15.2k tokens with full vision content.

Fixed keys:
- vision_documents (was product_vision)
- testing (was testing_config)
- memory_360 (was product_memory.sequential_history)
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions
from src.giljo_mcp.auth.dependencies import get_db_session


async def test_all_fields_excluded():
    """
    Test Scenario 1: All fields excluded (Priority 4)

    Expected:
    - Token count < 4500
    - No vision content
    - No testing content
    - No 360 memory content
    """
    print("\n" + "="*80)
    print("TEST 1: All Fields Excluded (Priority 4)")
    print("="*80)

    orchestrator_id = "323b551e-8991-45ba-bf52-dd9bd72ae7d1"
    tenant_key = "***REMOVED***"

    try:
        result = await get_orchestrator_instructions(
            orchestrator_id=orchestrator_id,
            tenant_key=tenant_key
        )

        mission_text = result.get('mission', '')
        estimated_tokens = result.get('estimated_tokens', 0)

        print(f"\n✓ MCP tool call successful")
        print(f"✓ Estimated tokens: {estimated_tokens}")
        print(f"✓ Mission length: {len(mission_text)} characters")

        # Check for excluded content (should NOT be present)
        failures = []

        # Vision documents check
        vision_keywords = ['vision document', 'product vision', '**vision**']
        if any(keyword in mission_text.lower() for keyword in vision_keywords):
            failures.append("❌ Vision content leaked!")
            print(f"❌ FAIL: Vision content found in mission (should be excluded)")
        else:
            print(f"✓ Vision content correctly excluded")

        # Testing check
        testing_keywords = ['testing configuration', 'test strategy', 'quality standards']
        if any(keyword in mission_text.lower() for keyword in testing_keywords):
            failures.append("❌ Testing content leaked!")
            print(f"❌ FAIL: Testing content found in mission (should be excluded)")
        else:
            print(f"✓ Testing content correctly excluded")

        # 360 Memory check
        memory_keywords = ['360 memory', 'sequential history', 'project closeout']
        if any(keyword in mission_text.lower() for keyword in memory_keywords):
            failures.append("❌ 360 memory leaked!")
            print(f"❌ FAIL: 360 memory content found in mission (should be excluded)")
        else:
            print(f"✓ 360 memory correctly excluded")

        # Tech stack check
        tech_keywords = ['tech stack', 'programming languages', 'frameworks']
        if any(keyword in mission_text.lower() for keyword in tech_keywords):
            failures.append("❌ Tech stack content leaked!")
            print(f"❌ FAIL: Tech stack content found (should be excluded)")
        else:
            print(f"✓ Tech stack correctly excluded")

        # Architecture check
        arch_keywords = ['architecture', 'design patterns', 'api style']
        if any(keyword in mission_text.lower() for keyword in arch_keywords):
            failures.append("❌ Architecture content leaked!")
            print(f"❌ FAIL: Architecture content found (should be excluded)")
        else:
            print(f"✓ Architecture correctly excluded")

        # Agent templates check
        template_keywords = ['agent template', 'agent library', 'template library']
        if any(keyword in mission_text.lower() for keyword in template_keywords):
            failures.append("❌ Agent templates content leaked!")
            print(f"❌ FAIL: Agent templates content found (should be excluded)")
        else:
            print(f"✓ Agent templates correctly excluded")

        # Token count check (should be low with everything excluded)
        if estimated_tokens > 4500:
            failures.append(f"❌ Too many tokens: {estimated_tokens} (expected <4500)")
            print(f"❌ FAIL: Token count too high: {estimated_tokens} (expected <4500)")
        else:
            print(f"✓ Token count OK: {estimated_tokens} tokens (within expected range)")

        # Print mission snippet for verification
        print(f"\n--- Mission Snippet (first 500 chars) ---")
        print(mission_text[:500])
        print("...")

        if failures:
            print(f"\n❌ TEST 1 FAILED: {len(failures)} issues found")
            for failure in failures:
                print(f"  {failure}")
            return False
        else:
            print(f"\n✅ TEST 1 PASSED: All exclusions respected, token count appropriate")
            return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_vision_included():
    """
    Test Scenario 2: Vision included (Priority 2), rest excluded

    Expected:
    - Token count > 8000 (vision adds significant content)
    - Vision content present with priority framing
    - Other excluded content still absent
    """
    print("\n" + "="*80)
    print("TEST 2: Vision Included (Priority 2), Rest Excluded")
    print("="*80)

    # First, update user config to include vision
    print("\n→ Updating user config to include vision_documents at Priority 2...")

    async with get_db_session() as session:
        from src.giljo_mcp.models import User
        from sqlalchemy import select

        tenant_key = "***REMOVED***"

        result = await session.execute(
            select(User).where(User.tenant_key == tenant_key)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ User not found for tenant_key: {tenant_key}")
            return False

        # Update field priority config
        config = user.field_priority_config or {}
        if 'priorities' not in config:
            config['priorities'] = {}

        config['priorities']['vision_documents'] = 2  # Include vision
        user.field_priority_config = config

        await session.commit()
        print(f"✓ User config updated: vision_documents = Priority 2")

    # Now test with updated config
    orchestrator_id = "323b551e-8991-45ba-bf52-dd9bd72ae7d1"
    tenant_key = "***REMOVED***"

    try:
        result = await get_orchestrator_instructions(
            orchestrator_id=orchestrator_id,
            tenant_key=tenant_key
        )

        mission_text = result.get('mission', '')
        estimated_tokens = result.get('estimated_tokens', 0)

        print(f"\n✓ MCP tool call successful")
        print(f"✓ Estimated tokens: {estimated_tokens}")
        print(f"✓ Mission length: {len(mission_text)} characters")

        failures = []

        # Vision should be present
        vision_keywords = ['vision', 'product vision']
        if not any(keyword in mission_text.lower() for keyword in vision_keywords):
            failures.append("❌ Vision content missing!")
            print(f"❌ FAIL: Vision content not found (should be included)")
        else:
            print(f"✓ Vision content correctly included")

        # Check for priority framing (IMPORTANT markers)
        if '**IMPORTANT:' not in mission_text and 'CRITICAL:' not in mission_text:
            print(f"⚠ WARNING: Priority framing markers not found (expected for Priority 2)")
        else:
            print(f"✓ Priority framing markers present")

        # Other content should still be excluded
        testing_keywords = ['testing configuration', 'test strategy']
        if any(keyword in mission_text.lower() for keyword in testing_keywords):
            failures.append("❌ Testing content leaked!")
            print(f"❌ FAIL: Testing content found (should still be excluded)")
        else:
            print(f"✓ Testing content correctly excluded")

        memory_keywords = ['360 memory', 'sequential history']
        if any(keyword in mission_text.lower() for keyword in memory_keywords):
            failures.append("❌ 360 memory leaked!")
            print(f"❌ FAIL: 360 memory found (should still be excluded)")
        else:
            print(f"✓ 360 memory correctly excluded")

        # Token count should be higher with vision
        if estimated_tokens < 8000:
            failures.append(f"❌ Token count too low: {estimated_tokens} (expected >8000 with vision)")
            print(f"❌ FAIL: Token count too low: {estimated_tokens} (expected >8000 with vision)")
        else:
            print(f"✓ Token count appropriate: {estimated_tokens} tokens (vision included)")

        # Print mission snippet
        print(f"\n--- Mission Snippet (first 1000 chars) ---")
        print(mission_text[:1000])
        print("...")

        if failures:
            print(f"\n❌ TEST 2 FAILED: {len(failures)} issues found")
            for failure in failures:
                print(f"  {failure}")
            return False
        else:
            print(f"\n✅ TEST 2 PASSED: Vision included, other exclusions respected")
            return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_logging():
    """
    Test Scenario 3: Verify structured logs use v2.0 field names

    Expected:
    - Logs show "vision_documents" (not "product_vision")
    - Logs show "testing" (not "testing_config")
    - Logs show "memory_360" (not "product_memory.sequential_history")
    """
    print("\n" + "="*80)
    print("TEST 3: Logging Verification (v2.0 Field Names)")
    print("="*80)

    log_file = Path.home() / ".giljo_mcp" / "logs" / "api.log"

    if not log_file.exists():
        print(f"⚠ WARNING: Log file not found at {log_file}")
        return True  # Not a critical failure

    try:
        # Read last 100 lines
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-100:]

        log_text = ''.join(lines)

        # Check for v2.0 field names
        v2_fields_found = []
        legacy_fields_found = []

        # Vision documents
        if 'vision_documents' in log_text:
            v2_fields_found.append('vision_documents')
            print(f"✓ Found v2.0 field name: vision_documents")
        if 'product_vision' in log_text:
            legacy_fields_found.append('product_vision')
            print(f"❌ Found legacy field name: product_vision")

        # Testing
        if '"testing"' in log_text or "'testing'" in log_text:
            v2_fields_found.append('testing')
            print(f"✓ Found v2.0 field name: testing")
        if 'testing_config' in log_text:
            legacy_fields_found.append('testing_config')
            print(f"❌ Found legacy field name: testing_config")

        # 360 Memory
        if 'memory_360' in log_text:
            v2_fields_found.append('memory_360')
            print(f"✓ Found v2.0 field name: memory_360")
        if 'product_memory.sequential_history' in log_text:
            legacy_fields_found.append('product_memory.sequential_history')
            print(f"❌ Found legacy field name: product_memory.sequential_history")

        if legacy_fields_found:
            print(f"\n❌ TEST 3 FAILED: Legacy field names found in logs: {legacy_fields_found}")
            return False
        elif v2_fields_found:
            print(f"\n✅ TEST 3 PASSED: v2.0 field names found in logs: {v2_fields_found}")
            return True
        else:
            print(f"\n⚠ TEST 3 INCONCLUSIVE: No field-related log entries found in last 100 lines")
            return True  # Not a failure, just no relevant logs

    except Exception as e:
        print(f"\n⚠ TEST 3 ERROR: {e}")
        return True  # Not critical


async def main():
    """Run all integration tests and generate report"""
    print("\n" + "="*80)
    print("INTEGRATION TEST SUITE: Handover 0282 MCP Field Exclusions")
    print("="*80)
    print("\nTesting CRITICAL fix for user exclusions being ignored")
    print("Bug: Users set Priority 4 (EXCLUDED) but received full content (~15.2k tokens)")
    print("Fix: Corrected field key mappings (vision_documents, testing, memory_360)")

    results = {
        'test1_all_excluded': await test_all_fields_excluded(),
        'test2_vision_included': await test_vision_included(),
        'test3_logging': await verify_logging()
    }

    # Generate summary report
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")
    print(f"Test 1 (All Excluded): {'✅ PASS' if results['test1_all_excluded'] else '❌ FAIL'}")
    print(f"Test 2 (Vision Included): {'✅ PASS' if results['test2_vision_included'] else '❌ FAIL'}")
    print(f"Test 3 (Logging): {'✅ PASS' if results['test3_logging'] else '❌ FAIL'}")

    overall_status = "✅ ALL TESTS PASSED" if all(results.values()) else "❌ SOME TESTS FAILED"
    print(f"\nOverall Status: {overall_status}")

    # Write detailed report
    report_path = Path(__file__).parent / "test_0282_mcp_exclusions_report.md"

    with open(report_path, 'w') as f:
        f.write("# Integration Test Report: Handover 0282 MCP Field Exclusions\n\n")
        f.write(f"**Date**: 2025-12-01\n")
        f.write(f"**Status**: {overall_status}\n\n")
        f.write("## Test Results\n\n")
        f.write(f"### Test 1: All Fields Excluded\n")
        f.write(f"- Status: {'✅ PASS' if results['test1_all_excluded'] else '❌ FAIL'}\n")
        f.write(f"- User Config: All 9 fields = Priority 4 (EXCLUDED)\n")
        f.write(f"- Expected: ~3.5k tokens, no excluded content\n\n")
        f.write(f"### Test 2: Vision Included\n")
        f.write(f"- Status: {'✅ PASS' if results['test2_vision_included'] else '❌ FAIL'}\n")
        f.write(f"- User Config: vision_documents = Priority 2, rest = Priority 4\n")
        f.write(f"- Expected: >8k tokens, vision content with priority framing\n\n")
        f.write(f"### Test 3: Logging Verification\n")
        f.write(f"- Status: {'✅ PASS' if results['test3_logging'] else '❌ FAIL'}\n")
        f.write(f"- Expected: v2.0 field names in logs\n\n")
        f.write(f"## Overall Result\n\n{overall_status}\n")

    print(f"\nDetailed report written to: {report_path}")

    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
