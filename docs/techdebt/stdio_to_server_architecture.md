# Technical Debt: Stdio to Server Architecture Migration

## Date Identified: 2025-09-28
## Severity: CRITICAL
## Status: ACTIVE

## Problem Statement

The current GiljoAI MCP implementation has a fundamental architectural mismatch. The system is designed as a multi-user, multi-project orchestration server but is using stdio (standard input/output) for the MCP interface, which is inherently single-user and session-bound.

### Current Issues:

1. **Stdio Limitations**:
   - Single connection only - one client at a time
   - Process dies when client disconnects
   - Cannot work over network (localhost only)
   - No concurrent user support
   - No persistent state between sessions

2. **Architecture Conflict**:
   - System designed for: Multiple users, persistent state, network access
   - Stdio provides: Single user, session-bound, local only
   - Result: Server exits immediately when run standalone

3. **Port Confusion**:
   - MCP Server: Port 6001 (stdio, exits immediately)
   - API Server: Port 8000 (HTTP/WebSocket, stays running)
   - Frontend: Port 6000 (Vite dev server)
   - Inconsistent with documentation claiming unified port 8000

## Single Source of Truth

### How It SHOULD Operate:

**Core Principle**: GiljoAI MCP is a persistent orchestration server that:

1. **Deployment Flexibility**:
   - Runs on localhost (started via desktop shortcut)
   - Runs on LAN/WAN servers (24/7 service)
   - Deployable as cloud SaaS
   - One codebase, multiple deployment modes

2. **Server Characteristics**:
   - Starts and stays running until explicitly stopped
   - Handles multiple concurrent connections
   - Maintains persistent state in database
   - Accessible via HTTP/WebSocket protocols
   - Independent of any client lifecycle

3. **Client Connections**:
   - Multiple coding agents can connect simultaneously
   - Clients connect via HTTP/REST API or WebSocket
   - MCP protocol support via thin adapter layer
   - Authentication based on deployment mode

4. **Unified Port Strategy**:
   - Single port 8000 for all server operations
   - API endpoints on http://server:8000/api
   - WebSocket on ws://server:8000/ws
   - Health checks on http://server:8000/health
   - MCP adapter translates stdio to HTTP calls

## Required Architecture Changes

### 1. Remove Stdio Dependency
- MCP server should NOT run on stdio directly
- Convert to HTTP-based server that stays running
- Create separate MCP adapter for Claude compatibility

### 2. Unify Server Components
```
Current (Broken):
- MCP Server (stdio, port 6001) - exits immediately
- API Server (HTTP, port 8000) - stays running
- Frontend (port 6000) - development only

Target Architecture:
- Orchestration Server (HTTP/WS, port 8000) - always running
- MCP Adapter (stdio → HTTP) - thin translator
- Frontend (static files served by main server in production)
```

### 3. MCP Adapter Pattern
```python
# New: mcp_adapter.py (runs via stdio)
async def main():
    # 1. Connect to orchestration server at localhost:8000
    # 2. Receive MCP commands via stdio
    # 3. Translate to HTTP/REST calls
    # 4. Forward to orchestration server
    # 5. Return responses via stdio
```

### 4. Server Startup Flow
```
Desktop User:
1. Click "Start Server" shortcut
2. Server starts on port 8000
3. Stays running until "Stop Server" clicked

Server Deployment:
1. systemd/Windows Service starts server
2. Server runs 24/7 on port 8000
3. Managed by system service manager

SaaS Deployment:
1. Container/process manager starts server
2. Load balancer routes to instances
3. Scales horizontally as needed
```

## Implementation Tasks

### Phase 1: Core Server Refactoring
- [ ] Merge MCP server functionality into API server
- [ ] Remove stdio dependency from main server
- [ ] Ensure server stays running when started
- [ ] Implement proper shutdown handlers

### Phase 2: MCP Adapter Creation
- [ ] Create thin stdio adapter (mcp_adapter.py)
- [ ] Adapter connects to localhost:8000
- [ ] Translates MCP protocol to REST calls
- [ ] Register adapter (not server) with Claude

### Phase 3: Unified Port Configuration
- [ ] All server operations on port 8000
- [ ] Remove references to ports 6001, 6002, etc.
- [ ] Update all configuration files
- [ ] Update documentation

### Phase 4: Startup Scripts Update
- [ ] start_giljo.bat starts ONE server on 8000
- [ ] No multiple windows needed
- [ ] Server stays running until stopped
- [ ] Desktop shortcuts work correctly

### Phase 5: Testing & Validation
- [ ] Test localhost deployment
- [ ] Test network deployment
- [ ] Test multiple concurrent connections
- [ ] Test Claude connection via adapter

## Success Criteria

1. **Single Server Process**: One process serving all functionality on port 8000
2. **Persistent Operation**: Server stays running until explicitly stopped
3. **Multi-User Support**: Multiple clients can connect simultaneously
4. **MCP Compatibility**: Claude can still connect via stdio adapter
5. **Clean Startup**: No multiple windows, clear status messages
6. **Proper Shutdown**: stop_giljo.bat cleanly stops the server

## Migration Path

1. **Keep API server as the base** (it already has the right architecture)
2. **Merge MCP functionality into API server** (tools, handlers)
3. **Create separate MCP adapter** for Claude stdio compatibility
4. **Update all startup scripts** to run single server
5. **Test thoroughly** in all deployment modes

## References

- Current API server: `/api/app.py` (correct architecture)
- Broken MCP server: `/src/giljo_mcp/__main__.py` (stdio-based)
- FastMCP documentation: Shows HTTP server examples
- MCP Protocol spec: Supports HTTP transport, not just stdio

## Priority: CRITICAL

This is blocking proper multi-user operation and causing confusion. The system cannot function as designed until this is fixed.