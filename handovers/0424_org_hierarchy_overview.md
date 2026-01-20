# Handover 0424: Organization Hierarchy Layer

**Date:** 2026-01-19
**From Agent:** Planning Session
**To Agent:** orchestrator-coordinator / tdd-implementor
**Priority:** HIGH
**Estimated Complexity:** 24-34 hours (5 sub-handovers)
**Status:** Ready for Implementation

---

## Summary

Implement Organization governance layer as foundation for multi-user access and future export/import:

**Current:** `User -> tenant_key -> Products -> Projects`
**Target:** `Organization -> Users (with roles) -> Products -> Projects`

---

## Why This Matters

1. **Multi-user access** - Multiple users can collaborate on products
2. **Product transfer** - Move products between orgs (future)
3. **View-only sharing** - Invite viewers without edit access
4. **Export/Import foundation** - Org-scoped data boundaries (Handover 0425)
5. **Clean isolation model** - `org_id` replaces `tenant_key` for product ownership

---

## Ownership Model Decision

**ORG owns Products** (confirmed by user):
- Products belong to organization, not individual users
- Users access products via org membership + roles
- `tenant_key` becomes org-scoped (org_id = tenant isolation unit)

---

## Sub-Handover Series

| ID | Title | Scope | Est. Hours |
|----|-------|-------|------------|
| **0424a** | Database Schema | Organizations + OrgMemberships tables | 4-6h |
| **0424b** | Service Layer | OrgService + OrgRepository | 6-8h |
| **0424c** | API Endpoints | CRUD + membership management | 4-6h |
| **0424d** | Frontend | Org settings page + member management + UI tweak | 6-8h |
| **0424e** | Migration & Testing | Data migration + E2E verification | 4-6h |

---

## Cascade Impact Analysis

### New Tables (2)

```
organizations
├── id (UUID, PK)
├── name (String, NOT NULL)
├── slug (String, UNIQUE) - URL-friendly identifier
├── created_at
├── updated_at
├── settings (JSONB) - org-level config
└── is_active (Boolean, default=True)

org_memberships
├── id (UUID, PK)
├── org_id (FK -> organizations)
├── user_id (FK -> users)
├── role (String) - 'owner', 'admin', 'member', 'viewer'
├── invited_by (FK -> users, nullable)
├── joined_at
└── is_active (Boolean, default=True)
```

### Modified Tables (5)

| Table | Change | Impact |
|-------|--------|--------|
| `products` | Add `org_id` FK, keep `tenant_key` for backward compat | HIGH - 15+ files |
| `users` | Keep `tenant_key`, add default org on creation | MEDIUM - 5 files |
| `agent_templates` | Add `org_id` for org-level templates | MEDIUM - 8 files |
| `tasks` | Add `org_id` for org-level tasks | MEDIUM - 4 files |
| `projects` | Inherits org from product (no direct `org_id`) | LOW - 2 files |

---

## File Impact Index

### BACKEND - Models (4 files):
```
□ src/giljo_mcp/models/organizations.py (NEW - ~150 lines)
□ src/giljo_mcp/models/__init__.py (add exports)
□ src/giljo_mcp/models/products.py (add org_id FK)
□ src/giljo_mcp/models/templates.py (add org_id FK)
□ src/giljo_mcp/models/tasks.py (add org_id FK)
```

### BACKEND - Services (5 files):
```
□ src/giljo_mcp/services/org_service.py (NEW - ~300 lines)
□ src/giljo_mcp/services/product_service.py (filter by org_id)
□ src/giljo_mcp/services/template_service.py (filter by org_id)
□ src/giljo_mcp/services/auth_service.py (create default org on registration)
□ src/giljo_mcp/services/user_service.py (list users in org)
```

### BACKEND - Repositories (1 file):
```
□ src/giljo_mcp/repositories/org_repository.py (NEW - ~200 lines)
```

### API - Endpoints (5 files):
```
□ api/endpoints/organizations/ (NEW folder)
  ├── crud.py (org CRUD)
  ├── members.py (membership management)
  └── models.py (Pydantic schemas)
□ api/app.py (register org routes)
□ api/auth_utils.py (add org permission checks)
```

### FRONTEND (8 files):
```
□ frontend/src/views/OrganizationSettings.vue (NEW)
□ frontend/src/components/org/MemberList.vue (NEW)
□ frontend/src/components/org/InviteMemberDialog.vue (NEW)
□ frontend/src/stores/orgStore.js (NEW)
□ frontend/src/router/index.js (add org routes)
□ frontend/src/layouts/MainLayout.vue (org context)
□ frontend/src/services/api.js (org API methods)
□ frontend/src/components/DatabaseConnection.vue (button move - UI tweak)
```

### DATABASE - Migrations (1 file):
```
□ migrations/versions/xxxx_add_organizations.py (NEW)
```

### TESTS (6+ files):
```
□ tests/services/test_org_service.py (NEW)
□ tests/api/test_organizations_api.py (NEW)
□ tests/integration/test_org_lifecycle.py (NEW)
□ frontend/tests/unit/components/org/ (NEW)
```

**TOTAL IMPACT:** 30+ files across 5 layers

---

## Permission Model

### Org Roles

| Role | Products | Projects | Templates | Users |
|------|----------|----------|-----------|-------|
| **owner** | CRUD + transfer | CRUD | CRUD | Invite/remove |
| **admin** | CRUD | CRUD | CRUD | Invite members |
| **member** | Read + create own | CRUD on assigned | Read | - |
| **viewer** | Read | Read | Read | - |

### Key Rules
- One owner per org (can transfer ownership)
- Admins can do everything except delete org or remove owner
- Members can create products (becomes org-owned)
- Viewers are read-only across everything

---

## Cascade Diagram

```
CURRENT STATE:
┌─────────────────────────────────────────┐
│  User                                   │
│  └── tenant_key (isolation unit)        │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Products                               │
│  └── tenant_key (owner = single user)   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Projects / Templates / Tasks           │
│  └── tenant_key (inherited)             │
└─────────────────────────────────────────┘

FUTURE STATE (After 0424 Series):
┌─────────────────────────────────────────┐
│  Organizations                          │
│  └── org_id (isolation unit)            │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  OrgMemberships                         │
│  └── user_id + org_id + role            │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Users (multi-org capable)              │
│  └── tenant_key (backward compat)       │
│  └── Can belong to multiple orgs (v2)   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Products                               │
│  └── org_id (org owns products)         │
│  └── tenant_key (deprecated, keep)      │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Projects / Templates / Tasks           │
│  └── org_id (inherited from product)    │
└─────────────────────────────────────────┘
```

---

## Migration Strategy

### Phase 1: Schema Addition (0424a)
1. Create `organizations` table
2. Create `org_memberships` table
3. Add `org_id` columns to products, templates, tasks (nullable initially)

### Phase 2: Backfill (0424e)
For each existing user:
1. Create personal organization with user as owner
2. Set all user's products to belong to that org
3. Set `org_id` on templates and tasks

### Phase 3: Enforcement (post-0424e)
1. Make `org_id` NOT NULL after backfill verified
2. Update queries to filter by `org_id` instead of `tenant_key`
3. Keep `tenant_key` for backward compatibility (deprecate later)

---

## Expected Test Failures After 0424a

After adding org_id columns (initially nullable), NO test failures expected.
Tests only fail after enforcement phase when queries require org_id.

---

## Verification Checklist

### Test Scenarios (0424e)
1. [ ] New user creates account -> default org created
2. [ ] Products created belong to user's org
3. [ ] Admin can invite member to org
4. [ ] Member can view org products
5. [ ] Viewer cannot edit products
6. [ ] Owner can transfer ownership
7. [ ] Existing users migrated with personal org
8. [ ] All existing products moved to user's org

---

## UI Tweak (Include in 0424d)

**Move "Test Connection" button above divider in DatabaseConnection.vue**
- File: `frontend/src/components/DatabaseConnection.vue`
- Change: Move button from below divider to above
- Reason: Better UX flow

---

## Follow-up Handovers

After ORG layer is complete:

| Handover | Scope | Dependencies |
|----------|-------|--------------|
| **0425** | Database Export/Import (org-aware) | 0424 complete |
| **0426** | Multi-org support (user in multiple orgs) | 0424 complete |
| **0427** | Org billing/subscription integration | 0424 + 0426 |

---

## Execution Order

1. **0424a** (Database Schema) - Foundation, no cascades
2. **0424b** (Service Layer) - Business logic after schema exists
3. **0424c** (API Endpoints) - REST interface after services exist
4. **0424d** (Frontend) - UI after API exists
5. **0424e** (Migration & Testing) - Data migration + E2E verification

**Note:** Phases 1-3 can potentially be parallelized by different agents.
Phase 4 (Frontend) depends on API being ready.
Phase 5 (Migration) depends on all code being ready.

---

## Success Criteria

- [ ] Organizations table exists with proper indexes
- [ ] OrgMemberships table with role-based access
- [ ] All existing users have personal organization
- [ ] All existing products belong to user's org
- [ ] API endpoints for org CRUD and membership
- [ ] Frontend UI for org management
- [ ] Test coverage >80% for new code
- [ ] No regressions in existing functionality
- [ ] Manual testing complete for all permission levels

---

## Rollback Plan

If critical issues discovered:
1. `org_id` columns remain nullable - no data loss
2. Queries continue using `tenant_key` until enforcement
3. Drop org tables if needed (clean slate)
4. Revert frontend routes (feature flag if needed)

---

## References

- Plan file: `C:\Users\giljo\.claude\plans\crispy-crafting-stardust.md`
- QUICK_LAUNCH.txt: Section 11 (Refactor Instructions)
- Service patterns: `docs/SERVICES.md`
- Testing patterns: `docs/TESTING.md`
