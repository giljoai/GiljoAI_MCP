#!/usr/bin/env python3
"""
Quick WebSocket Integration Test
Tests the backend WebSocket implementation
"""

import asyncio
import json
import sys
import time

import websockets


async def test_websocket():
    """Test WebSocket connection and features"""

    # Test configuration
    ws_url = "ws://localhost:8000/ws/test_client_001"
    test_results = {
        "connection": False,
        "ping_pong": False,
        "agent_update": False,
        "message_broadcast": False,
        "latency_ms": None,
    }

    try:
        # 1. Test connection
        async with websockets.connect(ws_url) as websocket:
            test_results["connection"] = True

            # 2. Test ping-pong
            start_time = time.time()
            await websocket.send(json.dumps({"type": "ping", "timestamp": start_time}))

            response = await asyncio.wait_for(websocket.recv(), timeout=2)
            pong = json.loads(response)

            if pong.get("type") == "pong":
                latency = (time.time() - start_time) * 1000
                test_results["ping_pong"] = True
                test_results["latency_ms"] = round(latency, 2)
            else:
                pass

            # 3. Test agent status update
            await websocket.send(json.dumps({"type": "subscribe", "entities": ["agents"]}))

            # Simulate agent status change (would normally come from API)
            await websocket.send(
                json.dumps({"type": "test_agent_update", "agent_id": "agent_001", "status": "in_progress"})
            )

            # Wait for broadcast
            try:
                update = await asyncio.wait_for(websocket.recv(), timeout=2)
                update_data = json.loads(update)
                if "agent" in str(update_data).lower():
                    test_results["agent_update"] = True
                else:
                    pass
            except asyncio.TimeoutError:
                pass

            # 4. Test message broadcast
            await websocket.send(json.dumps({"type": "subscribe", "entities": ["messages"]}))

            await websocket.send(json.dumps({"type": "test_message", "content": "Test broadcast message"}))

            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=2)
                msg_data = json.loads(msg)
                if "message" in str(msg_data).lower():
                    test_results["message_broadcast"] = True
                else:
                    pass
            except asyncio.TimeoutError:
                pass

    except Exception:
        pass

    # Print summary

    sum(1 for v in test_results.values() if v and v is not None)
    len([k for k in test_results if k != "latency_ms"])

    for test, result in test_results.items():
        if test == "latency_ms":
            if result:
                status = f"{result}ms"
                if result < 100:
                    status += " [MEETS SLA]"
                else:
                    status += " [EXCEEDS SLA]"
        else:
            status = "[PASS]" if result else "[FAIL]"

    # Check SLA compliance
    if test_results["latency_ms"] and test_results["latency_ms"] < 100:
        pass
    else:
        pass

    return test_results


if __name__ == "__main__":
    results = asyncio.run(test_websocket())

    # Exit code based on results
    if results["connection"] and results["ping_pong"]:
        sys.exit(0)  # Basic functionality working
    else:
        sys.exit(1)  # Critical failure
