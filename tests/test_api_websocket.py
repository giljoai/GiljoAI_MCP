"""
Quick WebSocket connection test
"""

import asyncio
import json
import uuid

import websockets


async def test_websocket():
    client_id = str(uuid.uuid4())
    uri = f"ws://localhost:6002/ws/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:

            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)

            if data.get("type") == "pong":
                pass
            else:
                pass

    except websockets.exceptions.ConnectionRefused:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(test_websocket())
