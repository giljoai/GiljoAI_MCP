# MCP authentication across three CLIs: a practical strategy

**Static API keys remain the only auth method that works reliably across Claude Code, Codex CLI, and Gemini CLI today.** All three tools support OAuth 2.0, but each implementation carries distinct, serious bugs that make OAuth an unreliable universal strategy in March 2026. The MCP specification mandates OAuth 2.1 with Authorization Code + PKCE for remote servers, but the gap between spec and CLI reality is wide. For a FastAPI-based MCP server forking into Community and SaaS editions, the most elegant path forward is a **tiered auth architecture**: hardened API keys now, OAuth 2.1 for the SaaS edition, and a compatibility shim that lets both coexist cleanly.

---

## What the MCP spec actually requires

The MCP authorization specification, last updated November 2025, classifies MCP servers as **OAuth 2.0 Resource Servers** under RFC 9728. This is the most important architectural detail — your server validates tokens but should not issue them. The spec requires servers to serve a `/.well-known/oauth-protected-resource` metadata document, validate `Authorization: Bearer` tokens per OAuth 2.1, and enforce the `resource` parameter from RFC 8707 to bind tokens to specific server audiences.

The auth discovery flow works like this: a client sends an unauthenticated request, the server returns **HTTP 401** with a `WWW-Authenticate: Bearer resource_metadata="<url>"` header, the client fetches protected resource metadata to discover authorization servers, then performs a standard OAuth 2.1 Authorization Code + PKCE flow. Client registration defaults to Client ID Metadata Documents (CIMD) as of the November 2025 spec, with Dynamic Client Registration (DCR) retained for backwards compatibility.

Three key protocol points affect your design. First, **stdio transport should not use OAuth** — the spec says local servers should retrieve credentials from environment variables. Second, the Device Authorization Grant (RFC 8628) is **not part of the MCP spec**, despite being ideal for CLI workflows. Third, Client Credentials flow was removed from the core spec in June 2025 and now lives as an official extension in the `modelcontextprotocol/ext-auth` repository, alongside Enterprise-Managed Authorization for SSO scenarios.

## Each CLI's auth reality is riddled with bugs

**Claude Code CLI** has the most mature OAuth implementation. It supports browser-based OAuth with DCR, custom headers via `--header "X-API-Key: your-key"`, bearer tokens, pre-configured OAuth credentials (`--client-id`, `--client-secret`), and environment variables for stdio servers. Configuration lives in `.mcp.json` (project) or `~/.claude.json` (user). However, Claude Code has a persistent refresh token bug where tokens stored in macOS Keychain are not always used for refresh, forcing manual re-authentication. Servers without DCR support fail with an "incompatible auth server" error, requiring manual client ID registration as a workaround.

**Codex CLI** supports OAuth via `codex mcp login`, bearer tokens via `bearer_token_env_var`, and static headers via `http_headers` in its TOML config. The critical bug is the **missing RFC 8707 resource parameter** — Codex omits the `resource` parameter from both authorization requests and token exchanges, causing failures with any OAuth provider that requires resource indicators. A partial fix (PR #12866) added manual `oauth_resource` configuration per server, but this requires users to configure it themselves. Additionally, Codex's HTTP client lacks a `User-Agent` header, causing **Cloudflare's bot protection to block OAuth discovery** with 403 errors — a showstopper for any MCP server behind Cloudflare.

**Gemini CLI** offers the most auth provider variety (dynamic OAuth discovery, Google ADC, service account impersonation, static headers). Its configuration uses JSON in `~/.gemini/settings.json`. The confirmed bugs include **OIDC token type confusion** (Issue #5588, P1) — Gemini sends the opaque `access_token` instead of the `id_token` JWT when using OIDC providers, causing 401 errors on compliant resource servers. The **incorrect OpenID Configuration fallback** (Issue #12628) causes Gemini to redundantly scan `/.well-known/openid-configuration` after successfully discovering OAuth metadata, then incorrectly reports "dynamic registration not supported" even when it is. A third bug breaks 401 handling for Streamable HTTP transport entirely, preventing the auth flow from triggering.

The cross-CLI compatibility matrix reveals a clear picture:

| Auth method | Claude Code | Codex CLI | Gemini CLI | Reliable? |
|---|---|---|---|---|
| Custom headers (API key) | ✅ `--header` | ✅ `http_headers` | ✅ `headers` field | **Yes** |
| Bearer token header | ✅ | ✅ `bearer_token_env_var` | ✅ | **Yes** |
| OAuth 2.0 browser flow | ✅ (DCR issues) | ✅ (resource param bug) | ✅ (OIDC confusion) | **No** |
| OAuth DCR | ✅ | ✅ | ⚠️ (fallback bug) | **No** |
| Env vars (stdio) | ✅ | ✅ | ✅ | **Yes** (stdio only) |

## How the ecosystem actually handles auth today

The pattern across major MCP servers is remarkably consistent: **OAuth for the hosted version, API keys/PATs as fallback**. GitHub's MCP server uses one-click OAuth for IDE integrations but falls back to Personal Access Tokens passed as Bearer headers for CLI and Docker environments. Supabase defaults to OAuth 2.1 with DCR for its hosted server at `mcp.supabase.com` but documents PAT auth for CI/CD. Cloudflare wraps OAuth in its Workers platform with an open-source OAuth Provider Library, plus API token fallback. Stripe accepts both OAuth and API keys passed as Bearer tokens for its remote MCP server, while its CLI uses a custom pairing-code flow that generates restricted, **90-day-expiring** API keys.

An Astrix Security survey found that **53% of MCP servers still rely on static API keys or PATs** and only **8.5% use OAuth**. The trend is toward OAuth 2.1 for production deployments, but the ecosystem hasn't caught up yet. The FastMCP framework (powering roughly 70% of Python MCP servers) offers a tiered auth model: simple bearer token validation, JWT verification against external IdP JWKS endpoints, or full OAuth 2.1 server — and its maintainers explicitly **recommend using external identity providers** rather than building a custom OAuth server.

## The recommended architecture: tiered auth with a compatibility shim

Given the constraints — cross-CLI compatibility, Community-to-SaaS scaling, and minimizing setup friction — here is the most practical approach:

**For the Community Edition (self-hosted, single-user):** Keep API key authentication as the primary method. Your current `X-API-Key` header approach works across all three CLIs without bugs. Enhance it by migrating to the `Authorization: Bearer <key>` header convention, which is both MCP-spec-aligned and supported by all CLIs' native bearer token configurations. Generate keys with identifiable prefixes (e.g., `mcp_sk_live_...`) following Stripe's convention, set **90-day expiration** by default, and implement a simple `server auth` CLI command that generates and stores the key in the user's config. For the single-user case, this provides the lowest-friction setup: run the server, generate a key, paste it into your CLI config, done in under 60 seconds.

**For the SaaS Edition (multi-tenant):** Implement the full MCP OAuth 2.1 spec as a Resource Server, delegating token issuance to an external identity provider (Auth0, Keycloak, or your own). Serve the `/.well-known/oauth-protected-resource` metadata endpoint, support both Authorization Code + PKCE (for CLI browser flows) and Client Credentials (via the ext-auth extension, for CI/CD). This lets CLIs with working OAuth implementations auto-discover your auth configuration. For CLIs with broken OAuth, the bearer token fallback still works — users generate a token through your web dashboard and configure it as a static header.

**The compatibility shim** is the key architectural insight. Your FastAPI middleware should accept tokens from multiple sources in priority order:

1. `Authorization: Bearer <token>` — standard OAuth access tokens or API keys
2. `X-API-Key: <key>` — legacy header for backwards compatibility
3. OAuth 2.1 discovery flow — for CLIs that support it

Internally, all paths resolve to the same JWT validation logic you already have. API keys are looked up in your database and mapped to a user context; OAuth tokens are validated against the IdP's JWKS endpoint. The server doesn't care which path the token arrived through — it validates the same way. This means a single MCP server codebase serves both editions, with the SaaS edition simply enabling OAuth discovery endpoints and the external IdP integration.

## Why Device Authorization Grant is tempting but premature

OAuth 2.0 Device Authorization Grant (RFC 8628) is the most elegant CLI auth flow available. The user runs a login command, gets a short code and URL, opens any browser on any device, enters the code, authorizes, and the CLI receives tokens automatically via polling. GitHub CLI, Azure CLI, and Auth0's own MCP server all use it. It works in headless environments, supports MFA and SSO, requires no localhost redirect server, and credentials never touch the CLI.

However, **RFC 8628 is not part of the MCP specification**, and none of the three CLI tools implement it for MCP server auth. The MCP spec's auth discovery flow assumes Authorization Code + PKCE with browser redirects. Adding device flow would require your server to implement a custom authorization server endpoint (the device authorization endpoint at `/device/code`) that falls outside the MCP spec's discovery mechanism. CLIs would need custom configuration to use it rather than auto-discovering it.

That said, if you control the CLI-side experience (e.g., providing a `yourserver auth login` command), device flow is worth implementing for the SaaS edition as an **out-of-band auth method** that generates a bearer token the user then configures in their CLI. This is essentially the Stripe CLI model: a custom login flow that produces a scoped, time-limited token. The token itself is then used as a standard bearer token, sidestepping all three CLIs' OAuth bugs.

## mTLS is the wrong tool for this job

Mutual TLS provides strong cryptographic identity verification and works well for infrastructure tools like Kubernetes, where operations teams already manage PKI. For a developer-facing MCP server, mTLS introduces unacceptable friction: generating key pairs, creating certificate signing requests, managing a CA, distributing certificates, and handling expiration and rotation. Kubernetes' `kubeconfig` with embedded client certificates works because `kubeadm` automates the entire lifecycle — without equivalent automation, mTLS setup takes **5–15 minutes** versus 30–60 seconds for token-based auth.

The one scenario where mTLS adds value is **zero-trust self-hosted deployments** where the MCP server runs on a private network. Even then, a reverse proxy like Caddy or Nginx handling mTLS termination while the MCP server uses bearer tokens internally is simpler than implementing mTLS in FastAPI directly. For your Community Edition, this is overkill; for your SaaS Edition, OAuth + TLS (one-way) provides sufficient security.

## Concrete implementation roadmap

**Phase 1 (now):** Migrate the `X-API-Key` header to `Authorization: Bearer <key>` as the primary auth method. Add key prefixes, 90-day default expiration, and a key generation endpoint. Update documentation with copy-paste config snippets for all three CLIs. This works today, universally.

**Phase 2 (SaaS launch):** Implement the MCP OAuth 2.1 Resource Server spec: serve `/.well-known/oauth-protected-resource`, return proper `WWW-Authenticate` headers on 401, integrate with an external IdP for token issuance. Add the Client Credentials extension for machine-to-machine auth. The bearer token fallback remains for CLIs with broken OAuth.

**Phase 3 (when CLI OAuth stabilizes):** As Claude Code, Codex, and Gemini fix their respective OAuth bugs, test and certify each CLI's OAuth flow against your server. Publish per-CLI setup guides that use native OAuth where it works and bearer token fallback where it doesn't. Consider implementing Device Authorization Grant as an optional login flow for a superior CLI UX.

## Conclusion

The MCP auth landscape is in an awkward transitional period. The spec prescribes OAuth 2.1, the ecosystem aspires to it, but the CLI implementations aren't ready. **Bearer tokens via the `Authorization` header are your universal constant** — they work across all three CLIs, align with the MCP spec's token format, and scale from single-user to multi-tenant with minimal architectural changes. The elegance isn't in choosing one protocol over another; it's in building a **token-agnostic validation layer** that accepts API keys and OAuth tokens through the same header, letting you evolve the auth mechanism without changing the server's core authentication logic or breaking any CLI integration. Build the compatibility shim now, implement OAuth 2.1 Resource Server endpoints for the SaaS edition, and let the CLIs catch up to the spec on their own timeline.