# 0750 Final Re-Audit

**Series:** 0750 (Code Quality Cleanup Sprint)
**Branch:** `0750-cleanup-sprint`
**Purpose:** Final quality assessment after all 7 phases complete. Score determines sprint success.

---

## Context

All 7 phases of the 0750 cleanup sprint are complete:
- 0750a: Protocol document patches
- 0750b: Test suite triage (GREEN suite)
- 0750c: Dict-to-exception migration (70 dict returns eliminated)
- 0750c2: get_project_summary status fix
- 0750c3: Fixture drift fix (+178 tests)
- 0750d: API endpoint hardening (auth + security)
- 0750e/e2: Monolith splits (OrchestrationService 3,427→2,705)
- 0750f: Dead code removal (~1,460 lines removed)
- 0750g: Frontend cleanup (composables, !important, ARIA)

**Baseline:** 6.6/10
**Mid-point:** 7.1/10
**Target:** 8.5/10

---

## Instructions

Execute the full audit methodology from `handovers/Code_quality_prompt.md`. Follow all 5 steps.

Compare against:
1. **Original audit:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md`
2. **Mid-point audit:** `prompts/0750_chain/midpoint_audit.json`

For each original finding, mark it as RESOLVED, PARTIALLY RESOLVED, or REMAINING.

---

## Output Format

Write your complete audit report to: `handovers/0700_series/0750_FINAL_AUDIT_REPORT.md`

ALSO write a machine-readable summary to: `prompts/0750_chain/final_audit.json`

Use the same JSON schema as the mid-point audit (`prompts/0750_chain/midpoint_audit.json`) but set `audit_type` to `"final"`.

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
```

### Step 2: Run the audit

### Step 3: Write both output files

### Step 4: Commit
```bash
git add handovers/0700_series/0750_FINAL_AUDIT_REPORT.md prompts/0750_chain/final_audit.json
git commit -m "audit(0750): Final re-audit — score X.X/10, sprint complete"
```

### Step 5: Update chain log
Read `prompts/0750_chain/chain_log.json` and set:
- `"chain_summary"`: 3-5 sentence summary of the entire sprint
- `"final_status"`: `"complete"`

Commit the chain log update:
```bash
git add prompts/0750_chain/chain_log.json
git commit -m "docs(0750): Close out sprint — final status complete"
```

### Step 6: Done
Do NOT spawn the next terminal.
Print "0750 SPRINT COMPLETE — Final Score: X.X/10" as your final message.
