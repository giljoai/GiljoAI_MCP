# ADR-009 — Single-user tenancy isolation invariant

**Status:** Amended (2026-07-14; supersedes the 2026-06-19 Teams-readiness decision)
**Scope:** Backend architecture / tenancy / edition isolation. Read **before** writing code that touches auth, billing/subscriptions, rate limiting, realtime fan-out, quotas, tenancy, or migrations.

## Context

Teams (multi-user-per-account or multi-user-per-tenant) is **permanently cancelled** for both CE and SaaS (operator directive, 2026-07-14). Neither edition will ship invitations, member administration, shared customer accounts, or an org-scoped tenant model.

A read-only audit (2026-06-19) established the ground truth:

- **`tenant_key` is assigned 1:1 PER-USER.** Each registration mints a fresh `tenant_key` (`auth_service.create_first_admin` / `saas/provisioning/service.py` via `TenantManager.generate_tenant_key`). This is now the permanent model.
- **The org boundary is DORMANT but POPULATED.** `organizations`, `OrgMembership`, `users.org_id`, `products.org_id` exist and are *written* at registration (a 1-user org per user) — but **zero resource queries scope on `org_id`**. Every product/project/task query filters by `tenant_key` only.
- **`tenant_key` == the single user account's isolation boundary.** In hosted SaaS it separates one customer account from every other customer account. In CE it identifies the single local account.
- Existing organization and membership rows are compatibility data from the retired multi-user direction. They are not a commitment to a future product tier and are not the authorization or isolation boundary.

Cancellation of Teams does **not** weaken tenant isolation. A SaaS tenant is still a customer-security boundary even though it contains exactly one user.

## Decision

**`tenant_key` is permanently per-user and remains the isolation boundary. CE and SaaS are permanently single-user-per-tenant products.**

All new work MUST:

1. **Scope every tenant-owned query and mutation by authenticated `tenant_key`.** IDs that appear globally unique do not replace the tenant predicate. Tenant identity never comes from untrusted REST or MCP input.
2. **Treat account-level concerns as TENANT-scoped.** In the permanent single-user model the tenant and account owner are 1:1, but the tenant boundary must stay explicit because it separates SaaS customers and scopes CE data consistently:

   | Area | Unsafe pattern | Required |
   |---|---|---|
   | Billing / subscription (BE-6060d, BE-3005c) | trust a request-supplied user or org identifier | gate the authenticated account's `tenant_key`/subscription row |
   | Rate limits / shared cache (INF-3009d) | key on `user_id` | key on `tenant_key` (optionally + `user_id`) |
   | Realtime fan-out (BE-3008b) | a connection indexed under the wrong tenant | registry and every envelope are keyed and validated by `tenant_key` |
   | Auth (BE-6027) | accept a credential without its tenant/purpose boundary | grants and API keys carry and enforce `tenant_key`; browser, OAuth, and API-key purposes remain distinct |
   | Quotas / counters | use an unscoped global counter | scope counters by `tenant_key` |

3. **Do not build or preserve behavior solely for a future Teams tier.** No invitations, member-management APIs/UI, shared-tenant memberships, role-management product surfaces, seat management, or per-org `tenant_key` flip.
4. **Treat existing `org_id`, `OrgMembership`, role, and organization data as compatibility state.** Do not delete, reinterpret, or stop populating it incidentally. Any simplification requires a dedicated schema/data decision with an idempotent migration or legacy tolerance so existing installations converge safely.
5. **Keep security controls account-complete.** Password/session revocation, API-key revocation, deletion, export, billing, realtime, and quota operations must affect the authenticated tenant account without relying on hypothetical additional members.

Every project's Definition of Done includes a **tenant-isolation check**.

## Permanently out of scope

Team features: invitations, multi-user accounts, member/seat administration, shared-tenant role management, ownership transfer between users, and the per-org `tenant_key` flip. Social login and OAuth are separate authentication capabilities and are not Team features.

## DoD line (paste into every project)

> **Tenant isolation:** Does every tenant-owned read, write, event, credential, cache key, rate limit, and lifecycle operation derive and enforce the authenticated `tenant_key`? Does any path trust a client-supplied tenant or create a cross-tenant relationship? If so, fix it at the owning boundary. Teams is permanently cancelled; do not add multi-user scaffolding. (ADR-009)

## Consequences

- **Positive:** product and authorization design can target the permanent single-user model without speculative Team-tier complexity.
- **Positive:** strict `tenant_key` enforcement continues to protect SaaS customers from one another and keeps CE data consistently scoped.
- **Cost:** existing org/membership compatibility data remains until a dedicated simplification project proves a safe migration path.
- **Risk if ignored:** cancellation of Teams could be misread as permission to weaken cross-tenant isolation, exposing one hosted customer's data or events to another.

## Evidence (audit 2026-06-19)

`auth_service.py:893` (per-user tenant mint) - `saas/provisioning/service.py:104` - `product_repository.py:190` (tenant_key-only scope) - `models/auth.py` (org_id nullable, tenant_key non-null) - `api/endpoints/organizations/crud.py:154` (1:1 user->org assumption) - `handovers/completed/0424f_codex_project_review-C.md` (historical future-org direction, now superseded by the 2026-07-14 cancellation directive).
