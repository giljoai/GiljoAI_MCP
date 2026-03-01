# 0750c: Tools Dict-to-Exception Migration

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 3 of 7
**Branch:** `0750-cleanup-sprint`
**Priority:** HIGH -- largest code debt item (70 dict returns across 11 files)

### Reference Documents
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 3 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md` (finding H-15)
- **Dependency graph:** `docs/cleanup/dependency_graph.json` -- `tool_accessor.py` has 28 dependents, `tenant.py` has 119 dependents
- **Exception hierarchy:** `src/giljo_mcp/exceptions.py` -- 30+ exception classes already defined
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750b `notes_for_next` before starting

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The code quality audit (2026-02-28) identified 70 instances of the dict-return anti-pattern across 11 files in the `src/` directory. Functions return `{"success": False, "error": "..."}` on failure instead of raising exceptions, and `{"success": True, ...}` on success instead of returning the useful value directly. This forces every caller to check `result["success"]` instead of using try/except, creating fragile, verbose code.

Phase 1 already patched protocol documents to mandate exceptions. Phase 2 triaged the test suite and identified 8 unit test files that are skipped because they assert on the old dict-return API. This phase eliminates the dict returns from production code and updates all callers.

---

## Exception Mapping

Use these existing exceptions from `src/giljo_mcp/exceptions.py`. Do NOT create new exception classes unless none of these fit:

| Error Scenario | Exception to Raise |
|---|---|
| Entity not found (project, agent, product, document) | `ResourceNotFoundError(message)` |
| Tenant context missing or invalid | `ValidationError(message)` |
| Invalid input / missing required parameter | `ValidationError(message)` or `DataValidationError(message)` |
| Agent/orchestration operation failure | `OrchestrationError(message)` |
| Project state invalid for operation | `ProjectStateError(message)` |
| MCP tool execution failure | `ToolError(message)` |
| Context/chunking failure | `ContextError(message)` or `ContextLimitError(message)` |
| File system error | `GiljoFileNotFoundError(message)` or `FileSystemError(message)` |
| Vision document error | `VisionError(message)` |
| Generic catch-all (use sparingly) | `BaseGiljoError(message)` |

Import from: `from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError, ...`

### Success Return Pattern

For functions that currently return `{"success": True, "key": value}`:
- Return the useful value directly: `return value`
- Or return a tuple if multiple values: `return (project_id, agent_count)`
- Or return a Pydantic model if the function is part of a service contract

---

## Scope: 11 Files, 70 Dict Returns

Work through files in the order listed. After migrating each file:
1. Use `grep` or `find_referencing_symbols` to find ALL callers
2. Update every caller to use try/except instead of `result["success"]` checks
3. Run `python -m pytest tests/ -x -q --timeout=60` to verify no regressions

### 3A: `src/giljo_mcp/tools/tool_accessor.py` (19 dict returns, 28 dependents -- HIGH RISK)

**Work function-by-function, not file-wide.** This file has 28 dependents in the dependency graph.

- [ ] **Line 70:** `return {"success": False, "error": "Project not found"}` --> `raise ResourceNotFoundError("Project not found")`
- [ ] **Line 73:** `return {"success": False, "error": f"Project cannot be activated from status '{project.status}'"}` --> `raise ProjectStateError(...)`
- [ ] **Line 83:** `return {"success": False, "error": "Parent product inactive or missing"}` --> `raise ProjectStateError("Parent product inactive or missing")`
- [ ] **Line 98:** `return {"success": False, "error": str(e)}` --> `raise` (re-raise or wrap in appropriate exception)
- [ ] **Line 550:** `return {"success": False, "error": "No tenant context available"}` --> `raise ValidationError("No tenant context available")`
- [ ] **Line 577:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 597:** `return {"success": False, "error": "No tenant context available"}` --> `raise ValidationError(...)`
- [ ] **Line 604:** `return {"success": False, "error": "Product not found"}` --> `raise ResourceNotFoundError("Product not found")`
- [ ] **Line 618:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 636:** `return {"success": False, "error": "No tenant context available"}` --> `raise ValidationError(...)`
- [ ] **Line 643:** `return {"success": False, "error": "Product not found"}` --> `raise ResourceNotFoundError("Product not found")`
- [ ] **Line 655:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 678:** `return {"success": False, "error": "content_type must be 'agent_templates' or 'slash_commands'"}` --> `raise ValidationError(...)`
- [ ] **Line 704:** `return {"success": False, "error": message}` --> `raise ValidationError(message)` or `raise ResourceNotFoundError(message)` depending on context
- [ ] **Line 730:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 865:** `return {"success": False, "error": "No active tenant"}` --> `raise ValidationError("No active tenant")`
- [ ] **Line 867:** `return {"success": False, "error": "project_id is required"}` --> `raise ValidationError("project_id is required")`
- [ ] **Line 881:** `return {"success": False, "error": "Project not found"}` --> `raise ResourceNotFoundError("Project not found")`
- [ ] **Line 898:** `return {"success": True, "project_id": project_id, "agent_count": len(agents)}` --> return the useful value directly, e.g. `return {"project_id": project_id, "agent_count": len(agents)}` (drop the success flag) or return a tuple
- [ ] **Find and update ALL 28 dependents** that check `result["success"]` or `result.get("success")`

### 3B: `src/giljo_mcp/tools/write_360_memory.py` (8 dict returns)

- [ ] **Line 232:** `return {"success": False, "error": "project_id is required"}` --> `raise ValidationError(...)`
- [ ] **Line 235:** `return {"success": False, "error": "summary is required"}` --> `raise ValidationError(...)`
- [ ] **Line 238:** `return {"success": False, "error": "db_manager is required"}` --> `raise ValidationError(...)`
- [ ] **Line 289:** `return {"success": False, "error": "Project not found or unauthorized for tenant"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 292:** `return {"success": False, "error": "Project not found or unauthorized for tenant"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 295:** `return {"success": False, "error": "Project not associated with product"}` --> `raise ValidationError(...)`
- [ ] **Line 308:** `return {"success": False, "error": "Product not found for project"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 453:** `return {"success": False, "error": str(exc)}` --> `raise`
- [ ] **Find and update all callers**

### 3C: `src/giljo_mcp/tools/project_closeout.py` (8 dict returns)

- [ ] **Line 54:** `return {"success": False, "error": "project_id is required"}` --> `raise ValidationError(...)`
- [ ] **Line 57:** `return {"success": False, "error": "summary is required"}` --> `raise ValidationError(...)`
- [ ] **Line 60:** `return {"success": False, "error": "db_manager is required"}` --> `raise ValidationError(...)`
- [ ] **Line 102:** `return {"success": False, "error": "Project not found or unauthorized for tenant"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 105:** `return {"success": False, "error": "Project not found or unauthorized for tenant"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 108:** `return {"success": False, "error": "Project not associated with product"}` --> `raise ValidationError(...)`
- [ ] **Line 120:** `return {"success": False, "error": "Product not found for project"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 223:** `return {"success": False, "error": str(exc)}` --> `raise`
- [ ] **Find and update all callers**

### 3D: `src/giljo_mcp/tools/agent.py` (9 dict returns)

- [ ] **Line 47:** `return {"success": False, "error": "Agent not found or tenant mismatch"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 62:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 91:** `return {"success": False, "error": "Project not found or tenant mismatch"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 102:** `return {"success": False, "error": "Parent agent not found or tenant mismatch"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 105:** `return {"success": True, "message": "Interaction validated"}` --> `return None` (or simply return; the success is implicit if no exception was raised)
- [ ] **Line 109:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 328:** `return {"success": False, "error": f"Agent execution '{agent_name}' not found"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 414:** `return {"success": False, "error": f"Project {project_id} not found"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 427:** `return {"success": False, "error": f"From agent '{from_agent}' not found"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 440:** `return {"success": False, "error": f"To agent '{to_agent}' not found"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Find and update all callers**

### 3E: `src/giljo_mcp/tools/context.py` (8 dict returns)

- [ ] **Line 77:** `return {"success": True, "index": index}` --> `return index`
- [ ] **Line 81:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 114:** `return {"success": False, "error": "No tenant context available"}` --> `raise ValidationError(...)`
- [ ] **Line 122:** `return {"success": False, "error": "Project not found"}` --> `raise ResourceNotFoundError(...)`
- [ ] **Line 153:** `return {"success": True, "index": index}` --> `return index`
- [ ] **Line 169:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 251:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 307:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 388:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Find and update all callers** -- callers currently checking `result["success"]` and reading `result["index"]` must change to direct assignment with try/except

### 3F: `src/giljo_mcp/tools/claude_export.py` (6 dict returns)

- [ ] **Line 76:** `return {"success": False, "error": str(e)}` --> `raise`
- [ ] **Line 80:** `return {"success": False, "error": f"Export failed: {e!s}"}` --> `raise ToolError(f"Export failed: {e!s}")`
- [ ] **Line 133:** `return {"success": False, "error": f"Path does not exist: {path}"}` --> `raise GiljoFileNotFoundError(...)`
- [ ] **Line 135:** `return {"success": False, "error": f"Path is not a directory: {path}"}` --> `raise FileSystemError(...)`
- [ ] **Line 144:** `return {"success": False, "error": "Product not found"}` --> `raise ResourceNotFoundError("Product not found")`
- [ ] **Line 159:** `return {"success": False, "error": f"Path validation failed: {e!s}"}` --> `raise FileSystemError(...)`
- [ ] **Find and update all callers**

### 3G: `src/giljo_mcp/context_management/chunker.py` (5 dict returns)

- [ ] **Line 285:** `return {"success": False, "error": f"Import error: {e}"}` --> `raise ContextError(...)`
- [ ] **Line 295:** `return {"success": False, "error": error_msg}` --> `raise ContextError(error_msg)`
- [ ] **Line 312:** `return {"success": False, "error": f"File not found: {normalized_path}"}` --> `raise GiljoFileNotFoundError(...)`
- [ ] **Line 320:** `return {"success": False, "error": error_msg}` --> `raise ContextError(error_msg)`
- [ ] **Line 325:** `return {"success": False, "error": error_msg}` --> `raise ContextError(error_msg)`
- [ ] **Find and update all callers**

### 3H: `src/giljo_mcp/context_management/manager.py` (1 dict return)

- [ ] **Line 67:** `return {"success": False, "chunks_created": 0, "total_tokens": 0, "message": "No content to chunk"}` --> `raise ContextError("No content to chunk")` OR return an empty result object (investigate caller expectations first)
- [ ] **Find and update all callers**

### 3I: `src/giljo_mcp/repositories/vision_document_repository.py` (1 dict return)

- [ ] **Line 222:** `return {"success": False, "message": "Document not found"}` --> `raise ResourceNotFoundError("Document not found")`
- [ ] **Find and update all callers**

### 3J: `src/giljo_mcp/tenant.py` (1 dict return -- CRITICAL RISK, 119 dependents)

**EXTREME CAUTION.** This file has 119 dependents. Read the function around line 299 completely. Understand who calls it and what they expect. Use `grep -rn 'validate_tenant\|get_tenant_key\|resolve_tenant' src/` (or whatever the function name is) to map every single caller before changing anything.

- [ ] **Line 299:** `return {"error": "Invalid tenant key"}` --> `raise ValidationError("Invalid tenant key")`
- [ ] **Find and update ALL callers** -- there may be many. Each one that checks for `"error"` in the result dict needs to change to try/except.

### 3K: `src/giljo_mcp/tools/context_tools/fetch_context.py` (1 dict return)

- [ ] **Line 204:** `return {"error": f"Invalid category: {category}", "valid_categories": ALL_CATEGORIES, "metadata": {}}` --> `raise ValidationError(f"Invalid category: {category}. Valid categories: {ALL_CATEGORIES}")`
- [ ] **Find and update all callers**

---

## Skipped Tests That May Become Fixable

Phase 2 skipped 8 unit test files because they assert on the old dict-return API. After this migration, some of these tests may need updating. **Do NOT unskip or rewrite these tests in this phase** -- just note which ones are now unblocked. The skip markers to look for:

```
reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns"
```

Files with this marker:
- `tests/unit/test_message_service.py`
- `tests/unit/test_orchestration_service.py`
- `tests/unit/test_product_service.py`
- `tests/unit/test_project_service.py`
- `tests/unit/test_project_service_deleted_state.py`
- `tests/unit/test_project_service_field_priorities.py`
- `tests/unit/test_task_service.py`
- `tests/unit/test_vision_repository_async.py`

Note: These tests may ALSO have fixture issues (separate skip markers). The dict-return migration alone may not make them pass.

---

## What NOT To Do

- Do NOT change any file outside `src/giljo_mcp/` (no test changes, no frontend, no docs)
- Do NOT create new exception classes unless absolutely none of the 30+ existing ones fit
- Do NOT unskip or modify the 0750b-skipped tests -- that is a separate concern
- Do NOT change functions that return dicts as part of MCP tool protocol responses (these are expected by the MCP protocol). If a function is an MCP tool handler that returns `{"content": [...]}` style MCP responses, leave it alone.
- Do NOT refactor, rename, or restructure files -- only change the return/raise pattern
- Do NOT modify `tenant.py` without first mapping ALL 119 dependents and confirming the dict return is not part of a broader contract
- Do NOT do file-wide find-and-replace -- investigate each dict return individually
- Do NOT change `return {"success": True, ...}` in functions where the caller depends on the dict structure for non-error data (investigate first)

---

## Acceptance Criteria

- [ ] `grep -rn 'return {"success": False' src/` returns zero matches
- [ ] `grep -rn 'return {"error":' src/` returns zero matches
- [ ] `grep -rn 'return {"success": True' src/` returns zero matches (or only MCP protocol returns)
- [ ] All modified functions raise exceptions from `giljo_mcp.exceptions` instead of returning error dicts
- [ ] All callers updated to use try/except instead of `result["success"]` checks
- [ ] `python -m pytest tests/ -x -q --timeout=60` still passes (same or better than baseline: 1238 passed, 522 skipped, 0 failed)
- [ ] No new exception classes created (unless justified and documented)

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
# If not: git checkout 0750-cleanup-sprint
```

### Step 2: Commit your changes
Stage only `src/` files. Do NOT stage test files, docs, or frontend.
```bash
git add src/giljo_mcp/tools/ src/giljo_mcp/context_management/ src/giljo_mcp/repositories/vision_document_repository.py src/giljo_mcp/tenant.py
git commit -m "refactor(0750c): Migrate 70 dict-return anti-patterns to exceptions across tools and context layers"
```

If the commit is too large, split into two commits:
```bash
# First commit: tool_accessor.py + its callers (largest, riskiest)
git add src/giljo_mcp/tools/tool_accessor.py
git commit -m "refactor(0750c): Migrate tool_accessor.py — 19 dict returns to exceptions"

# Second commit: all remaining files
git add src/giljo_mcp/tools/ src/giljo_mcp/context_management/ src/giljo_mcp/repositories/vision_document_repository.py src/giljo_mcp/tenant.py
git commit -m "refactor(0750c): Migrate remaining 51 dict returns across tools, context, repo, tenant"
```

### Step 3: Record the commit hash(es)
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, then update session `0750c`:
- Set `"status": "complete"`
- Set `"started_at"` and `"completed_at"` to timestamps
- Fill in `"tasks_completed"` with what you actually did (list each file migrated and count)
- Fill in `"deviations"` if you skipped any returns or changed approach
- Fill in `"blockers_encountered"` if you hit issues
- Fill in `"notes_for_next"` with: which dict returns were left (if any) and why, caller update status, any test impacts observed
- Fill in `"summary"` with a 2-3 sentence summary

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, then update `phases[2]`:
- Set `"status": "complete"`
- Set `"commits": ["<hash>"]` (or multiple hashes)
- Set `"notes"` to a brief summary including before/after dict-return counts

### Step 6: Verify acceptance criteria
Run these commands and confirm zero matches:
```bash
grep -rn 'return {"success": False' src/
grep -rn 'return {"error":' src/
grep -rn 'return {"success": True' src/
python -m pytest tests/ -x -q --timeout=60
```

### Step 7: Done
Do NOT spawn the next terminal. The orchestrator session handles chaining.
Print "0750c COMPLETE" as your final message.
