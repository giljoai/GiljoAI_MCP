"""
Test WebSocket real-time functionality
"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime

async def test_websocket():
    """Test WebSocket connection and real-time updates"""
    client_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{client_id}"
    
    print(f"Connecting to WebSocket as client: {client_id}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Test 1: Handle ping-pong
            async def handle_messages():
                async for message in websocket:
                    data = json.loads(message)
                    print(f"📨 Received: {data['type']}")
                    
                    if data['type'] == 'ping':
                        # Respond with pong
                        pong = {"type": "pong"}
                        await websocket.send(json.dumps(pong))
                        print("🏓 Sent pong response")
                    
                    elif data['type'] == 'entity_update':
                        print(f"📊 Entity Update: {data}")
                    
                    elif data['type'] == 'agent_update':
                        print(f"🤖 Agent Update: {data['data']}")
                    
                    elif data['type'] == 'message':
                        print(f"💬 Message Update: {data['data']}")
                    
                    elif data['type'] == 'progress':
                        percentage = data['data']['percentage']
                        message = data['data']['message']
                        print(f"⏳ Progress: {percentage}% - {message}")
                    
                    elif data['type'] == 'notification':
                        notif_type = data['data']['notification_type']
                        title = data['data']['title']
                        msg = data['data']['message']
                        icon = {
                            'info': 'ℹ️',
                            'warning': '⚠️',
                            'error': '❌',
                            'success': '✅'
                        }.get(notif_type, '📢')
                        print(f"{icon} {title}: {msg}")
                    
                    elif data['type'] == 'project_update':
                        update_type = data['data']['update_type']
                        print(f"📁 Project {update_type}: {data['data']}")
            
            # Start message handler
            handler_task = asyncio.create_task(handle_messages())
            
            # Test 2: Subscribe to a test project
            test_project_id = "test-project-123"
            subscribe_msg = {
                "type": "subscribe",
                "entity_type": "project",
                "entity_id": test_project_id
            }
            await websocket.send(json.dumps(subscribe_msg))
            print(f"📝 Subscribed to project: {test_project_id}")
            
            # Test 3: Subscribe to an agent
            test_agent = "test-agent"
            subscribe_agent = {
                "type": "subscribe",
                "entity_type": "agent",
                "entity_id": f"{test_project_id}:{test_agent}"
            }
            await websocket.send(json.dumps(subscribe_agent))
            print(f"🤖 Subscribed to agent: {test_agent}")
            
            # Keep connection alive for testing
            print("\n🎯 WebSocket test client running...")
            print("💡 Trigger API endpoints to see real-time updates")
            print("   - Create/update projects")
            print("   - Send messages")
            print("   - Update agent status")
            print("\n⏸️  Press Ctrl+C to stop\n")
            
            # Wait for messages
            await handler_task
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Failed to connect - is the API server running on port 8000?")
    except KeyboardInterrupt:
        print("\n👋 Closing WebSocket test client")
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_broadcast_triggers():
    """Test that API calls trigger WebSocket broadcasts"""
    import httpx
    
    print("\n🧪 Testing broadcast triggers via API calls...")
    
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Test project creation broadcast
        project_data = {
            "name": f"Test Project {datetime.now().isoformat()}",
            "mission": "Test WebSocket broadcasts",
            "agents": []
        }
        
        try:
            response = await client.post("/api/v1/projects/", json=project_data)
            if response.status_code == 200:
                project = response.json()
                print(f"✅ Created project: {project['id']}")
                print("   👀 Check WebSocket client for project_update broadcast")
            else:
                print(f"❌ Failed to create project: {response.status_code}")
        except Exception as e:
            print(f"❌ API call failed: {e}")

if __name__ == "__main__":
    print("🚀 WebSocket Real-time Test Suite")
    print("=" * 50)
    
    # Run the WebSocket test
    asyncio.run(test_websocket())