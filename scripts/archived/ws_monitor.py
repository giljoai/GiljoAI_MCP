#!/usr/bin/env python3
import asyncio
import datetime
import json

import websockets


async def monitor_messages():
    uri = "ws://localhost:5000/ws"

    try:
        async with websockets.connect(uri) as websocket:
            # Subscribe to orchestrator messages
            await websocket.send(json.dumps({"type": "subscribe", "entity_type": "agent", "entity_id": "orchestrator"}))

            while True:
                message = await websocket.recv()
                data = json.loads(message)

                if (
                    data.get("type") == "message"
                    and data.get("to_agents")
                    and "orchestrator" in data.get("to_agents", [])
                ):
                    datetime.datetime.now().strftime("%H:%M:%S")
                    data.get("from_agent", "unknown")
                    data.get("content", "")[:100]

    except Exception:
        await asyncio.sleep(10)
        await monitor_messages()


if __name__ == "__main__":
    asyncio.run(monitor_messages())
