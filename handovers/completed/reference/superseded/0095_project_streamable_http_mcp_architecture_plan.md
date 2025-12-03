# Project 0095 — MCP Streamable HTTP + HTTPS Migration Plan

---
**⚠️ RETIRED (2025-11-27): SKIPPED - NOT REQUIRED**

This handover has been **retired** after comprehensive investigation revealed:
- **Codex CLI already works** with standard HTTP JSON-RPC transport (verified in handover 0092)
- Bearer token support implemented and functional (Nov 3, 2025)
- No evidence of "handshake failures" or streaming requirement for Codex
- SSE streaming is a speculative enhancement, not a critical requirement
- HTTPS functionality covered by new handover 0250 (optional security enhancement)

**Decision**: Skipped as unnecessary. All three CLIs (Claude Code, Codex, Gemini) work with current HTTP implementation.
**Location**: Moved to `handovers/completed/superseded/`

---
**⚠️ CRITICAL UPDATE (2025-11-12): DEFERRED TO HANDOVER 0515**

This handover has been **reorganized** into the 0500 series remediation project:

**New Scope**: Part of Handover 0515 - Frontend Consolidation (Streaming API Integration)
**Parent Project**: Projectplan_500.md
**Status**: Deferred until after critical remediation (Handovers 0500-0514 complete)

**Reason**: The refactoring (Handovers 0120-0130) left 23 critical implementation gaps that must be fixed BEFORE proceeding with this enhancement. HTTP/HTTPS streaming migration requires stable foundation. See:
- **Investigation Reports**: Products, Projects, Settings, Orchestration breakage
- **Master Plan**: `handovers/Projectplan_500.md`
- **New Handover**: `handovers/0515_frontend_consolidation.md` (includes streaming API integration)

**Original scope below** (preserved for historical reference):

---

Document version: 1.1.0
Date: 2025-11-08 (Updated)
Owner: Core Platform

---

## Changelog

**v1.1.0 (2025-11-08)**:
- Added HTTP/HTTPS toggle for development via Admin Settings UI
- Added Certificate Management section (Let's Encrypt + Caddy)
- Added localhost vs LAN vs WAN deployment scenarios
- Added backend HTTPS enforcement logic with helpful error messages
- Added environment variable override (`ALLOW_HTTP_MCP`)
- Updated implementation plan with admin UI tasks
- Updated action items with detailed security & deployment checklist
- Clarified "practical security" approach (not enterprise-grade)

**v1.0.0 (2025-11-04)**:
- Initial plan for streamable HTTP MCP transport
- SSE + POST dual-endpoint design
- nginx/Caddy proxy examples
- Multi-client CLI support (Codex, Gemini, Claude Code)

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

### HTTP/HTTPS Toggle for Development (Admin Settings Integration)

**Design Philosophy**: HTTPS by default for production security, with a toggleable fallback for local development.

We add an admin-configurable setting to allow HTTP for MCP endpoints during local development, while enforcing HTTPS in production:

**Configuration (`config.yaml`)**:
```yaml
features:
  mcp_allow_http: false  # Default: require HTTPS. Set true only for local dev.
```

**Admin UI Integration** (System Settings → Network Tab):

Add a toggle switch after the "Server Configuration" section in `frontend/src/views/SystemSettings.vue`:

- **Switch label**: "Allow HTTP for MCP (Development Only)"
- **Default state**: Off (requires HTTPS)
- **Warning banner**: Displays when enabled, alerting about cleartext transmission risk
- **Visual indicator**: Shield icon (red when HTTP enabled, green when HTTPS enforced)
- **Placement**: Between "Frontend Port" and "CORS Origins" sections in Network tab

**Backend Enforcement** (`api/endpoints/mcp_stream.py`):

```python
from fastapi import HTTPException, Request

@router.get("/mcp/stream")
async def mcp_stream_sse(request: Request):
    # Check HTTPS requirement
    allow_http = state.config.get("features.mcp_allow_http", False)
    is_https = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    if not is_https and not allow_http:
        raise HTTPException(
            status_code=403,
            detail="HTTPS required. Enable 'Allow HTTP for MCP' in Admin Settings → Network for local development only."
        )
    # ... continue with stream logic
```

**Environment Variable Override**:
```bash
# For CI/CD or scripted local dev
ALLOW_HTTP_MCP=true python -m uvicorn api.app:app
```

**Use Cases**:
- **Production**: Toggle OFF (default). nginx terminates TLS, uvicorn sees `X-Forwarded-Proto: https`
- **Local Dev**: Toggle ON temporarily. Test MCP over `http://localhost:7272` without certs
- **CI/CD**: Set env var `ALLOW_HTTP_MCP=true` for automated testing

**Security Considerations**:
- Default is secure (HTTPS required)
- UI shows prominent warning when HTTP enabled
- Logged at startup: `[MCP] SECURITY WARNING: HTTP allowed for MCP endpoints (development mode)`
- Recommended practice: toggle on only when actively debugging, toggle off when done

**Localhost vs Network Deployment**:

This setting addresses different deployment scenarios:

1. **Pure localhost development** (`http://localhost:7272`):
   - Toggle ON: Test MCP CLIs without setting up certificates
   - No network exposure (127.0.0.1 only)
   - Acceptable risk: credentials never leave the machine

2. **LAN deployment** (`http://192.168.1.100:7272`):
   - Toggle OFF: Use HTTPS even on LAN
   - Simple setup: nginx + self-signed cert OR Caddy (auto Let's Encrypt with domain)
   - API keys cross the network → HTTPS mandatory

3. **WAN/Internet deployment** (https://your-domain.com):
   - Toggle OFF (enforced): HTTPS always required
   - Use Let's Encrypt for free, auto-renewing certificates
   - nginx or Caddy handles TLS termination

**Recommendation**: Only enable HTTP mode for same-machine testing. Any network access (even LAN) should use HTTPS.

### Certificate Management (Let's Encrypt)

For production deployments, obtain free SSL certificates via Let's Encrypt:

**Initial Setup**:
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate (interactive)
sudo certbot --nginx -d your-domain.com

# Certificates stored at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

**Auto-Renewal**:
```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot installs cron job automatically
# Manual renewal if needed:
sudo certbot renew
```

**nginx Integration** (already configured in example above):
- Certbot auto-updates nginx config when using `--nginx` flag
- Certificates auto-renew every 60 days
- No manual intervention required

**Caddy Alternative** (automatic HTTPS):
```
# Caddyfile - Caddy handles certificates automatically
your-domain.com {
    reverse_proxy localhost:7272 {
        # SSE-safe settings
        flush_interval -1
        header_up Connection ""
    }
}
```

Caddy automatically obtains and renews Let's Encrypt certificates with zero configuration.

### Security Notes

- Continue accepting `X-API-Key` and `Authorization: Bearer` (same credential).
- Consider optionally accepting `x-goog-api-key` alias for broader client compatibility.
- Add rate limits and idle stream timeouts; heartbeat monitoring to detect dead connections.
- **Practical approach**: We don't need enterprise-grade security (HSMs, cert pinning, mTLS). Simple HTTPS with Let's Encrypt + reverse proxy is sufficient.

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
   - Add HTTP/HTTPS toggle: `features.mcp_allow_http = false` (default)

6) Admin UI for HTTP/HTTPS toggle
   - Add toggle switch in `frontend/src/views/SystemSettings.vue` (Network tab)
   - UI elements:
     - v-switch component with warning/success shield icon
     - Warning v-alert when HTTP mode enabled
     - Info text explaining development-only use
   - Backend API:
     - Read setting via `GET /api/v1/config` (features.mcp_allow_http)
     - Update setting via `PATCH /api/v1/config` (already exists)
   - Environment variable support: `ALLOW_HTTP_MCP=true`

7) MCP endpoint security enforcement
   - Check `features.mcp_allow_http` config at runtime
   - Inspect request scheme (`https` or `x-forwarded-proto` header)
   - Return 403 with helpful error if HTTPS required but not present
   - Log warning at startup if HTTP mode enabled

8) Client commands & UI
   - Update AI tool config generators to use `/mcp/stream`
   - Keep legacy `/mcp` docs for plain JSON‑RPC
   - Document HTTPS requirement and admin toggle for dev

9) Certificate setup documentation
   - Add Let's Encrypt + Certbot setup guide
   - Include Caddy automatic HTTPS alternative
   - Document auto-renewal verification

10) Observability
    - New log: `logs/mcp_stream.log`
    - Basic metrics: active streams, messages/sec, avg latency
    - Log warning when MCP HTTP mode enabled

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
- Admin UI toggle + backend enforcement: 0.5 day
- Certificate setup docs (Let's Encrypt): 0.5 day
- Tests (unit + integration) + tweaks: 1–2 days
- Total initial delivery: ~5–7 days

## Out of Scope (phase 1)

- WebSocket transport (optional future)
- Multi‑region fanout; Redis/Kafka event bus
- Fine‑grained per‑tool rate limiting (basic rate limit only)

---

## Action Items

**Core Implementation:**
- [ ] Implement `api/endpoints/mcp_stream.py` with `GET /mcp/stream` (SSE) and `POST /mcp/stream` (send)
- [ ] Add in‑memory stream manager and heartbeats
- [ ] Reuse MCP handlers; push results to SSE

**Security & Configuration:**
- [ ] Add `features.mcp_allow_http` to `config.yaml` (default: false)
- [ ] Add environment variable override: `ALLOW_HTTP_MCP`
- [ ] Implement HTTPS enforcement in MCP stream endpoints (check scheme + `x-forwarded-proto`)
- [ ] Add startup logging for HTTP mode warning

**Admin UI:**
- [ ] Add HTTP/HTTPS toggle in `SystemSettings.vue` Network tab
- [ ] Add v-switch component with shield icon (red=HTTP, green=HTTPS)
- [ ] Add warning v-alert when HTTP mode enabled
- [ ] Wire toggle to `PATCH /api/v1/config` endpoint
- [ ] Add loading state for MCP security settings

**HTTPS Deployment:**
- [ ] Add nginx sample config with SSE-safe settings
- [ ] Add Caddy sample config (automatic HTTPS)
- [ ] Document Let's Encrypt + Certbot setup
- [ ] Document certificate auto-renewal verification
- [ ] Update `.env.example` and `config.yaml.example`

**Client Integration:**
- [ ] Update AI tool generators to use `/mcp/stream` for Codex/Gemini/Claude
- [ ] Document HTTPS requirement in client setup guides
- [ ] Document admin toggle for local development

**Testing & Observability:**
- [ ] Add tests for HTTP/HTTPS enforcement
- [ ] Add tests for stream open/close; heartbeat; stale cleanup
- [ ] Add tests for auth resolution (X-API-Key vs Bearer)
- [ ] Add `logs/mcp_stream.log` with key prefix masking
- [ ] Add basic metrics: active streams, messages/sec, errors

---

## Quick Reference: Implementation Snippets

### Config File Update

Add to `config.yaml`:
```yaml
features:
  # ... existing features ...
  mcp_allow_http: false  # HTTPS required by default
```

### Frontend UI (SystemSettings.vue)

Insert in Network tab after "Frontend Port" field (around line 98):

```vue
<!-- MCP Transport Security -->
<v-divider class="my-6" />

<h3 class="text-h6 mb-3">MCP Transport Security</h3>

<v-switch
  v-model="mcpAllowHttp"
  label="Allow HTTP for MCP (Development Only)"
  color="warning"
  hint="When disabled, MCP endpoints require HTTPS."
  persistent-hint
  @update:model-value="onMcpSecurityChange"
>
  <template v-slot:prepend>
    <v-icon :color="mcpAllowHttp ? 'error' : 'success'">
      {{ mcpAllowHttp ? 'mdi-shield-off' : 'mdi-shield-check' }}
    </v-icon>
  </template>
</v-switch>

<v-alert v-if="mcpAllowHttp" type="error" variant="tonal" class="mt-4">
  <v-icon start>mdi-alert</v-icon>
  <strong>Security Warning:</strong> API keys transmitted in cleartext.
  Use only for localhost development.
</v-alert>
```

### Backend Enforcement (mcp_stream.py)

```python
from fastapi import HTTPException, Request
from api.app import state

@router.get("/mcp/stream")
async def mcp_stream_sse(request: Request):
    # Check HTTPS requirement
    allow_http = state.config.get("features.mcp_allow_http", False)
    is_https = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    if not is_https and not allow_http:
        raise HTTPException(
            status_code=403,
            detail="HTTPS required for MCP endpoints. Enable HTTP mode in Admin Settings → Network (development only)."
        )

    # Log warning if HTTP allowed
    if allow_http and not is_https:
        logger.warning(
            "[MCP Stream] Accepting HTTP connection (development mode enabled). "
            "API keys transmitted in cleartext!"
        )

    # ... continue with SSE stream logic
```

### Environment Variable Override

Add to `config_manager.py` `_load_from_env()` method:

```python
# MCP security settings (around line 720)
if val := os.getenv("ALLOW_HTTP_MCP"):
    # Import FeatureFlags if not already available
    self.features.mcp_allow_http = val.lower() in ("true", "1", "yes")
```

### Let's Encrypt Setup (Debian/Ubuntu)

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate (interactive, auto-configures nginx)
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Certificates location
ls -l /etc/letsencrypt/live/your-domain.com/
```

### Caddy Config (Alternative - Automatic HTTPS)

Create `Caddyfile`:
```
your-domain.com {
    reverse_proxy localhost:7272 {
        flush_interval -1
        header_up Connection ""
    }
}
```

Run Caddy:
```bash
sudo caddy run --config Caddyfile
```

Caddy automatically obtains and renews Let's Encrypt certificates - zero configuration needed!
