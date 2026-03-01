# 0750a: Protocol Document Patches

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 1 of 7
**Branch:** `0750-cleanup-sprint`
**Priority:** HIGHEST — multiplier effect on all future sessions

### Reference Documents (read these if you need context, not required for execution)
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 1 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md`
- **Dependency graph:** `docs/cleanup/dependency_graph.json` (not needed for this phase — docs only)

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

A code quality audit (2026-02-28) found that 45% of findings trace to gaps and contradictions in three protocol documents that agents read before writing code. Fixing these documents has a multiplier effect — every future agent session inherits the corrections.

This handover modifies **only documentation** — no production code, no tests.

---

## Scope: 3 Files, Documentation Only

### File 1: `handovers/Reference_docs/QUICK_LAUNCH.txt`

**Problem:** The service template code examples use the OLD dict-return pattern (`return {"success": False, "error": str(e)}`) even though prose elsewhere says to use exceptions. Agents copy the template code, not the prose.

Tasks:
- [ ] Read the full file first
- [ ] **Lines ~745-807 (service template):** Replace all `return {"success": False, ...}` patterns with `raise ServiceError(...)` or appropriate exception. The template must demonstrate the correct pattern.
- [ ] **Lines ~148-150 (endpoint example):** Same fix — replace dict returns with `raise HTTPException(...)`.
- [ ] **Lines ~313-322 (exception rule note):** Strengthen from a note to a hard rule. New text should say: "ALL Python layers — services, tools, orchestration, helpers, and context management — MUST raise exceptions for error handling. Never return dict error responses like `{"success": False}`. This applies everywhere, not just services."
- [ ] **Scan the entire file** for any other dict-return examples and fix them.

### File 2: `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`

**Problem:** Contains stale status values and references to files/tools that no longer exist.

Tasks:
- [ ] Read the full file first
- [ ] **Lines ~86-89 (status values):** Replace with the canonical 6 post-0491 statuses: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`. Remove `failed` and `cancelled`.
- [ ] **Lines ~228-232 (file references):** Verify each referenced file exists on disk. For each:
  - Run `find_file` or check filesystem
  - If file exists: keep the reference
  - If file was renamed: update the reference
  - If file was deleted: remove the reference
- [ ] **Line ~141 (acknowledge_job tool):** This tool was removed. Find and remove all references to it.
- [ ] **Add "Last Verified: 2026-02-28" at the top** of the document, below the title.
- [ ] **Scan for any other stale references** — old endpoint names, removed services, deprecated patterns.

### File 3: `handovers/handover_instructions.md`

**Problem:** Missing entire categories of rules that agents need. Contains a dict-return rule scoped too narrowly to "services" only.

Tasks:
- [ ] Read the full file first
- [ ] **Line ~128 (dict-return rule):** Change "Services raise exceptions" to "All Python layers raise exceptions — services, tools, orchestration, helpers, and context management (post-0480/0730)."
- [ ] **Add new section: "Endpoint Security" (after the Code Discipline section):**
  ```
  ### Endpoint Security
  - Every API router MUST inject `Depends(get_current_active_user)` for authentication
  - Admin-only endpoints (configuration, database, system management) MUST additionally check user role
  - Only explicitly public endpoints (login, health check, frontend config) may skip auth
  - Pattern: `async def my_endpoint(current_user: User = Depends(get_current_active_user)):`
  ```
- [ ] **Add new section: "Frontend Code Discipline":**
  ```
  ### Frontend Code Discipline
  - Shared logic goes in `composables/` — do not duplicate utility functions across components
  - Use Vuetify theme variables for colors — no `!important` CSS overrides unless compensating for a verified framework bug
  - When removing a parent event listener, also remove the child `$emit` call
  - Interactive elements must have ARIA labels for accessibility
  ```
- [ ] **Add new section: "Function Size Limits":**
  ```
  ### Function Size Limits
  - No function or method exceeds 200 lines without explicit justification documented in the handover
  - No class exceeds 1000 lines — split into focused modules
  ```
- [ ] **Add to the "Cascading Impact" section (~line 56):**
  ```
  When modifying or removing code, trace the full chain:
  model → repository → service → tool → endpoint → frontend component → test
  When removing a DB column: grep for the column name across ALL layers
  When removing a tool: check MCP registration, frontend tool lists, and test fixtures
  ```
- [ ] **Add new section: "No Placeholder Data":**
  ```
  ### No Placeholder Data
  - No `random.randint()` or fabricated values in production code paths
  - No hardcoded fake metrics or statistics
  - If real data is unavailable: return null, raise an exception, or mark as "not yet implemented" — never fabricate
  ```

---

## What NOT To Do

- Do NOT modify any Python, JavaScript, or Vue files
- Do NOT run tests (there's no code to test)
- Do NOT change anything outside the three files listed above
- Do NOT add new protocol documents — patch the existing ones
- Do NOT rewrite the documents from scratch — make targeted edits preserving existing content

---

## Acceptance Criteria

- [ ] QUICK_LAUNCH.txt: Zero dict-return examples in any code template
- [ ] AGENT_FLOW_SUMMARY.md: Shows only 6 valid statuses, zero references to deleted files/tools
- [ ] handover_instructions.md: Has new sections for endpoint security, frontend discipline, size limits, cascading cleanup, and no placeholder data
- [ ] Dict-return rule broadened to "all layers" (not just services)
- [ ] No contradictions between prose rules and code examples across all three files

---

## Completion Steps

### Step 1: Verify you are on the correct branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
# If not: git checkout 0750-cleanup-sprint
```

### Step 2: Commit your changes
```bash
git add handovers/Reference_docs/QUICK_LAUNCH.txt handovers/Reference_docs/AGENT_FLOW_SUMMARY.md handovers/handover_instructions.md
git commit -m "docs(0750a): Patch protocol docs — fix dict-return templates, add missing rules"
```

### Step 3: Record the commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, then update the first session entry:
- Set `"status": "complete"`
- Set `"completed_at"` to current timestamp
- Fill in `"tasks_completed"` with what you actually did
- Fill in `"deviations"` if you changed anything from the plan
- Fill in `"blockers_encountered"` if you hit any issues
- Fill in `"notes_for_next"` with anything the next agent should know
- Fill in `"summary"` with a 2-3 sentence summary

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, then update `phases[0]`:
- Set `"status": "complete"`
- Set `"commits": ["<commit_hash_from_step_3>"]`
- Set `"notes"` to a brief summary

### Step 6: Done
Do NOT spawn the next terminal. The orchestrator session handles chaining.
Print "0750a COMPLETE" as your final message.
