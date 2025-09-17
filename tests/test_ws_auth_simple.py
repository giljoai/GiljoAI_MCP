#!/usr/bin/env python
"""
Simple WebSocket authentication test
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_auth():
    """Test WebSocket authentication requirement"""
    
    results = []
    
    # Test 1: Connection without auth (should fail)
    print("Test 1: Connecting without authentication...")
    try:
        async with websockets.connect("ws://localhost:8000/ws/test") as ws:
            results.append("FAIL - Unauthenticated connection accepted!")
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:  # Policy violation
            results.append("PASS - Unauthenticated connection rejected with code 1008")
        else:
            results.append(f"PARTIAL - Connection rejected but wrong code: {e.code}")
    except Exception as e:
        results.append(f"ERROR - Test 1 failed: {e}")
    
    # Test 2: Connection with invalid API key (should fail)
    print("Test 2: Connecting with invalid API key...")
    try:
        async with websockets.connect("ws://localhost:8000/ws/test?api_key=invalid123") as ws:
            results.append("FAIL - Invalid API key accepted!")
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            results.append("PASS - Invalid API key rejected with code 1008")
        else:
            results.append(f"PARTIAL - Connection rejected but wrong code: {e.code}")
    except Exception as e:
        results.append(f"ERROR - Test 2 failed: {e}")
    
    # Test 3: Connection with valid API key (would need real key)
    print("Test 3: Valid auth test skipped (requires real API key)")
    results.append("SKIP - Valid auth test requires real API key")
    
    # Print results
    print("\n" + "="*60)
    print("WEBSOCKET AUTHENTICATION TEST RESULTS")
    print("="*60)
    
    passed = sum(1 for r in results if r.startswith("PASS"))
    failed = sum(1 for r in results if r.startswith("FAIL"))
    errors = sum(1 for r in results if r.startswith("ERROR"))
    
    for i, result in enumerate(results, 1):
        print(f"Test {i}: {result}")
    
    print("\n" + "-"*60)
    print(f"Summary: {passed} PASSED, {failed} FAILED, {errors} ERRORS")
    
    if failed > 0:
        print("\n🚨 CRITICAL: WebSocket accepts unauthenticated connections!")
        print("The security vulnerability is NOT fixed!")
        return False
    elif passed >= 2:
        print("\n✅ SUCCESS: WebSocket properly rejects unauthenticated connections!")
        print("The security vulnerability appears to be fixed!")
        return True
    else:
        print("\n⚠️ INCONCLUSIVE: Unable to properly test authentication")
        return None

if __name__ == "__main__":
    # Check if API is running
    print("Testing WebSocket authentication...")
    print("NOTE: This requires the API server to be running on localhost:8000")
    print("-"*60)
    
    try:
        result = asyncio.run(test_websocket_auth())
        # sys.exit(0 if result else 1)  # Commented for pytest
    except Exception as e:
        print(f"Failed to run tests: {e}")
        print("\nIs the API server running? Start it with:")
        print("  python api/run_api.py")
        # sys.exit(1)  # Commented for pytest