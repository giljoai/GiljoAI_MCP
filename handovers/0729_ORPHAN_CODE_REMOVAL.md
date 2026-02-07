# Handover 0729: Orphan Code Removal (Phase 1)

**Series:** 0700 Code Health Audit Follow-Up
**Priority:** P1 - HIGH (Technical Debt)
**Risk Level:** MEDIUM
**Estimated Effort:** 16-24 hours
**Prerequisites:** Handover 0725 Audit Complete
**Status:** READY

---

## Mission Statement

Remove orphan/zombie code identified in the 0725 audit to reduce maintenance burden and improve codebase clarity.

**Current Status:** 129 orphan modules (50% of 260 files), 444 unused functions, 30+ orphan test files.

---

## Phase 1 Scope (This Handover)

Focus on **definite orphans** with 100% confidence - safe to remove without risk.

### Targets:
1. 6 orphan modules (never imported)
2. 8 unused variables (100% confidence)
3. Dead functions in `agent_jobs/` endpoints
4. 30+ orphan test files

**Defer to Phase 2:** The remaining 123 orphan modules require deeper analysis.

---

## Part 1: Remove Orphan Modules (6 files)

### Safe to Remove (No Imports Found)

1. **src/giljo_mcp/lock_manager.py**
   - No imports found in codebase
   - Likely replaced by database-based locking

2. **src/giljo_mcp/mcp_http_stdin_proxy.py**
   - stdio support removed per CLAUDE.md (Handover 0334)
   - MCP-over-HTTP is authoritative

3. **src/giljo_mcp/staging_rollback.py**
   - No imports found
   - Staging functionality may have been refactored

4. **src/giljo_mcp/template_materializer.py**
   - No imports found
   - Template system refactored in 0041

5. **src/giljo_mcp/job_monitoring.py**
   - No imports found
   - Monitoring moved to dashboard/WebSocket

6. **src/giljo_mcp/cleanup/visualizer.py**
   - Only imported in unused `cleanup/__init__.py`
   - Cleanup module appears abandoned

**Removal Process:**
```bash
# 1. Verify no imports (double-check)
grep -r "lock_manager\|mcp_http_stdin_proxy\|staging_rollback\|template_materializer\|job_monitoring\|visualizer" src/ api/ tests/

# 2. Remove files
rm src/giljo_mcp/lock_manager.py
rm src/giljo_mcp/mcp_http_stdin_proxy.py
rm src/giljo_mcp/staging_rollback.py
rm src/giljo_mcp/template_materializer.py
rm src/giljo_mcp/job_monitoring.py
rm src/giljo_mcp/cleanup/visualizer.py

# 3. Run tests to verify nothing breaks
pytest tests/ -x
```

---

## Part 2: Remove Unused Variables (8 locations)

**100% Confidence** (detected by Vulture):

1. `src/giljo_mcp/discovery.py:602` - unused variable `max_chars`
2. `src/giljo_mcp/discovery.py:623` - unused variable `max_chars`
3. `src/giljo_mcp/discovery.py:623` - unused variable `paths_include`
4. `src/giljo_mcp/mission_planner.py:1144` - unused variable `category_key`
5. `src/giljo_mcp/services/task_service.py:207` - unused variable `assigned_to`
6. `src/giljo_mcp/services/task_service.py:246` - unused variable `assigned_to`
7. `src/giljo_mcp/tools/context.py:82` - unused variable `force_reindex`
8. `src/giljo_mcp/tools/tool_accessor.py:307` - unused variable `assigned_to`

**Removal Process:**
```python
# Example fix (discovery.py:602)
# BEFORE
max_chars = 10000  # Unused variable
result = process_data()

# AFTER
result = process_data()  # Variable removed
```

**Verification:**
```bash
# Run Vulture again to confirm
vulture src/ api/ --min-confidence 80
# Should not report these 8 variables anymore
```

---

## Part 3: Clean Up agent_jobs/ Endpoints (12 files)

**Location:** `api/endpoints/agent_jobs/`

Many files have dead functions (never called). Audit findings identified:

- `executions.py` - `get_job_executions()` unused
- `filters.py` - `get_filter_options()` unused
- `lifecycle.py` - `report_job_error()` unused
- `messages.py` - `get_job_messages()` unused
- `operations.py` - `get_job_health()` unused
- `orchestration.py` - `regenerate_mission()`, `launch_implementation()` unused
- `status.py` - `list_pending_jobs()`, `get_job_mission()` unused
- `table_view.py` - `get_agent_jobs_table_view()` unused

**Investigation Steps:**
1. For each file, verify functions are truly unused:
   ```bash
   grep -r "get_job_executions" api/ frontend/
   ```
2. If no callers found, remove function
3. Check if entire endpoint file can be removed (if all functions dead)
4. Update router registration in `api/app.py` if files removed

**Caution:** Some functions may be called from frontend. Verify frontend doesn't use these endpoints before removing.

---

## Part 4: Remove Orphan Test Files (30+ files)

**Location:** `tests/api/`

Test files that test non-existent or renamed modules:

- `test_users_category_validation.py`
- `test_users_new_categories.py`
- `test_admin_fixtures.py`
- `test_agent_display_name_schemas.py`
- `test_depth_controls.py`
- `test_filter_options.py`
- `test_health_status_api.py`
- `test_implementation_prompt_api.py`
- ... (22 more files)

**Verification Process:**
1. For each test file, identify what it tests
2. Check if production code still exists
3. If production code deleted/renamed, remove test
4. If test is outdated, update or remove

**Example:**
```bash
# Check what test_health_status_api.py tests
grep -r "health.*status" api/endpoints/

# If no matching endpoint found, safe to remove
rm tests/api/test_health_status_api.py
```

---

## Part 5: Update Dependency Analysis (if needed)

If `handovers/0700_series/dependency_analysis.json` exists:
1. Remove orphan modules from graph
2. Regenerate dependency analysis
3. Verify no new circular dependencies introduced

---

## Testing Strategy

### After Each Removal:
```bash
# Run full test suite
pytest tests/ -x  # Stop on first failure

# Run ruff linting
ruff check src/ api/

# Check for import errors
python -c "import src.giljo_mcp"
python -c "import api"
```

### Regression Testing:
- All existing tests should still pass
- No new import errors
- Application starts successfully
- Dashboard loads correctly

---

## Success Criteria

- [ ] 6 orphan modules removed
- [ ] 8 unused variables removed
- [ ] Dead functions in agent_jobs/ removed
- [ ] 30+ orphan test files removed
- [ ] All tests pass
- [ ] Ruff linting clean
- [ ] Application starts successfully
- [ ] No import errors
- [ ] Documentation updated (if needed)

---

## Files to Remove

**Production Files:**
1. `src/giljo_mcp/lock_manager.py`
2. `src/giljo_mcp/mcp_http_stdin_proxy.py`
3. `src/giljo_mcp/staging_rollback.py`
4. `src/giljo_mcp/template_materializer.py`
5. `src/giljo_mcp/job_monitoring.py`
6. `src/giljo_mcp/cleanup/visualizer.py`
7. Possibly some `api/endpoints/agent_jobs/*.py` files

**Test Files:**
- 30+ orphan test files (see Part 4 for list)

---

## Files to Modify

**Remove Unused Variables:**
1. `src/giljo_mcp/discovery.py` (lines 602, 623)
2. `src/giljo_mcp/mission_planner.py` (line 1144)
3. `src/giljo_mcp/services/task_service.py` (lines 207, 246)
4. `src/giljo_mcp/tools/context.py` (line 82)
5. `src/giljo_mcp/tools/tool_accessor.py` (line 307)

**Update Router:**
- `api/app.py` (if endpoint files removed)

---

## Phase 2 Preview (Future Handover)

**Remaining 123 orphan modules** require deeper analysis:
- Some may be imported dynamically
- Some may be imported only in tests
- Some may be part of plugin system
- Need call graph analysis to confirm safety

**Phase 2 Effort:** 40-60 hours (comprehensive cleanup)

---

## Reference

**Audit Report:** `handovers/0725_AUDIT_REPORT.md` (Lines 135-177)
**Orphan Findings:** `handovers/0725_findings_orphans.md`
