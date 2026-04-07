# Handover 0950m: Final Audit: Full Re-Run + PASS/FAIL Verdict

**Date:** 2026-04-05
**From Agent:** Planning Session
**To Agent:** Next Session (audit-focused)
**Priority:** Critical
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0950m of 0950a–0950n — read `prompts/0950_chain/chain_log.json` first

---

## 1. Task Summary

Re-execute the full code quality audit against the entire codebase after all 0950a–0950l work is complete. Score all 10 dimensions using the rubric from `handovers/Reference_docs/Code_quality_prompt.md`. Produce a PASS or FAIL verdict. PASS requires all hard gates met and a score of >= 9.0/10. FAIL triggers the conditional 0950n remediation handover.

---

## 2. Context and Background

The 0950 sprint baseline is documented in `prompts/0950_chain/audit_baseline.md` (written by session 0950a). Sessions 0950b–0950l addressed every finding from that baseline audit. This session measures whether those fixes achieved the target score.

The 0769 sprint baseline (referenced in `Code_quality_prompt.md`) was 8.5/10 with 1,893 frontend tests, 661 backend unit tests, zero ruff issues, and ESLint 6 warnings. The 0950 target is 9.0/10 with the same test floor.

This handover depends on ALL prior handovers (0950a through 0950l) being complete. Confirm every session shows `"status": "complete"` in the chain log before running any check.

**Critical agent rules — read before touching any file:**
- Before deleting ANY code: verify zero upstream/downstream references using grep
- Tests that fail must be fixed or deleted — never skip
- No commented-out code — delete it
- Commit with descriptive message prefixed `cleanup(0950m):`
- Update chain log session entry at `prompts/0950_chain/chain_log.json` before stopping
- Do NOT spawn the next terminal — orchestrator handles that
- Read `orchestrator_directives` in chain log FIRST before starting work

---

## 3. Technical Details

### Scope

Entire codebase: `src/`, `api/`, `frontend/src/`, `tests/`, `frontend/tests/`

### Output file

Write the full audit report to:
```
/media/patrik/Work/GiljoAI_MCP/prompts/0950_chain/audit_final.md
```

Use the standard 10-dimension rubric format from `handovers/Reference_docs/Code_quality_prompt.md`.

---

## 4. Implementation Plan

### Step 1: Read the audit protocol

Read `handovers/Reference_docs/Code_quality_prompt.md` in full. The audit procedure there is the authoritative source. The steps below are a checklist overlay specific to the 0950 sprint — they supplement, not replace, that document.

### Step 2: Confirm all prerequisites complete

```
Read prompts/0950_chain/chain_log.json
```

Every session from 0950a through 0950l must show `"status": "complete"`. If any session is not complete, halt and write a blocker.

### Step 3: Run all automated checks

Execute each check and record the exact output. Any regression from baseline is a finding that affects scoring.

**Backend lint:**
```bash
cd /media/patrik/Work/GiljoAI_MCP
ruff check src/ api/
```
Target: 0 issues.

**Frontend lint:**
```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx eslint src/ --max-warnings 8
```
Target: <= 8 warnings (pass the `--max-warnings 8` flag so this is machine-verifiable).

**Frontend build:**
```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npm run build
```
Target: clean build with no errors.

**CE/SaaS import boundary:**
```bash
cd /media/patrik/Work/GiljoAI_MCP
python scripts/check_saas_import_boundary.py src/ api/ frontend/src/
```
Target: 0 violations.

**Frontend test suite:**
```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run 2>&1 | tail -10
```
Target: >= 1893 pass, 0 skip, 0 fail.

**Backend unit tests:**
```bash
cd /media/patrik/Work/GiljoAI_MCP && python -m pytest tests/unit/ -q --timeout=60 --no-cov 2>&1 | tail -5
```
Target: >= 661 pass, 0 fail, 0 skip.

**Application startup:**
```bash
cd /media/patrik/Work/GiljoAI_MCP && python -c "from api.app import create_app; print('OK')"
```
Target: prints "OK" with no import errors or tracebacks.

### Step 4: Launch parallel audit subagents

Follow the 5-subagent structure from `Code_quality_prompt.md`:

- Subagent 1: Backend source (`src/giljo_mcp/`) — dead methods, dict-return regression, broad exception catches, stale status values, oversized functions
- Subagent 2: API endpoints (`api/`) — tenant isolation gaps, auth gaps, CSRF, secrets in source, oversized handlers
- Subagent 3: Test suite (`tests/`, `frontend/tests/`, `frontend/src/**/*.spec.js`) — skipped tests, dead fixtures, coverage gaps
- Subagent 4: Frontend (`frontend/src/`) — hardcoded hex colours, accessibility, dead code, stale backend references
- Subagent 5: Convention compliance — forbidden terminology, version consistency, CE/SaaS boundary, commented-out code, AI signatures

Use the `deep-researcher` agent type for all five subagents. Wait for all five to complete before scoring.

### Step 5: Compare against baseline

Read `prompts/0950_chain/audit_baseline.md` (written by 0950a). For every dimension, compare the current score against the 0950a baseline score. Document improvement or regression in the audit report.

### Step 6: Score all 10 dimensions and produce the report

Write the full report to `prompts/0950_chain/audit_final.md` using this structure:

```markdown
## Code Quality Audit Report — 0950 Final
**Date:** 2026-04-05
**Sprint:** 0950 Pre-Release Quality Sprint
**Auditor:** 0950m session

### Automated Check Results
- Ruff: N issues (baseline: 0, target: 0)
- ESLint: N warnings (baseline: 6, budget: 8)
- Frontend build: clean / N warnings
- CE/SaaS boundary: N violations (target: 0)
- Frontend tests: N pass / N skip / N fail (target: >= 1893 / 0 / 0)
- Backend unit tests: N pass / N fail / N skip (target: >= 661 / 0 / 0)
- App startup: OK / FAIL

### 10-Dimension Rubric Scoring

| # | Dimension | 0950a Score | 0950m Score | Delta | Notes |
|---|-----------|-------------|-------------|-------|-------|
| 1 | Lint cleanliness | X/10 | X/10 | +/-N | |
| 2 | Dead code density | X/10 | X/10 | +/-N | |
| 3 | Pattern compliance | X/10 | X/10 | +/-N | |
| 4 | Tenant isolation | X/10 | X/10 | +/-N | |
| 5 | Security posture | X/10 | X/10 | +/-N | |
| 6 | Test health | X/10 | X/10 | +/-N | |
| 7 | Frontend hygiene | X/10 | X/10 | +/-N | |
| 8 | Exception handling | X/10 | X/10 | +/-N | |
| 9 | Code organisation | X/10 | X/10 | +/-N | |
| 10 | Convention & docs | X/10 | X/10 | +/-N | |

**Overall Score: X.X/10** (0950a baseline: X.X, target: >= 9.0)

### Hard Gate Checklist
- [ ] Ruff: 0 issues
- [ ] ESLint: <= 8 warnings
- [ ] Frontend tests: >= 1893 pass / 0 skip
- [ ] Backend unit tests: >= 661 pass / 0 fail / 0 skip
- [ ] No class exceeds 1000 lines
- [ ] No function exceeds 200 lines
- [ ] Zero unannotated broad exception catches
- [ ] Zero dict-returns in services
- [ ] Zero hardcoded hex colours in Vue components
- [ ] Overall score >= 9.0/10

### VERDICT: PASS / FAIL

### Findings by Severity (if FAIL)
...
```

### Step 7a: If PASS

1. Update the baseline section in `handovers/Reference_docs/Code_quality_prompt.md`:
   - Replace the 0769 sprint baseline numbers with the 0950 sprint numbers
   - Update the overall score, test counts, and ESLint warning count

2. Write "PASS" in the chain log summary for session 0950m.

3. The 0950n remediation handover is not executed — mark it "SKIPPED — 0950m PASSED" in the chain log.

### Step 7b: If FAIL

1. In the audit report, document each failing dimension with:
   - The specific findings (file path, line number, description)
   - Whether the finding is a regression from 0950a or a pre-existing issue that the sprint did not address

2. Write "FAIL — dimensions X, Y below target" in the chain log summary for session 0950m.

3. The orchestrator will fill in 0950n with specific remediation tasks based on this report. Do not attempt to fix findings during this session — 0950m is an audit and verdict session only.

---

## 5. Hard Gates

All of the following must be true for a PASS verdict. A single failing gate produces a FAIL verdict regardless of the overall score.

| Gate | Target |
|------|--------|
| `ruff check src/ api/` | 0 issues |
| `npx eslint src/ --max-warnings 8` | exit code 0 |
| Frontend tests | >= 1893 pass, 0 skip |
| Backend unit tests | >= 661 pass, 0 fail, 0 skip |
| No class over 1000 lines | 0 violations |
| No function over 200 lines | 0 violations |
| Unannotated broad exception catches | 0 |
| Dict-returns in services or tools | 0 |
| Hardcoded hex colours in Vue components | 0 |
| Overall rubric score | >= 9.0/10 |

---

## 6. Dependencies and Blockers

**Must complete first:**
- All of 0950a through 0950l — every session must show `"status": "complete"` in the chain log before this session begins

**Triggers (if FAIL):**
- 0950n conditional remediation — orchestrator spawns this with specific tasks from the 0950m findings

**Known blockers:** None. If MyPy remains blocked by the src-layout dual-module-name pre-existing issue, note it as pre-existing and do not count it against the score.

---

## 7. Success Criteria

- `prompts/0950_chain/audit_final.md` exists and contains a complete 10-dimension report with a PASS or FAIL verdict
- All automated checks have been run and their exact output recorded
- Every hard gate is evaluated with a pass/fail result
- Chain log session 0950m is updated with the verdict and commit hash
- If PASS: `handovers/Reference_docs/Code_quality_prompt.md` baseline section updated

---

## 8. Rollback Plan

This handover is read-only except for writing the audit report and (on PASS) updating the Code_quality_prompt.md baseline. Neither change requires a rollback — both are additive document updates.

---

## 9. Additional Resources

- Audit protocol: `handovers/Reference_docs/Code_quality_prompt.md`
- 0950 sprint baseline: `prompts/0950_chain/audit_baseline.md`
- 0950 chain log: `prompts/0950_chain/chain_log.json`
- 0769 sprint baseline numbers: Section "Baseline" in `Code_quality_prompt.md`

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 0950m** in the 0950 Pre-Release Quality Sprint. This is the verdict session.

### Step 1: Read Chain Log and Directives

```
Read prompts/0950_chain/chain_log.json
```

Check `orchestrator_directives` for session `0950m`. If it contains "STOP", halt immediately. Read `notes_for_next` from session 0950l.

### Step 2: Confirm All Prerequisites

Every session 0950a through 0950l must show `"status": "complete"`. If any is not complete, halt and document the blocker.

### Step 3: Mark Session Started

```json
"status": "in_progress"
```

### Step 4: Execute Audit

Run all automated checks and parallel subagents. Write the full report to `prompts/0950_chain/audit_final.md`.

### Step 5: Update Chain Log Before Stopping

- `tasks_completed`: list each automated check run and each subagent launched
- `deviations`: any check that could not run and why
- `blockers_encountered`: any issues
- `notes_for_next`: verdict (PASS or FAIL), specific dimensions that fell short if FAIL
- `summary`: 2-3 sentences with verdict and overall score
- `status`: "complete"

### Step 6: Commit and STOP

```bash
git add prompts/0950_chain/audit_final.md
# If PASS, also stage the updated Code_quality_prompt.md baseline:
git add handovers/Reference_docs/Code_quality_prompt.md
git commit -m "cleanup(0950m): final audit report — <PASS/FAIL>, score <X.X>/10"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950m chain log — audit complete, verdict <PASS/FAIL>"
```

**Do NOT spawn the next terminal.** The orchestrator reads the verdict from the chain log and either closes the sprint (PASS) or spawns 0950n with specific tasks (FAIL).
