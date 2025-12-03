# 0078 Completion Summary: Task Tenant & JWT Mismatch Diagnosis

Status: Completed/Retired (Diagnosis Consolidated)
Date: 2025-10-31
Owner: Project 0078

---

## Executive Summary

0078 investigated task invisibility after save in a multi‑tenant setup. Root cause: JWT cookie contained a default/fallback tenant_key that didn’t match the user’s actual tenant, causing product discovery and task filters to query the wrong tenant. This summary consolidates findings and the remediation plan.

---

## Problem & Impact

- Symptoms
  - Task creation succeeds but new tasks don’t appear under “Product Tasks”.
  - Tasks created without product_id when productStore.currentProductId is null.
  - No user‑visible error; filters return empty set.

- Impact Chain
  - Wrong JWT tenant_key → active product fetch returns none → productStore.currentProductId null → create uses product_id=null → “Product Tasks” filter hides task.

---

## Findings (Root Cause)

- JWT token contained DEFAULT tenant (`tk_cyy...`) instead of user’s tenant (`tk_eHuG...`).
- Fresh‑install default tenant persisted beyond setup; cookies not refreshed.
- Middleware logs showed successful auth but user context had mismatched tenant.

---

## Remediation Plan

Backend (Auth & Middleware)
- Ensure JWT payload uses `user.tenant_key` at login and refresh; never fall back to DEFAULT tenant post‑setup.
- Invalidate legacy sessions after setup completion to force re‑login with correct tenant.
- Optional guard: compare JWT tenant_key with DB user tenant_key on `get_current_user`; if mismatch, 401 + instruct client to re‑auth.

Frontend
- Defensive UX: if no active product is found, surface a warning and allow switching to “All Tasks” view automatically.
- On login, clear cached product selection if tenant changes.

Verification
- Create task with active product selected → appears under “Product Tasks”.
- Switch to “All Tasks” → shows tasks with product_id=null.
- Re‑login after invalidation → tenant_key in JWT matches DB; active product fetch succeeds.

---

## Artifacts Archived

- handovers/completed/0078_task_tenant_jwt_mismatch_diagnosis-C.md

---

## Status

Diagnosis consolidated and closed. Implementation of the remediation plan can proceed under a separate handover if needed (e.g., “Auth Tenant Sync Hardening”).

