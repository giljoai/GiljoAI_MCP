# ADR-009 — Teams-readiness tenancy invariant

**Status:** Accepted (2026-06-19)
**Scope:** Backend architecture / tenancy / edition isolation. Read **before** writing code that touches auth, billing/subscriptions, rate limiting, realtime fan-out, quotas, tenancy, or migrations.

## Context

Teams (multi-user-per-account) is an **intentionally postponed** product expansion (operator directive, 2026-06-19). We keep building **every other** project — but nothing we build may **block** a future Teams architecture.

A read-only audit (2026-06-19) established the ground truth:

- **`tenant_key` is assigned 1:1 PER-USER today.** Each registration mints a fresh `tenant_key` (`auth_service.create_first_admin` / `saas/provisioning/service.py` via `TenantManager.generate_tenant_key`).
- **The org boundary is DORMANT but POPULATED.** `organizations`, `OrgMembership`, `users.org_id`, `products.org_id` exist and are *written* at registration (a 1-user org per user) — but **zero resource queries scope on `org_id`**. Every product/project/task query filters by `tenant_key` only.
- So today **`tenant_key` == user identity**, and the org scaffolding is forward-looking structure, not load-bearing logic.
- Flipping to "tenant = org" (mint one `tenant_key` per org, members inherit it) is ~60-100 files. **That flip IS the postponed Teams migration** — we do NOT do it now.

Key realization: because all resources already scope by `tenant_key`, **when the flip later redefines `tenant_key` from "user" to "org," those queries become org-correct for free.** The only things that would *block* the flip are NEW per-user assumptions for account-level concerns. So a guardrail invariant — not a skeleton build — is sufficient.

## Decision

**`tenant_key` is the isolation boundary. It is per-USER today and BECOMES per-ORG at the postponed Teams flip. `user` is an actor WITHIN a tenant (via `users.org_id` + `OrgMembership`). Never collapse `user == tenant` in NEW code.**

All new work MUST:

1. **Scope every query by `tenant_key`** (already the rule) — makes it org-correct after the flip, for free.
2. **Treat account-level concerns as TENANT-scoped, never per-user** (a future Team = one tenant, many users):

   | Area | Trap (blocks Teams) | Required |
   |---|---|---|
   | Billing / subscription (BE-6060d, BE-3005c) | gate per-`user_id` | gate per-`tenant_key`/org (`OrganizationPlan`) — one sub covers all members |
   | Rate limits / shared cache (INF-3009d) | key on `user_id` | key on `tenant_key` (optionally + `user_id`) |
   | Realtime fan-out (BE-3008b) | 1 socket per tenant | registry = `tenant_key -> SET of connections`; broadcast to all |
   | Auth (BE-6027) | assume `user == tenant` | OAuth client stays **global + grant-carries-tenant** (do NOT re-scope); API keys stay `user_id + tenant_key` |
   | Quotas / counters | per-user | per-tenant |

3. **Keep populating `org_id` + `OrgMembership` at registration, and NEVER delete the org scaffolding** even though Solo doesn't use it for scoping — it is the dormant Teams foundation. A migration squash (INF-5060) MUST preserve it.
4. **Support both tenant-level AND user-level granularity** where cheap (e.g. security kill-switches SEC-3001a — revoke a member OR a whole account).

Every project's Definition of Done includes a **Teams-readiness check**.

## Out of scope (HELD — do NOT build)

Team *features*: invitations, roles/permissions UI, member management, social-login, the per-org `tenant_key` flip itself. This ADR keeps the door open; it does not walk through it.

## DoD line (paste into every project)

> **Teams-readiness:** Does this gate/scope per-`user_id` where it should be account/tenant-level? Assume 1-user-per-tenant or 1-socket-per-tenant? Preserve `org_id`/`OrgMembership`? If any — fix the dimension to `tenant_key`. (ADR-009)

## Consequences

- **Positive:** non-Team work proceeds at full speed; nothing reworks when Teams ships (the flip just redefines `tenant_key`; resources are already tenant-scoped).
- **Cost:** a small standing discipline (the DoD check) on account-level features.
- **Risk if ignored:** one per-user subscription gate or a 1-socket-per-tenant registry forces a rewrite when Teams lands.

## Evidence (audit 2026-06-19)

`auth_service.py:893` (per-user tenant mint) - `saas/provisioning/service.py:104` - `product_repository.py:190` (tenant_key-only scope) - `models/auth.py` (org_id nullable, tenant_key non-null) - `api/endpoints/organizations/crud.py:154` (1:1 user->org assumption) - `handovers/completed/0424f_codex_project_review-C.md` (Option A "org==tenant_key" documented as the future refactor). Supersedes the aspirational "use organizations for tenant key discovery" reading of `CLAUDE.md` and the "single implicit org" note in `EDITION_ISOLATION_GUIDE.md` — both reconciled to point here.
