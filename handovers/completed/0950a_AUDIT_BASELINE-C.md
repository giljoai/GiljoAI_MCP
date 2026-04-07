# Handover: 0950a — Comprehensive Audit: Establish Baseline Score

**Date:** 2026-04-05
**From Agent:** Documentation session (0950 sprint setup)
**To Agent:** Deep Researcher (read-only audit mode)
**Priority:** High
**Edition Scope:** CE
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Sprint:** 0950 Pre-Release Quality Sprint (chain: `prompts/0950_chain/chain_log.json`)

---

## MANDATORY STARTUP SEQUENCE

Before doing anything else:

1. Read `prompts/0950_chain/chain_log.json` — check `orchestrator_directives` for your session ID (`0950a`) before starting.
2. Read `handovers/Reference_docs/QUICK_LAUNCH.txt` and `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`.
3. Read `handovers/Reference_docs/Code_quality_prompt.md` — this defines the full 10-dimension rubric you will score against.
4. This is a **read-only audit**. Do NOT modify any source files.

---

## Task Summary

Execute the full Code_quality_prompt.md protocol across the entire CE codebase and produce an authoritative baseline quality score with all findings itemized by severity. This score and findings list will drive every subsequent 0950-series session.

The 0769 sprint (March 2026) established an 8.5/10 baseline. This audit determines whether that baseline has been maintained or degraded by the handovers that followed (0880 onward, through the UI changes in `f8a87bf9`).

The output of this session is a single file: `prompts/0950_chain/audit_baseline.md`. No code changes. All decisions deferred to 0950b onward.

---

## Context and Background

The 0950 sprint targets a 9.0/10 quality score before the CE release. Sessions 0950b through 0950m are each scoped to a specific class of issue. This session (0950a) establishes what those issues actually are, so downstream sessions do not waste time on false positives.

Known likely areas of concern from git log since 0769:
- `feat(ui)` commits (f8a87bf, b5d6f8d, 47dc1fcd, 8e8e9f4e) — frontend-only changes, potential hardcoded colors, dialog anatomy deviations.
- `ffee9931` — modal rewrite, large component change.
- `api/endpoints/products/lifecycle.py:68` — deferred TODO comment known to exist.

Baseline numbers to beat or match:
- Ruff: 0 issues
- ESLint: 6 warnings (budget 8)
- Frontend build: clean, main chunk ~736KB
- CE/SaaS boundary: 0 violations
- Frontend tests: 1,893 pass, 0 skip, 0 fail
- Backend unit tests: 661 pass, 0 fail
- Overall quality score: 8.5/10

---

## Technical Details

### Files to Examine

This is a whole-codebase audit. Priority areas:

- `src/giljo_mcp/` — services, tools, models, orchestration
- `api/endpoints/` — all endpoint modules
- `api/endpoints/products/lifecycle.py` — known TODO at line 68
- `frontend/src/` — components, composables, stores, views
- `tests/unit/` — skips, dead fixtures, coverage gaps
- `scripts/check_saas_import_boundary.py` — run it; do not read it

### Automated Checks (run all of these; record exact output)

Run from `/media/patrik/Work/GiljoAI_MCP`:

```bash
# 1. Backend linting — baseline: 0 issues
ruff check src/ api/

# 2. Frontend linting — budget: 8 warnings max
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx eslint src/ --max-warnings 8

# 3. Frontend build — baseline: clean
cd /media/patrik/Work/GiljoAI_MCP/frontend && npm run build

# 4. CE/SaaS import boundary — baseline: 0 violations
python /media/patrik/Work/GiljoAI_MCP/scripts/check_saas_import_boundary.py \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/

# 5. Frontend tests — baseline: 1,893+ pass, 0 skip, 0 fail
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run

# 6. Backend unit tests — baseline: 661+ pass, 0 fail (no DB required)
cd /media/patrik/Work/GiljoAI_MCP && python -m pytest tests/unit/ -q --timeout=60 --no-cov

# 7. Startup import check — must succeed without a running database
python -c "from api.app import create_app; print('Startup import OK')"
```

Record the **exact** pass/fail/warning counts from each command. Any regression from the baseline numbers above is a finding.

### Subagent Scope

Launch 5 parallel subagents as defined in `handovers/Reference_docs/Code_quality_prompt.md`:

- **Subagent 1 — Backend source** (`src/giljo_mcp/`): dead methods, dict-return regressions, broad exception catches without inline justification, stale status values, oversized functions.
- **Subagent 2 — API endpoints and security** (`api/`): tenant isolation gaps, auth gaps, CSRF, dict returns, hardcoded secrets, CORS.
- **Subagent 3 — Test suite** (`tests/`): skipped tests, dead fixtures, stale pycache.
- **Subagent 4 — Frontend** (`frontend/src/`): dead code, hardcoded hex colors, `!important` overrides, stale backend references.
- **Subagent 5 — Convention and documentation** (whole repo): forbidden terms ("MIT", "open source", "open core"), version consistency, commented-out code, stale status names in docstrings.

**False positive prevention (mandatory):**
- Use `find_referencing_symbols` before flagging dead code — grep alone misses live usages.
- `active`, `pending`, `preparing`, `cancelled`, `failed` are stale statuses. Valid statuses: `waiting`, `working`, `blocked`, `idle`, `sleeping`, `complete`, `silent`, `decommissioned`.
- Slash command infrastructure (`SlashCommandSetup.vue`, `slash_commands/__init__.py`, `/slash/execute`) is intentional — not dead code.
- Product integration references (claude-code, codex, gemini) are features — not bloat.

---

## Implementation Plan

### Phase 1: Run automated checks (30 min)

Run all 7 automated checks listed above. Record exact output. Any deviation from baseline numbers is a finding that must be logged.

### Phase 2: Launch parallel audit subagents (60-90 min)

Launch all 5 subagents as defined in Code_quality_prompt.md. Collect findings.

### Phase 3: Score and compile output file (30 min)

Produce `prompts/0950_chain/audit_baseline.md` using this exact format:

```markdown
## Code Quality Audit — 0950 Baseline
**Date:** 2026-04-05
**Commit:** [git show --format="%H %s" -s HEAD]
**Auditor:** 0950a

### Automated Check Results
- Ruff: N issues (baseline: 0) — [PASS/FAIL]
- ESLint: N warnings (budget: 8) — [PASS/FAIL]
- Frontend build: [clean/N warnings] — [PASS/FAIL]
- CE/SaaS boundary: N violations (baseline: 0) — [PASS/FAIL]
- Frontend tests: N pass / N skip / N fail (baseline: 1893+/0/0) — [PASS/FAIL]
- Backend unit tests: N pass / N fail (baseline: 661+/0) — [PASS/FAIL]
- Startup import: [OK/FAIL] — [PASS/FAIL]

### 10-Dimension Rubric Scores

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | Lint cleanliness | X/10 | |
| 2 | Dead code density | X/10 | |
| 3 | Pattern compliance | X/10 | |
| 4 | Tenant isolation | X/10 | |
| 5 | Security posture | X/10 | |
| 6 | Test health | X/10 | |
| 7 | Frontend hygiene | X/10 | |
| 8 | Exception handling | X/10 | |
| 9 | Code organization | X/10 | |
| 10 | Convention & docs | X/10 | |

**Overall Score: X.X/10** (baseline: 8.5, target: 9.0)

### Findings by Severity

#### SECURITY
- [file:line] description

#### HIGH
- [file:line] description

#### MEDIUM
- [file:line] description

#### LOW
- [file:line] description

### Prioritized Action List
1. [SECURITY] file:line — what to do — <5 min
2. ...
```

Every finding must include: file path, line number (or range), what the issue is, and which downstream session (0950b–0950l) should address it.

---

## Testing Requirements

This session has no code changes and therefore no tests to run beyond the automated checks above.

---

## Dependencies and Blockers

**Depends on:** Nothing. This is the first session in the chain.

**Blockers:** None anticipated. If `npm run build` fails with an out-of-memory error, add `NODE_OPTIONS=--max-old-space-size=4096` prefix.

---

## Success Criteria

1. `prompts/0950_chain/audit_baseline.md` exists and contains a score for all 10 dimensions.
2. Every finding includes file path, line number, severity, and target session.
3. All 7 automated checks have been run and results recorded (pass or fail, with exact counts).
4. No source files have been modified.
5. Chain log updated before stopping.

---

## Rollback Plan

Read-only session — no rollback required.

---

## Agent Rules (Non-Negotiable)

- **Before deleting ANY code:** verify zero upstream and downstream references using grep and `find_referencing_symbols`. (This session makes no deletions — note this for downstream sessions.)
- **Every DB query must filter by `tenant_key`** — verify after any refactoring.
- **Tests that fail must be fixed or deleted** — never skip.
- **No commented-out code** — delete it; git has the history.
- **No dict-return patterns** — exceptions only.
- **Commit with descriptive message prefixed `cleanup(0950a):`** when done.
- **Update the chain log session entry** at `prompts/0950_chain/chain_log.json` before stopping — set `status` to `"complete"`, fill `tasks_completed`, `notes_for_next`, and `summary`.
- **Do NOT spawn the next terminal** — the orchestrator handles that.
- **Read `orchestrator_directives`** in the chain log FIRST before starting work.

---

## Progress Updates

*(Agent: fill this in as work proceeds)*

### [Date] — 0950a
**Status:** Not Started
**Work Done:** —
**Next Steps:** Run automated checks, launch subagents, compile findings.
