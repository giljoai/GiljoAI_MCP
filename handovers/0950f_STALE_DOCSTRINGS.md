# Handover: 0950f — Backend: Stale Docstrings + Dead Pass Statements

**Date:** 2026-04-05
**From Agent:** Documentation session (0950 sprint setup)
**To Agent:** Backend Integration Tester / Documentation Manager
**Priority:** Medium
**Edition Scope:** CE
**Estimated Complexity:** 1-2 hours
**Status:** Not Started
**Sprint:** 0950 Pre-Release Quality Sprint (chain: `prompts/0950_chain/chain_log.json`)

---

## MANDATORY STARTUP SEQUENCE

Before doing anything else:

1. Read `prompts/0950_chain/chain_log.json` — check `orchestrator_directives` for your session ID (`0950f`) and read `notes_for_next` from session `0950b`.
2. Read `prompts/0950_chain/audit_baseline.md` — this is the 0950a output. Cross-reference any docstring or pass-statement findings logged there before adding your own search results.
3. Read `handovers/Reference_docs/QUICK_LAUNCH.txt` and `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`.

---

## Task Summary

Sweep `src/giljo_mcp/` for three classes of doc/code hygiene issue: stale status value references in docstrings and comments, bare `pass` statements in non-trivial production code paths, and stale "not yet implemented" or "(legacy)" markers on methods and schema fields that are actually implemented. Remove or update each finding.

No API contracts change. No migrations. No frontend changes. This is documentation accuracy work inside the Python source.

---

## Context and Background

### Valid agent statuses (post-0491, 0880)

The valid agent statuses are exactly:
`waiting`, `working`, `blocked`, `idle`, `sleeping`, `complete`, `silent`, `decommissioned`

Old statuses from before 0491 still appear in some docstrings and comments. These mislead future developers into thinking the old values are still valid:
- `active` (replaced by `idle` or `working`)
- `pending` (replaced by `waiting`)
- `preparing` (removed)
- `cancelled` (removed)
- `failed` (removed)
- `running` (replaced by `working`)
- `queued` (replaced by `waiting`)
- `paused` (removed)
- `review` (removed)
- `planning` (removed)
- `completed` (replaced by `complete`)

Note: these old values may appear legitimately in test fixtures (as historical data), in migration files (for upgrade logic), and in documentation describing the transition. Flag only occurrences in **production code** under `src/giljo_mcp/` that describe current behavior.

### Scope

Strictly: `src/giljo_mcp/`

Do not touch:
- `tests/` — test fixtures may legitimately reference old statuses for regression coverage
- `migrations/` — migration files may reference old status values for upgrade paths
- `api/` — covered by 0950b
- Frontend — covered by 0950c/0950d/0950e

---

## Technical Details

### Task 1: Stale status value references in docstrings and comments

Search:

```bash
grep -rn '"active"\|"pending"\|"preparing"\|"cancelled"\|"failed"\|"running"\|"queued"\|"paused"\|"review"\|"planning"\|"completed"' \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/
```

Also check for unquoted references in comments:

```bash
grep -rn '#.*\bactive\b\|#.*\bpending\b\|#.*\bpreparing\b\|#.*\bcancelled\b\|#.*\bfailed\b' \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/
```

For each hit:

- **In a docstring describing what values a field or parameter accepts:** Update to list only the valid statuses above.
- **In a comment describing expected behavior:** Update the comment to reflect current behavior, or delete it if it is no longer accurate.
- **In a docstring that lists an example value:** Update the example to use a valid status.
- **In actual code logic** (not a string in a comment/docstring): This is out of scope for this session — flag it in the chain log as a new finding for 0950b or escalate to the orchestrator. Do not fix logic bugs here.

Do not change the values of Python string literals used in `if` conditions, `==` comparisons, or dict lookups — those are logic changes, not documentation changes.

### Task 2: Audit bare `pass` statements in production code

Search:

```bash
grep -rn '^\s*pass$' /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/
```

For each hit, classify it:

**Intentional and correct — leave it:**
- `__init__.py` files that only exist for package namespace
- Abstract method bodies: `def my_method(self): pass` or `raise NotImplementedError`
- Exception class bodies: `class MyError(Exception): pass`
- Protocol/ABC method stubs that are intentionally unimplemented at the base class level

**Suspicious — investigate and fix:**
- `pass` as the only statement inside a non-abstract, non-init method body in a service, tool, or repository. If the method is called and does nothing, it is either dead code or a bug.
- `except SomeError: pass` — silently swallowed exceptions are bugs. Add a log statement at minimum, or re-raise.
- `pass` inside an `if`/`else` branch in a service or tool. If the branch is intentional no-op, add a comment explaining why. If the branch is unreachable, delete it.

For each suspicious `pass`:
1. Use `find_referencing_symbols` to confirm whether the method is called anywhere.
2. If it is called and does nothing: determine whether it should do something (and add a TODO-free implementation) or whether it should be deleted along with its callers.
3. If it is never called: delete the method entirely (after confirming zero references).

### Task 3: Remove stale "not yet implemented" docstrings from implemented methods

Search:

```bash
grep -rn 'not yet implemented\|Not yet implemented\|not implemented\|TODO: implement' \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/
```

For each hit:
- Read the method body. If the method has an actual implementation (more than `pass` or `raise NotImplementedError`), delete the stale qualifier from the docstring.
- If the method truly is not implemented (body is `pass` or `raise NotImplementedError`), that is a Task 2 finding — treat accordingly.
- Never delete the whole docstring just because the "not yet implemented" line was there — update the docstring to describe what the method actually does.

### Task 4: Remove `(legacy)` labels from schema field descriptions

Search:

```bash
grep -rn '(legacy)' /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/
```

For each hit in a Pydantic model `Field(description=...)` or similar schema annotation:
- If the field is still in active use (it appears in serialized responses or API docs): remove the `(legacy)` label from the description string. It is not legacy — calling it so is misleading.
- If the field is genuinely deprecated and should be removed: do not remove it here (that is a schema/migration change). Add a note to the chain log for a future session.

---

## Implementation Plan

### Phase 1: Grep and triage (20 min)

Run all search commands above. Build a flat list of hits, classified by task. Cross-reference with the 0950a baseline audit to avoid duplicating work already claimed by 0950b.

### Phase 2: Make changes (40-60 min)

Work through the list:
- Docstring updates are low-risk: read, update, move on.
- Pass-statement removals require a reference check first — do not delete without confirming zero callers.
- For every file you touch: ensure no new ruff issues are introduced.

### Phase 3: Run checks (15 min)

```bash
# Must be 0
cd /media/patrik/Work/GiljoAI_MCP && ruff check src/ api/

# All must pass, none skipped
cd /media/patrik/Work/GiljoAI_MCP && python -m pytest tests/unit/ -q --timeout=60 --no-cov
```

### Phase 4: Commit

```bash
git add <specific files only>
git commit -m "cleanup(0950f): remove stale status names from docstrings, audit bare pass statements, drop legacy field labels"
```

---

## Testing Requirements

### Unit Tests

- No new tests are required for docstring changes.
- If a bare `pass` method is deleted (Task 2), confirm no test was asserting the method's existence or calling it. If a test was, delete the test too — it was testing a no-op.
- If a `except SomeError: pass` is replaced with logging + re-raise, confirm existing tests still pass (the exception will now propagate where it previously was swallowed).

### Validation

After all changes:

1. `ruff check src/ api/` — must report 0 issues.
2. `python -m pytest tests/unit/ -q --timeout=60 --no-cov` — all must pass, none skipped.

---

## Dependencies and Blockers

**Depends on:** 0950b — this session reads `notes_for_next` from 0950b. If 0950b flagged any stale status or docstring issues it deferred here, pick those up.

**Blockers:** None anticipated.

**Coordination note:** If 0950b is still in progress when this session starts, read its chain log entry for any in-progress files to avoid conflicts.

---

## Success Criteria

1. `grep -rn '"active"\|"pending"\|"preparing"\|"cancelled"\|"failed"' src/giljo_mcp/` returns zero hits in docstrings and comments (test files excluded).
2. `grep -rn 'not yet implemented\|TODO: implement' src/giljo_mcp/` returns zero hits.
3. `grep -rn '(legacy)' src/giljo_mcp/` returns zero hits in schema field descriptions.
4. Every bare `pass` remaining in `src/giljo_mcp/` production code paths (non-init, non-abstract) has been confirmed intentional or deleted.
5. `ruff check src/ api/` reports 0 issues.
6. `python -m pytest tests/unit/ -q --timeout=60 --no-cov` — all tests pass, none skipped.

---

## Rollback Plan

All changes are to docstrings and comments in existing Python files. No schema changes, no migrations, no API changes. Rollback by reverting specific files:

```bash
git restore src/giljo_mcp/<path/to/file>.py
```

---

## Agent Rules (Non-Negotiable)

- **Before deleting ANY code:** verify zero upstream and downstream references using grep and `find_referencing_symbols`. This applies especially to bare `pass` method bodies — confirm zero callers before deleting.
- **Every DB query must filter by `tenant_key`** — if you happen to touch a query while investigating a bare `pass`, confirm `tenant_key` filtering is present.
- **Tests that fail must be fixed or deleted** — never add `@pytest.mark.skip`.
- **No commented-out code** — delete it; git has the history.
- **No dict-return patterns** — exceptions only (if you encounter one, flag it in the chain log for 0950b rather than fixing it here, since 0950b is already complete by the time this session runs).
- **Commit with descriptive message prefixed `cleanup(0950f):`**.
- **Update the chain log session entry** at `prompts/0950_chain/chain_log.json` before stopping — set `status` to `"complete"`, fill `tasks_completed`, `notes_for_next`, and `summary`.
- **Do NOT spawn the next terminal** — the orchestrator handles that.
- **Read `orchestrator_directives`** in the chain log FIRST before starting work.

---

## Progress Updates

*(Agent: fill this in as work proceeds)*

### [Date] — 0950f
**Status:** Not Started
**Work Done:** —
**Next Steps:** Read 0950b notes, run grep sweep, triage and fix findings.
