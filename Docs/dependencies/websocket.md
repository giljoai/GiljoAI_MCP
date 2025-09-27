# WebSocket Dependencies

WebSocket communication is critical for GiljoAI MCP's real-time agent coordination. This document covers all WebSocket-related dependencies and their purposes.

## Overview

GiljoAI MCP uses a hybrid WebSocket approach:

- **Client-side:** aiohttp for connecting to WebSocket servers
- **Server-side:** FastAPI's built-in WebSocket support
- **Protocol:** websockets library for low-level protocol handling

## Core WebSocket Dependencies

### aiohttp (>=3.8.0) - **CRITICAL**

**Purpose:** WebSocket client for real-time agent communication

**Used In:**

- `src/giljo_mcp/websocket_client.py` - Main WebSocket client implementation
- `src/giljo_mcp/tools/agent.py` - Agent event broadcasting

**Key Features:**

- Async WebSocket client connections
- Session management for persistent connections
- Automatic reconnection capabilities
- JSON message serialization

**Code Example:**

```python
from src.giljo_mcp.websocket_client import WebSocketEventClient

client = WebSocketEventClient("ws://localhost:6000/ws/mcp_tool_client")
await client.connect(api_key="your-api-key")
await client.send_agent_event("spawned", agent_name="analyzer", project_id="123")
```

**Critical Use Cases:**

1. **Agent Event Broadcasting** - When agents spawn, complete tasks, or hand off work
2. **Real-time Status Updates** - Live dashboard updates
3. **Inter-agent Communication** - Coordination between multiple agents

### websockets (>=12.0)

**Purpose:** WebSocket protocol implementation

**Used In:**

- FastAPI WebSocket endpoints
- Low-level protocol handling
- Connection management

**Key Features:**

- Pure Python WebSocket implementation
- Full RFC 6455 compliance
- Extension support (compression, etc.)
- Robust error handling

### fastapi (>=0.100.0)

**Purpose:** WebSocket server endpoints

**Used In:**

- `src/giljo_mcp/api/` - WebSocket API endpoints
- Dashboard real-time updates
- Client connection management

**WebSocket Endpoints:**

- `/ws/mcp_tool_client` - MCP tool event broadcasting
- `/ws/dashboard` - Dashboard real-time updates
- `/ws/agent/{agent_id}` - Agent-specific communication

## WebSocket Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   MCP Tools     │ ─────────────→   │  FastAPI Server │
│   (aiohttp)     │     Events       │   (websockets)  │
└─────────────────┘                  └─────────────────┘
        │                                     │
        │                                     │
        ▼                                     ▼
┌─────────────────┐                 ┌─────────────────┐
│ Agent Events    │                 │   Dashboard     │
│ - spawn         │                 │   - Live status │
│ - complete      │                 │   - Progress    │
│ - handoff       │                 │   - Metrics     │
└─────────────────┘                 └─────────────────┘
```

## Implementation Details

### WebSocket Client (aiohttp)

Located in `src/giljo_mcp/websocket_client.py`:

```python
class WebSocketEventClient:
    """Client for sending WebSocket events from MCP tools to the FastAPI server"""

    def __init__(self, ws_url: str = "ws://localhost:6000/ws/mcp_tool_client"):
        self.ws_url = ws_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False

    async def connect(self, api_key: Optional[str] = None):
        """Connect to the WebSocket server"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = self.ws_url
        if api_key:
            url = f"{url}?api_key={api_key}"

        self.ws = await self.session.ws_connect(url)
        self._connected = True
```

### WebSocket Server (FastAPI)

WebSocket endpoints in the API layer:

```python
@app.websocket("/ws/mcp_tool_client")
async def websocket_mcp_tools(websocket: WebSocket, api_key: Optional[str] = None):
    """WebSocket endpoint for MCP tool events"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)

            # Broadcast to dashboard clients
            await broadcast_to_dashboard(event)

    except WebSocketDisconnect:
        logger.info("MCP tool client disconnected")
```

## Event Types

### Agent Events

- **spawned** - New agent created
- **activated** - Agent started working
- **completed** - Agent finished task
- **handoff** - Agent passed work to another agent
- **decommissioned** - Agent shut down

### System Events

- **status_update** - System status change
- **performance_metric** - Performance data
- **error** - Error occurred

### Message Format

```json
{
  "type": "agent_event",
  "event": "spawned",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "agent_name": "analyzer",
    "project_id": "uuid-123",
    "mission": "Analyze codebase structure",
    "parent_agent": "orchestrator"
  }
}
```

## Configuration

### Environment Variables

```bash
# WebSocket server settings
GILJO_WEBSOCKET_PORT=6000
GILJO_WEBSOCKET_HOST=localhost

# Client settings
GILJO_WS_RECONNECT_INTERVAL=5
GILJO_WS_MAX_RETRIES=3
```

### Default URLs

- **Local Development:** `ws://localhost:6000/ws/mcp_tool_client`
- **LAN Deployment:** `ws://your-server:6000/ws/mcp_tool_client`
- **Production:** `wss://your-domain.com/ws/mcp_tool_client` (with TLS)

## Security Considerations

### Authentication

WebSocket connections support API key authentication:

```python
await client.connect(api_key="your-secure-api-key")
```

### TLS/SSL

Production deployments should use secure WebSocket connections (wss://):

```python
client = WebSocketEventClient("wss://production-server.com/ws/mcp_tool_client")
```

### Rate Limiting

WebSocket connections implement rate limiting to prevent abuse:

- Max 100 messages per minute per connection
- Max 10 KB message size
- Connection timeout after 30 minutes of inactivity

## Troubleshooting

### Common Issues

#### 1. "aiohttp not found" Error

```bash
# Solution: Install aiohttp
pip install aiohttp>=3.8.0

# Or reinstall all dependencies
pip install -r requirements.txt
```

#### 2. WebSocket Connection Failed

```python
# Check if server is running
curl -I http://localhost:6000/health

# Check WebSocket endpoint
wscat -c ws://localhost:6000/ws/mcp_tool_client
```

#### 3. "Connection refused" Error

Possible causes:

- Server not running on specified port
- Firewall blocking WebSocket connections
- Wrong URL or port in configuration

#### 4. Authentication Errors

```bash
# Check API key
export GILJO_API_KEY="your-api-key"

# Test WebSocket with authentication
wscat -c "ws://localhost:6000/ws/mcp_tool_client?api_key=your-api-key"
```

### Debug Mode

Enable WebSocket debugging:

```python
import logging
logging.getLogger('aiohttp').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)
```

### Performance Monitoring

Monitor WebSocket performance:

```python
# Check connection stats
client.get_connection_stats()

# Monitor message throughput
client.get_message_stats()
```

## Testing

### Unit Tests

```python
import pytest
from src.giljo_mcp.websocket_client import WebSocketEventClient

@pytest.mark.asyncio
async def test_websocket_connection():
    client = WebSocketEventClient("ws://localhost:6000/ws/test")
    await client.connect()
    assert client.is_connected()
    await client.disconnect()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_agent_event_broadcasting():
    client = WebSocketEventClient()
    await client.connect()

    await client.send_agent_event(
        "spawned",
        agent_name="test_agent",
        project_id="test_project"
    )

    # Verify event was received by dashboard
    dashboard_events = await get_dashboard_events()
    assert len(dashboard_events) == 1
    assert dashboard_events[0]["event"] == "spawned"
```

## Best Practices

### 1. Connection Management

- Always use async context managers
- Implement proper error handling
- Use connection pooling for multiple clients

### 2. Message Handling

- Validate message format before sending
- Implement message queuing for reliability
- Use appropriate message types

### 3. Error Recovery

- Implement exponential backoff for reconnections
- Handle network interruptions gracefully
- Log all connection events for debugging

### 4. Performance

- Batch related events when possible
- Use compression for large messages
- Monitor connection health

## Related Documentation

- [API Dependencies](./api.md) - FastAPI and HTTP client dependencies
- [Database Dependencies](./database.md) - Database-related packages
- [Complete Dependencies Guide](../DEPENDENCIES.md) - All project dependencies
- [Configuration Guide](../configuration.md) - WebSocket configuration options

---

_WebSocket functionality is critical for GiljoAI MCP's real-time orchestration capabilities. Ensure all dependencies are properly installed and configured._
