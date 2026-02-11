# 0740 TODO Inventory

**Series:** 0740 Comprehensive Post-Cleanup Audit (Audit #5)
**Date:** 2026-02-10
**Baseline:** post-0730 (after 0700 cleanup series + 0727 test fixes + 0730 service response models)

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Actionable TODOs** | 28 |
| DONE (work completed, TODO remains) | 5 |
| ACTIVE (still needed) | 13 |
| OBSOLETE (no longer relevant) | 10 |
| **By Priority** | |
| P0 Critical | 0 |
| P1 High | 3 |
| P2 Medium | 17 |
| P3 Low | 8 |
| **By Category** | |
| Testing | 22 |
| Enhancement | 5 |
| Cleanup | 1 |

**Key Finding:** The codebase has **zero P0 (critical) TODOs**. The vast majority of TODOs (22 of
28) are in test files, reflecting placeholder tests from earlier development phases. Five TODOs
reference work that is already complete (toast composable exists, JWT auth implemented) and ten are
obsolete (primarily the 0127a-2 MCPAgentJob refactoring that was superseded by the AgentExecution
model, plus stale references to ProductService which now exists).

---

## Methodology

### Search Process

1. **Searched directories:** `src/`, `api/`, `frontend/src/`, `tests/`
2. **File types:** `*.py`, `*.vue`, `*.js`, `*.ts`
3. **Patterns:** `TODO`, `FIXME`, `HACK`, `XXX` (case-sensitive)
4. **Tool:** ripgrep with content mode and line numbers

### False Positive Filtering

The raw search returned approximately 50 matches. After manual review, 28 were classified as
false positives:

| False Positive Type | Count | Examples |
|---------------------|-------|---------|
| Feature references (TODO items feature) | 18 | `orchestration_service.py` "TODO items completed" |
| Model field comments | 4 | `agent_identity.py:354` "TODO item description/task text" |
| UI text content | 3 | `ProductIntroTour.vue:227` "Track technical debt and TODOs" |
| Test feature descriptions | 2 | `test_thin_prompt_generator_execution_mode.py:373` "TODO-style Steps" |
| String formatting (XXX) | 1 | `core_services.py:97` "...XXXX" in API key masking |

### Classification Criteria

- **DONE:** The referenced work is verified complete in the codebase (e.g., class exists, feature
  implemented) but the TODO comment was not removed
- **ACTIVE:** The referenced work has no evidence of completion
- **OBSOLETE:** The referenced feature, model, or pattern has been removed or superseded

---

## TODOs by Status

### DONE (5 items - work completed, comment remains)

| # | File | Line | Text | Evidence |
|---|------|------|------|----------|
| 1 | `frontend/src/components/TemplateManager.vue` | 1111 | Add toast notification when toast composable is available | `useToast.js` exists at `frontend/src/composables/useToast.js` |
| 2 | `frontend/src/components/TemplateManager.vue` | 1124 | Add error toast when composable is available | Same - `useToast.js` composable exists |
| 3 | `frontend/src/components/TemplateManager.vue` | 1287 | Add toast notification when composable is available | Same - `useToast.js` composable exists |
| 4 | `tests/test_pin_recovery.py` | 348 | Add authentication header when JWT is implemented | JWT auth implemented in `api/auth_utils.py` and `api/middleware/auth.py` |
| 5 | `tests/test_pin_recovery.py` | 426 | Add admin authentication header when JWT is implemented | JWT auth implemented |

**Recommended Action:** Remove the 3 TemplateManager TODOs by replacing console.log/warn with
actual `useToast()` calls. Update the 2 pin recovery tests with proper JWT auth headers.

---

### ACTIVE (13 items - still needed)

| # | File | Line | Priority | Text | Category |
|---|------|------|----------|------|----------|
| 1 | `api/endpoints/mcp_installer.py` | 232 | P2 | Query from APIKey table if needed | Enhancement |
| 2 | `tests/performance/test_vision_chunking_load.py` | 20 | P3 | ChunkingTools class doesn't exist yet | Testing |
| 3 | `tests/performance/test_message_queue_load.py` | 20 | P3 | MessageTools class doesn't exist yet | Testing |
| 4 | `tests/test_e2e_sub_agent_lifecycle.py` | 20 | P3 | AgentTools class doesn't exist yet | Testing |
| 5 | `tests/test_pin_recovery.py` | 460 | P2 | Add non-admin authentication header | Testing |
| 6 | `tests/test_pin_recovery.py` | 474 | P2 | Add admin authentication header | Testing |
| 7 | `tests/test_pin_recovery.py` | 505 | P2 | Add admin authentication header | Testing |
| 8 | `tests/integration/test_full_stack_mode_flow.py` | 203 | P2 | Optimize prompt generator to reach 600 tokens target | Enhancement |
| 9 | `tests/integration/test_orchestration_e2e.py` | 146 | P1 | Fix database injection (MessageService requires separate db_manager) | Testing |
| 10 | `tests/integration/test_backup_integration.py` | 243 | P3 | Verify backup file content when implementation exists | Testing |
| 11 | `tests/services/test_vision_summarizer.py` | 240 | P3 | Implement VisionDocumentSummarizer tests (3 placeholders at 240, 261, 281) | Testing |
| 12 | `tests/integration/test_server_mode_auth.py` | 83 | P2 | Replace with actual API key generation/retrieval | Testing |
| 13 | `tests/integration/test_priority_system_integration.py` | 560 | P2 | Phase 6 - Add WebSocket event assertion | Testing |

**P1 Active Items (1):**

1. **Database injection fix** (`test_orchestration_e2e.py:146`) - MessageService requires a
   separate `db_manager` instance. This is a real architectural constraint blocking test coverage
   for agent communication workflows. Resolving this requires understanding the MessageService's
   database session management pattern.

**Notable P2/P3 Items:**

- **Vision summarizer placeholder tests** (`test_vision_summarizer.py:240,261,281`) - Counted as
  one logical TODO (todo-021). VisionDocumentSummarizer now exists but these 3 placeholder tests
  were never implemented. They skip immediately with no assertions.
- **API key generation** (`test_server_mode_auth.py:83`) - Test returns hardcoded placeholder
  string instead of generating a real API key from the APIKey table.
- **WebSocket event assertion** (`test_priority_system_integration.py:560`) - Phase 6 of
  priority system testing; asserts response 200 but does not verify WebSocket event emission.

---

### OBSOLETE (10 items - no longer relevant)

| # | File | Line | Text | Why Obsolete |
|---|------|------|------|-------------|
| 1 | `tests/performance/test_database_benchmarks.py` | 12 | TODO(0127a-2): Refactoring for MCPAgentJob | MCPAgentJob was never created; model is AgentExecution. Entire file skipped. |
| 2 | `tests/performance/test_database_benchmarks.py` | 30 | TODO(0127a-2): Agent to MCPAgentJob | Same as above - duplicate TODO in same file |
| 3 | `tests/integration/test_backup_integration.py` | 21 | TODO(0127a-2): Refactoring for MCPAgentJob | Entire file skipped. MCPAgentJob never existed. |
| 4 | `tests/integration/test_hierarchical_context.py` | 14 | TODO(0127a-2): Refactoring for MCPAgentJob | Entire file skipped. MCPAgentJob never existed. |
| 5 | `tests/integration/test_message_queue_integration.py` | 10 | TODO(0127a-2): Refactoring for MCPAgentJob | Entire file skipped. MCPAgentJob never existed. |
| 6 | `tests/integration/test_orchestrator_template.py` | 20 | TODO(0127a): Commented-out import of old Agent model | File skipped. Agent/MCPAgentJob never existed; model is AgentExecution. |
| 7 | `tests/integration/test_upgrade_validation.py` | 25 | TODO(0127a): Commented-out import of old Agent model | File skipped. Same obsolete model reference. |
| 8 | `tests/unit/test_vision_repository_async.py` | 65 | Update to await after async refactoring | `mark_chunked` is already async (vision_document_repository.py:244). Test already uses await. |
| 9 | `tests/unit/test_products_crud.py` | 31 | Complete mock once ProductService exists | ProductService exists at `src/giljo_mcp/services/product_service.py`. Trivial stub test. |
| 10 | `tests/unit/test_products_crud.py` | 49 | Complete mock once ProductService exists | Same as above - duplicate in same file. |

**Note on 0127a-2 TODOs:** Seven of the ten obsolete items reference handover 0127a or 0127a-2,
which proposed refactoring tests from the old `Agent` model to `MCPAgentJob`. The actual model
name used in production is `AgentExecution`. These test files are entirely skipped and contribute
zero test coverage. They could be safely deleted or rewritten from scratch using current patterns.

The affected files are:
- `test_database_benchmarks.py` (2 TODOs)
- `test_backup_integration.py` (1 TODO)
- `test_hierarchical_context.py` (1 TODO)
- `test_message_queue_integration.py` (1 TODO)
- `test_orchestrator_template.py` (1 TODO)
- `test_upgrade_validation.py` (1 TODO)

---

## Comparison vs 0725b Baseline

| Metric | 0725b Claim | 0740 Actual | Delta |
|--------|-------------|-------------|-------|
| Raw TODO matches | 43 | ~56 | +13 (more thorough search) |
| False positives filtered | (none) | ~28 | - |
| Actionable TODOs | 43 (unfiltered) | 28 | -15 |
| Active only | (not classified) | 13 | - |

**Explanation of Difference:**

The 0725b baseline of 43 likely counted raw matches without filtering false positives. The GiljoAI
MCP codebase has a "TODO items" feature (agent task tracking displayed in the Plan/TODOs tab) that
generates numerous references to "TODO" in model definitions, service code, WebSocket handlers,
frontend stores, and test descriptions. These are feature references, not actionable development
tasks.

After rigorous filtering, the actual actionable TODO count is **28**, of which only **13** are
genuinely active items that need attention. 10 are obsolete (referencing models or services that
no longer exist or have been superseded), and 5 reference work that is already complete.

---

## Mapped to Follow-Up Handovers

### Handover Group 1: Toast Notifications (3 DONE items)
**Files:** `frontend/src/components/TemplateManager.vue` (lines 1111, 1124, 1287)
**Effort:** Small (import useToast, replace console.log/warn with showToast calls)
**Impact:** Better user feedback for template activation/deactivation and clipboard copy

### Handover Group 2: Pin Recovery Test Auth (5 items: 2 DONE + 3 ACTIVE)
**Files:** `tests/test_pin_recovery.py` (lines 348, 426, 460, 474, 505)
**Effort:** Medium (create test fixtures for JWT tokens, update all test methods)
**Impact:** Pin recovery tests will properly validate auth behavior instead of accepting 401

### Handover Group 3: Obsolete Test Cleanup (10 OBSOLETE items)
**Files:** 7 integration/performance test files with 0127a/0127a-2 skips + 3 stale unit tests
**Effort:** Small (delete or rewrite from scratch)
**Impact:** Removes confusion from permanently-skipped tests referencing non-existent models

### Handover Group 4: Missing Tool Classes (3 ACTIVE items)
**Files:** `test_vision_chunking_load.py`, `test_message_queue_load.py`, `test_e2e_sub_agent_lifecycle.py`
**Effort:** Large (requires implementing ChunkingTools, MessageTools, AgentTools classes)
**Impact:** Performance and E2E test coverage for chunking, messaging, and agent lifecycle

### Handover Group 5: API Key Query (1 ACTIVE item)
**Files:** `api/endpoints/mcp_installer.py` (line 232)
**Effort:** Small (query APIKey table instead of using getattr fallback)
**Impact:** Proper API key resolution for MCP installer script generation

### Handover Group 6: Test Fixture Improvements (2 ACTIVE items)
**Files:** `test_server_mode_auth.py` (line 83), `test_priority_system_integration.py` (line 560)
**Effort:** Medium (API key generation, WebSocket event assertion)
**Impact:** More realistic test fixtures and complete integration test assertions

### Standalone Items
- `test_orchestration_e2e.py:146` (P1) - Database injection fix for MessageService
- `test_full_stack_mode_flow.py:203` (P2) - Token optimization target validation
- `test_backup_integration.py:243` (P3) - Backup content verification
- `test_vision_summarizer.py:240,261,281` (P3) - Vision summarizer test implementation

---

## Recommendations

1. **Immediate (P1):** Fix the MessageService database injection issue blocking
   `test_orchestration_e2e.py`. This is the only P1 active item and blocks test coverage for
   a critical workflow (agent communication).

2. **Quick Wins:** Remove the 3 TemplateManager TODOs by wiring up the existing `useToast()`
   composable. Delete or rewrite the 7 obsolete 0127a/0127a-2 test files. Remove the 2 stale
   `test_products_crud.py` stub tests and the `test_vision_repository_async.py` stale TODO.
   These are low-effort, high clarity improvements.

3. **Test Improvement Sprint:** Update `test_pin_recovery.py` with proper JWT auth fixtures.
   Implement the 3 vision summarizer placeholder tests. These would meaningfully increase test
   coverage.

4. **Backlog:** The missing tool classes (ChunkingTools, MessageTools, AgentTools) are prerequisites
   for performance and E2E tests. These should be planned when performance testing becomes a
   priority.

5. **Process:** Establish a convention that TODO comments include a handover reference
   (e.g., `# TODO(0750): description`) to enable tracking and prevent orphaned TODOs.
