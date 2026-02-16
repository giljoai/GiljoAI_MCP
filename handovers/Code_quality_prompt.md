# Code Quality Audit Prompt

**Purpose:** Invoke this prompt to run a comprehensive code quality audit against the 0700 cleanup baseline. Agents reading this should launch parallel subagents and report findings with a quality score.

**Usage:** Ask an agent: "Read `handovers/Code_quality_prompt.md` and execute the audit."

**Frequency:** After every 15-30 commits, or before any release milestone.

---

## Instructions for the Executing Agent

You are performing a **post-cleanup code health audit** against the 0700 series baseline (architecture score 8/10, zero lint errors, ~15,800 lines removed). Your job is to detect drift from that clean state.

### Step 1: Scope the Audit

Determine the commit range to audit:

```bash
# See recent commits since last known-clean state
git log --oneline -30
git diff --stat HEAD~30..HEAD  # Adjust range as needed
```

Count files changed, lines added/removed. This frames the audit scope.

### Step 2: Quick Lint Check

Run this directly (do NOT delegate to a subagent - it takes seconds):

```bash
ruff check src/ api/
```

**Baseline:** Zero issues. Any issues are regressions.

### Step 3: Launch Parallel Audit Subagents

Launch **4 subagents in parallel** using the `deep-researcher` agent type. Each covers one domain:

#### Subagent 1: Backend Source Code (`src/giljo_mcp/`)

Search for:
- **Dead methods**: Use `find_referencing_symbols` on any method that looks unused. Zero refs = dead code.
- **Dict return regression**: After 0480/0730, services MUST raise exceptions (not return `{"success": False, ...}`). Grep for `return {"success": False` or `return {"error":` in services.
- **Bare expressions**: Statements that compute a value but never assign it (e.g., `len(x) // 4` on its own line).
- **Stale status values**: After 0491, valid agent statuses are ONLY: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`. Flag any code referencing old statuses (`active`, `pending`, `preparing`, `running`, `queued`, `paused`, `review`, `planning`, `failed`, `cancelled`, `completed`).
- **Duplicate logic**: Service layer vs tool layer doing the same thing.
- **Oversized functions**: Methods >250 lines that should be extracted.
- **Config reading pattern**: Repeated `yaml.safe_load(open("config.yaml"))` instead of using config_manager.

#### Subagent 2: API Endpoints (`api/`)

Search for:
- **Tenant isolation gaps**: Every DB query MUST filter by `tenant_key`. Look for endpoints that query without it.
- **Dict returns in endpoints**: After 0480, endpoints should raise `HTTPException`, not return `{"success": False}`.
- **Fake/placeholder data**: Any `random.randint()`, hardcoded metrics, or TODO stubs.
- **Duplicate endpoints**: Same functionality exposed on multiple routes.
- **Dead code in endpoints**: Unused imports, unreachable branches, commented-out blocks.
- **Oversized handler functions**: Single endpoint handlers >200 lines.

#### Subagent 3: Test Suite (`tests/`)

Search for:
- **Dead test fixtures**: Files in `tests/fixtures/` that are never imported by any test.
- **Unused imports**: Imports at top of test files that are never used.
- **Stale `__pycache__`**: Bytecode from deleted test modules (check `tests/*/__pycache__/` for .pyc files without matching .py).
- **Oversized test files**: Files >500 lines that should be split.
- **No-op fixtures**: Fixtures that just pass through without adding value.

#### Subagent 4: Frontend (`frontend/src/`)

Search for:
- **Dead code in views**: Unused variables (`const x = useX()` where `x` is never referenced in template or script).
- **Dead config fields**: Config objects with properties that are never read by consuming code.
- **Dead infrastructure**: Event handlers, confirmation dialogs, or UI patterns wired up but never triggered.
- **Dead store state**: Pinia/Vuex state properties that are set but never read.
- **Stale references**: References to removed backend features.

### Step 4: Consolidate Findings

After all subagents complete, compile results into a single report with this structure:

```
## Code Quality Audit Report
**Date:** YYYY-MM-DD
**Commit Range:** [first]...[last] (N commits)
**Files Changed:** N files, +X/-Y lines

### Lint Status
- Issues found: N (baseline: 0)

### Findings by Severity

#### SECURITY (fix immediately)
- [tenant isolation gaps, auth bypass, etc.]

#### HIGH (fix before next release)
- [dead methods >50 lines, dict return regressions, fake data]

#### MEDIUM (fix in next cleanup pass)
- [stale statuses, oversized functions, dead config fields]

#### LOW (housekeeping)
- [unused imports, dead fixtures, stale pycache]

### Migration Blockers
- [inverted dependencies, ToolAccessor direct calls, 
  test files importing dead layers]

### Quality Score
Rate the codebase 1-10 based on:
- Lint cleanliness (0 issues = 10/10)
- Dead code density (0 dead methods = 10/10)
- Pattern compliance (exceptions not dicts, tenant isolation)
- Test health (no dead fixtures, no stale imports)
- Frontend hygiene (no dead vars, no dead config)

**Overall Score: X/10** (baseline from 0700: 8/10, target: >= 7/10)
```

### Step 5: Prioritized Action List

End the report with a numbered action list, ordered by:
1. Security fixes (do immediately)
2. Quick wins (<5 minutes each, high impact)
3. Medium effort cleanup (15-30 minutes each)
4. Technical debt (requires planning)

For each item, include: file path, line number, what to do, estimated effort.

---

## What This Audit Does NOT Cover

- **Feature correctness** - This is a code hygiene audit, not a functional test.
- **Performance** - No load testing or query optimization analysis.
- **Full test execution** - We check test code quality, not whether tests pass (run `pytest` separately).
- **Frontend build** - We check source code quality, not whether `npm run build` succeeds.

---

## Historical Context

The 0700 cleanup series (Feb 2026) achieved:
- ~15,800 lines removed across ~110 files
- Zero ruff lint issues (down from 21K accumulated violations)
- Architecture score 8/10
- 7 deprecated DB columns dropped
- Dict-to-exception migration (0480/0730 series)
- Agent status simplified to 6 values (0491)

This audit ensures we don't regress from that baseline. Every finding is measured against the 0700 clean state.

---

## 0725 Audit Precedent Warning

A previous code health audit (0725) had a **75%+ false positive rate** due to naive static analysis. To avoid repeating this:

- **Always verify with `find_referencing_symbols`** before flagging dead code. LSP-based analysis catches real usage.
- **Check git blame/log** before flagging something as "newly introduced" - it may be pre-existing.
- **Distinguish product integration code from dead code**: References to `claude-code`, `codex`, `gemini` are product features, not bloat.
- **Slash commands infrastructure is intentional**: `SlashCommandSetup.vue`, `slash_commands/__init__.py`, `/slash/execute` endpoint are all live.
