# Handover: 0950b — Backend: Security + Dict-Returns + Exception Annotations

**Date:** 2026-04-05
**From Agent:** Documentation session (0950 sprint setup)
**To Agent:** Backend Integration Tester / TDD Implementor
**Priority:** High
**Edition Scope:** CE
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Sprint:** 0950 Pre-Release Quality Sprint (chain: `prompts/0950_chain/chain_log.json`)

---

## MANDATORY STARTUP SEQUENCE

Before doing anything else:

1. Read `prompts/0950_chain/chain_log.json` — check `orchestrator_directives` for your session ID (`0950b`) and read `notes_for_next` from session `0950a`.
2. Read `prompts/0950_chain/audit_baseline.md` — this is the 0950a output. Your work is scoped to the findings listed there. Do not invent new scope.
3. Read `handovers/Reference_docs/QUICK_LAUNCH.txt` and `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`.
4. Read `docs/EDITION_ISOLATION_GUIDE.md` — review the CE/SaaS boundary rules before touching any file.

---

## Task Summary

Fix the backend quick-win issues identified by the 0950a audit. The three categories are: dict-return regressions (services or endpoints returning error dicts instead of raising), unannotated broad exception catches, and stale TODO/REMOVED comment lines in production code. One known stub also exists in `api/endpoints/products/lifecycle.py` that must be resolved.

None of these changes alter API contracts or require frontend changes. They are internal code hygiene fixes.

**Expected outcome:** Zero unannotated broad `except Exception` catches, zero dict-return patterns in services and endpoints, no TODO/REMOVED comments in production code, all backend tests green.

---

## Context and Background

The post-0480 / post-0730 rule is firm: all Python layers raise exceptions on error. They never return `{"success": False, ...}` or `{"error": ...}`. The 0700 cleanup series enforced this across ~110 files. This session patches any regressions introduced since then.

The broad-exception annotation rule was established in 0765d: every `except Exception` must carry an inline comment (`# Broad catch: <reason>`) so reviewers can see the deliberate choice. Unannotated catches are indistinguishable from lazy error swallowing.

Known pre-existing finding (confirmed in source before 0950a ran):
- `api/endpoints/products/lifecycle.py:68` — `# TODO: Query for deactivated projects when ProjectService integration is complete` with a comment block and an empty list assigned to `deactivated_projects`. The ProjectService integration is considered complete as of 0731d. Either implement the query or drop the comment and document that the empty list is intentional behavior.

---

## Technical Details

### Scope

Fix only within these directories:
- `api/endpoints/`
- `src/giljo_mcp/services/`
- `src/giljo_mcp/tools/`
- `src/giljo_mcp/downloads/`

Do not touch `src/giljo_mcp/saas/`, `api/saas_endpoints/`, or `api/saas_middleware/` — those are out of scope for CE work.

### Task 1: Resolve dict-return regressions

Search for the pattern in services and endpoints:

```bash
grep -rn 'return {"success": False' src/giljo_mcp/services/ src/giljo_mcp/tools/ api/endpoints/
grep -rn 'return {"error":' src/giljo_mcp/services/ src/giljo_mcp/tools/ api/endpoints/
grep -rn 'return {"status": "error"' src/giljo_mcp/services/ src/giljo_mcp/tools/ api/endpoints/
```

For each hit:
- In a **service or tool**: replace with a raised exception. Use an existing exception class from `src/giljo_mcp/exceptions.py` (or the closest available) rather than creating new ones.
- In an **endpoint**: replace with `raise HTTPException(status_code=..., detail=...)`.
- Verify the caller handles the exception correctly (look one layer up). If the caller was catching a dict and checking `["success"]`, that catch must be updated to handle the exception instead.
- Do not change the HTTP response status code or response shape visible to the frontend — only change the internal propagation mechanism.

### Task 2: Annotate all unannotated broad exception catches

Search:

```bash
grep -rn 'except Exception' src/giljo_mcp/services/ src/giljo_mcp/tools/ src/giljo_mcp/downloads/ api/endpoints/
```

For each hit:
- Read the surrounding context (what is being caught, what is logged or re-raised).
- If the broad catch is intentional (e.g., "catch-all for unexpected downstream errors at a service boundary"), add an inline comment on the same line: `except Exception:  # Broad catch: <specific reason here>`
- If the broad catch is swallowing exceptions silently with no logging, that is a bug — either narrow the catch or add logging and re-raise.
- If the broad catch is wrapping a re-raise (e.g., `except Exception as e: raise SomeOtherError(str(e))`), add the annotation and confirm the wrapping is appropriate.

Valid annotation examples:
- `except Exception:  # Broad catch: subprocess may raise any OS error`
- `except Exception as e:  # Broad catch: third-party LLM client can raise unpredictably`
- `except Exception:  # Broad catch: WebSocket close can fail in many ways; log and continue`

### Task 3: Resolve the lifecycle.py deferred stub

File: `api/endpoints/products/lifecycle.py`
Location: lines 68-70 (the TODO block inside `activate_product`)

Current code (lines 68-70):
```python
# TODO: Query for deactivated projects when ProjectService integration is complete
# For now, return empty list as projects will be handled in future handover
deactivated_projects = []
```

Resolution options — pick ONE based on current state of ProjectService:

**Option A — ProjectService integration is available:** Implement the query. Use `ProjectService` (injected via `Depends`) to fetch projects that were paused/deactivated as part of this product activation. The `ProductActivationResponse.deactivated_projects` field is typed — populate it correctly. Write or update a unit test for this behavior.

**Option B — The empty list is correct behavior:** The `deactivated_projects` field may be informational and the response contract may intentionally allow an empty list when no projects were paused. In that case: delete both comment lines and replace with a single explanatory comment:
```python
# Project pause state is managed by ProductService.activate_product(); list remains
# empty here because the frontend polls project state separately after activation.
deactivated_projects = []
```

Check whether `ProductService.activate_product()` already handles project pausing internally. If it does, Option B is correct. If it does not, implement Option A.

Do not leave the word `TODO` in production code.

### Task 4: Delete stale comment lines

Search for comment-only lines matching these patterns in production code (not in tests):

```bash
grep -rn '# REMOVED:' src/giljo_mcp/ api/
grep -rn '# TODO:' src/giljo_mcp/services/ src/giljo_mcp/tools/ src/giljo_mcp/downloads/ api/endpoints/
```

For each hit:
- If it is a legitimate work item with no associated implementation: either implement it now (if it is within this session's scope and < 15 minutes) or convert it to a proper handover entry and delete the comment.
- If the TODO is already resolved (the implementation exists nearby): delete the comment.
- Never leave a `# TODO:` or `# REMOVED:` line in a committed production file.

Note: `# type: ignore` and `# noqa` directives are NOT TODO comments — leave those alone.

---

## Implementation Plan

### Phase 1: Grep and triage (20 min)

Run all four grep commands above. For each hit, classify it:
- Dict-return: fix now (Task 1)
- Unannotated broad catch: annotate now (Task 2)
- lifecycle.py TODO: resolve now (Task 3)
- Stale REMOVED/TODO comment: delete now (Task 4)

If 0950a flagged findings outside this scope (e.g., in `src/giljo_mcp/utils/` or other subdirectories), include those too.

### Phase 2: Make changes (60-90 min)

Work through the triage list. For each change:
- Verify no upstream callers break (trace the call chain one level up and one level down).
- For any dict-return converted to an exception: ensure the exception is imported or defined, and that the caller does not rely on the old dict shape.
- Every DB query you touch while implementing changes must filter by `tenant_key` — confirm this is true before moving on.

### Phase 3: Run checks (20 min)

```bash
# Must be 0 — no regressions
cd /media/patrik/Work/GiljoAI_MCP && ruff check src/ api/

# Must all pass
cd /media/patrik/Work/GiljoAI_MCP && python -m pytest tests/unit/ -q --timeout=60 --no-cov
```

If ruff reports new issues, fix them before committing. If tests fail, fix or delete the failing test — never skip.

### Phase 4: Commit

```bash
git add <specific files only — do not use git add -A>
git commit -m "cleanup(0950b): annotate broad catches, resolve lifecycle TODO, remove stale comments"
```

---

## Testing Requirements

### Unit Tests

- If Option A was chosen for Task 3 (implement the deactivated projects query), add a unit test in `tests/unit/test_product_endpoints.py` (or nearest equivalent) covering the new behavior.
- For each dict-return converted to an exception: check whether a test existed that was asserting the old dict shape. If so, update that test to expect the exception instead.
- No new tests are required purely for annotation changes (Task 2) or comment deletion (Task 4).

### Validation

After all changes:

1. `ruff check src/ api/` — must report 0 issues
2. `python -m pytest tests/unit/ -q --timeout=60 --no-cov` — all must pass, none skipped
3. `python -c "from api.app import create_app; print('OK')"` — must succeed

---

## Dependencies and Blockers

**Depends on:** 0950a — read `prompts/0950_chain/audit_baseline.md` before starting. The audit findings are your authoritative work list.

**Blockers:** None anticipated. If a dict-return conversion reveals a caller that fundamentally requires a dict response (e.g., a legacy test fixture using `assert result["success"]`), update the test — do not revert the fix.

---

## Success Criteria

1. `grep -rn 'return {"success": False' src/giljo_mcp/services/ src/giljo_mcp/tools/ api/endpoints/` returns zero results.
2. `grep -rn 'except Exception' src/giljo_mcp/services/ src/giljo_mcp/tools/ api/endpoints/` returns only hits where every line has an inline `# Broad catch:` annotation.
3. `api/endpoints/products/lifecycle.py` contains no `TODO` comment in the `activate_product` function.
4. `grep -rn '# REMOVED:\|# TODO:' src/giljo_mcp/services/ src/giljo_mcp/tools/ api/endpoints/` returns zero results.
5. `ruff check src/ api/` reports 0 issues.
6. `python -m pytest tests/unit/ -q --timeout=60 --no-cov` — all tests pass, none skipped.

---

## Rollback Plan

All changes are to existing production code files only (no new files, no migrations, no schema changes). If something goes wrong:

```bash
git diff --stat  # see what changed
git restore src/giljo_mcp/services/<file>.py  # revert specific file
```

The full git history preserves all original code.

---

## Agent Rules (Non-Negotiable)

- **Before deleting ANY code:** verify zero upstream and downstream references using grep and `find_referencing_symbols`. A dead method that appears unused may be called via reflection or registered dynamically.
- **Every DB query must filter by `tenant_key`** — if you touch a query while implementing Task 3 (Option A), confirm `tenant_key` filtering is present.
- **Tests that fail must be fixed or deleted** — never add `@pytest.mark.skip`.
- **No commented-out code** — delete it; git has the history.
- **No dict-return patterns** — raise exceptions.
- **Commit with descriptive message prefixed `cleanup(0950b):`**.
- **Update the chain log session entry** at `prompts/0950_chain/chain_log.json` before stopping — set `status` to `"complete"`, fill `tasks_completed`, `notes_for_next`, and `summary`.
- **Do NOT spawn the next terminal** — the orchestrator handles that.
- **Read `orchestrator_directives`** in the chain log FIRST before starting work.

---

## Progress Updates

*(Agent: fill this in as work proceeds)*

### [Date] — 0950b
**Status:** Not Started
**Work Done:** —
**Next Steps:** Read 0950a findings, run grep triage, work through task list.
