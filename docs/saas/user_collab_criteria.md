# User Collaboration Criteria

**Purpose:** Track considerations and requirements that must be addressed when building multi-user product collaboration for SaaS edition.

**Edition Scope:** SaaS
**Created:** 2026-03-16
**Status:** Tracking (no implementation yet)

---

## Context

The current system uses **per-user tenant isolation**. Each user gets a unique `tenant_key` generated from their username (`TenantManager.generate_tenant_key(username)` in `auth_service.py:554`). Even users in the same Organization have different `tenant_key` values and are completely isolated from each other's data. The Organization model exists but is effectively a logical grouping — it does not serve as the data isolation boundary.

For SaaS multi-user collaboration, this isolation model must evolve so users within the same organization can share products, projects, and memories.

---

## Items to Address

### 1. Tenant Key Model: Per-User to Per-Org Migration (CRITICAL)
- **Current state:** `tenant_key` is generated per-user. Each user has their own unique key. All data isolation (products, projects, jobs, memories, tasks, templates) filters by this per-user key.
- **Impact:** Users in the same org CANNOT see each other's products, memories, or any data — they are fully isolated even if they belong to the same Organization.
- **Needed for SaaS:** Shift isolation boundary from per-user to per-org. All users in an org should share the same `tenant_key` (the org's key), so they can collaborate on shared products.
- **Risk:** This is a fundamental schema and data migration. Every table with `tenant_key` is affected. Existing single-user CE installations need a migration path.
- **Code locations:** `auth_service.py:554` (user creation), `auth_service.py:776` (admin creation), `TenantManager.generate_tenant_key()`, every model with a `tenant_key` column.
- **Discovered:** 2026-03-16

### 2. Product Invitation / Sharing System
- **Current state:** Products are visible only to the user who created them (per-user tenant_key isolation). No sharing mechanism.
- **Needed:** Once tenant_key is per-org, all org members see all org products by default. Fine-grained access (per-product roles: owner, contributor, viewer) may be needed later.
- **Tables affected:** May need `product_memberships` join table for fine-grained access, or rely on org membership roles.
- **Discovered:** 2026-03-16

### 3. 360 Memory Visibility in Multi-User Context
- **Current state:** `product_memory_entries` filters by `tenant_key + product_id`. Since tenant_key is per-user, each user's 360 memory is fully isolated.
- **After per-org migration:** All org members working on the same product would see ALL memory entries from all org members' project closeouts — this is the correct behavior for shared product knowledge.
- **Desired behavior:** 360 memory should be product-level institutional knowledge shared across all product collaborators. No per-user scoping needed.
- **Discovered:** 2026-03-16

### 4. OrgMembership Roles Not Enforced at Product/Memory Layer
- **Current state:** `OrgMembership` model has roles (owner, admin, member, viewer) but these are NOT checked in `ProductService`, `ProductMemoryRepository`, or context tools.
- **Needed:** Role-based access enforcement when querying products and their children (projects, tasks, memories).
- **Discovered:** 2026-03-16

### 5. Agent/Job Ownership Tracking
- **Current state:** `product_memory_entries.author_*` fields track the AI agent identity, not the human user who triggered the orchestration.
- **Consider:** Adding `initiated_by_user_id` to track which human user's orchestration produced each memory entry. Useful for audit trails in multi-user SaaS.
- **Discovered:** 2026-03-16

---

## Notes

- Items in this document are NOT bugs or security vulnerabilities in the current system
- The per-user tenant_key model is correct for single-user CE — it provides strong isolation
- These are design considerations for future SaaS multi-user features
- Item 1 (per-user to per-org migration) is the foundational change that unblocks all other items
- Each item should be referenced when the relevant SaaS feature handover is created
