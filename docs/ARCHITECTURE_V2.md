# GiljoAI MCP Architecture v2.0 - HTTP-Based Multi-User System

## Executive Summary

GiljoAI MCP has been redesigned from a stdio-based single-user tool to a proper HTTP-based multi-user orchestration server. This document describes the new architecture and migration path.

## The Problem with v1.0

The original implementation used stdio (standard input/output) for MCP communication:

- **Single connection only** - stdio can only handle one client
- **Session-bound** - server dies when client disconnects
- **Local only** - cannot work over network
- **No persistence** - loses state between sessions
- **No multi-user** - core feature was impossible

## The Solution: v2.0 Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                   Clients Layer                          │
├─────────────┬──────────────┬──────────────┬─────────────┤
│   Claude    │    Cursor    │   Browser    │  API Client │
│   (stdio)   │   (HTTP)     │   (HTTP)     │   (HTTP)    │
└──────┬──────┴──────┬───────┴──────┬───────┴──────┬──────┘
       │             │               │               │
       ▼             │               │               │
┌─────────────┐      │               │               │
│ MCP Adapter │      │               │               │
│(stdio→HTTP) │      │               │               │
└──────┬──────┘      │               │               │
       │             │               │               │
       └─────────────┼───────────────┼───────────────┘
                     │               │
                     ▼               ▼
        ┌────────────────────────────────────────┐
        │   Unified Orchestration Server         │
        │         (Port 8000)                    │
        ├────────────────────────────────────────┤
        │  • REST API (/api/v1/*)               │
        │  • MCP Tools (/mcp/tools/*)           │
        │  • WebSocket (/ws)                    │
        │  • Health (/health)                   │
        └────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │         Database Layer                 │
        │    (SQLite / PostgreSQL)               │
        └────────────────────────────────────────┘
```

### Component Details

#### 1. Unified Orchestration Server (`api/app.py`)
- **Port**: 8000
- **Protocol**: HTTP/WebSocket
- **Features**:
  - Persistent operation (stays running)
  - Multiple concurrent connections
  - REST API endpoints
  - MCP tool execution via HTTP
  - WebSocket for real-time updates
  - Authentication support (API keys/JWT)

#### 2. MCP Stdio Adapter (`src/giljo_mcp/mcp_adapter.py`)
- **Purpose**: Bridge Claude's stdio to HTTP server
- **Operation**:
  1. Receives MCP commands via stdio from Claude
  2. Translates to HTTP REST calls
  3. Forwards to server on localhost:8000
  4. Returns responses via stdio
- **Benefits**:
  - Claude compatibility maintained
  - Server remains multi-user capable
  - No session binding

#### 3. MCP Tool Endpoints (`api/endpoints/mcp_tools.py`)
- **Route**: `/mcp/tools/*`
- **Functions**:
  - `/mcp/tools/execute` - Execute any MCP tool
  - `/mcp/tools/list` - List available tools
  - `/mcp/tools/health` - MCP-specific health check
- **Integration**: Uses existing `ToolAccessor` class

## Migration from v1.0 to v2.0

### What Changed

| Component | v1.0 (Old) | v2.0 (New) |
|-----------|------------|------------|
| Main Server | stdio-based MCP server | HTTP-based API server |
| Port | 6001 (MCP), 8000 (API) | 8000 (unified) |
| Claude Integration | Direct stdio | Stdio adapter → HTTP |
| Multi-user | Not possible | Fully supported |
| Persistence | Dies with client | Stays running |
| Network Access | Local only | LAN/WAN capable |

### File Changes

#### Deprecated Files
- `src/giljo_mcp/__main__.py.deprecated` - Old stdio server entry
- `src/giljo_mcp/server.py.deprecated` - Old FastMCP stdio server

#### New Files
- `src/giljo_mcp/mcp_adapter.py` - Stdio to HTTP adapter
- `api/endpoints/mcp_tools.py` - MCP tool HTTP endpoints
- `docs/ARCHITECTURE_V2.md` - This document

#### Modified Files
- `api/app.py` - Added MCP tool router
- `start_giljo.bat` - Starts only HTTP server
- `stop_giljo.bat` - Stops unified server
- `register_claude.bat` - Registers adapter, not server

## Usage Instructions

### Starting the Server

```bash
# Windows
start_giljo.bat

# Direct Python
cd api
python run_api.py
```

The server will:
1. Start on port 8000
2. Stay running until stopped
3. Accept multiple connections
4. Provide all endpoints

### Connecting Claude

```bash
# One-time registration
register_claude.bat

# This registers the MCP adapter, not the server
# The adapter bridges stdio to HTTP
```

### API Access

All functionality available via HTTP:

```bash
# Execute MCP tool
POST http://localhost:8000/mcp/tools/execute
{
  "tool": "create_project",
  "arguments": {
    "name": "My Project",
    "mission": "Build something awesome"
  }
}

# List tools
GET http://localhost:8000/mcp/tools/list

# Health check
GET http://localhost:8000/mcp/tools/health
```

### Multi-User Example

```python
# Multiple clients can connect simultaneously
import httpx
import asyncio

async def client_task(client_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mcp/tools/execute",
            json={
                "tool": "create_project",
                "arguments": {
                    "name": f"Project {client_id}",
                    "mission": f"Client {client_id} mission"
                }
            }
        )
        print(f"Client {client_id}: {response.json()}")

# Run 10 concurrent clients
async def main():
    tasks = [client_task(i) for i in range(10)]
    await asyncio.gather(*tasks)

asyncio.run(main())
```

## Benefits of v2.0

### For Users
1. **Server persists** - No need to restart for each session
2. **Multiple projects** - Work on several projects simultaneously
3. **Team collaboration** - Multiple users can connect
4. **Network access** - Can run on remote servers
5. **Better reliability** - Server doesn't die unexpectedly

### For Developers
1. **Standard HTTP** - Use any HTTP client
2. **REST API** - Well-documented endpoints
3. **WebSocket** - Real-time updates
4. **Testable** - Easy to test HTTP endpoints
5. **Scalable** - Can add load balancing

### For Operations
1. **Single process** - One server to manage
2. **Standard ports** - Uses port 8000
3. **Health checks** - Monitor server status
4. **Logging** - Centralized logging
5. **Deployment ready** - Can dockerize easily

## Configuration

### Environment Variables

```bash
# Server configuration
GILJO_API_URL=http://localhost:8000  # API server URL
GILJO_API_KEY=your-api-key          # API key (if not LOCAL mode)

# Database configuration
DATABASE_URL=sqlite:///giljo_mcp.db  # or postgresql://...
```

### Deployment Modes

1. **LOCAL** (default)
   - No authentication
   - Localhost only
   - SQLite database

2. **LAN**
   - API key authentication
   - Network accessible
   - SQLite or PostgreSQL

3. **WAN/SaaS**
   - JWT authentication
   - Internet accessible
   - PostgreSQL required

## Troubleshooting

### Server Won't Start
```bash
# Check if port 8000 is in use
netstat -an | findstr :8000

# Kill existing process
# Windows
for /f "tokens=5" %a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %a
```

### Claude Can't Connect
```bash
# Re-register the adapter
claude mcp remove giljo-mcp
register_claude.bat

# Check server is running
curl http://localhost:8000/health
```

### Multiple User Issues
```bash
# Check server logs
tail -f ~/.giljo_mcp/logs/api.log

# Test with curl
curl -X POST http://localhost:8000/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_projects", "arguments": {}}'
```

## Future Enhancements

### Planned Features
1. **Load balancing** - Multiple server instances
2. **Caching layer** - Redis for performance
3. **GraphQL API** - Alternative to REST
4. **Metrics** - Prometheus integration
5. **Tracing** - OpenTelemetry support

### Migration Path
1. **v2.1** - Add Redis caching
2. **v2.2** - GraphQL endpoint
3. **v3.0** - Microservices architecture

## Conclusion

The v2.0 architecture transforms GiljoAI MCP from a single-user tool to a proper multi-user orchestration platform. By moving from stdio to HTTP, we enable:

- Multiple concurrent users
- Persistent server operation
- Network deployment options
- Standard API access
- Future scalability

The stdio adapter ensures backward compatibility with Claude while the HTTP server provides the foundation for team collaboration and production deployment.