# MCP-over-HTTP Integration Guide

**Document Version**: 1.0.0
**Last Updated**: 2025-01-05 (Harmonized)
**Status**: Production Ready
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey including MCP integration setup
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical verification

**Supported AI Coding Agents** (native MCP support):
- **Claude Code** - via `claude-code mcp add` command
- **Codex CLI** - via `codex mcp add` command  
- **Gemini CLI** - via `gemini mcp add` command

**Agent Template Export** (Handover 0102):
- 15-minute token TTL for secure downloads
- Download token system for slash commands and agent templates
- See Simple_Vision.md for complete export workflow

---

## Appendix: Download Token Refactor (0102)

MCP-over-HTTP integration now leverages the 0102 single-token download system:

- Token-first flow: Generate token (pending) → stage content at `temp/{tenant_key}/{token}/` → mark ready → return URL.
- Lifecycle: `staging_status` (pending|ready|failed), metrics `download_count`, `last_downloaded_at`.
- Endpoints:
  - `POST /api/download/generate-token` (auth) – accepts `content_type` in query or JSON body (compatibility)
  - `GET /api/download/temp/{token}/{filename}` (public) – token is the auth
- Security: filename validation prevents traversal; background cleanup removes expired/failed/abandoned tokens and staged files.
- Client impact: slash-commands ZIP contains only `gil_handover.md`; agent templates compiled per tenant at request time.
**Last Updated**: January 18, 2025

---

## Overview

GiljoAI MCP implements **MCP-over-HTTP**, enabling Claude Code, Codex CLI, and other MCP clients to connect via HTTP transport with zero client dependencies. This eliminates the need for local Python installations or source code distribution, providing a true SaaS-ready deployment model.

### What is MCP-over-HTTP?

MCP-over-HTTP is an implementation of the Model Context Protocol (MCP) using HTTP as the transport layer instead of stdio (standard input/output). This architecture provides:

- **Zero-dependency client setup** - Just Claude Code + API key + one command
- **SaaS deployment ready** - No source code distribution required
- **Cross-platform compatibility** - Works on any system with HTTP access
- **Firewall-friendly** - Standard HTTP/HTTPS ports
- **Stateful sessions** - PostgreSQL-backed session management

### Why HTTP Transport Over Stdio?

**Traditional stdio transport requires:**
- Python installation on every client machine
- Package distribution (PyPI or source code)
- Client-side dependency management
- Local execution environment

**HTTP transport provides:**
- Single server deployment
- API key-based authentication
- Network-accessible from any client
- True multi-tenant SaaS architecture
- Zero client-side installation

---

## Architecture

### HTTP Endpoint Design

GiljoAI MCP exposes a Streamable HTTP endpoint powered by the official Anthropic **FastMCP SDK**:

```
Endpoint: http://server:7272/mcp
Transport: Streamable HTTP (MCP SDK)
Auth: X-API-Key: gk_YOUR_API_KEY_HERE
```

The FastMCP SDK handles protocol framing, session management, and method dispatch internally. Clients (Claude Code, Codex CLI, Gemini CLI) connect using their native `--transport http` flag -- no manual JSON construction required.

### Session Management Architecture

**PostgreSQL-Based Sessions:**
- Session data stored in `mcp_sessions` table
- Auto-expiration after 24 hours of inactivity
- Tenant context preserved across tool calls
- Project context switching support

**Session Lifecycle:**
1. Client sends request with `X-API-Key` header
2. Server authenticates API key → resolves User → extracts tenant_key
3. Server creates or retrieves existing session
4. Session stores: initialized state, client info, tool call history
5. Session auto-expires after 24 hours (configurable)

**Database Schema:**
```sql
CREATE TABLE mcp_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL DEFAULT gen_random_uuid(),
    api_key_id INTEGER NOT NULL REFERENCES api_keys(id),
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36),
    session_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(session_id)
);

CREATE INDEX idx_mcp_session_api_key ON mcp_sessions(api_key_id);
CREATE INDEX idx_mcp_session_tenant ON mcp_sessions(tenant_key);
CREATE INDEX idx_mcp_session_last_accessed ON mcp_sessions(last_accessed);
```

### Multi-Tenant Isolation Architecture

**Authentication Flow:**
```
X-API-Key → APIKey (database lookup)
         → User (via api_key.user_id)
         → tenant_key (from User record)
         → Tenant context established
```

**Isolation Guarantees:**
- Each API key belongs to exactly one User
- Each User belongs to exactly one Tenant (via tenant_key)
- All tool operations filtered by tenant_key
- No cross-tenant data access possible

**Code Reference:**
- `api/endpoints/mcp_session.py:43-70` - Authentication flow
- `api/endpoints/mcp_sdk_server.py` - FastMCP SDK endpoint
- `src/giljo_mcp/models.py:1330-1357` - MCPSession model

---

## Implementation Details

### File Structure

```
api/
├── endpoints/
│   ├── mcp_sdk_server.py   # FastMCP SDK Streamable HTTP endpoint
│   └── mcp_session.py      # PostgreSQL session management (186 lines)
├── middleware.py           # Authentication middleware (line 111: /mcp public)
└── app.py                  # FastAPI app (mounts MCP SDK endpoint)

src/giljo_mcp/
└── models.py               # MCPSession model (lines 1295-1357)

frontend/src/
├── utils/
│   └── configTemplates.js  # HTTP transport config generation
└── components/
    └── McpConfigComponent.vue  # MCP configuration UI
```

### Key Code Locations

**MCP SDK Endpoint:**
- File: `api/endpoints/mcp_sdk_server.py`
- Endpoint: Streamable HTTP at `/mcp`
- The FastMCP SDK handles initialization, tool listing, and tool dispatch internally

**Session Management:**
- File: `api/endpoints/mcp_session.py`
- Class: `MCPSessionManager`
- Methods:
  - `authenticate_api_key()` - API key validation
  - `get_or_create_session()` - Session lifecycle management
  - `update_session_data()` - Session state updates
  - `cleanup_expired_sessions()` - Background cleanup

**Middleware Configuration:**
- File: `api/middleware.py`
- Line 111: `/mcp` added to public endpoints list
- MCP endpoint handles own authentication via X-API-Key header

### Supported MCP Methods

The FastMCP SDK handles all MCP protocol methods automatically:

**1. initialize** - Connection handshake (protocol version negotiation, capability exchange)

**2. tools/list** - Returns all registered MCP tools with schemas and descriptions

**3. tools/call** - Executes a tool by name with provided arguments, returns structured results

Clients interact with these methods transparently through their native MCP transport -- no manual JSON-RPC construction is needed.

---

## Usage Guide

### Generating API Keys

**Via Frontend Dashboard:**
1. Login to GiljoAI MCP dashboard
2. Click avatar → "My Settings"
3. Navigate to "API and Integrations" tab
4. Click "Personal API Keys" section
5. Click "Generate New API Key"
6. Name your key (e.g., "Claude Code Access")
7. Copy the API key (shown only once)

**Key Format:**
```
gk_RANDOMSTRING123456789
```

**Security Note:**
- API keys are hashed with bcrypt before storage
- Plaintext key shown only once during generation
- Keys can be revoked at any time from dashboard

### Connecting Claude Code

**Step 1: Generate API Key**
```bash
# From GiljoAI MCP dashboard:
# Avatar → My Settings → API & Integrations → Personal API Keys → Generate
```

**Step 2: Add MCP Server**
```bash
claude mcp add --transport http giljo-mcp http://10.1.0.164:7272/mcp \
  --header "X-API-Key: gk_YOUR_API_KEY_HERE"
```

**Step 3: Verify Connection**
```bash
# Within Claude Code, check MCP status
> /mcp

# You should see "giljo-mcp" listed with "Connected" status
```

**Step 4: Test Tool Execution**
```bash
# In Claude Code, ask for project list
> "Can you list all my projects?"

# Claude Code will use the list_projects tool via MCP
```

### Example Tool Calls

**Get orchestrator instructions:**
```
> "Fetch my orchestrator instructions for job abc123"
```

**List all agents:**
```
> "Show me all the agents working on the project"
```

**Send a message:**
```
> "Send a message to the frontend-developer agent asking for a status update"
```

### Session Management

**Session Lifetime:**
- Default: 24 hours from last access
- Configurable in `MCPSessionManager.DEFAULT_SESSION_LIFETIME_HOURS`

**Session Cleanup:**
- Expired sessions automatically deleted after 48 hours
- Background cleanup runs periodically

**Session Data Stored:**
```json
{
  "initialized": true,
  "client_info": {"name": "claude-code", "version": "1.0.0"},
  "protocol_version": "2024-11-05",
  "client_capabilities": {},
  "last_tool_call": {
    "tool": "list_projects",
    "timestamp": "2025-01-18T10:30:00Z",
    "success": true
  }
}
```

---

## Security

### Authentication Headers

The MCP endpoint accepts either header (both map to the same API key validation):

```
X-API-Key: gk_YOUR_API_KEY_HERE
Authorization: Bearer gk_YOUR_API_KEY_HERE
```

**Authentication Flow:**
1. Client sends request with X-API-Key or Authorization: Bearer
2. Server looks up API key in database (hashed comparison)
3. Server validates API key is active
4. Server retrieves associated User record
5. Server extracts tenant_key from User
6. Server creates/retrieves session with tenant context

**Code Reference:**
- `api/endpoints/mcp_session.py` - `authenticate_api_key()`
- `api/endpoints/mcp_sdk_server.py` - API key resolution (X-API-Key or Bearer)

### Tenant Isolation Guarantees

**Database-Level Isolation:**
- All tool operations filtered by `tenant_key`
- No cross-tenant data access in queries
- Foreign key constraints enforce tenant boundaries

**Session-Level Isolation:**
- Each session tied to single tenant_key
- Tenant context never changes during session
- Project switching limited to tenant's projects

**Code References:**
- `api/endpoints/mcp_sdk_server.py` - Tenant context setting and session validation

### Session Expiration

**Default Policy:**
- Sessions expire after 24 hours of inactivity
- `last_accessed` updated on every request
- `expires_at` automatically extended on access

**Cleanup Policy:**
- Sessions older than 48 hours deleted
- Cleanup runs via background task
- No manual intervention required

**Code Reference:**
- `api/endpoints/mcp_session.py:160-174` - `cleanup_expired_sessions()`
- `src/giljo_mcp/models.py:1346-1356` - Expiration logic

### Public Endpoint Security Model

**Why /mcp is Public:**
- MCP endpoint requires API key authentication (X-API-Key or Bearer)
- Standard authentication middleware bypassed
- Custom authentication in endpoint handler
- Prevents double-authentication issues

**Security Layers:**
1. **X-API-Key validation** - First defense
2. **Tenant isolation** - Second defense
3. **Session expiration** - Third defense
4. **OS Firewall** - Fourth defense (network level)

**Code Reference:**
- `api/middleware.py:97-113` - Public endpoint list
- `api/endpoints/mcp_sdk_server.py` - X-API-Key validation

---

## Troubleshooting

### Common Connection Issues

**Issue: "X-API-Key header required"**
```bash
# Solution: Ensure API key header is included
claude mcp add --transport http giljo-mcp http://10.1.0.164:7272/mcp \
  --header "X-API-Key: gk_YOUR_ACTUAL_KEY"
```

**Issue: "Invalid API key"**
- Check API key is correct (case-sensitive)
- Verify API key hasn't been revoked
- Generate new API key from dashboard

**Issue: "Session expired"**
- Sessions expire after 24 hours of inactivity
- Simply make a new request to create new session
- No manual intervention required

**Issue: "Connection refused"**
- Verify server is running: `curl http://localhost:7272/health`
- Check firewall allows port 7272
- Verify correct server IP/hostname

### How to Verify Server is Running

**Check API Health:**
```bash
curl http://localhost:7272/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "checks": {
    "api": "healthy",
    "database": "healthy",
    "websocket": "healthy"
  }
}
```

**Test MCP Endpoint:**
```bash
# Use Claude Code's built-in MCP connection test
claude mcp add --transport http giljo-mcp http://localhost:7272/mcp \
  --header "X-API-Key: gk_YOUR_KEY"
# Then run /mcp in Claude Code to verify connection
```

### How to Check Logs

**API Server Logs:**
```bash
# From project root
tail -f logs/api.log

# Look for MCP-related messages:
# - "MCP session initialized"
# - "Tool executed successfully"
# - "API key authenticated"
```

**Database Query Logs:**
```sql
-- Check active MCP sessions
SELECT session_id, tenant_key, created_at, last_accessed
FROM mcp_sessions
WHERE expires_at > NOW()
ORDER BY last_accessed DESC;

-- Check expired sessions
SELECT session_id, tenant_key, expires_at
FROM mcp_sessions
WHERE expires_at < NOW();
```

### Python Cache Issues

**Problem: Old bytecode causing import errors**

**Solution:**
```bash
# From project root
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Restart API server
python api/run_api.py
```

**Verification:**
```bash
# Check imports work correctly
python -c "from src.giljo_mcp.models import MCPSession; print('OK')"
```

---

## Developer Guide

### How to Add New MCP Tools

**Step 1: Register Tool with FastMCP SDK**

Define your tool function decorated with `@mcp.tool()` in `api/endpoints/mcp_sdk_server.py`, or add the method to the appropriate tools module and register it during server setup:

---

## Agent Communication Tools & WebSocket Events (from Handover 0040)

The Agent Flow Visualization work (Handover 0040) standardized a simple tool/event contract for agent–orchestrator communication:

### MCP Tools (polling/ack/status)
- `check_orchestrator_messages(agent_id|job_id, tenant_key, …)`
- `acknowledge_message(job_id, tenant_key, message_id, response)`
- `report_status(job_id, tenant_key, status, progress, task)`

These tools are called on a 30–60s cadence by CLI/editor agents to drive live updates.

### WebSocket Events (UI updates)
- `agent_communication:message_sent`
- `agent_communication:message_acknowledged`
- `agent_communication:status_update`
- `agent_communication:artifact_created`

The frontend subscribes to these events to animate message lines, update node status/metrics, and append artifacts.

See also: `frontend/AGENT_FLOW_VISUALIZATION_INTEGRATION.md` for component wiring and store logic.

```python
{
    "name": "my_new_tool",
    "description": "Description of what this tool does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param1"]
    }
}
```

**Step 2: Implement Tool Method**

Add method to `src/giljo_mcp/tools/` or appropriate module:

```python
async def my_new_tool(self, param1: str) -> dict:
    """Tool implementation"""
    # Your logic here
    return {"result": "success"}
```

**Step 3: Test Tool**

```bash
# From Claude Code
> "Use my_new_tool with param1 set to 'test'"
```

### Session State Management

**Reading Session Data:**
```python
from api.endpoints.mcp_session import MCPSessionManager

async def my_handler(session_id: str, db: AsyncSession):
    session_manager = MCPSessionManager(db)
    session = await session_manager.get_session(session_id)

    if session:
        client_info = session.session_data.get("client_info", {})
        print(f"Client: {client_info.get('name')}")
```

**Updating Session Data:**
```python
await session_manager.update_session_data(
    session_id,
    {
        "custom_field": "value",
        "timestamp": datetime.now(timezone.utc).isoformat()
    },
    merge=True  # Merge with existing data
)
```

**Session Expiration Management:**
```python
# Extend session expiration
session.extend_expiration(hours=24)
await db.commit()

# Check if session expired
if session.is_expired:
    print("Session has expired")
```

### Testing MCP Endpoints

MCP tool testing is done through the FastMCP SDK's built-in test utilities or by connecting a real MCP client (Claude Code) and exercising tools interactively.

### Debugging Tips

**Enable Debug Logging:**
```python
import logging

# In api/endpoints/mcp_sdk_server.py
logger.setLevel(logging.DEBUG)

# Will log:
# - MCP session initialization details
# - Tool execution parameters and results
# - Authentication flow information
```

**Debug Session State:**
```python
# In handler code
print(f"Session data: {session.session_data}")
print(f"Tenant: {session.tenant_key}")
print(f"Expires: {session.expires_at}")
print(f"Last accessed: {session.last_accessed}")
```

**Debug API Key Resolution:**
```python
# In mcp_session.py authenticate_api_key()
print(f"API key lookup: {api_key_value[:10]}...")
print(f"Found user: {user.username} (tenant: {user.tenant_key})")
```

---

## See Also

- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Overall system architecture
- [Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md) - Installation guide
- [Connect Claude Code to tools via MCP](Connect%20Claude%20Code%20to%20tools%20via%20MCP.md) - Claude Code MCP setup
- [MCP Tools Manual](manuals/MCP_TOOLS_MANUAL.md) - Complete MCP tools reference
- [Handover 0032](../handovers/0032_HANDOVER_20251018_MCP_OVER_HTTP_IMPLEMENTATION.md) - Implementation details

---

**Last Updated**: January 18, 2025
**Version**: 1.0.0
**Status**: Production Ready
