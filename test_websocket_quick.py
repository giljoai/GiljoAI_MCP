#!/usr/bin/env python3
"""
Quick WebSocket connection test to verify server is running
"""

import asyncio
import json
import uuid

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK


async def test_websocket_connection():
    """Test basic WebSocket connection"""
    client_id = str(uuid.uuid4())
    uri = f"ws://localhost:6002/ws/{client_id}"

    print(f"Testing WebSocket connection to: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] WebSocket connection established")

            # Send a ping
            ping_msg = {"type": "ping", "timestamp": asyncio.get_event_loop().time()}
            await websocket.send(json.dumps(ping_msg))
            print("[OK] Sent ping message")

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"[OK] Received response: {data}")

                if data.get("type") == "pong":
                    print("[OK] Ping/pong successful")
                    return True
                print(f"[ERROR] Unexpected response type: {data.get('type')}")
                return False

            except asyncio.TimeoutError:
                print("[ERROR] Timeout waiting for response")
                return False

    except (ConnectionRefusedError, OSError) as e:
        print(f"[ERROR] Connection refused - server not running on port 6002: {e}")
        return False
    except (ConnectionClosedError, ConnectionClosedOK) as e:
        print(f"[ERROR] WebSocket connection closed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_websocket_connection())
    if result:
        print("\n[SUCCESS] WebSocket server is working correctly!")
    else:
        print("\n[FAILED] WebSocket server test failed")
