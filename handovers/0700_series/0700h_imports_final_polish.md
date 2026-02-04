# Handover 0700h: Import Cleanup and Final Polish

## Context

**Pre-release cleanup decision (2026-02-04):** Final cleanup pass to remove unused imports identified by static analysis and any remaining deprecated code.

**Reference:** `handovers/0700_series/dead_code_audit.md` - Vulture output appendix

## Scope

Address all findings from static analysis tools:
1. Unused imports from Vulture/Pylint
2. Unused variables
3. Unreachable code
4. Final deprecated marker sweep

**Files Affected:** Multiple files across `src/` and `api/`

## Tasks

### 1. Fix Vulture Findings (High Confidence)

From audit report appendix:

- [ ] `api/endpoints/agent_jobs/operations.py:35`
  - Remove unused import: `ForceFailJobRequest`
  - Remove unused import: `ForceFailJobResponse`

- [ ] `api/endpoints/projects/lifecycle.py:27`
  - Remove unused import: `StagingCancellationResponse`

- [ ] `api/endpoints/prompts.py:23`
  - Remove unused import: `ThinPromptResponse`

- [ ] `api/startup/database.py:48`
  - Fix redundant if-condition

- [ ] `src/giljo_mcp/colored_logger.py:20`
  - Remove unused import: `Back`

- [ ] `src/giljo_mcp/discovery.py:602, 623`
  - Remove unused variable: `max_chars` (2 instances)

- [ ] `src/giljo_mcp/services/project_service.py:1475`
  - Remove unreachable code after raise

- [ ] `src/giljo_mcp/services/task_service.py:223`
  - Remove unused variable: `assigned_to`

- [ ] `src/giljo_mcp/services/template_service.py:34`
  - Remove unused import: `TemplateRenderError`
  - Remove unused import: `TemplateValidationError`
  - (Note: These may be removed in 0700g already)

- [ ] `src/giljo_mcp/tools/agent.py:17`
  - Remove unused import: `broadcast_sub_agent_event`

- [ ] `src/giljo_mcp/tools/context.py:97`
  - Remove unused variable: `force_reindex`

- [ ] `src/giljo_mcp/tools/template.py:16`
  - Remove unused import: `extract_variables`

- [ ] `src/giljo_mcp/tools/tool_accessor.py:361`
  - Remove unused variable: `assigned_to`

### 2. Run Fresh Static Analysis

After fixing known issues, run tools again:

- [ ] `vulture src/ api/ --min-confidence 80` - Should be clean
- [ ] `pylint src/ api/ --disable=all --enable=W0611` - Minimal warnings
- [ ] `ruff check src/ api/` - No errors

### 3. Remove Remaining Deprecated Parameters

Location: `src/giljo_mcp/thin_prompt_generator.py`

- [ ] **Line 141**: Remove deprecated `instance_number` parameter handling
  ```python
  instance_number: Orchestrator instance number (for succession) - DEPRECATED in continuation mode
  ```

- [ ] **Line 964**: Consider if deprecated method can be removed
  ```python
  DEPRECATED: Use generate_staging_prompt() instead (universal Scenario B).
  ```

- [ ] **Line 1134**: Remove deprecated parameter
  ```python
  instance_number: DEPRECATED - kept for backward compatibility only
  ```

### 4. Final DEPRECATED Marker Sweep

- [ ] `grep -r "DEPRECATED" src/ api/ --include="*.py" | wc -l` - Should be 0
- [ ] `grep -r "v4.0" src/ api/ --include="*.py"` - Remove timeline references
- [ ] `grep -r "backward compat" src/ api/ --include="*.py"` - Review each

### 5. Code Quality Pass

- [ ] Run `black src/ api/` - Format all Python
- [ ] Run `ruff check src/ api/ --fix` - Auto-fix lint issues
- [ ] Run `mypy src/` - Check for type errors (informational)

## Verification

- [ ] All tests pass: `pytest tests/`
- [ ] No vulture findings at 80% confidence
- [ ] No pylint W0611 (unused import) warnings
- [ ] Ruff check passes with no errors
- [ ] `grep -r "DEPRECATED" src/ api/` returns 0 results
- [ ] Server starts without warnings: `python api/run_api.py`

## Risk Assessment

**LOW** - Removing unused code with verification at each step

**Mitigation:**
- Each removal is verified by static analysis
- Tests catch any functional regressions
- Changes are mechanical (removing unused code)

## Dependencies

- **Depends on:** 0700b, 0700c, 0700d, 0700e, 0700f, 0700g (all prior cleanups)
- **Blocks:** None (this is the final handover)

## Estimated Impact

- **Lines removed:** ~50-100 (imports, variables, unreachable code)
- **Files modified:** 15-20
- **Final codebase state:** Zero DEPRECATED markers, clean static analysis

## Success Criteria for 0700 Series

After completing 0700h, verify:

1. `grep -r "DEPRECATED" src/ api/ --include="*.py"` returns **0 results**
2. `vulture src/ api/ --min-confidence 80` returns **0 findings**
3. All tests pass with **>80% coverage**
4. Fresh install completes in **<1 second**
5. No backwards compatibility code remains
6. Codebase is **release-ready**
