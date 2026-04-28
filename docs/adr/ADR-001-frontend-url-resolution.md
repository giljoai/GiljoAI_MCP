# ADR-001: Frontend URL Resolution

**Status:** Accepted
**Date:** 2026-04-28
**Edition Scope:** Both (CE and SaaS)

---

## Context

The frontend historically composed API and WebSocket URLs by reading `host`,
`port`, and `protocol` fields from `/api/v1/config/frontend` and building
strings like `${protocol}://${host}:${port}`. This works on a developer
machine where the browser and server share the same host, but breaks the
moment any proxy sits between them.

On 2026-04-21 (demo go-live), six chained routing and loading bugs were
traced to this pattern. The proxied deployment (`demo.giljo.ai` via
Cloudflare Tunnel) exposed the internal address (`10.1.0.x:7272`) to the
browser. The browser received a host it could not reach, producing CORS
failures, mixed-content blocks, and unreachable-host errors.

The fix introduced `@/composables/useApiUrl` as the single resolver.
`configService` still reads the raw config fields, but only the two resolver
composables are permitted to compose full URLs from them.

The affected files that were migrated away from the anti-pattern:
- `frontend/src/router/index.js`
- `frontend/src/main.js`
- `frontend/src/layouts/DefaultLayout.vue`
- `frontend/src/views/Login.vue`
- `frontend/src/saas/views/RegisterView.vue` (SaaS-only, rule still applies)
- `frontend/src/saas/views/PasswordResetPage.vue` (SaaS-only)
- `frontend/src/saas/components/ForgotPasswordEmail.vue` (SaaS-only)
- `frontend/src/components/navigation/NavigationDrawer.vue`

---

## Decision

**All API and WebSocket URL composition in frontend code MUST use
`getApiBaseUrl()` and `getWsBaseUrl()` from `@/composables/useApiUrl`.**

Resolution order (see the composable for the authoritative comment):
1. `VITE_API_URL` env var (absolute URL, used verbatim — demo mode).
2. `window.API_BASE_URL` runtime override.
3. Empty string in Vite dev mode (Vite proxy handles `/api` and `/ws`).
4. `window.location.origin` same-origin fallback (CE prod, SaaS subdomains).

`VITE_API_PORT` MUST NOT be concatenated with any of the above. If a
non-standard port is needed, set `VITE_API_URL=http://host:port` explicitly.

WebSocket base is always derived from the API base via scheme substitution
(`http` → `ws`, `https` → `wss`). Do not compose WebSocket URLs independently.

### Anti-pattern (banned)

```js
// BANNED: reads internal fields, breaks behind any reverse proxy
const url = `${config.api.protocol}://${config.api.host}:${config.api.port}`
```

### Required pattern

```js
import { getApiBaseUrl, getWsBaseUrl } from '@/composables/useApiUrl'

const apiBase = getApiBaseUrl()   // '' in dev, full origin in prod
const wsBase  = getWsBaseUrl()    // '' in dev, ws(s):// in prod
```

---

## Consequences

**Positive:**
- Same-origin resolution works uniformly for CE localhost, LAN, demo via
  tunnel, and SaaS subdomains without per-deployment config.
- `VITE_API_URL` gives the demo build a single override point.
- Internal host:port fields never reach the browser as composed URLs.

**Negative:**
- Two files are legitimately exempt (see Exceptions). Future developers must
  know these are the resolver implementations, not violations.

---

## Exceptions

Exactly two files may compose URLs from raw config fields, because they ARE
the resolvers that `useApiUrl` and the MCP config wizard build on:

1. `frontend/src/composables/useApiUrl.js` — the canonical resolver.
2. `frontend/src/services/configService.js` (around line 143-145) —
   `getApiBaseUrl()` on `ConfigService` composes from raw config for the MCP
   wizard's server-URL heuristic. This is the only sanctioned site.

No other file may compose `${protocol}://${host}:${port}` from config fields.

---

## References

- Root-cause commit: `92ddabe6b` (`fix(frontend): unblock demo go-live -- 6 chained routing/loading bugs`, 2026-04-21)
- Canonical resolver: `frontend/src/composables/useApiUrl.js`
- Sanctioned exception: `frontend/src/services/configService.js:143-145`
- Sanctioned exception: `frontend/src/composables/useMcpConfig.js` (server-URL heuristic)
