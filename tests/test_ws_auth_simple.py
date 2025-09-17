#!/usr/bin/env python
"""
Simple WebSocket authentication test
"""

import asyncio

import websockets


async def test_websocket_auth():
    """Test WebSocket authentication requirement"""

    results = []

    # Test 1: Connection without auth (should fail)
    try:
        async with websockets.connect("ws://localhost:8000/ws/test"):
            results.append("FAIL - Unauthenticated connection accepted!")
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:  # Policy violation
            results.append("PASS - Unauthenticated connection rejected with code 1008")
        else:
            results.append(f"PARTIAL - Connection rejected but wrong code: {e.code}")
    except Exception as e:
        results.append(f"ERROR - Test 1 failed: {e}")

    # Test 2: Connection with invalid API key (should fail)
    try:
        async with websockets.connect("ws://localhost:8000/ws/test?api_key=invalid123"):
            results.append("FAIL - Invalid API key accepted!")
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            results.append("PASS - Invalid API key rejected with code 1008")
        else:
            results.append(f"PARTIAL - Connection rejected but wrong code: {e.code}")
    except Exception as e:
        results.append(f"ERROR - Test 2 failed: {e}")

    # Test 3: Connection with valid API key (would need real key)
    results.append("SKIP - Valid auth test requires real API key")

    # Print results

    passed = sum(1 for r in results if r.startswith("PASS"))
    failed = sum(1 for r in results if r.startswith("FAIL"))
    sum(1 for r in results if r.startswith("ERROR"))

    for _i, _result in enumerate(results, 1):
        pass

    if failed > 0:
        return False
    if passed >= 2:
        return True
    return None


if __name__ == "__main__":
    # Check if API is running

    try:
        result = asyncio.run(test_websocket_auth())
        # sys.exit(0 if result else 1)  # Commented for pytest
    except Exception:
        pass
        # sys.exit(1)  # Commented for pytest
