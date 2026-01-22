# 0424 Codex Project Review (Org Hierarchy Refactor)

**Date:** 2026-01-20  
**Scope:** Review + gap analysis for `handovers/0424_org_hierarchy_overview.md` + `0424a–0424e` against current repo state.  
**Goal:** Reduce “whack-a-mole” by surfacing architectural conflicts, missing decisions, high-risk touchpoints, and a safer sequencing strategy before implementation.

---

## Executive Summary (What I Found)

- The 0424 Organization layer **is not implemented** in the current codebase (no `Organization`, `OrgMembership`, `OrgService`, org endpoints, etc.).
- The current architecture is **deeply tenant-key centric** (multi-tenant isolation is enforced everywhere via `tenant_key`).
- The 0424 plan assumes a shift to **org-owned products** and “org_id replaces tenant_key for ownership”, but the repo’s architecture + docs currently treat **tenant_key as the isolation boundary** (and many services/repositories enforce it as a security requirement).
- Tooling quality gates are not currently “green”:
  - `ruff check src` reports **~2084 issues** (so it’s not usable as a hard gate yet without a strategy).
  - `black --check src` would reformat **122 files** (so formatting the whole repo would be a massive diff).
  - `pytest` currently fails early due to a broken import (`tests/test_mcp_server.py` imports a missing `src.giljo_mcp.server` module). Also, pytest output capturing hit a `ValueError` on Python 3.14 unless run with `-s`.

**Bottom line:** 0424 is feasible, but only if you first resolve the tenancy model conflict and adopt an incremental migration strategy that respects how pervasive `tenant_key` is today.

---

## Critical Design Conflicts / Missing Decisions

### 1) “tenant_key” meaning vs 0424 org model (blocking decision)

**Current repo reality**
- `tenant_key` is used as the **primary isolation boundary** across models/services/endpoints. Some base patterns explicitly state: “CRITICAL: Always filter by tenant_key”.
- Many tables store `tenant_key` directly (not just products), so “sharing products across users” is not just a products-table change.

**0424 goal**
- Organization → Users → Products → Projects (multi-user collaboration, roles, product transfer).

**You need an explicit decision:**

**Option A (lowest blast radius): “Org == tenant_key (for now)”**
- `tenant_key` remains the *technical* isolation boundary, but now represents the organization/account.
- All users in an org share the same `tenant_key`; org membership + roles control access.
- Keeps most existing filtering/eventing intact (services/repos/websocket broadcasts already key off `tenant_key`).
- Caveat: multi-org-per-user requires additional work later (but you already list this as 0426).

**Option B (largest refactor): Keep tenant_key per user, add org_id everywhere that must be shared**
- Add `org_id` and change access control to be membership-based.
- Requires updating a large portion of the codebase because projects/tasks/agent-jobs/messages/etc are currently filtered by `tenant_key`.
- Requires a durable “active org” context for API + MCP (see next section).

If you proceed without picking A or B, you will get exactly the whack-a-mole scenario you’re trying to avoid.

---

## Refined Proposal (from discussion): “Org == tenant_key”, but future-proof

This is the “simple now” version that still supports your stated ambitions:
- Each user can create products/projects, launch agents/jobs, and manage their own templates.
- Tasks behave like an org-scoped “technical debt repo” that can be converted to projects.
- Future: multiple users share a product, viewers exist, org/user statistics, auditability, and product transfer when someone leaves.

### SaaS separation at scale (50–60 orgs, 1000 users)

Repurposing `tenant_key` is *how* you separate organizations cleanly in a hosted SaaS model:

- **Each org gets a unique `tenant_key`** (opaque, server-generated).
- **All org-owned rows carry that `tenant_key`** (users, products, projects, tasks, templates, jobs, messages, etc.).
- **All queries filter by `tenant_key`** (this becomes the DB “firewall” between orgs).
- WebSocket fanout naturally becomes “org rooms” because the system already broadcasts by tenant_key.

This is the classic multi-tenant approach: org boundary = partition key. Your current codebase already leans heavily into it.

### Non-negotiables (so hosted mode + auditability don’t break later)

1) **Tenant resolution must be server-derived (not client-supplied)**
   - For hosted service safety, don’t trust `X-Tenant-Key` from the browser.
   - Tenant/org should come from authenticated identity (JWT/API key) + membership, not arbitrary headers.

2) **Add per-user attribution fields to key entities**
   - Minimum: `created_by_user_id` on products/projects/tasks/agent jobs/executions/templates/messages.
   - Optional: `updated_by_user_id` and/or a lightweight audit log table for high-value events.

3) **Use org membership roles for permissions; keep “system role” separate**
   - Org roles (`owner/admin/member/viewer`) decide what users can do inside an org.
   - Existing `User.role` (`admin/developer/viewer`) becomes “instance/global” authority (e.g., support staff, superadmin).

### How your desired behavior maps cleanly

- **Products**: org-scoped via `tenant_key`, but track `created_by_user_id` and optionally a per-product ACL later.
- **Projects**: org-scoped; `created_by_user_id` enables per-user stats and attribution.
- **Agent templates**: org-scoped, but UI defaults to “my templates” (`created_by_user_id == me`), with optional sharing toggles later.
- **Tasks (tech debt repo)**: org-scoped, created/owned by user; conversions preserve attribution.
- **Viewer users**: org membership role gates “create project”, “launch agent”, “edit product”, etc.

### Why this reduces whack-a-mole now

It preserves the repo’s deepest assumption: **tenant isolation is enforced everywhere**. You introduce collaboration by moving from “per-user tenant” to “per-org tenant” rather than rewriting every query to join via org membership.

---

## Keys & Authentication Model (clarifying “tenant key vs user key”)

This is the clean mental model to use when rewriting 0424:

### 1) `tenant_key` becomes the org key (partition key)

- `users.tenant_key` already exists in the repo today.
- Under this proposal, **`users.tenant_key` == the organization’s tenant key** (all employees share it).
- `tenant_key` is used for:
  - DB isolation filters (`WHERE tenant_key = ...`)
  - scoping WebSocket broadcasts/rooms (org-wide updates)
  - scoping “single active product” constraints (org-wide behavior)

### 2) The “user key” is the authenticated identity (user_id), not a separate header

- Users are identified by `users.id` (UUID-like string).
- **API keys are per-user licenses**: `api_keys.user_id` points to the user.
- JWT cookies also identify the user (`sub = user_id`).

### 3) How REST + MCP should work (hosted-safe)

**REST (dashboard)**
- Client authenticates via JWT cookie (or bearer JWT).
- Server loads `User` by `user_id`, then derives `tenant_key` from the user row.
- Client should not be able to “choose” tenant by header; the server enforces it.

**MCP `/mcp` (HTTP JSON-RPC)**
- Client authenticates with `X-API-Key` (or `Authorization: Bearer <token>` as a fallback for some transports).
- Server validates the API key → resolves the **user** → derives the **org tenant_key**.
- The session layer (`MCPSession`) can store `tenant_key` for continuity across tool calls.

### 4) Do we “add tenant_key to all MCP tool calls”?

Generally **no** for hosted safety:
- Tools should not require clients to pass `tenant_key` as an argument.
- The tool layer should obtain tenant scope from the authenticated session/request context.

If some internal tool functions currently accept `tenant_key` arguments, treat those as *internal plumbing* and ensure they come from the server-side context, not user input.

### 5) The real refactor change: stop generating per-user tenants

Today, user registration logic generates a brand-new tenant per created user.
For “org = tenant”:
- First org admin creation generates the org tenant_key once.
- Subsequent users created by org admin **inherit the admin’s tenant_key**.

This is the change that makes “invite employees to products” and “shared org resources” work without rewriting every service.

### 2) “Active org” context for requests + MCP sessions (needs a plan)

Even in “single-org now, multi-org later”, invitations/memberships imply users may eventually access multiple orgs.

You need to define where “current org” lives:
- REST: header (e.g., `X-Org-Id`), cookie, or derived from “active product”.
- MCP `/mcp`: `MCPSession` currently preserves `tenant_key` + `project_id`. If org is introduced, decide whether sessions preserve `org_id` and how tools infer it.

Without this, permissions + filtering become inconsistent across UI vs MCP tool calls.

### 3) Two different “role” systems (system vs org)

Current user model has `role IN ('admin','developer','viewer')`.  
0424 introduces org roles: `owner/admin/member/viewer`.

Decide:
- Are org roles the only thing controlling product/project access (recommended)?
- What does system `admin` mean after orgs exist? (global server admin vs org admin)

### 4) Deletion semantics: What happens to products/projects on org delete?

0424a suggests `ondelete="SET NULL"` for `products.org_id` (and similar for templates/tasks).

This creates “orphaned” resources unless you:
- prohibit org deletion when data exists (`RESTRICT`), or
- cascade delete/soft-delete everything under an org, or
- implement an explicit “transfer products before delete” workflow.

This needs to be specified before writing migrations.

### 5) Data duplication risk (org_id stored vs derived)

Storing `org_id` on tables that already have a path to product (and product→org) can create **consistency drift**.

Example:
- `tasks` already has `product_id` and/or `project_id`. If `org_id` is added, you must ensure it always matches the product’s org.

Suggested approach:
- Store `org_id` only where you cannot derive it (e.g., truly org-level records that don’t reference a product/project).
- Otherwise, derive via joins.

---

## Scope Reality Check (Why 0424 touches more than “30 files”)

- There are ~11k references to `tenant_key` across `src/`, `api/`, and `tests/`.
- Models beyond `products/templates/tasks/projects` are tenant-scoped today (examples: sessions, messages, agent jobs, context indexes, settings/config).

If you choose Option B (org-based access while keeping per-user tenant isolation), you will need to audit and adjust:
- every place that filters shared entities by `tenant_key`
- every WebSocket event broadcast keyed by tenant_key
- every “active product per tenant” constraint (currently per `tenant_key`)

If you choose Option A (“org == tenant”), you can keep most of that intact and layer in roles.

---

## Frontend Plan Gaps (0424d)

### API client mismatch
The proposed `orgStore.js` uses:
- `import api from '@/services/api'` and then calls `api.get(...)`

But `frontend/src/services/api.js` exports an object of grouped methods (`api.products.list`, etc.), not an axios instance with `.get()/.post()`.

Fix direction:
- Add `api.organizations = { list/create/get/update/delete/... }` methods inside `frontend/src/services/api.js`, then call those from the store.

### User ID / role lookup
The plan uses `localStorage.getItem('userId')`, but the current app uses `useUserStore()` and stores the current user in-memory (`currentUser.value`), and sets tenant key for requests via `setTenantKey(currentUser.tenant_key)`.

Fix direction:
- derive user id from `useUserStore().currentUser.id`

### Endpoint paths
Repo patterns heavily use `/api/v1/...` for REST (mixed with some `/api/...` legacy endpoints).  
0424c suggests `/api/organizations...`. Either is fine, but pick one and keep frontend/backend aligned.

---

## Tooling + Test Health (Pre-flight Recommendations)

### Pytest is not currently a reliable “safety net”
- `pytest -x -s` fails in collection due to `tests/test_mcp_server.py` importing missing `src.giljo_mcp.server`.
- Pytest output capturing crashed under Python 3.14 without `-s`.

Recommendation:
- Fix/skip the broken test import before starting 0424 (otherwise every change is “is it my refactor or baseline broken?”).
- Consider pinning a stable Python version (repo docs recommend 3.11+; running 3.14 is likely to create surprises).

### Ruff/Black are currently “too loud” to be hard gates
- `ruff check src` reports ~2084 issues.
- `black --check src` would reformat 122 files.

Recommendation:
- Enforce formatting/linting only for *new* org files + files you touch in 0424.
- Optionally add a CI step that runs ruff/black on a file list (git diff) rather than the entire repo until legacy is cleaned up.

---

## Safer Implementation Strategy (Minimize Whack-a-Mole)

### Phase 0 (Decision + contract)
- Pick tenancy option (A or B) and document it.
- Define “active org” rule for REST + MCP.
- Define org deletion/transfer semantics.

### Phase 1 (Schema-only, no behavioral change)
- Add `organizations`, `org_memberships` (+ required indexes/constraints).
- Avoid changing product/service filters yet.
- Add minimal tests for constraints/relationships.

### Phase 2 (Org creation + membership plumbing)
- On user creation (first admin + later users), create:
  - org (or attach to existing org depending on Option A/B)
  - org membership (owner/admin)
- Add service + endpoint for “list my orgs” and “get org members”.
- Add tests for membership + permissions.

### Phase 3 (Adopt org scoping for products/tasks/templates incrementally)
- If Option A: keep tenant_key filters, add role checks and org metadata.
- If Option B: introduce org-based filtering behind a feature flag and migrate one vertical slice at a time (products → projects → tasks → templates → agent jobs).

### Phase 4 (Frontend)
- Add org settings UI only after backend contracts are stable.
- Ensure tenant/org headers and selection behavior are consistent with MCP + REST.

### Phase 5 (Migration + verification)
- Add idempotent migration script and/or one-time migration command.
- Add E2E tests for:
  - org creation
  - member role enforcement
  - product visibility/edit rights
  - WebSocket updates reaching the right audience

---

## Concrete Technical Recommendations for 0424 Specs

### DB schema
- Make `organizations.slug` uniqueness case-insensitive (Postgres: functional unique index on `lower(slug)`), or enforce slug normalization strictly.
- Add `ondelete` behavior intentionally:
  - memberships: likely `CASCADE` on org delete
  - products: likely `RESTRICT` or soft delete, not `SET NULL` long-term
- Prefer explicit `Enum`/`CheckConstraint` for membership roles (you already use `CheckConstraint` for user roles).

### Services + repos
- Create an “OrgContext” helper/dependency that resolves:
  - current user
  - org_id (or tenant_key mapping)
  - membership role
- Do not copy/paste tenant filtering patterns into org filtering without first deciding A vs B.

### API
- Align route prefixing (`/api/v1/...` vs `/api/...`) and reuse existing dependency injection patterns (like `api/endpoints/products/dependencies.py`).
- Return consistent error shapes/status codes (your app has a global HTTPException handler that wraps `detail` already).

### Frontend
- Add org API methods to `frontend/src/services/api.js` instead of raw axios calls in stores.
- Derive current user from `frontend/src/stores/user.js`, not localStorage.

---

## Actionable “Before You Start Coding 0424” Checklist

- [ ] Decide whether org == tenant (Option A) or org_id-based access (Option B)
- [ ] Define active org selection for REST + MCP sessions
- [ ] Define deletion/transfer semantics (org delete behavior)
- [ ] Fix baseline pytest collection failure (`tests/test_mcp_server.py` import)
- [ ] Decide lint/format strategy (new files only vs repo-wide)
- [ ] Add a migration + rollback strategy that matches Alembic-first workflow

---

## Appendix: Commands I Ran (for reproducibility)

- Compile check: `python -m compileall -q src api`
- Ruff: `venv\\Scripts\\ruff.exe check src`
- Black: `venv\\Scripts\\black.exe --check src`
- Pytest: `venv\\Scripts\\pytest.exe -q -x -s` (fails on `tests/test_mcp_server.py`)

---

## If You Still Want “Full Blast Now” (Option B) — What It Really Requires

You *can* do it now (being pre-release is a valid reason), but to avoid the exact blast radius you’re worried about, you need containment:

### What “full blast” actually means in this repo

To make org membership the access boundary (while tenant_key stays per-user), you must systematically replace:
- **filters**: `Model.tenant_key == self.tenant_key` → org-aware filters
- **broadcast scopes**: websocket “tenant rooms” → org rooms
- **constraints**: “single active product per tenant” → “single active product per org”
- **MCP sessions**: session context must persist org identity and tools must enforce org scoping

If you only change `products` and a few services, you will leak/lose data or deny legitimate access because other subsystems will still gate by tenant_key.

### Containment strategy (so you don’t rewrite 11k references)

If you pursue Option B, the safest pattern is:

1) **Introduce an `OrgContext` abstraction early**
   - “current_org_id”, “current_user_id”, “role”, and “is_system_admin”.
   - One place to resolve org from request/JWT/API key, not sprinkled across endpoints.

2) **Do a vertical slice with a feature flag**
   - Start with: org endpoints + org membership + org-scoped product listing/creation.
   - Keep the rest of the system tenant-key based until each subsystem is migrated.
   - This avoids half-migrated state where products are org-scoped but tasks/agents still use tenant_key.

3) **Plan and execute a table-by-table scoping map**
   - Decide which tables become org-scoped vs remain user-scoped vs derived via product/project joins.
   - Avoid adding `org_id` redundantly where it can drift (prefer derived-by-join).

4) **Rewrite tests to assert “org boundary” instead of “tenant boundary”**
   - Otherwise you’ll “fix the code” but break the suite because the suite encodes the old tenancy model.

### Key question that determines if full blast is worth it

Do you want **multi-org-per-user** *soon*, or is it firmly “later”?  
If it’s later, Option A gets you 80% of the product goals with ~20% of the refactor risk.  
If it’s soon, Option B may be justified now, but only if you commit to the containment strategy above.
