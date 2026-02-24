# Handover 0732: API Consistency Fixes

**Series:** 0700 Code Health Audit Follow-Up
**Priority:** P3 - LOW (Minor Polish)
**Risk Level:** LOW
**Estimated Effort:** ~1 hour
**Prerequisites:** None (0725 Audit complete, this is the follow-up)
**Status:** COMPLETE
**Completed:** 2026-02-23
**Implementation Commit:** `30072759`

---

## Mission Statement

Fix the 2 remaining API inconsistencies from the 0725 audit. Two of the original four findings have been resolved by prior work; this handover covers only what remains.

### Scope (2 items)

| # | What | File | Effort |
|---|------|------|--------|
| 1 | URL naming: `execution_mode` -> `execution-mode` | `api/endpoints/users.py` + 1 test file | ~15 min |
| 2 | Dict error returns -> HTTPException | `api/endpoints/database_setup.py` | ~45 min |

### Dropped (already resolved)

| Original Item | Why Dropped |
|---------------|-------------|
| Dict errors in `configuration.py` (old lines 573, 584, 587) | File refactored to 508 lines. All dict error returns already converted to HTTPException by prior work. |
| HTTPException in service layer (`ProductService`) | Investigated: zero `raise HTTPException` in any of the 16 service files. Only a docstring example in `template_service.py:495`. |

---

## Part 1: URL Naming Convention Fix

**Severity:** LOW
**Breaking Change:** NO - frontend does not call this endpoint directly

### The Violation

**File:** `api/endpoints/users.py`

```python
@router.get("/me/settings/execution_mode")   # Line 892 - underscore
async def get_execution_mode(...)             # Lines 892-905

@router.put("/me/settings/execution_mode")    # Line 909 - underscore
async def update_execution_mode(...)          # Lines 908-926
```

**Convention:** All other API URLs use kebab-case (`/vision-documents`, `/close-out`, `/api-keys`, `/agent-jobs`, etc.). These two routes are the only violation in the entire API surface.

### What to Change

**1. Backend routes (2 lines)**

File: `api/endpoints/users.py`

```python
# Line 892: change the route string only
@router.get("/me/settings/execution-mode")    # was: execution_mode

# Line 909: change the route string only
@router.put("/me/settings/execution-mode")    # was: execution_mode
```

Do NOT rename the Python function names (`get_execution_mode`, `update_execution_mode`) - those are snake_case by Python convention and are correct.

**2. Test file URL strings (~30 occurrences)**

File: `tests/api/test_execution_mode_endpoints.py`

Global find-replace in this file only:
```
OLD: /api/v1/users/me/settings/execution_mode
NEW: /api/v1/users/me/settings/execution-mode
```

Also update the docstring header (lines 5-6) and section comments (lines 69, 173) which reference the old URL.

**3. Frontend: NO changes needed**

Verified: `grep -r "settings/execution_mode" frontend/src/` returns zero matches. The frontend does not call this endpoint. The `execution_mode` references in `ProjectTabs.vue` and `api.js` are query parameters and request body fields for *different* endpoints (staging prompts, project updates) - not this URL path.

### Verification

```bash
# Run the dedicated test file
pytest tests/api/test_execution_mode_endpoints.py -v

# Confirm no stale references remain
grep -rn "settings/execution_mode" api/ tests/
# Should return 0 results after fix
```

---

## Part 2: database_setup.py Error Handling Standardization

**Severity:** LOW
**Breaking Change:** YES for any frontend code parsing these responses (see note below)

### The Problem

`api/endpoints/database_setup.py` (369 lines, 3 endpoint functions) mixes two error patterns:
- **Dict returns** for operational errors: `return {"success": False, "status": "error", "message": "..."}` (12 instances)
- **HTTPException raises** for system errors: `raise HTTPException(status_code=500, detail="...")` (4 instances)

This means error responses sometimes return HTTP 200 with `{"success": False}` and sometimes return HTTP 500 with a proper error body. Frontend must handle both patterns, which is inconsistent with every other endpoint in the codebase.

### Current State by Function

#### Function 1: `test_database_connection` (lines 37-120)

| Line(s) | Pattern | What | Target Status Code |
|---------|---------|------|-------------------|
| 91-98 | Dict success | Connected OK | KEEP (200) |
| 103-107 | Dict error | Auth failed | -> 401 |
| 109-113 | Dict error | Connection refused | -> 503 |
| 114 | Dict error | Generic connection failure | -> 503 |
| 118 | HTTPException 500 | psycopg2 not installed | KEEP (already correct) |
| 119 | Dict error | Generic test failure (OSError/ValueError) | -> 500 |

#### Function 2: `setup_database` (lines 122-233)

| Line(s) | Pattern | What | Target Status Code |
|---------|---------|------|-------------------|
| 160-165 | Dict error | Setup failed | -> 500 |
| 181-185 | Dict error | config.yaml not found | -> 500 |
| 217-228 | Dict success | Setup completed OK | KEEP (200) |
| 232 | HTTPException 500 | ImportError/OSError/ValueError | KEEP (already correct) |

#### Function 3: `verify_database_setup` (lines 235-369)

| Line(s) | Pattern | What | Target Status Code |
|---------|---------|------|-------------------|
| 278-283 | Dict error | Missing .env credentials | -> 400 |
| 320-331 | Dict success | Verified OK | KEEP (200) |
| 337-342 | Dict error | Auth failed | -> 401 |
| 344-349 | Dict error | Database doesn't exist | -> 404 |
| 351-356 | Dict error | Connection refused | -> 503 |
| 357-362 | Dict error | Generic connection error | -> 503 |
| 366 | HTTPException 500 | psycopg2 not installed | KEEP (already correct) |
| 368 | HTTPException 500 | OSError/ValueError | KEEP (already correct) |

### How to Fix

Convert each dict error return to an HTTPException raise. Example transformation:

```python
# BEFORE (line 103-107):
return {
    "success": False,
    "status": "auth_failed",
    "message": "Invalid PostgreSQL admin password",
}

# AFTER:
raise HTTPException(
    status_code=401,
    detail="Invalid PostgreSQL admin password"
)
```

**Rules:**
- Keep all success dict returns unchanged (they return useful metadata the frontend needs)
- Convert all `{"success": False, ...}` error returns to `raise HTTPException(...)`
- Use semantically correct HTTP status codes (401 for auth, 503 for connection, 404 for missing DB, 400 for bad input, 500 for internal)
- HTTPException is already imported in the file (used on lines 118, 232, 366, 368)
- Do NOT touch the 4 existing HTTPException raises - they're already correct

### Frontend Impact Note

These endpoints are called during initial database setup (installer flow). Check if the installer frontend parses `response.json().success === false`. If so, it will need to switch to checking HTTP status codes (4xx/5xx). Search:

```bash
grep -rn "test.database\|setup.database\|verify.database\|database_setup\|database-setup" frontend/src/
```

If the frontend checks `response.ok` or status codes already, no frontend changes are needed.

### Verification

```bash
# Run database setup tests (if they exist)
pytest tests/api/ -k database -v

# Lint check
ruff check api/endpoints/database_setup.py
```

---

## Implementation Order

1. **Part 1 first** (URL rename) - smallest, zero risk, verifiable in isolation
2. **Part 2 second** (database_setup.py) - mechanical but more lines to touch

---

## Success Criteria

- [ ] `execution_mode` URL paths renamed to `execution-mode` in users.py (2 routes)
- [ ] Test file URLs updated in `test_execution_mode_endpoints.py`
- [ ] `pytest tests/api/test_execution_mode_endpoints.py` passes
- [ ] All dict error returns in `database_setup.py` converted to HTTPException
- [ ] Success dict returns in `database_setup.py` left unchanged
- [ ] `ruff check api/endpoints/` clean
- [ ] Full test suite passes: `pytest tests/ -x`

---

## Files to Modify

| File | What | Changes |
|------|------|---------|
| `api/endpoints/users.py` | Route strings on lines 892, 909 | 2 string replacements |
| `tests/api/test_execution_mode_endpoints.py` | URL strings throughout | ~30 string replacements (global find-replace) |
| `api/endpoints/database_setup.py` | Error returns in 3 functions | 12 dict returns -> HTTPException |

**Files NOT modified:** `configuration.py` (already fixed), any service files (clean), any frontend files (Part 1 not called from frontend; Part 2 check installer flow).

---

## Implementation Summary

### 2026-02-23 - Completed

**Commit:** `30072759` - "fix: Standardize API consistency (execution-mode URLs + HTTPException errors)"

**What was done:**
- Part 1: Renamed `/me/settings/execution_mode` to `/me/settings/execution-mode` in `users.py` (2 routes) and updated all ~30 URL references in `test_execution_mode_endpoints.py`
- Part 2: Converted 12 dict-style error returns in `database_setup.py` to `raise HTTPException(...)` with semantic status codes (401/400/404/500/503). Success dict returns preserved.
- 3 files changed, +76/-91 lines net reduction

**All success criteria met.** Ruff clean, tests passing.

---

## Reference

- **Original audit:** 0725 Code Health Audit (completed 2026-02-07)
- **Validation:** 2026-02-23 subagent research confirmed current line numbers and resolved/remaining status
