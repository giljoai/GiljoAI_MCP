# 0769g: Documentation & Convention Sync

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 7 of 7 (FINAL)
**Branch:** `feature/0769-quality-sprint`
**Priority:** MEDIUM — documentation drift
**Estimated Time:** 1 hour

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (sections M3, M7, M8, LOW)
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

Documentation has drifted from code reality. 8 docs reference old agent job statuses, archived files contain forbidden licensing terms, and test fixtures are orphaned. This final phase brings documentation into sync with the codebase as left by phases a-f.

---

## Scope

### Task 1: Fix Stale Agent Job Status Values in Docs

The current valid agent job statuses (per state machine) are: `waiting`, `preparing`, `working`, `review`, `complete`, `blocked`, `cancelled`, `failed`.

Update these files to replace old status values in agent-job-related examples and text:
- `pending` -> `waiting`
- `active` -> `working`

**Files:**
1. `docs/api/AGENT_JOBS_API_REFERENCE.md` (9 references — lines 187, 239, 267, 276, 331, 640, 658, 800, 816)
2. `docs/api/agent_jobs_endpoints.md` (line 81)
3. `docs/api/context_tools.md` (line 356)
4. `docs/guides/agent_monitoring_developer_guide.md` (lines 175, 462, 532)
5. `docs/guides/staging_rollback_integration_guide.md` (lines 80-81, 385-386)
6. `docs/TESTING.md` (lines 120, 267)
7. `docs/cleanup/refactoring_roadmap.md` (line 381)

**IMPORTANT:** Only change agent-job-related status references. "active" and "pending" remain valid for other entity types (projects use "active", messages/tasks use "pending"). Read the surrounding context before replacing.

### Task 2: Handle Forbidden Terms in Archived Docs

**Files in `docs/archive/retired-2026-01/`:**
1. `installation_page.md:269` — "open-source software"
2. `0045/USER_GUIDE.md:1865` — "Free and open-source"
3. `0041/DEPLOYMENT_GUIDE.md:635` — "Open Source" (referring to Grafana)

**Options (choose one per file):**
- If the file is clearly retired and not shipping: add a header `> **ARCHIVED:** This document is retired and may contain outdated information.`
- If the term refers to third-party software (like Grafana): leave it — "open source" describing Grafana is factually accurate, not a license claim about GiljoAI

### Task 3: Delete Dead Test Fixtures

- Delete `tests/fixtures/orchestrator_simulator.py` — only imported by its own test file, not used by real tests
- Delete `tests/fixtures/mock_agent_simulator.py` — same situation
- Verify: grep for imports of these files across the test suite. If any real test imports them, do NOT delete.

### Task 4: Update Code Quality Baseline

**File:** `handovers/Code_quality_prompt.md`

Update line 9 (Baseline) to reflect the post-sprint state:
```
**Baseline:** 0769 sprint (March 2026) — X.X/10, N tests / 0 skipped, zero ruff issues, ESLint budget 8 warnings.
```
(Fill in actual scores from the chain log after all phases complete.)

### Task 5: Update Handover Catalogue

Update `handovers/HANDOVER_CATALOGUE.md`:
- Mark 0769 as COMPLETE with date
- Update the 0700-0769 range description

---

## What NOT To Do

- Do NOT modify any source code (Python or JavaScript)
- Do NOT change any API behavior
- Do NOT rewrite documentation — only fix the specific stale references listed above
- Do NOT add new documentation

---

## Acceptance Criteria

- [ ] Zero stale agent job status values in docs (grep for `"pending"` and `"active"` in agent-job context)
- [ ] Archived docs handled (header or left alone for third-party references)
- [ ] Dead test fixtures deleted (if no real test imports them)
- [ ] Code_quality_prompt.md baseline updated
- [ ] Handover catalogue updated
- [ ] No source code changes in this phase

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review all previous sessions' summaries to understand final state
- Get the final test count and lint results for the baseline update

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Tasks 1-5.

### Step 4: Update Chain Log
This is the FINAL session. Update your session AND:
- Set `chain_summary` with overall sprint results
- Set `final_status` to `"complete"`
- Include final quality score if you can compute it

### Step 5: STOP
Do NOT spawn any terminal. This is the last phase. Commit chain log update and exit.
