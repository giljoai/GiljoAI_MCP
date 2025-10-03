# Session: Server Architecture Discovery and Issues

## Date: 2025-09-28
## Phase: Testing & Architecture Analysis

## What Was Discovered

### Installation Process Issues

1. **Installer Messaging**: Successfully updated both GUI and CLI installers to clearly communicate that GiljoAI MCP is a standalone server, not a project tool.

2. **Desktop Shortcuts**: Created comprehensive shortcut system:
   - Start Server
   - Stop Server
   - Connect Project
   - Check Status
   - Optional Windows auto-start

3. **Project Connection**: Built `connect_project.py` to properly merge with existing `.mcp.json` files without breaking other MCP servers (like Serena).

### Critical Architecture Problem Discovered

During testing, discovered that **the MCP server is fundamentally broken for multi-user operation**:

1. **Stdio Limitation**: MCP server uses stdio (standard input/output) which:
   - Only supports single connection
   - Dies when client disconnects
   - Cannot work over network
   - Makes multi-user impossible

2. **Server Immediately Exits**: When running `python -m giljo_mcp`:
   - Server initializes
   - Checks for stdio connection
   - Finds none (when run standalone)
   - Exits immediately

3. **Port Confusion**:
   - Documentation claims port 8000
   - Reality: MCP on 6001, API on 8000, Frontend on 6000
   - Multiple windows opening unnecessarily

### What Actually Works

The **API server on port 8000** has the correct architecture:
- Stays running persistently
- Handles multiple connections
- Supports HTTP/WebSocket
- Already has all the endpoints needed

## Root Cause Analysis

The system was designed with two conflicting paradigms:

1. **Design Intent**: Multi-user orchestration server
   - Multiple projects
   - Multiple users
   - Network accessible
   - Persistent state
   - 24/7 operation

2. **Implementation Reality**: Single-user stdio interface
   - One connection only
   - Session-bound lifecycle
   - Local only
   - Dies with client

This is a fundamental architectural mismatch that prevents the system from working as designed.

## Current State

### Working Components:
- ✅ API Server (port 8000) - correct architecture
- ✅ Frontend (port 6000) - serves dashboard
- ✅ Database layer - multi-tenant ready
- ✅ WebSocket support - real-time updates
- ✅ Installation process - clear messaging

### Broken Components:
- ❌ MCP Server - stdio-based, exits immediately
- ❌ Startup scripts - open multiple windows
- ❌ Port configuration - inconsistent
- ❌ Claude registration - registers wrong component

## Solution Path

### Correct Architecture:
```
Persistent Orchestration Server (port 8000)
           ↑
    HTTP/WebSocket
           ↑
Multiple Clients (Claude, Cursor, etc.)
```

### MCP Compatibility:
- Create thin stdio adapter that translates to HTTP
- Adapter connects to main server
- Claude talks to adapter, not server directly

## Key Decisions Made

1. **Stdio is wrong** for multi-user orchestration
2. **API server is correct** base architecture
3. **Need unified server** on single port
4. **MCP should be adapter**, not server
5. **Desktop shortcuts essential** for UX

## Files Created/Modified

### Created:
- `/docs/techdebt/stdio_to_server_architecture.md`
- `/connect_project.py` - Smart project connector
- `/create_shortcuts.py` - Desktop shortcut creator
- `/INSTALLATION.md` - Clear architecture docs
- `/PROJECT_CONNECTION.md` - Connection guide

### Modified:
- `setup_gui.py` - Clear server messaging
- `setup_interactive.py` - Clear server messaging
- `bootstrap.py` - Server installation warnings
- `register_claude.bat` - Global registration
- `stop_giljo.bat` - Proper shutdown

## Next Steps Required

1. **Merge MCP into API server** - Single server process
2. **Create MCP adapter** - Stdio to HTTP translator
3. **Fix startup scripts** - One window, one server
4. **Unify ports** - Everything on 8000
5. **Test multi-user** - Verify concurrent connections

## Lessons Learned

1. **Architecture first** - Stdio vs server should have been decided early
2. **Test deployment modes** - Would have caught this sooner
3. **User experience matters** - Desktop shortcuts make a difference
4. **Documentation critical** - Clear architecture docs prevent confusion

## Impact Assessment

This architectural issue is **CRITICAL** because:
- Blocks multi-user operation (core feature)
- Causes confusion (multiple windows, ports)
- Prevents network deployment
- Makes SaaS impossible

Must be fixed before any production use.