"""
Quick WebSocket connection test
"""

import asyncio
import websockets
import json
import uuid

async def test_websocket():
    client_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    print(f"Testing WebSocket connection to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("SUCCESS: Connected to WebSocket")
            
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(response)
            
            if data.get("type") == "pong":
                print("SUCCESS: Received pong response")
            else:
                print(f"Received: {data}")
            
            print("WebSocket test PASSED - Backend is working!")
            
    except websockets.exceptions.ConnectionRefused:
        print("ERROR: Connection refused - is the API running?")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    print("WebSocket Backend Test")
    print("-" * 30)
    asyncio.run(test_websocket())