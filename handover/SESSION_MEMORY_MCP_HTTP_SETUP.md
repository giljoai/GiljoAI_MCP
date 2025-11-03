Session Memory: MCP over HTTP Setup (Codex CLI)
Date: 2025-11-03

Overview
- Use hosted HTTP MCP with API key; stdio is local-only.
- Your server exposes JSON-RPC MCP at `POST /mcp` with header `X-API-Key`.

Correct Codex CLI Command (HTTP + header)
- Bash/zsh:
  codex mcp add --url http://10.1.0.164:7272/mcp giljo-mcp -- --header 'X-API-Key: gk_YOUR_KEY'

- PowerShell:
  codex mcp add --url http://10.1.0.164:7272/mcp giljo-mcp -- --header "X-API-Key: gk_YOUR_KEY"

Why the `--`? 
- Codex parses `--header` as its own flag unless you stop parsing. `--` tells Codex to pass the rest to the HTTP transport.

Verify
- List registrations: codex mcp list
- Test connection:  codex mcp test-connection giljo-mcp

Direct HTTP Checks
- Tools list:
  curl -X POST http://10.1.0.164:7272/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: gk_YOUR_KEY" \
    -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'

- Call health tool:
  curl -X POST http://10.1.0.164:7272/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: gk_YOUR_KEY" \
    -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"health_check","arguments":{}},"id":2}'

Notes
- If you see "unexpected argument '--header'": ensure the `--` separator is present and placed before `--header`.
- If 401/403: confirm API key, header formatting, and network reachability to 10.1.0.164:7272.
- If only a few tools appear, expand the HTTP MCP tool exposure in `api/endpoints/mcp_http.py` (tools list and dispatch map).

Next Steps
- Standardize on HTTP MCP for hosted access.
- Optionally generate tool list/map from `state.tool_accessor` to avoid drift.
