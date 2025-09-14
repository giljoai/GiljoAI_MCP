#!/usr/bin/env python3
import asyncio
import json
import websockets
import datetime

async def monitor_messages():
    uri = "ws://localhost:5000/ws"
    
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Connecting to WebSocket...")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Subscribe to orchestrator messages
            await websocket.send(json.dumps({
                "type": "subscribe",
                "entity_type": "agent",
                "entity_id": "orchestrator"
            }))
            
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Monitoring for orchestrator messages...")
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "message" and data.get("to_agents") and "orchestrator" in data.get("to_agents", []):
                    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                    from_agent = data.get("from_agent", "unknown")
                    content_preview = data.get("content", "")[:100]
                    
                    print(f"\n[{timestamp}] 📬 NEW MESSAGE FOR ORCHESTRATOR")
                    print(f"  From: {from_agent}")
                    print(f"  Preview: {content_preview}...")
                    print(f"  Message ID: {data.get('id', 'unknown')}")
                    print("-" * 50)
                    
    except Exception as e:
        print(f"[ERROR] WebSocket connection failed: {e}")
        print("Retrying in 10 seconds...")
        await asyncio.sleep(10)
        await monitor_messages()

if __name__ == "__main__":
    print("=" * 50)
    print("ORCHESTRATOR MESSAGE MONITOR")
    print("=" * 50)
    asyncio.run(monitor_messages())
