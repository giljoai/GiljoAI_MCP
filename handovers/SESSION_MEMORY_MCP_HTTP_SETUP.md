Session Memory: MCP over HTTP Setup and Decisions
Date: 2025-11-03

Overview
- Hosted MCP will use HTTP transport with API key authentication. Stdio is local-only and not used for LAN/WAN access.
- The server already exposes a pure MCP-over-HTTP JSON-RPC endpoint at `POST /mcp` with `X-API-Key` auth.
- Some tools were not visible because the HTTP MCP endpoint listed/routed only a subset. Action item: expose the full tool catalog via `mcp_http.py`.

Key Endpoints and Files
- HTTP MCP endpoint: api/endpoints/mcp_http.py:329 (registered in api/app.py:558; public in api/middleware.py:109).
- Stdio adapter (optional, local bridge): src/giljo_mcp/mcp_adapter.py.
- FastMCP stdio server (local/dev use): src/giljo_mcp/mcp_server.py.

Correct Client Registration (Hosted HTTP)
- Claude (supports HTTP):
  claude mcp add --transport http giljo-mcp http://10.1.0.164:7272/mcp --header "X-API-Key: gk_YOUR_KEY"
- Codex (HTTP via --url):
  codex mcp add --url http://10.1.0.164:7272/mcp --header "X-API-Key: gk_YOUR_KEY" giljo-mcp
- Gemini (if CLI supports HTTP MCP):
  gemini mcp add --url http://10.1.0.164:7272/mcp --header "X-API-Key: gk_YOUR_KEY" giljo-mcp

Why Not Stdio for Hosted
- Stdio MCP is a local process protocol (pipes). It cannot accept remote network connections. For LAN/WAN, use HTTP MCP.
- The stdio adapter/server are kept for local dev or clients without HTTP transport.

Observed Confusion and Resolution
- Claim: “No MCP server existed.” Reality: A real HTTP MCP endpoint exists; the gap was tool exposure.
- Claim: “Must run native stdio server remotely.” Reality: Not needed for hosted access; use HTTP MCP.
- Root cause of missing tools: handle_tools_list() and handle_tools_call() in api/endpoints/mcp_http.py expose a subset.

Action Items
- Expand tool exposure in HTTP MCP:
  - Add remaining tools to tools list: api/endpoints/mcp_http.py:120-210
  - Add handlers to tool_map: api/endpoints/mcp_http.py:248-278
  - Optional: generate schemas/maps dynamically from state.tool_accessor to avoid drift.

Verification (Pure HTTP)
- Health (REST):
  curl http://10.1.0.164:7272/health
- MCP tools list (JSON-RPC over HTTP):
  curl -X POST http://10.1.0.164:7272/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: gk_YOUR_KEY" \
    -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
- Call a tool (health_check):
  curl -X POST http://10.1.0.164:7272/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: gk_YOUR_KEY" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"health_check","arguments":{}},"id":2}'

Agreed Test Plan
- User will remove any prior local stdio-based MCP config and re-add HTTP MCP configuration using the commands above.
- Expectation: Full tool visibility depends on HTTP MCP tool exposure; expanding the list/map will surface all tools.

Notes for Fresh Sessions
- Use HTTP MCP registration commands above; do not rely on local stdio unless the client lacks HTTP support.
- If only a few tools appear, update api/endpoints/mcp_http.py tool list/map.

