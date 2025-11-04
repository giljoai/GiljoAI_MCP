# Project 0095 — MCP Streamable HTTP + HTTPS Migration Plan

Document version: 1.0.0
Date: 2025-11-04
Owner: Core Platform

---

## Summary

Codex CLI’s URL transport expects a “streamable HTTP” MCP server. Our current `/mcp` endpoint implements plain JSON‑RPC over request/response and closes the connection, which causes Codex to fail during the handshake. This project adds a streamable HTTP transport (and SSE variant) while keeping the existing JSON‑RPC endpoint for compatibility. We also adopt HTTPS for all MCP traffic to protect API keys/Bearer tokens.

## Drivers

- Codex CLI requires a streamable HTTP MCP transport (cannot use stdio; cannot pass arbitrary headers in URL mode).
- Gemini CLI supports HTTP and SSE transports; can send headers directly.
- Claude Code supports HTTP transport; implementing a streamable variant ensures compatibility across tools.
- Security: API keys must not traverse the network in clear‑text → move to HTTPS.

## Requirements

- Add a streamable transport compatible with Codex URL mode.
- Keep current JSON‑RPC `/mcp` endpoint working as before (backward compatible).
- Preserve auth and tenancy (API keys; `X-API-Key` and `Authorization: Bearer`).
- Support both streamable HTTP and SSE to maximize client compatibility.
- Adopt HTTPS termination with proxy configuration that supports streaming.

## Target Transport Design

We will implement a bidirectional channel over HTTP using two endpoints (compatible with CLI patterns and proxies):

- Server → Client: SSE stream (Text/EventStream) that stays open.
- Client → Server: HTTP POST for sending MCP messages.

This avoids true HTTP duplex (poorly supported) but still delivers a “streamable HTTP” experience for clients. For CLIs that insist on a single URL, we present `/mcp/stream` as the advertised base and document both directions under that path.

### Endpoints (new)

- `GET /mcp/stream` — Open/attach SSE stream
  - Auth: `X-API-Key` or `Authorization: Bearer`
  - Returns: EventSource stream of MCP JSON messages
  - Behavior: Creates or reuses an active MCP session; keeps connection alive; heartbeats every 20–30s

- `POST /mcp/stream` — Send MCP messages from client → server
  - Auth: `X-API-Key` or `Authorization: Bearer`
  - Body: Single JSON‑RPC message or array of messages
  - Response: 202 Accepted (processing async); results/notifications are emitted on SSE stream

- `POST /mcp/stream/close` — Close session (optional)
  - Auth: same
  - Body: `{}` or `{ "reason": "..." }`

Notes:
- Session resolution is by API key (one active stream per key). If multiple clients connect with the same key, the newest replaces the previous. We can optionally extend with an `X-MCP-Client` header to support multiple per‑key streams later.
- Keep existing `POST /mcp` (plain JSON‑RPC) for simple, non‑streaming clients.

### Message Format

- JSON‑RPC 2.0 envelopes for all messages (initialize, tools/list, tools/call, notifications).
- SSE events:
  - `event: message` with `data: <json>` — a JSON‑RPC message from server to client
  - `event: heartbeat` — periodic keep‑alive
  - `event: close` — server instructs client to disconnect

### Server Architecture

- In‑memory per‑API‑key stream state:
  - `streams[key] = { queue: asyncio.Queue, sse_response: EventSourceResponse, last_seen: ts }`
  - Enforce one active SSE per key; replacing closes older stream.
- Reuse existing `MCPSessionManager` + DB persistence;
  - Stream state is transient; protocol/session data remains in DB.
- Reuse existing MCP handlers from `api/endpoints/mcp_http.py` for initialize, tools/list, tools/call.
  - For stream mode, enqueue results to the stream’s queue instead of returning immediately.

## Client Matrix & Commands

- Codex CLI (URL transport; streamable HTTP)
  - Proposed URL: `https://<host>:7272/mcp/stream`
  - Registration: `codex mcp add --url https://<host>:7272/mcp/stream --bearer-token-env-var GILJO_API_KEY giljo-mcp`

- Gemini CLI (HTTP or SSE)
  - HTTP variant: `gemini mcp add -t http -H "X-API-Key: gk_..." giljo-mcp https://<host>:7272/mcp/stream`
  - SSE variant: `gemini mcp add -t sse -H "X-API-Key: gk_..." giljo-mcp https://<host>:7272/mcp/stream`

- Claude Code CLI (HTTP)
  - `claude mcp add --transport http giljo-mcp https://<host>:7272/mcp/stream --header "X-API-Key: gk_..."`
  - Note: Claude supports HTTP transport; streamable endpoint ensures full compatibility.

## HTTPS Migration

We will enable HTTPS for all MCP endpoints.

### Recommended: Reverse Proxy TLS Termination

Use nginx or Caddy in front of uvicorn:

- nginx key settings:
  - `proxy_set_header Connection ''` and `proxy_http_version 1.1`
  - `proxy_buffering off` to support SSE
  - Increase timeouts: `proxy_read_timeout 3600s`, `keepalive_timeout 75s`
- Example nginx snippet (SSE‑safe):

```
server {
    listen 443 ssl http2;
    server_name my.domain.tld;

    ssl_certificate     /etc/letsencrypt/live/my.domain.tld/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/my.domain.tld/privkey.pem;

    location /mcp/stream {
        proxy_pass http://127.0.0.1:7272;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }

    location / {
        proxy_pass http://127.0.0.1:7272;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Alternative: Direct TLS in uvicorn

- For development only; provide cert/key via config and run uvicorn with SSL.

### Security Notes

- Continue accepting `X-API-Key` and `Authorization: Bearer` (same credential).
- Consider optionally accepting `x-goog-api-key` alias for broader client compatibility.
- Add rate limits and idle stream timeouts; heartbeat monitoring to detect dead connections.

## Implementation Plan

1) Add stream endpoints
   - New module: `api/endpoints/mcp_stream.py`
   - Endpoints: `GET /mcp/stream`, `POST /mcp/stream`, `POST /mcp/stream/close`
   - SSE via `EventSourceResponse` (or `StreamingResponse` with SSE framing)

2) Stream session manager
   - In‑memory map keyed by API key (or future client ID)
   - Async queue per stream for server→client messages
   - Heartbeat task + cleanup of stale streams

3) Handler reuse
   - Wrap existing MCP handlers (initialize, tools/list, tools/call)
   - For stream mode, process POSTed messages and push results to queue as JSON‑RPC responses

4) Auth integration
   - Reuse current `MCPSessionManager` for DB session lifecycle
   - Accept API keys from `X-API-Key` or Bearer; same as `/mcp`

5) HTTPS enablement
   - Provide nginx/Caddy examples; update docs and `.env.example`/`config.yaml.example` for external host
   - Add feature flag: `features.mcp_stream.enabled = true`

6) Client commands & UI
   - Update AI tool config generators to use `/mcp/stream`
   - Keep legacy `/mcp` docs for plain JSON‑RPC

7) Observability
   - New log: `logs/mcp_stream.log`
   - Basic metrics: active streams, messages/sec, avg latency

## Testing Plan

- Unit tests:
  - Auth resolution (X-API-Key vs Bearer)
  - Stream open/close; heartbeat; stale cleanup
  - Message routing initialize → tools/list → tools/call

- Integration tests:
  - `GET /mcp/stream` + `POST /mcp/stream` end‑to‑end with httpx + sse client
  - Codex CLI: `codex mcp add --url https://<host>/mcp/stream --bearer-token-env-var ...`
  - Gemini CLI (HTTP and SSE variants)
  - Claude Code CLI (HTTP transport to `/mcp/stream`)

## Backward Compatibility

- `POST /mcp` (plain JSON‑RPC) remains available and unchanged.
- Existing Claude integrations using HTTP + `X-API-Key` continue to work.
- New stream endpoints are additive.

## Risks & Mitigations

- Proxy buffering breaks SSE
  - Disable buffering; increase read timeouts; test behind nginx/Caddy

- Multiple clients with the same API key
  - Current policy: last writer wins (new stream replaces previous)
  - Future enhancement: support `X-MCP-Client` for disambiguation

- Idle timeouts
  - Heartbeats and server‑side timers to keep connections alive

- Horizontal scaling (multi‑instance)
  - Initial: single instance; stream state is in‑memory
  - Scale: move to Redis pub/sub for stream fanout; sticky sessions at LB

## Cautions & Developer Notes

These are hard‑won details and edge cases discovered during diagnosis and design. Please read before coding:

- Transport mismatch (Codex): Codex URL transport expects a streamable HTTP protocol. Our current `POST /mcp` (JSON‑RPC request/response) will fail the handshake. Implement the new `/mcp/stream` endpoints and validate with Codex early.

- Single URL vs. two‑leg streams: The proposed design uses SSE for server→client and POST for client→server under the same base path `/mcp/stream`. Most clients accept this (open SSE, then POST `initialize`). If Codex strictly requires a single long‑lived duplex HTTP stream, we may need to add a chunked transfer variant. Validate with Codex CLI (v0.53.0+) early.

- Gemini CLI specifics: Gemini supports `-t http` and `-H` for headers, and expects the order `<name> <url>`. Example: `gemini mcp add -t http -H "X-API-Key: gk_..." giljo-mcp https://host:7272/mcp/stream`.

- Claude CLI: Supports HTTP transport and `--header`. Point Claude to `/mcp/stream` post‑implementation, not `/mcp`.

- Auth headers: All new endpoints must accept both `X-API-Key` and `Authorization: Bearer` and route to the same API key verification path. Consider optional `x-goog-api-key` alias only if needed.

- Middleware routing: Add `/mcp/stream` to public endpoints in `api/middleware.py` (like `/mcp`). The endpoint will perform its own API key authentication.

- HTTPS everywhere for MCP: We are transmitting credentials; terminate TLS at a reverse proxy (nginx/Caddy). Ensure SSE‑safe proxy settings: `proxy_buffering off`, `proxy_http_version 1.1`, long `proxy_read_timeout`, and keepalive. Test behind your actual proxy/CDN (some CDNs buffer SSE by default).

- Mixed content and CSP/CORS: If the frontend UI is served over HTTPS, avoid mixed content by also proxying the API over HTTPS. If UI and API are cross‑origin, add the API origin to CORS allowlist and CSP `connect-src`. Current CSP includes `ws:`/`wss:`; add explicit `https://api.domain` if needed.

- WebSockets: Existing WS code is unaffected. Under HTTPS, connections become `wss://` automatically via the proxy. No server changes required.

- Cookies/JWT: Web login flows continue to work. Under HTTPS, set cookies with `Secure` (and recommended `SameSite=Lax`). No token refactor needed.

- Session policy: Define “one active stream per API key; last writer wins.” Close the previous stream when a new one attaches. For future multi‑client per key, add an `X-MCP-Client` identifier.

- Heartbeats & cleanup: Send periodic SSE heartbeats; implement server‑side idle timeouts and cleanup on disconnect to avoid memory leaks. Ensure queues are drained and session references removed when a stream closes.

- Observability & key hygiene: Add `logs/mcp_stream.log`. Never log full API keys; log only prefixes (e.g., `gk_abcdef...`). Include counters for active streams, messages/sec, and error rates.

- Rate limiting & quotas: Long‑lived streams can be abused. Add simple limits: max streams per key, overall max streams, per‑IP request caps for `POST /mcp/stream`. Integrate with existing per‑key usage later.

- Large payloads: SSE is for signaling; don’t push large binary/file payloads through MCP messages. Continue using existing REST endpoints for uploads/downloads. If large JSON results are needed, consider paging or a separate fetch endpoint.

- Graceful shutdown: On API restart, proactively emit an `event: close` over SSE. Clients should reconnect autonomously. Document this for users.

- Backward compatibility: Keep `POST /mcp` as‑is. Do not alter existing REST or WS routes. The new stream feature is additive to minimize blast radius.

- Version drift: Codex CLI behaviors can change between versions. Pin a minimum tested version (e.g., v0.53.0) in docs once verified.

## Timeline & Effort (estimate)

- Stream endpoints + manager + wiring: 2–3 days
- HTTPS proxy config + docs: 0.5–1 day
- Tests (unit + integration) + tweaks: 1–2 days
- Total initial delivery: ~4–6 days

## Out of Scope (phase 1)

- WebSocket transport (optional future)
- Multi‑region fanout; Redis/Kafka event bus
- Fine‑grained per‑tool rate limiting (basic rate limit only)

---

## Action Items

- [ ] Implement `api/endpoints/mcp_stream.py` with `GET /mcp/stream` (SSE) and `POST /mcp/stream` (send)
- [ ] Add in‑memory stream manager and heartbeats
- [ ] Reuse MCP handlers; push results to SSE
- [ ] Add nginx/Caddy sample configs; enable HTTPS in deployment
- [ ] Update AI tool generators to use `/mcp/stream` for Codex/Gemini/Claude
- [ ] Add tests and monitoring
