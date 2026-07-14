# ADR-003: Frontend API URL Composition Enforcement

**Status:** Accepted
**Date:** 2026-05-13
**Edition Scope:** Both (CE and SaaS)

---

## Context

ADR-001 established `@/composables/useApiUrl` as the single resolver for API
and WebSocket URLs after the 2026-04-21 demo go-live failure. At the time of
that decision, the fix was applied to the known offending files but no
automated gate existed to prevent the anti-pattern from being reintroduced.

During the IMP-0013 quality sweep (2026-05-13), the codebase was audited for
any remaining `${protocol}://${host}:${port}` or `${host}:${port}` template
literals that compose URLs directly from raw config fields. The audit found
four files where the pattern was intentionally present (the resolver itself
and three legitimate user-facing config-paste surfaces) and confirmed all
HTTP-client paths flow through `useApiUrl`. The distinction between
"resolver/wizard" sites and "HTTP client" sites is not obvious to a new
contributor; without a lint rule it would be re-violated on any refactor that
touches `configService` or adds a new HTTP client.

The audit also removed three unused `configService` methods
(`getApiBaseUrl()`, `getWebSocketUrl()`, and a related import) that had been
superseded by `useApiUrl` but not yet deleted (commits `f3601db67` and
`6a39513f4`).

---

## Decision

**An ESLint rule (`no-manual-api-url-composition`) MUST flag any template
literal or string concatenation that composes a URL from two or more of
`protocol`, `host`, and `port` config fields outside the allowlisted files.**

The allowlist is encoded in the rule via inline suppression comments
(`// giljo-allow: url-composition`) and is restricted to exactly four files:

- `frontend/src/composables/useMcpConfig.js` — builds a literal MCP-server
  URL string for AI-tool configuration snippets, not the frontend's own HTTP
  client base.
- `frontend/src/config/api.js` — the Axios instance base-URL resolver.
- `frontend/src/views/DashboardView.vue` — renders the server URL for the
  user's copy-paste config display.
- `frontend/src/views/Login.vue` — renders the server address in an
  informational callout.

All four sites are annotated with a comment explaining why they are exempt.
Any new allowlist entry requires a corresponding comment at the call site and
an update to the rule's documentation.

The rule operates at `error` level in `eslint.config.js`. The `npm run lint`
step runs in Tier-1 CI (every push to master) and in the
`merge_to_public.sh` preflight, so violations block both private-origin and
public-export paths.

### Anti-pattern (banned outside allowlist)

```js
// BANNED: composes URL from config fields — breaks behind any reverse proxy
const base = `${config.api.protocol}://${config.api.host}:${config.api.port}`
const ws   = `ws://${host}:${port}`
```

### Required pattern

```js
import { getApiBaseUrl, getWsBaseUrl } from '@/composables/useApiUrl'

const base = getApiBaseUrl()  // '' in Vite dev, full origin in prod
const ws   = getWsBaseUrl()   // '' in Vite dev, wss:// in prod
```

---

## Rationale

ADR-001 documents why manual URL composition breaks behind reverse proxies;
this ADR records the decision to enforce that rule automatically rather than
relying on code review alone. The allowlist approach was chosen over an
outright ban because the resolver and wizard surfaces genuinely need access to
raw config fields — an outright ban would have required restructuring
`useMcpConfig.js` for no gain.

A rule without an allowlist would produce false positives on the four
legitimate sites, causing lint to fail on clean code. A rule with an
undocumented allowlist would silently excuse violations. The combination of
an in-file suppression comment plus rule-level documentation makes the
exception visible at both the call site and the rule definition.

---

## Consequences

**Positive:**
- Any attempt to compose a URL manually in a new file or in a refactored
  version of an existing file is caught at `npm run lint` before CI runs.
- The four allowlisted sites are self-documenting: the suppression comment
  at the call site explains the exemption to the next reader.
- Removal of the three dead `configService` methods (`f3601db67`,
  `6a39513f4`) reduces the surface area that future contributors might reach
  for, shrinking the likelihood of accidental anti-pattern reuse.

**Negative:**
- The allowlist is static in the rule file; adding a new legitimate site
  requires a rule source edit (intentional friction).
- The rule is heuristic (pattern-match on template literals); a developer
  could circumvent it with string concatenation using `+`. The rule should be
  extended if that pattern is observed in practice.

---

## References

- ADR-001: `docs/adr/ADR-001-frontend-url-resolution.md` (original
  architectural decision; this ADR adds enforcement only)
- ESLint rule: `frontend/eslint-rules/rules/no-manual-api-url-composition.cjs`
- Allowlisted files annotated: commits `2eb43e7db` (rule + annotations),
  `f3601db67` (dead import removals), `6a39513f4` (dead method deletions +
  `useMcpConfig.js` comment)
- Root-cause fix: `9696c4563` (`fix(frontend): centralize API URL composition
  to fix demo Cloudflare Tunnel`, 2026-04-21)
- IMP-0013 quality sweep audit: `198b2e6d9`
