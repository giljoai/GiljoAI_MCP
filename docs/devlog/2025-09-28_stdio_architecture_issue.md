# DevLog: Critical Architecture Issue - Stdio vs Server

**Date**: September 28, 2025
**Status**: 🔴 CRITICAL ISSUE DISCOVERED
**Component**: Core Server Architecture

## 🚨 Critical Discovery

During first test installation, discovered that **GiljoAI MCP cannot work as a multi-user orchestration server** due to fundamental architecture mismatch.

## 🔍 The Problem

### Expected Behavior:
- Server starts and stays running
- Multiple users can connect
- Works over network
- Persistent state

### Actual Behavior:
- Server starts and immediately exits
- Uses stdio (single connection only)
- Local only, session-bound
- Dies when client disconnects

## 📊 Technical Analysis

### Stdio Limitations:
```python
# Current broken implementation
if hasattr(mcp_app, "run_stdio"):
    await mcp_app.run_stdio()  # Single connection, blocking
else:
    logger.info("Server initialized")
    # EXITS HERE! No ongoing service
```

### Why This Breaks Everything:
1. **Multi-user impossible** - stdio = one connection
2. **No persistence** - server dies with client
3. **No network** - stdio is local only
4. **No scaling** - can't handle concurrent requests

## 💡 The Solution

### Current (Broken):
```
Claude → stdio → MCP Server (dies when Claude closes)
```

### Required (Fixed):
```
Multiple Clients → HTTP API Server (persistent)
Claude → stdio adapter → HTTP API Server
```

## 🏗️ Architecture Changes Required

### 1. Unify Server Components
- Merge MCP functionality into API server (port 8000)
- Remove standalone stdio server
- Single persistent process

### 2. Create MCP Adapter
```python
# New: mcp_adapter.py
class MCPAdapter:
    """Thin stdio-to-HTTP translator for Claude"""

    async def run_stdio(self):
        # Receive from stdio
        # Convert to HTTP calls
        # Forward to API server
        # Return via stdio
```

### 3. Fix Startup Process
- One server, one port, one window
- Server stays running until stopped
- Clear status messages

## 🎯 Impact

### What This Blocks:
- ❌ Multi-user operation
- ❌ Network deployment
- ❌ Production use
- ❌ SaaS potential
- ❌ Team collaboration

### What Works Now:
- ✅ API Server (correct architecture)
- ✅ Database (multi-tenant ready)
- ✅ WebSocket (real-time updates)
- ✅ Frontend (dashboard)

## 📝 Code Locations

### Files That Need Fixing:
- `/src/giljo_mcp/__main__.py` - Remove stdio, make persistent
- `/src/giljo_mcp/server.py` - Merge with API server
- `/api/app.py` - Add MCP tool endpoints
- `/start_giljo.bat` - Start single server only

### New Files Needed:
- `/src/giljo_mcp/mcp_adapter.py` - Stdio to HTTP translator
- `/src/giljo_mcp/unified_server.py` - Combined server

## 🔧 Configuration Issues

### Current Mess:
- MCP: Port 6001 (stdio)
- API: Port 8000
- Frontend: Port 6000
- WebSocket: Various

### Target:
- Everything: Port 8000
- `/api` - REST endpoints
- `/ws` - WebSocket
- `/health` - Health check

## 📈 Priority: CRITICAL

**This must be fixed before any production deployment.**

The entire value proposition of GiljoAI MCP (multi-agent orchestration for teams) is impossible with stdio architecture.

## ✅ Success Criteria

1. Server starts and stays running
2. Multiple clients can connect
3. Works over network
4. Claude still works (via adapter)
5. Single port, single process

## 🚀 Next Agent Mission

Fix this architectural issue by:
1. Merging MCP into API server
2. Creating stdio adapter for Claude
3. Unifying all operations on port 8000
4. Updating startup scripts
5. Testing multi-user scenarios

---

*This is a breaking change but necessary for the system to work as designed.*