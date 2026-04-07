# Handover 0950c: Frontend: ESLint Budget + Commented-Out Code

**Date:** 2026-04-05
**From Agent:** Planning Session (0950 Pre-Release Quality Sprint)
**To Agent:** Next Session (frontend-tester or implementer profile)
**Priority:** High
**Estimated Complexity:** 1-2 hours
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0950c of 0950 chain — read `prompts/0950_chain/chain_log.json` first
**Depends On:** 0950a must be complete

---

## 1. Task Summary

Bring the frontend ESLint warning count from ~17 down to 8 or fewer, and eliminate all
commented-out code blocks from both Python backend files (7 identified) and Vue/JS
frontend files. This is a code hygiene session: no feature changes, no refactoring of
business logic — delete dead code and silence linter noise.

---

## 2. Context and Background

The 0950 Pre-Release Quality Sprint targets a code quality score of 9.0. Two of the
scoring rubric dimensions are directly addressed here:

- **Lint budget:** ESLint currently emits ~17 warnings. The sprint budget is 8. Most
  violations are dead variables, unused imports, stray `console.log` calls, and a handful
  of `vue/no-v-html` occurrences on server-controlled content.
- **Commented-out code:** Zero tolerance per project convention. Git has the history.
  Seven Python files were flagged in the audit; Vue components may also contain stale
  comment blocks.

The 0950a audit session establishes the exact warning list. Read its `notes_for_next`
in the chain log before starting — the audit agent may have identified specific files
and line numbers that narrow the search.

---

## 3. Chain Execution Instructions (Orchestrator-Gated v3)

You are a session in the 0950 chain on branch `feature/0950-pre-release-quality`.

### Step 1: Read Chain Log and Directives
Read `/media/patrik/Work/GiljoAI_MCP/prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` in your session entry (0950c). If it contains "STOP",
  halt and report immediately.
- Read 0950a's `notes_for_next` for exact warning counts, file list, and any deviations
  from the plan that affect this session.

### Step 2: Verify Prerequisite
Confirm 0950a status is `"complete"` in the chain log. If not, STOP and report.

### Step 3: Mark Session Started
Update your entry in the chain log:
```json
"status": "in_progress"
```

### Step 4: Execute (see Section 5 below)

### Step 5: Update Chain Log Before Stopping
Fill in `tasks_completed`, `deviations`, `notes_for_next` (for 0950d — list any
components you edited so 0950d avoids simultaneous edits), `summary`, `status: "complete"`.

### Step 6: Commit and STOP
```bash
git add -A
git commit -m "cleanup(0950c): ESLint budget — fix warnings, remove commented-out code"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950c chain log — session complete"
```

Do NOT spawn the next terminal. The orchestrator handles that.

---

## 4. Critical Agent Rules (Read Before Touching Any File)

- **Before deleting ANY code:** verify zero upstream/downstream references using grep.
  A "dead" variable may be referenced in a template via `v-model` or `:prop` binding.
- **Tests that fail must be fixed or deleted — never skip.** If your change breaks a
  Vitest test, fix the test or delete it if it tests removed code.
- **No commented-out code.** Any block you find gets deleted, not re-commented.
- **Read `frontend/design-system-sample-v2.html`** as the authoritative UI/brand
  reference before making any template changes.
- Commit with prefix `cleanup(0950c):` on all commits.

---

## 5. Implementation Plan

### Phase 1: ESLint Baseline

Run from the repo root (use absolute paths in all commands):

```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx eslint src/ --max-warnings 8
```

This will fail (~17 warnings) and list every violation. Save the output — you need the
exact file paths and rule names. The expected violation categories are:

| ESLint Rule | Typical Fix |
|---|---|
| `no-unused-vars` | Delete the variable/import after grepping for template usage |
| `no-console` (`console.log`) | Change to `console.warn` with a justification comment, or delete if debugging noise |
| `vue/no-v-html` | Add `// eslint-disable-next-line vue/no-v-html` with a one-line comment: `// Content is server-controlled markdown — XSS risk accepted` |

### Phase 2: Fix Each ESLint Violation

For every warning in the ESLint output:

1. **Unused imports/variables:**
   - Grep the filename for the symbol across the entire file (template + script).
   - If genuinely unused: delete the import line or variable declaration.
   - If used in template but ESLint misses it (e.g., a composable return value accessed
     via destructuring): add `// eslint-disable-next-line no-unused-vars` with a note.

2. **`console.log` calls:**
   - If it is a debug trace with no operational value: delete the line.
   - If it is a genuine warning/error that should stay: change `console.log` to
     `console.warn` or `console.error` as appropriate.

3. **`vue/no-v-html`:**
   - Only suppress when content is verifiably server-controlled (API response that has
     already been sanitized server-side, or static markdown rendered by marked/DOMPurify).
   - Use: `<!-- eslint-disable-next-line vue/no-v-html -->` in the template, followed
     by a comment line: `<!-- Content sanitized by DOMPurify server-side -->`.
   - If the content is user-generated or from an untrusted source: replace `v-html`
     with a text binding or a sanitization wrapper.

### Phase 3: Commented-Out Code — Python Files

These 7 Python files were identified in the 0950a audit as containing commented-out
code blocks:

- `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/logging/__init__.py`
- `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/template_manager.py`
- `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/tools/agent_coordination.py`
- `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/services/orchestration_service.py`
- `/media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/template_renderer.py`
- `/media/patrik/Work/GiljoAI_MCP/api/endpoints/users.py`
- `/media/patrik/Work/GiljoAI_MCP/api/app.py`

For each file:
1. Open the file and locate all `# ...` comment blocks that contain code (function calls,
   assignments, imports, old logic).
2. Run `git blame <file>` to understand when and why they were commented out.
3. If the code is clearly superseded or replaced: delete it.
4. If context is ambiguous: check git log for the surrounding commit message. If the
   commit was a cleanup/refactor, delete. If it was a "temp disable", still delete —
   git has the history.
5. Pure explanatory prose comments (not code) are fine to leave.

### Phase 4: Commented-Out Code — Vue/JS Files

Scan for multi-line HTML comment blocks containing what looks like code:

```bash
grep -rn "<!--" /media/patrik/Work/GiljoAI_MCP/frontend/src/ --include="*.vue" | grep -v "^.*<!--\s*$" | grep -E "v-|:[\w]|@[\w]|\{\{" | head -40
```

Also scan for multi-line JS comment blocks in `.js` and `.vue` files:

```bash
grep -rn "/\*" /media/patrik/Work/GiljoAI_MCP/frontend/src/ --include="*.vue" --include="*.js" | grep -v "eslint-disable\|jshint\|global\|@" | head -40
```

For each hit: determine if it is explanatory documentation (leave it) or commented-out
functional code (delete it).

### Phase 5: Verify

```bash
# ESLint must pass under budget
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx eslint src/ --max-warnings 8

# All frontend tests must pass
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run

# Python lint must be clean (don't introduce regressions in Python files)
cd /media/patrik/Work/GiljoAI_MCP && ruff check src/ api/
```

---

## 6. Files in Scope

**Primary (frontend):**
- Any file in `frontend/src/` flagged by ESLint in Phase 1

**Secondary (Python — commented-out code only, no logic changes):**
- `src/giljo_mcp/logging/__init__.py`
- `src/giljo_mcp/template_manager.py`
- `src/giljo_mcp/tools/agent_coordination.py`
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/template_renderer.py`
- `api/endpoints/users.py`
- `api/app.py`

**Do NOT touch** (these are in scope for 0950d/0950e and editing them simultaneously
causes conflicts):
- Dialog chrome in Vue components (handled by 0950d)
- Hardcoded hex color values (handled by 0950e)

---

## 7. Testing Requirements

- `npx eslint src/ --max-warnings 8` passes (exit code 0)
- `npx vitest run` — all tests pass, no new failures
- `ruff check src/ api/` — clean, no regressions from Python edits
- Visual spot-check: open the app and verify no obvious regressions in at least one
  dialog and one table view

---

## 8. Success Criteria

- ESLint warning count is 8 or fewer
- Zero commented-out code blocks in all 7 Python files listed above
- Zero commented-out code blocks in Vue/JS files (confirmed by grep)
- All Vitest tests pass
- Ruff reports clean on Python files

---

## 9. Rollback Plan

All changes are deletions. Git revert is trivial:
```bash
git revert HEAD
```
No schema changes, no new files, no dependency changes.

---

## 10. Additional Resources

- `frontend/design-system-sample-v2.html` — authoritative UI/brand reference (open in browser)
- `frontend/src/styles/main.scss` — dialog classes, smooth-border, text-muted-a11y
- `frontend/src/styles/design-tokens.scss` — all SCSS tokens
- `prompts/0950_chain/chain_log.json` — orchestrator directives and 0950a notes

---

## Progress Updates

*(Agent updates this section during execution)*
