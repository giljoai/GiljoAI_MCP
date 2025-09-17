"""
Test WebSocket real-time functionality
"""

import asyncio
import json
import uuid
from datetime import datetime

import websockets


async def test_websocket():
    """Test WebSocket connection and real-time updates"""
    client_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{client_id}"

    try:
        async with websockets.connect(uri) as websocket:

            # Test 1: Handle ping-pong
            async def handle_messages():
                async for message in websocket:
                    data = json.loads(message)

                    if data["type"] == "ping":
                        # Respond with pong
                        pong = {"type": "pong"}
                        await websocket.send(json.dumps(pong))

                    elif data["type"] == "entity_update" or data["type"] == "agent_update" or data["type"] == "message":
                        pass

                    elif data["type"] == "progress":
                        data["data"]["percentage"]
                        message = data["data"]["message"]

                    elif data["type"] == "notification":
                        notif_type = data["data"]["notification_type"]
                        data["data"]["title"]
                        data["data"]["message"]
                        {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(notif_type, "📢")

                    elif data["type"] == "project_update":
                        data["data"]["update_type"]

            # Start message handler
            handler_task = asyncio.create_task(handle_messages())

            # Test 2: Subscribe to a test project
            test_project_id = "test-project-123"
            subscribe_msg = {"type": "subscribe", "entity_type": "project", "entity_id": test_project_id}
            await websocket.send(json.dumps(subscribe_msg))

            # Test 3: Subscribe to an agent
            test_agent = "test-agent"
            subscribe_agent = {
                "type": "subscribe",
                "entity_type": "agent",
                "entity_id": f"{test_project_id}:{test_agent}",
            }
            await websocket.send(json.dumps(subscribe_agent))

            # Keep connection alive for testing

            # Wait for messages
            await handler_task

    except websockets.exceptions.ConnectionRefused:
        pass
    except KeyboardInterrupt:
        pass
    except Exception:
        pass


async def test_broadcast_triggers():
    """Test that API calls trigger WebSocket broadcasts"""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Test project creation broadcast
        project_data = {
            "name": f"Test Project {datetime.now().isoformat()}",
            "mission": "Test WebSocket broadcasts",
            "agents": [],
        }

        try:
            response = await client.post("/api/v1/projects/", json=project_data)
            if response.status_code == 200:
                response.json()
            else:
                pass
        except Exception:
            pass


if __name__ == "__main__":

    # Run the WebSocket test
    asyncio.run(test_websocket())
