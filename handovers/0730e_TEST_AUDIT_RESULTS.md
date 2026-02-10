# Handover 0730e: API Test Suite Audit Results

## Executive Summary

**Goal:** Slim down from ~614 API tests to ~100-150 well-maintained tests.

**Current State:**
- 654 total test functions across 41 files
- 390 passing (60%), 88 failed (13%), 61 errors (9%), 75+ skipped (11%)
- 37% overall failure rate

**Target State:**
- ~150 well-maintained tests across ~25 files  
- >95% pass rate
- Focus on CRUD, security, and isolation tests

---

## Summary Stats

| Category | Count | Percentage |
|----------|-------|------------|
| **Total Test Functions** | ~654 | 100% |
| **Passing** | 390 | 60% |
| **Failed** | 88 | 13% |
| **Errors** | 61 | 9% |
| **Skipped (pytest.mark.skip)** | 75+ | 11%+ |
| **Total Test Files** | 41 | - |

### Recommendation Summary

| Action | Count | Target After Cleanup |
|--------|-------|---------------------|
| **DELETE** (entire file) | 6 files (~74 tests) | - |
| **DELETE** (individual tests) | ~85 tests | - |
| **KEEP** (essential) | ~150 tests | ~150 |
| **FIX** (high priority) | ~30 tests | - |

---

## DELETE LIST - Files to Remove Entirely

### 1. test_jobs_endpoint_mission_acknowledged.py (11 tests)
**Reason:** Module-level skip - table_view module removed in 0700c

### 2. test_jobs_endpoint_message_counters.py (6 tests)
**Reason:** Module-level skip - AgentExecution.project_id removed in 0366a

### 3. test_table_view_endpoint.py (21 tests)
**Reason:** Tests for removed table_view module

### 4. test_table_view_mission_fields.py (4 tests)
**Reason:** Tests for removed table_view module

### 5. test_websocket_table_updates.py (10 tests)
**Reason:** TDD scaffolds never completed

### 6. test_0367b_mcpagentjob_removal.py (22 tests)
**Reason:** Migration validation tests - migration complete

---

## DELETE LIST - Individual Tests to Remove

### A. Skipped Template Tests (22 tests)
**File:** test_templates_api.py
Templates are now system-managed and cannot be modified.

### B. Cancel Endpoint Tests (3 tests)
**File:** test_agent_jobs_api.py
Cancel endpoint removed per passive HTTP architecture.

### C. Obsolete Pattern Tests (6 tests)
**File:** test_create_successor_orchestrator.py
Uses result["success"] pattern - now exception-based (0730d).

### D. Slash Commands Tests (7 tests)  
**File:** test_slash_commands_api.py
Tests skipped due to endpoint returning 404 - tenant isolation issues.

### E. Tasks API Infrastructure Tests (9 tests)
**File:** test_tasks_api.py
Test client cookie persistence issues.

---

## KEEP LIST - Essential Tests

### 1. Auth/Security Tests (CRITICAL - 16 tests)
**File:** test_mcp_security.py - KEEP ALL

### 2. Happy Path CRUD Tests (ESSENTIAL - ~50 tests)
Products, Projects, Tasks, Templates, Agent Jobs, Users, Organizations, Settings

### 3. Multi-Tenant Isolation Tests (CRITICAL - ~25 tests)
Cross-tenant blocking tests across all entity types

### 4. Error Response Format Tests (ESSENTIAL - ~15 tests)
401 Unauthorized, 403 Forbidden, 404 Not Found

### 5. Validation Schema Tests (KEEP - ~18 tests)
tests/api/endpoints/test_users_category_validation.py
tests/api/endpoints/test_users_new_categories.py

---

## RECOMMENDED ACTIONS - Prioritized

### Priority 1: Delete Obsolete Files (Quick Win)
Delete 6 files: test_jobs_endpoint_mission_acknowledged.py, test_jobs_endpoint_message_counters.py, test_table_view_endpoint.py, test_table_view_mission_fields.py, test_websocket_table_updates.py, test_0367b_mcpagentjob_removal.py
**Impact:** -74 tests

### Priority 2: Delete Skipped Template Tests
Remove 22 skipped tests from test_templates_api.py
**Impact:** -22 tests

### Priority 3: Fix or Delete Infrastructure Tests
Review test_tasks_api.py skipped tests.

### Priority 4: Move Service Layer Tests
test_create_successor_orchestrator.py to tests/services/

### Priority 5: Keep Slash Command Tests Skipped

---

## Post-Cleanup Test Count Estimate

| Category | Count |
|----------|-------|
| Products API | ~20 |
| Projects API | ~25 |
| Tasks API | ~25 |
| Templates API | ~15 |
| Agent Jobs API | ~25 |
| Users API | ~20 |
| Organizations API | ~10 |
| Settings API | ~10 |
| MCP Security | ~10 |
| User Validation | ~18 |
| **TOTAL** | **~150-180** |

---

## Summary

**Current State:** 654 tests across 41 files with 37% failure rate

**Target State:** ~150 well-maintained tests with >95% pass rate

**Key Actions:**
1. Delete 6 obsolete files (-74 tests)
2. Delete 22 skipped template tests  
3. Fix or delete ~15 infrastructure-broken tests
4. Keep essential CRUD, security, and isolation tests
