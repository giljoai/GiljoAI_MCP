# Handover 0828: OAuth 2.1 PKCE Flow for MCP Client Authorization

**Date:** 2026-03-19
**From Agent:** Planning Session
**To Agent:** Next Session (tdd-implementor + network-security-engineer)
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Add an OAuth 2.1 Authorization Code + PKCE flow so GUI-based MCP clients (Claude Desktop app connector) can authenticate with the server. This is an **additional** auth method — existing API key and Bearer token auth for CLI tools (Claude Code, Codex, Gemini) remain unchanged.

**Why:** Claude Desktop's "Add custom connector" dialog only supports OAuth, not custom headers. Without this, users cannot connect Claude Desktop to GiljoAI MCP.

**Why CE (not SaaS):** This enables core MCP connectivity for any user including solo. It uses the existing user credential system — no external identity providers (Auth0, LDAP, SAML). SaaS Phase 4 extends this foundation with external SSO providers.

---

## Context and Background

- Claude Desktop requires OAuth 2.1 for its "custom connector" feature (Streamable HTTP MCP servers)
- The `/mcp` endpoint (`api/endpoints/mcp_http.py:998`) currently accepts `X-API-Key` or `Authorization: Bearer <api_key>` — both require custom headers that GUI apps cannot set
- The existing `JWTManager` (`src/giljo_mcp/auth/jwt_manager.py`) already issues HS256 JWTs with tenant_key claims — OAuth tokens will be the same JWT format
- The existing `MCPSession` model already tracks sessions by api_key + tenant — OAuth sessions will follow the same pattern
- First-boot admin creation flow is **unchanged** — OAuth only activates after a user account exists
- User confirmed: fresh install is acceptable (no migration of existing OAuth state needed), but a simple migration script to seed the OAuth client record for existing installs is welcome if trivial
- User directive: "mild number of tests" — surgical coverage of auth flows, not exhaustive

### Cascading Analysis

- **Downstream:** No impact. OAuth issues the same JWT that the system already trusts. Tool execution, tenant isolation, WebSocket events — all unchanged.
- **Upstream:** No impact. Organization, User, Product hierarchy untouched.
- **Sibling:** API key auth and cookie auth continue working. OAuth is additive only.
- **Installation:** `install.py` needs a minor addition to seed the default OAuth client record. Alembic migration adds the `oauth_authorization_codes` table.

---

## Technical Details

### New Files to Create

| File | Purpose |
|------|---------|
| `api/endpoints/oauth.py` | OAuth endpoints: `/oauth/authorize` (GET), `/oauth/token` (POST), `/oauth/client-info` (GET) |
| `src/giljo_mcp/models/oauth.py` | `OAuthAuthorizationCode` model |
| `src/giljo_mcp/services/oauth_service.py` | OAuth business logic (code generation, PKCE verification, token issuance) |
| `frontend/src/views/OAuthAuthorize.vue` | Consent/login page shown when MCP client initiates OAuth |
| `tests/test_oauth.py` | OAuth flow tests |
| `migrations/versions/xxxx_add_oauth_tables.py` | Alembic migration |

### Files to Modify

| File | Change |
|------|--------|
| `api/app.py` | Register OAuth router |
| `api/endpoints/mcp_http.py` | Add OAuth JWT validation alongside API key auth (lines 1021-1046) |
| `api/middleware/auth.py` | Add `/oauth/authorize`, `/oauth/token` to public endpoints whitelist (line 147-163) |
| `src/giljo_mcp/models/__init__.py` | Import `OAuthAuthorizationCode` |
| `frontend/src/router/index.js` | Add `/oauth/authorize` route |
| `install.py` | Seed default OAuth client record on fresh install |

### Database Schema: `oauth_authorization_codes` Table

```python
class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String(128), unique=True, nullable=False, index=True)
    client_id = Column(String(64), nullable=False)  # "giljo-mcp-default" for built-in
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_key = Column(String(64), nullable=False)
    redirect_uri = Column(String(2048), nullable=False)
    code_challenge = Column(String(128), nullable=False)  # PKCE S256
    code_challenge_method = Column(String(10), default="S256")
    scope = Column(String(512), default="mcp")
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 10 min lifetime
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**No `oauth_clients` table needed for now.** The built-in client (`giljo-mcp-default`) is hardcoded — a single constant. SaaS Phase 4 can add a dynamic client registry if needed. This avoids unnecessary schema for a single-client scenario.

### OAuth 2.1 Flow (What Gets Built)

```
1. Claude Desktop calls GET /oauth/authorize?
       response_type=code&
       client_id=giljo-mcp-default&
       redirect_uri=<callback>&
       code_challenge=<S256_hash>&
       code_challenge_method=S256&
       state=<random>

2. Server renders OAuthAuthorize.vue:
   - If user has active JWT cookie → show consent page ("Authorize Claude Desktop?")
   - If no session → show login form, then consent page

3. User clicks "Authorize" → POST submits to backend

4. Backend generates authorization code, stores in DB with PKCE challenge,
   redirects to redirect_uri?code=<code>&state=<state>

5. Claude Desktop calls POST /oauth/token
       grant_type=authorization_code&
       code=<code>&
       client_id=giljo-mcp-default&
       code_verifier=<original_random>&
       redirect_uri=<same_callback>

6. Backend verifies:
   - Code exists + not expired (10 min) + not used
   - PKCE: SHA256(code_verifier) == stored code_challenge
   - redirect_uri matches
   - Marks code as used (one-time)

7. Backend issues JWT access token (same format as existing JWTs)
   with claims: sub, username, role, tenant_key, type="oauth_access"
   Returns: { access_token, token_type: "bearer", expires_in: 86400 }

8. Claude Desktop sends Authorization: Bearer <jwt> with every /mcp request
   → Existing bearer validation in mcp_http.py already handles this
```

### Key Design Decisions

1. **No refresh tokens for v1.** OAuth access tokens expire in 24h (matching existing JWT lifetime). Claude Desktop will re-authorize when token expires. Refresh tokens add complexity with minimal gain for a local MCP connection. SaaS can add refresh tokens later.

2. **Single hardcoded client.** `client_id=giljo-mcp-default` with no client secret (public client per OAuth 2.1 — PKCE replaces secret for native apps). No dynamic client registration needed for CE.

3. **Reuse JWTManager.** OAuth tokens are standard JWTs issued by the same `JWTManager.create_access_token()` with an extra `type=oauth_access` claim. The `/mcp` endpoint already accepts Bearer JWTs — it just needs to validate the new claim type.

4. **Authorization codes in DB, not memory.** Survives server restarts, supports multi-process. 10-minute expiry, one-time use, cleaned up on token exchange.

5. **PKCE mandatory (S256 only).** OAuth 2.1 requires PKCE. Plain code_challenge_method is rejected.

---

## Implementation Plan

### Phase 1: Database + Model (30 min)

1. Create `src/giljo_mcp/models/oauth.py` with `OAuthAuthorizationCode` model
2. Register in `src/giljo_mcp/models/__init__.py`
3. Create Alembic migration
4. Add cleanup job for expired codes (reuse silence_detector's periodic pattern or simple query in token exchange)

**Test:** Migration runs forward/backward cleanly

### Phase 2: OAuth Service (1-2 hours)

1. Create `src/giljo_mcp/services/oauth_service.py`:
   - `generate_authorization_code(user_id, tenant_key, client_id, redirect_uri, code_challenge, scope)` → returns code string
   - `exchange_code_for_token(code, client_id, code_verifier, redirect_uri)` → returns JWT + expiry
   - `verify_pkce(code_verifier, stored_challenge)` → bool (SHA256 comparison)
   - `cleanup_expired_codes()` → deletes codes older than 10 min
   - Built-in client validation: `BUILTIN_CLIENT_ID = "giljo-mcp-default"`
   - Validate redirect_uri against allowlist (localhost + server's own domain)

2. Use existing `JWTManager.create_access_token()` for token issuance

**Tests (Phase 2):**
- `test_generate_code_stores_in_db`
- `test_exchange_valid_code_returns_jwt`
- `test_exchange_expired_code_rejected`
- `test_exchange_used_code_rejected`
- `test_pkce_valid_verifier_accepted`
- `test_pkce_invalid_verifier_rejected`
- `test_invalid_client_id_rejected`

### Phase 3: OAuth Endpoints (1-2 hours)

1. Create `api/endpoints/oauth.py`:
   - `GET /oauth/authorize` — validates params, returns redirect to frontend consent page
   - `POST /oauth/authorize` — processes consent, generates code, redirects to callback
   - `POST /oauth/token` — exchanges code for JWT (standard OAuth token endpoint)
   - `GET /oauth/.well-known/oauth-authorization-server` — metadata endpoint (optional but good practice, helps clients auto-discover)

2. Register router in `api/app.py`

3. Add `/oauth/authorize` and `/oauth/token` to `auth.py` middleware public endpoints whitelist

**Tests (Phase 3):**
- `test_authorize_endpoint_redirects_to_consent`
- `test_token_endpoint_returns_jwt`
- `test_token_endpoint_rejects_bad_pkce`
- `test_full_oauth_flow_e2e` (authorize → consent → code → token → use with /mcp)

### Phase 4: MCP Endpoint Auth Update (30 min)

1. Modify `api/endpoints/mcp_http.py` (lines 1021-1046): When `Authorization: Bearer` is provided, first try JWT validation via `JWTManager.verify_token()`. If valid JWT with tenant_key claim, create/reuse MCPSession from the JWT claims (user_id + tenant_key) instead of API key lookup. Fall back to API key validation if JWT validation fails.

2. This requires a new `MCPSessionManager` method: `get_or_create_session_from_jwt(user_id, tenant_key)` — creates session without api_key_id.

**Tests:**
- `test_mcp_endpoint_accepts_oauth_jwt`
- `test_mcp_endpoint_still_accepts_api_key`

### Phase 5: Frontend Consent Page (1-2 hours)

1. Create `frontend/src/views/OAuthAuthorize.vue`:
   - Simple page: "Authorize [client_name] to access GiljoAI MCP?"
   - Shows: client name, requested scope, user's identity
   - Buttons: "Authorize" / "Deny"
   - If not logged in: show login form first (reuse existing login logic from user store)
   - On authorize: POST to backend, which redirects to callback URI

2. Add route in `frontend/src/router/index.js` — no auth guard (page handles its own auth)

**Test:** Manual verification (consent page renders, authorize redirects correctly)

### Phase 6: Installation Integration (30 min)

1. Update `install.py`: After migration, seed a config entry or just document the built-in client ID. Since the client is hardcoded (no DB table for clients), this is just ensuring the migration runs.

2. **Migration script for existing installs:** The Alembic migration handles the new table. No data migration needed — OAuth is opt-in (users connect Claude Desktop when they want to). Existing API keys continue working.

3. Update config.yaml comments to note OAuth availability.

---

## Testing Requirements

**Target: ~15-20 tests (mild, surgical)**

| Category | Count | Focus |
|----------|-------|-------|
| Unit: OAuthService | 7 | Code generation, PKCE verification, token exchange, expiry, replay |
| Integration: Endpoints | 4 | Authorize flow, token endpoint, error cases, metadata |
| Integration: MCP auth | 2 | OAuth JWT accepted at /mcp, API key still works |
| E2E: Full flow | 1 | Authorize → code → token → MCP tool call |
| **Total** | **~14** | |

---

## Dependencies and Blockers

**Dependencies:** None. All building blocks exist (JWTManager, MCPSession, User model, FastAPI router pattern).

**New Python packages:** None required. `hashlib` (stdlib) handles SHA256 for PKCE. `secrets` (stdlib) generates authorization codes.

**Blockers:** None identified.

---

## Success Criteria

1. User can add GiljoAI MCP as a "custom connector" in Claude Desktop using `http://localhost:7272/oauth/authorize` flow
2. Claude Desktop can list and call MCP tools after OAuth authorization
3. Existing CLI tools (Claude Code, Codex, Gemini) with API key auth continue working with zero changes
4. First-boot admin creation flow is completely unchanged
5. All tests pass, pre-commit hooks pass
6. No new Python dependencies added

---

## Rollback Plan

- Delete the Alembic migration (or run downgrade)
- Remove `oauth.py` endpoint, service, and model files
- Revert the 3-line change in `mcp_http.py`
- Remove `/oauth/*` from middleware whitelist
- Remove frontend route and Vue component

All changes are additive — rollback is clean deletion with no impact on existing functionality.

---

## SaaS Fork Compatibility

This implementation is **specifically designed** to be extended in SaaS Phase 4:

| CE (this handover) | SaaS Phase 4 Extension |
|---------------------|----------------------|
| Hardcoded `giljo-mcp-default` client | Dynamic `oauth_clients` table, client registration API |
| No client secret (public client + PKCE) | Confidential clients with secrets for server-to-server |
| No refresh tokens | Refresh token grant with rotation |
| Local user credentials only | Auth0/Clerk/Keycloak as identity provider |
| Single redirect_uri allowlist | Per-client redirect_uri validation |
| No scopes enforcement | Granular scope-based tool access |

The OAuth endpoints, PKCE verification, and token exchange logic all carry forward unchanged. SaaS just adds more client types and identity sources.
