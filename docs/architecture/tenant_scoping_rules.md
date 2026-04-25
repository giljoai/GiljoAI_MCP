# Tenant Scoping Rules

*Last updated: 2026-04-23*

This document codifies the rules for tenant scoping in GiljoAI MCP. It is the architecture-level companion to the query-layer discipline enforced by `TenantManager` and the existing 61 property-A regression tests. It was written after the SEC-0005 series (April 2026) uncovered a class of bug — admin-role endpoints that mutate or read tenant-owned data without tenant scope — that the February 2026 audit did not cover.

The rules here are load-bearing. Breaking any of them is a tenant-isolation regression and must be flagged in code review.

---

## Rule 1 — `require_admin` alone is never sufficient for tenant-level endpoints

`Depends(require_admin)` asserts one thing: the authenticated user has `role == "admin"`. It does NOT:

- Extract the user's `tenant_key`.
- Pass `tenant_key` to the service layer.
- Scope any query or mutation.

**Rule:** every endpoint that touches tenant-owned data (rows where `tenant_key` is a meaningful scope) must pair `require_admin` with explicit `tenant_key` scoping at the service layer. The endpoint reads `current_user.tenant_key` (or `request.state.tenant_key`) from the injected `User` and passes it into the service call. The service uses it in every query and every write.

**How to apply:** at code-review time, when you see `Depends(require_admin)` on an endpoint, ask: "does this endpoint touch a model that has a `tenant_key` column?" If yes, the endpoint must pass `current_user.tenant_key` explicitly. If no (the endpoint mutates truly server-global state like `config.yaml`), the endpoint must carry `Depends(require_ce_mode)` and a `# SERVER-LEVEL: <reason>` marker — see Rule 4.

**Reference implementations (canonical examples):**

- SEC-0005a (`917c66d5`) — tenant-scoped user list at `api/endpoints/users.py` (`GET /` filters by `current_user.tenant_key`; 400 on null) and the `GILJO_MODE` admin-menu split that removed the `include_all_tenants=true` cross-tenant enumeration leak.
- SEC-0005b (`13fd2906`) — tenant-scoped `SystemPromptService` at `src/giljo_mcp/system_prompts/service.py`; the orchestrator prompt is now stored per tenant and the override is injected into `_build_orchestrator_response()` at runtime for the correct tenant.
- `src/giljo_mcp/services/tenant_configuration_service.py` and the `/tenant` endpoints in `api/endpoints/configuration.py` (`GET/PUT/DELETE /tenant`) — the canonical tenant-configuration write path.

**Anti-pattern (what SEC-0005 fixed):** the pre-fix `SystemPromptService`, which hardcoded `Configuration.tenant_key.is_(None)` in every method and bypassed the tenant layer entirely despite being admin-gated. Any admin on any tenant overwrote the shared row.

---

## Rule 2 — `Configuration` rows are either tenant-scoped or explicitly whitelisted as system config

The `Configuration` table has `tenant_key String(36) nullable=True`. Nullability is load-bearing — some keys legitimately represent server-wide config (e.g., `config.yaml`-style infrastructure settings). But nullability also creates a footgun: a developer can write a new "global singleton" with `tenant_key=None` and silently leak it across tenants.

**Rule:** every Configuration row belongs to exactly one of two buckets:

- **(a) Tenant-scoped.** `tenant_key = <some uuid>`. All reads and writes filter by tenant.
- **(b) Server-global system config.** `tenant_key = NULL`. Permitted ONLY for keys that are explicitly listed in `SYSTEM_CONFIG_KEYS` (whitelist in the config module). A write to Configuration with `tenant_key=None` for a key not in the whitelist is a bug.

No third bucket. No "sometimes-global-sometimes-tenant" keys. No NULL-as-default fallback.

**How to apply:** when introducing a new Configuration key, ask: "does this value differ per tenant?" If yes, write it tenant-scoped. If no, add the key to `SYSTEM_CONFIG_KEYS` and document why it is server-global in the same commit.

**Current server-global keys (whitelist seed):** the `config.yaml`-backed keys mutated by the SERVER-LEVEL `configuration.py` endpoints (`PUT /key/{key_path}`, `PATCH /`, `POST /reload`, `GET/POST /database`, `POST /database/password`, `GET/POST /ssl`, `GET /health/database`). These mutate in-memory `config.yaml`, the `.env` file, the PostgreSQL role, or SSL certificates on disk — they are intentionally server-wide and gated by `Depends(require_ce_mode)`.

---

## Rule 3 — Every tenant-level endpoint must satisfy property A AND property B with regression tests

- **Property A (isolation):** when `tenant_key` is set, the endpoint's query must filter by it. Tenant A cannot read or write tenant B's rows.
- **Property B (tenant required):** when `tenant_key` is absent (user has no `tenant_key`, or cross-tenant header mismatch), the endpoint must 4xx — NOT silently fall back to "no filter" or NULL.

The Feb 2026 audit validated property A on the 31 core data models. Property B was untested. The SEC-0005 series introduces `tests/security/test_tenant_required.py` (the `TestTenantRequired` regression class) to cover it.

**Rule:** when you add a new tenant-level endpoint, you add a row to BOTH test suites:

- The existing tenant-isolation test file (for property A: tenant A cannot read tenant B).
- `tests/security/test_tenant_required.py` (for property B: endpoint refuses without tenant context).

A PR that adds a tenant-level endpoint without the property-B row should be blocked in review.

**Edge case — per-user tenancy (`POST /auth/register`):** the registration endpoint creates a new tenant per registrant via `TenantManager.generate_tenant_key(username)`. It uses a custom assertion shape rather than the standard "400 when no tenant context" check, because the endpoint legitimately mints a fresh tenant from the caller's tenant context. The custom test verifies the registrant lands in a tenant_key distinct from the admin's. CE installs are protected by the single-user license check (edition == "community" + user count >= 1 → 403).

---

## Rule 4 — Every admin-gated endpoint carries an intent marker

At the endpoint function definition, a one-line comment marker immediately above `@router.<verb>(...)` declares the lane:

- `# TENANT-LEVEL` — endpoint reads `current_user.tenant_key` (or `request.state.tenant_key`) and passes it down. Available in all modes (CE, demo, SaaS).
- `# SERVER-LEVEL: <reason>` — endpoint mutates or reads server-global state. Must ALSO carry `Depends(require_ce_mode)` (404 in demo/SaaS). Reason must be concrete (e.g., "mutates in-memory config.yaml", "ALTER USER on PostgreSQL", "reads server-global SSL paths on disk").

This makes the lane visible at a glance and grep-able for future audits.

**How to apply:** when reviewing a PR that adds or modifies a `Depends(require_admin)` endpoint, require the marker. If the intent is unclear, the PR is not ready to merge.

**Sweep completed:** SEC-0005c Phase 1 applied these markers to all 24 existing admin-gated endpoints across `system_prompts.py`, `users.py`, `user_settings.py`, `configuration.py`, `settings.py`, and `auth.py`. See `handovers/SEC-0005c_sweep_taxonomy.md` for the full two-lane taxonomy table (16 TENANT-LEVEL, 8 SERVER-LEVEL, 0 BROKEN). Bucket (c) — admin-gated endpoints with neither tenant scope nor a `require_ce_mode` gate — is empty after SEC-0005a/b/c.

---

## Rule 5 (invariant) — Role and mode are orthogonal; never tangle them

**Role** controls what a user can do *within their tenant*. Three values: `admin` (of their tenant), `developer`, `viewer`. That is the entire role model. There is no `super_admin`. There is no god-mode. No product role grants cross-tenant visibility or server-level control.

**`GILJO_MODE`** controls what the product exposes at all. Three values:

- `ce` — Community Edition. Single-user self-hosted install. Product shows both product-level and server-level tabs; server-level endpoints are active.
- `demo` — hosted `demo.giljo.ai`. Users register into their own org (one tenant per user). Product shows product-level tabs only. Server-level endpoints return 404 via `require_ce_mode`.
- `saas` — paid SaaS (Solo, future Team). Same tab visibility as Demo. Server-level endpoints 404.

**The two axes never tangle.** A CE admin and a Demo admin both have `role=admin`. They see different tabs because `GILJO_MODE` gates product exposure — NOT because of their role. Same role value, different visibility, by design.

**The SaaS operator is never inside the product.** Server management happens via the external ops panel (tracked as `INF-0002`), a standalone web app separate from the product. The product codebase has no code path that serves the operator as a product user. The operator manages the server the way an SSH user would — just with a nicer visual interface, outside the product's FastAPI router.

**How to apply:** any proposal that adds a new role value, or suggests letting a role read server-level state, or conflates "admin of tenant" with "admin of server" — reject. The fix lives in `GILJO_MODE` gating or in the ops panel, not in the product role model.

**What this invariant prevents:**

- A future "super_admin" role creeping in because "we need someone to see all tenants."
- Server-level endpoints being exposed via role check instead of mode check (the bug SEC-0005a fixed in the user-list endpoint).
- Demo users accidentally seeing server logs or DB config because someone added the tab without a mode gate.
- Cross-tenant dumps being re-introduced by a new admin-only endpoint that forgets to scope by `tenant_key` (the bug class SEC-0005b fixed in `SystemPromptService`).

---

## Reference — the bug class the SEC-0005 series closed

Before SEC-0005:

1. `SystemPromptService` admin endpoints stored the orchestrator prompt with `tenant_key=None` — any admin on any tenant overwrote the shared row, and the override was never injected into the live orchestrator response.
2. `GET /api/v1/users/?include_all_tenants=true` allowed admin-gated users to enumerate admin emails in other tenants.

Both were the same bug class: admin-role gate without tenant-scope pairing. Both slipped through the February 2026 audit because the audit validated property A only.

Both are fixed (SEC-0005a `917c66d5`, SEC-0005b `13fd2906`). The rules above prevent the next one.

---

## Revision history

- 2026-04-23 — finalized after SEC-0005c Phase 1 sweep. Rules 1-5 reflect the shipped model; SEC-0005a and SEC-0005b cited as canonical examples.
- 2026-04-22 — initial draft, SEC-0005 deliverable 6 (in `handovers/SEC-0005_package/tenant_scoping_rules_draft.md`).
