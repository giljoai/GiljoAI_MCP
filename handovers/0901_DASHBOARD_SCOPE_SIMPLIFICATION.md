# Handover 0901: Dashboard Scope Simplification

**Date:** 2026-04-03
**Edition Scope:** CE
**Priority:** Low
**Estimated Complexity:** 1 hour
**Status:** Completed

---

## Task Summary

Remove the product selector (filter buttons) from the CE dashboard. The dashboard should show all tenant-level activity — no per-product or per-project filtering. The current "All Products" / individual product filter chips at the top of DashboardView are unnecessary for CE where a single user manages everything.

**SaaS note:** Per-org/per-user productivity metrics may be added on the `saas` branch later as an admin/viewer feature. This is CE-only simplification.

---

## What to Remove

### Frontend: `DashboardView.vue`

1. **Remove the `ProductSelector` component** and its import
2. **Remove `selectedProductId` / `selectedProductName`** refs and all filtering logic that branches on product selection
3. **Simplify the data fetch** — always call the dashboard API without a product filter (or pass no product_id)
4. **Remove the "All Products" / product chip filter bar** from the template
5. **Keep the dashboard title** ("Dashboard") without the `/ ProductName` suffix

### Backend (optional cleanup)

The `/api/v1/stats/dashboard` endpoint accepts an optional `product_id` query param. This can stay — it's harmless and may be useful for SaaS. No backend changes required.

---

## What to Keep

- All stat cards, charts, agent distribution, recent projects list
- The dashboard still scopes to the authenticated user's tenant (tenant_key filtering)
- Responsive layout and all existing styling

---

## Success Criteria

- [x] No product selector/filter UI on the dashboard
- [x] Dashboard shows all-tenant stats on load (no product scoping)
- [x] No broken imports or dead refs after removal
- [x] Existing dashboard tests still pass (update if they reference ProductSelector)

---

## Implementation Summary

### What Was Done
- Removed `ProductSelector` component import and template usage from `DashboardView.vue`
- Removed `selectedProductId` ref, `selectedProductName` computed, `onProductSelect` handler, and the `watch` on product selection
- Removed `useProductStore` import and `productStore.fetchProducts()` call
- Simplified `fetchDashboardData()` to always fetch all-tenant data (no product_id param)
- Removed `/ ProductName` suffix from dashboard header
- Cleaned up unused `watch` import and `.dash-product-label` CSS
- Deleted `frontend/src/components/dashboard/ProductSelector.vue`

### Verification
- `vite build` succeeds with zero errors
- No remaining references to `ProductSelector` in the frontend codebase
- All pre-existing frontend tests unaffected (38 pre-existing failures, none related to this change)
