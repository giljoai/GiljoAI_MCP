# Handover: 0765r — Final Re-Audit (Fourth Audit)

## Context
You are the FOURTH independent quality auditor for the 0765 sprint.
- **0765i** audited at **8.2/10** (10 findings)
- **0765k** re-audited at **8.5/10** (54 findings)
- **0765n** re-audited at **8.5/10** (~1,800 lines dead code, 75+ dead Vue vars)
- **0765o** quick-win fixes (7 dead Vue vars, stale refs, ruff version, .gitignore)
- **0765p** branding standardization (design-tokens.scss + agent-colors.scss reconciled to design system)
- **0765q** dead code remediation (~2,528 lines removed, eslint budget 124 → 8)

Your job: **score the codebase AFTER 0765o+p+q fixes**. Target: >= 9.5/10.

## What Changed Since Last Audit (0765n at 8.5/10)

### 0765o (quick wins):
- 7 dead Vue variables removed (theme, userStore, settingsStore)
- 2 stale doc references fixed
- Ruff noqa A005 removed, pre-commit ruff updated v0.9.1 → v0.15.0
- Commented-out code removed from setup.py
- Linux_Installer/credentials/ gitignored + untracked

### 0765p (branding):
- design-tokens.scss: agent colors, status colors, font family, text color, radius scale, elevation scale all corrected
- agent-colors.scss: status CSS vars corrected
- All values now match canonical sources (agentColors.js, statusConfig.js)

### 0765q (dead code):
- 16 dead backend methods deleted (-736 lines)
- 3 dead test helper files deleted (-1,204 lines)
- Dead test fixtures + imports cleaned
- 107 eslint no-unused-vars fixed across 46 Vue files (-588 lines)
- 4 dead frontend exports removed
- eslint warning budget lowered from 124 to 8

## Audit Methodology

Follow the standard rubric from `handovers/Code_quality_prompt.md`. Score on 10 dimensions:

1. **Lint cleanliness** — ruff check src/ api/ (baseline: 0 issues)
2. **Dead code density** — dead methods, dead files, dead imports, dead CSS
3. **Pattern compliance** — exceptions not dicts, tenant isolation, config via ConfigManager
4. **Test health** — no dead fixtures, no stale imports, no skips, all pass
5. **Frontend hygiene** — no dead vars, no dead config, no dead exports, design token compliance
6. **Security posture** — no hardcoded secrets, auth on all endpoints, tenant isolation complete
7. **Exception handling** — narrow catches where safe, annotated broad catches
8. **Code organization** — no oversized functions (>250 lines), clean module boundaries
9. **Documentation accuracy** — no stale references to removed features
10. **Build & CI health** — frontend builds clean, pre-commit passes, no warnings

## Critical Rules
- You are a FRESH agent with zero prior context — do NOT trust any claims
- Verify everything yourself using code search and symbol analysis
- Your job is to FIND PROBLEMS, not confirm success
- Check for REGRESSIONS from 0765o/p/q fixes
- Use the 0725 audit precedent: always verify with `find_referencing_symbols` or grep before flagging dead code
- No AI signatures in code or commits

## Use Subagents to Preserve Context Budget

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Backend audit | `deep-researcher` | Audit src/giljo_mcp/ for dead code, patterns, organization |
| API audit | `deep-researcher` | Audit api/ for tenant isolation, dead code, security |
| Test audit | `deep-researcher` | Audit tests/ for dead fixtures, broken refs, health |
| Frontend audit | `deep-researcher` | Audit frontend/src/ for dead vars, eslint, design tokens |

## Deliverables
1. Write findings report to `handovers/0765r_final_audit_report.md`
2. Score on 10-dimension rubric
3. PASS (>= 9.5) or FAIL verdict
4. If FAIL: prioritized fix list with file paths and line numbers

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0765_chain/chain_log.json` — verify 0765o, 0765p, 0765q all complete.

### Step 2: Mark Session Started
Update 0765r: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Audit
Run ruff, launch 4 parallel subagents, consolidate findings, score.

### Step 4: Update Chain Log
Set 0765r to `complete` with summary and PASS/FAIL verdict.

### Step 5: Commit
Single commit: `audit(0765r): Final re-audit — score X.X/10`

### Step 6: Done
Do NOT spawn another terminal. Report completion via chain log.
