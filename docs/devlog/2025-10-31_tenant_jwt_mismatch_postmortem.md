# Postmortem — Tenant JWT Mismatch Causing Invisible Tasks

Date: 2025-10-31
Related: handovers/completed/0078_task_tenant_jwt_mismatch_diagnosis-C.md
Impact: Multi-tenant isolation bug; tasks saved under null product and hidden in filtered views

---

## Summary

Users reported successful task creation (HTTP 200) but tasks were not visible when filtering by the active product. Root cause was a tenant mismatch between JWT creation and verification paths, leading to `product_id = null` at save time and filtering mismatches in the UI.

## Root Cause

- Two JWT implementations with incompatible payloads:
  - Token creation (`jwt_manager.py`): `sub`, `username`, `role`, `tenant_key`
  - Token verification (`auth_legacy.py`): expected `user_id`, `tenant_key`
- Middleware verified tokens using the legacy expectation, misresolving tenant context.

## Fix

- Standardize on a single JWT manager and payload shape
- Ensure middleware extracts `tenant_key` consistently from the active implementation
- Verify frontend uses correct tenant when deriving `currentProductId`

## Verification

- Create task with an active product selected → saved with correct `product_id`
- Filter by Product Tasks → task appears
- Cross-tenant fetch blocked as expected

See detailed investigation notes: `handovers/completed/0078_task_tenant_jwt_mismatch_diagnosis-C.md`.

