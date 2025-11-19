# Handover 0132: Per-User Tenancy Policy

Status: COMPLETE (2025-11-18)

Objective
- Adopt per-user tenancy by assigning a unique tenant_key on user registration.
- Ensure UI and WS reflect active product changes instantly, tenant-scoped.

Scope
- Backend auth: `/api/auth/register` now generates a tenant_key per user (request value ignored).
- Product lifecycle: Publish EventBus events on activation/deactivation; WS listener broadcasts `product:status:changed` (tenant-scoped).
- Frontend: ActiveProductDisplay refreshes on `product:status:changed`; ProductsView counts by `is_active`.
- Docs updated: CLAUDE.md, AGENTS.md, docs/CHANGES_2025-11-18_PER_USER_TENANCY.md.

Tests
- Integration: `tests/integration/test_user_tenant_isolation.py`
- Integration: `tests/integration/test_product_ws_event.py`

Notes
- Existing tenants not migrated automatically; forward-only policy for new users.
- Optional script provided to clone baseline configuration for a user’s tenant.

