# Mission: Fix Critical Server Architecture Issue

## Context

GiljoAI MCP has a fundamental architecture problem that prevents it from working as designed. The system is supposed to be a multi-user, multi-project orchestration server that can run on localhost, LAN/WAN, or as SaaS. However, it's currently using stdio (standard input/output) which only supports single connections and dies when the client disconnects.

## The Problem

1. **MCP server uses stdio**: This means only one client at a time, local only, session-bound
2. **Server exits immediately**: When run standalone, it initializes then exits (no stdio = no service)
3. **Can't support multiple users**: Core feature is impossible with current architecture
4. **Wrong component registered with Claude**: The stdio server is registered instead of an adapter

## Your Mission

Transform GiljoAI MCP from a stdio-based single-user tool into a proper HTTP-based multi-user orchestration server.

## Critical Files to Review First

1. `/docs/techdebt/stdio_to_server_architecture.md` - Full problem analysis
2. `/docs/sessions/2025-09-28_server_architecture_discovery.md` - Discovery details
3. `/docs/devlog/2025-09-28_stdio_architecture_issue.md` - Technical breakdown
4. `/src/giljo_mcp/__main__.py` - Current broken MCP server (exits immediately)
5. `/api/app.py` - Working API server (correct architecture)

## Required Changes

### Phase 1: Unify Server Architecture
- The API server on port 8000 already has the correct architecture (stays running, handles multiple connections)
- Merge all MCP tool functionality into the API server
- Remove the standalone stdio-based MCP server
- Ensure the unified server stays running when started

### Phase 2: Create MCP Adapter
- Create a new `mcp_adapter.py` that provides stdio interface for Claude
- This adapter should:
  - Accept MCP commands via stdio from Claude
  - Translate them to HTTP REST calls
  - Forward to the main server on localhost:8000
  - Return responses back via stdio
- This is a thin translation layer, not a server

### Phase 3: Update Configuration
- Everything runs on port 8000:
  - `/api/v1/*` - REST endpoints
  - `/ws` - WebSocket connections
  - `/health` - Health checks
  - `/docs` - API documentation
- Remove all references to ports 6001, 6002, etc.
- Update all config files

### Phase 4: Fix Startup Scripts
- `start_giljo.bat` should:
  - Start ONE server process on port 8000
  - NOT open multiple windows
  - Show clear status that server is running
  - Keep running until explicitly stopped
- Update `stop_giljo.bat` to properly stop the unified server
- Update desktop shortcuts to work with new architecture

### Phase 5: Update Claude Registration
- The `register_claude.bat` should register the MCP ADAPTER, not the server
- The adapter (`mcp_adapter.py`) talks stdio to Claude
- The adapter makes HTTP calls to the actual server

## Success Criteria

1. **Server stays running**: Start it, and it runs until stopped
2. **Multiple connections work**: Open multiple Claude instances, all can use it
3. **Network capable**: Can access from other machines (in LAN/WAN mode)
4. **Clean startup**: One window, clear messages, no confusion
5. **Claude still works**: Via the stdio adapter
6. **All tests pass**: Multi-user scenarios work

## Architecture Diagram

```
CURRENT (BROKEN):
Claude → stdio → MCP Server (exits/dies)
                      ↓
                  Database

REQUIRED (FIXED):
                 Unified Server (port 8000)
                    ↑ HTTP/WebSocket ↑
          ┌─────────┴─────────┬───────────┐
    MCP Adapter            REST API     Dashboard
    (stdio→HTTP)           Clients      (Browser)
          ↑                    ↑            ↑
       Claude            Cursor/Other    Users
```

## Important Notes

1. **The API server is correct**: It already stays running and handles multiple connections. Build on it.
2. **Don't break existing functionality**: The database, WebSocket, and frontend are working
3. **Think production**: This needs to work as a real server (localhost, LAN, WAN, SaaS)
4. **Test thoroughly**: Multiple concurrent connections must work
5. **Keep it simple**: One server, one port, clear architecture

## Testing Requirements

After your changes:
1. Run `start_giljo.bat` - server should start and stay running
2. Open multiple terminals and run `python connect_project.py` - all should connect
3. Server should not exit when clients disconnect
4. Claude should still work via the adapter

## Questions to Answer

1. Can multiple users connect simultaneously? (MUST be yes)
2. Does the server stay running when clients disconnect? (MUST be yes)
3. Can it work over network (not just localhost)? (MUST be yes)
4. Does Claude still work? (MUST be yes, via adapter)

## Final Note

This is a CRITICAL issue that blocks the entire value proposition of GiljoAI MCP. The system cannot work as a multi-user orchestration platform with stdio architecture. Fix this, and the system becomes what it was designed to be: a powerful multi-agent orchestration server for teams.

Good luck!