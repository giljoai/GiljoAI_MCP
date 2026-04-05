# Handover 0950n: Conditional Remediation (if 0950m FAIL)

**Date:** 2026-04-05
**From Agent:** Planning Session
**To Agent:** Next Session (remediation-focused)
**Priority:** Critical
**Estimated Complexity:** TBD — depends on 0950m findings
**Status:** Conditional (only executed if 0950m produces FAIL verdict)
**Edition Scope:** CE
**Series:** 0950n of 0950a–0950n — read `prompts/0950_chain/chain_log.json` first

---

## 1. Task Summary

This is a placeholder handover that is only executed when session 0950m produces a FAIL verdict. If 0950m passes, this handover is never executed — mark it "SKIPPED — 0950m PASSED" in the chain log and stop. If 0950m fails, this session reads the 0950m audit report, works through every failing dimension with targeted fixes, and re-runs all hard gates to confirm the sprint target of >= 9.0/10 is reached.

---

## 2. Context and Background

The 0950 Pre-Release Quality Sprint target is a code quality score of >= 9.0/10 with all hard gates met. Session 0950m runs the authoritative final audit. If any single hard gate fails — or if the overall rubric score falls below 9.0 — the verdict is FAIL and this handover is activated by the orchestrator with specific tasks drawn from the 0950m findings.

The orchestrator fills in section 4 (Implementation Plan) with the exact findings from `prompts/0950_chain/audit_final.md` before spawning this session. Do not begin work without reading that report.

**Critical agent rules — read before touching any file:**
- Before deleting ANY code: verify zero upstream/downstream references using grep
- Tests that fail must be fixed or deleted — never skip
- No commented-out code — delete it
- Commit with descriptive message prefixed `cleanup(0950n):`
- Update chain log session entry at `prompts/0950_chain/chain_log.json` before stopping
- Do NOT spawn the next terminal — orchestrator handles that
- Read `orchestrator_directives` in chain log FIRST before starting work

---

## 3. Technical Details

### Scope

Wherever 0950m found violations. Read `prompts/0950_chain/audit_final.md` for the exact file paths and line numbers. The common remediation targets by dimension are listed below for reference — the orchestrator will confirm which apply.

### Possible remediation targets by dimension

| Dimension | Likely file scope | Typical fix |
|-----------|------------------|-------------|
| Lint cleanliness | `src/`, `api/` | `ruff check --fix`, then manual review of remaining issues |
| Dead code density | `src/giljo_mcp/`, `frontend/src/` | Delete unreferenced functions/components after grep confirms zero callers |
| Pattern compliance | `src/giljo_mcp/services/`, `api/` | Replace dict-returns with exceptions; replace bare `except Exception` with annotated catches |
| Tenant isolation | `api/` endpoints | Add `tenant_key` filter to any raw query that bypasses `TenantManager` |
| Security posture | `api/` endpoints | Add `Depends(get_current_active_user)` to unprotected endpoints |
| Test health | `tests/`, `frontend/src/**/*.spec.js` | Remove or re-enable skipped tests; fill coverage gaps |
| Frontend hygiene | `frontend/src/` | Replace hardcoded hex values with design tokens; fix WCAG AA violations |
| Exception handling | `src/`, `api/` | Annotate or narrow broad catches; remove try/pass blocks |
| Code organisation | `src/giljo_mcp/`, `frontend/src/` | Split any class still over 1000 lines or function over 200 lines |
| Convention & docs | Any | Remove AI signatures; fix forbidden terminology; resolve stale docstrings |

---

## 4. Implementation Plan

> The orchestrator populates this section with specific tasks before spawning this session.
> Each task entry should have: dimension, file path, line number range, description of the finding, and the required fix.

**Template for orchestrator-injected tasks:**

```
### Finding N — <Dimension Name>

**File:** `path/to/file.py` (lines X–Y)
**Finding:** Description of the issue.
**Required fix:** What must change.
**Verification:** Command to confirm the fix is complete.
```

---

## 5. Re-Verification Protocol

After all findings are addressed, re-run the complete hard gate set from 0950m. Every gate must pass before this session is considered complete.

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
Target: exit code 0 (< = 8 warnings).

**Frontend build:**
```bash
cd /media/patrik/Work/GiljoAI_MCP/frontend && npm run build
```
Target: clean build, no errors.

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
Target: prints "OK" with no errors.

After all gates pass: re-score all 10 dimensions using the rubric in `handovers/Reference_docs/Code_quality_prompt.md`. If the overall score is still below 9.0/10, document the remaining gaps and flag for orchestrator decision — do not loop indefinitely. A second remediation round (0950o) is preferable to an open-ended session.

---

## 6. Hard Gates

All of the following must be true for this handover to be considered complete:

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

## 7. Dependencies and Blockers

**Must complete first:**
- 0950m (final audit) — this handover is only activated if 0950m produces a FAIL verdict. Do not begin until the 0950m chain log entry shows `"status": "complete"` and its `notes_for_next` contains "FAIL".

**Enables:**
- Sprint close — once 0950n passes, update `handovers/Reference_docs/Code_quality_prompt.md` baseline with new numbers and mark the sprint complete in the chain log.

**Known blockers:** None at the time of writing. The orchestrator will document any pre-existing issues that are out of scope for remediation (e.g., the MyPy src-layout dual-module-name issue) so they are not counted against the score.

---

## 8. Success Criteria

- All 0950m hard gates met (re-verified by running the full check set above)
- Overall rubric score >= 9.0/10
- `prompts/0950_chain/audit_final.md` updated (or a new `audit_final_0950n.md` appended) with the post-remediation scores
- `handovers/Reference_docs/Code_quality_prompt.md` baseline section updated with new numbers
- Chain log session 0950n shows `"status": "complete"` with PASS summary

---

## 9. Rollback Plan

Each fix is targeted and isolated. If a fix causes a regression:

```bash
git revert HEAD
```

Or for a specific file:

```bash
git checkout -- path/to/file
```

No migrations, no config changes, and no install.py changes are expected in a remediation session. If a finding requires a schema change, escalate to the orchestrator — do not proceed without explicit approval.

---

## 10. Additional Resources

- 0950m final audit report (primary input): `prompts/0950_chain/audit_final.md`
- Audit protocol and rubric: `handovers/Reference_docs/Code_quality_prompt.md`
- 0950 sprint baseline: `prompts/0950_chain/audit_baseline.md`
- 0950 chain log: `prompts/0950_chain/chain_log.json`
- Design system reference: `frontend/design-system-sample-v2.html`

---

## Chain Execution Instructions (Orchestrator-Gated v3)

You are **session 0950n** in the 0950 Pre-Release Quality Sprint. This session only runs if 0950m failed.

### Step 1: Check Activation Condition

```
Read prompts/0950_chain/chain_log.json
```

Check session `0950m` status and `notes_for_next`. If `notes_for_next` contains "PASS" or "SKIPPED", do NOT proceed — this handover is not needed. Update your chain log entry to `"status": "skipped"` with summary "SKIPPED — 0950m PASSED" and stop.

### Step 2: Read Chain Log and Directives

Check `orchestrator_directives` for session `0950n`. If it contains "STOP", halt immediately.

### Step 3: Read the Audit Report

```
Read prompts/0950_chain/audit_final.md
```

Identify every finding that caused the FAIL verdict. The orchestrator should have injected specific tasks into section 4 of this handover before spawning this session. If section 4 contains only the template placeholder, derive the task list from the audit report directly.

### Step 4: Mark Session Started

Update your session entry in `prompts/0950_chain/chain_log.json`:
```json
"status": "in_progress"
```

### Step 5: Execute Fixes

Work through each finding from the audit report. For each fix:
1. Grep to confirm the exact scope before changing anything
2. Apply the fix
3. Run the relevant verification command immediately (do not batch all verification to the end)
4. Confirm no regressions before moving to the next finding

### Step 6: Re-Run Full Hard Gate Set

After all individual fixes, run the complete verification protocol from section 5 above. Record the exact output of each command.

### Step 7: Update Chain Log Before Stopping

Update your session entry with:
- `tasks_completed`: list each finding addressed (dimension, file path, fix description)
- `deviations`: any finding that could not be fixed within this session and why
- `blockers_encountered`: any issues requiring orchestrator decision
- `notes_for_next`: final hard gate results and overall score; if still below 9.0, specific remaining gaps
- `summary`: 2-3 sentences with final verdict (PASS or "still short on dimension X") and commit hash
- `status`: "complete"

### Step 8: Commit and STOP

```bash
git add src/ api/ frontend/src/ tests/ frontend/tests/
git commit -m "cleanup(0950n): remediation — <brief description of main fixes>"
git add prompts/0950_chain/audit_final.md handovers/Reference_docs/Code_quality_prompt.md
git commit -m "docs: 0950n — post-remediation audit update, score <X.X>/10"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950n chain log — remediation complete"
```

**Do NOT spawn the next terminal.** The orchestrator reads the chain log and either closes the sprint (all gates pass) or creates a 0950o round-two remediation handover.

---

## Progress Updates

*(Agent updates this section during implementation)*
