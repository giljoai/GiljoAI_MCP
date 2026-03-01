# 0750f: Dead Code Removal

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 6 of 7
**Branch:** `0750-cleanup-sprint`
**Priority:** MEDIUM — housekeeping, reduces confusion

### Reference Documents
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 6 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md` (H-7 through H-14, H-17)
- **Mid-point audit:** `prompts/0750_chain/midpoint_audit.json` (remaining findings list)
- **Dependency graph:** `docs/cleanup/dependency_graph.json` — refresh FIRST before using
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750e `notes_for_next`

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The mid-point audit (7.1/10) identified significant dead code across backend and frontend. This phase removes verified dead code to reduce confusion, improve maintainability, and push the quality score toward 8.5/10.

**CRITICAL RULE:** The dependency graph flags 948 files as orphans. Most are NOT dead code. Do NOT bulk-delete graph orphans. Every deletion must be individually verified.

---

## Investigation Protocol (MANDATORY for every candidate)

Before deleting ANYTHING, follow this protocol:

1. **Read the file/function** — understand what it does
2. **Check if it's an entry point** — `if __name__ == "__main__"`, CLI script, startup file → do NOT delete
3. **Check if dynamically loaded** — grep for the filename/function name as a string across the codebase
4. **Use `find_referencing_symbols`** — LSP-based analysis catches real usage. Zero refs = likely dead.
5. **Check git blame** — was it recently added? Could be work-in-progress.
6. **Only delete after ALL checks confirm dead**

---

## Scope

### 6A: Backend Dead Code (from audit findings)

**H-7: Dead backend methods (7 methods with 0 refs)**
- [ ] Investigate each method listed in the audit report using `find_referencing_symbols`
- [ ] For each confirmed dead method: delete it
- [ ] Run tests after each batch

**H-8: Dead schemas — `api/schemas/agent_job.py` (331 lines)**
- [ ] Verify no endpoint or service imports these schemas
- [ ] Check for string-based references: `grep -rn "agent_job" api/ src/`
- [ ] If confirmed dead: delete the file or remove dead schemas

**H-9: `AgentJobRepository.get_jobs_by_status` (0 refs)**
- [ ] Verify with `find_referencing_symbols`
- [ ] If confirmed dead: delete the method

**H-4: `AgentJobRepository` references non-existent model columns (`started_by`, `completed_by`)**
- [ ] Verify these columns don't exist in the model
- [ ] Remove the references

**H-5: `create_job` uses `status=pending` (violates CHECK constraint)**
- [ ] Verify the CHECK constraint values
- [ ] Fix to use correct status value

**H-17: 107 lines duplicate code (closeout/360memory)**
- [ ] Read `tools/project_closeout.py` and `tools/write_360_memory.py`
- [ ] Identify the duplicated code
- [ ] Extract shared logic into a common helper, or remove the duplicate

**NEW-3 (from midpoint audit): `AgentJobRepository.get_job_statistics` crashes on non-existent columns**
- [ ] Investigate and fix or remove the method

### 6B: Frontend Dead Code (from audit findings)

**H-6: `ProjectTabs.vue` calls non-existent `api.agentJobs.acknowledge()`**
- [ ] Remove the dead call

**H-10: 5 dead functions in `JobsTab.vue`**
- [ ] Verify each with grep across all Vue files
- [ ] Remove confirmed dead functions

**H-11: Dead `activateProject()` in `ProjectsView.vue`**
- [ ] Verify no template or parent references
- [ ] Remove if confirmed dead

**H-12: Dead `goToIntegrations()` in `ProjectTabs.vue`**
- [ ] Verify no template or parent references
- [ ] Remove if confirmed dead

**H-20: 4 orphan emit declarations in `JobsTab`**
- [ ] Check all possible parent components for listeners
- [ ] Remove orphan emits with no parent listener

**H-21: Dead `@hand-over` handler in `ProjectTabs`**
- [ ] Verify no child emits this event
- [ ] Remove if confirmed dead

**H-22: Unused theme variable in `JobsTab`**
- [ ] Remove unused variable

**H-23: Unused readonly prop in `JobsTab`**
- [ ] Check if any parent passes this prop
- [ ] Remove if never passed

### 6C: Stale Artifacts

- [ ] Remove `.pyc` files for deleted `.py` modules:
  ```bash
  find tests/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
  find src/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
  ```
- [ ] **Refresh the dependency graph**:
  ```bash
  python scripts/update_dependency_graph_full.py
  ```
- [ ] Record new orphan count for comparison

### 6D: Stale Status Strings (M-1, M-3, NEW-2)

- [ ] Search for old status values in production code:
  ```bash
  grep -rn '"active"\|"pending"\|"preparing"\|"running"\|"queued"\|"paused"\|"review"\|"planning"\|"failed"\|"cancelled"' src/giljo_mcp/ --include="*.py"
  ```
- [ ] For each match: determine if it's a legitimate use (e.g., Project.status = "active" is valid) or a stale AgentExecution/AgentIdentity status reference
- [ ] Fix stale references to use post-0491 values: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`
- [ ] **IMPORTANT:** Project-level statuses (`active`, `completed`) may be correct — only AgentExecution/AgentIdentity statuses were changed in 0491

---

## What NOT To Do

- Do NOT bulk-delete graph orphans — investigate each one individually
- Do NOT delete entry points (`if __name__`), CLI scripts, or dynamically-loaded modules
- Do NOT delete `tests/helpers/test_db_helper.py` (54 dependents, critical test infrastructure)
- Do NOT delete any file without completing the investigation protocol
- Do NOT change frontend dict-return patterns (those are intentional Vue.js convention)
- Do NOT delete `models/__init__.py` or any model registry file
- Do NOT modify the auth system

---

## Acceptance Criteria

- [ ] All audit-listed dead methods verified and removed (H-7 through H-14)
- [ ] Frontend dead code removed (H-6, H-10 through H-12, H-20 through H-23)
- [ ] Duplicate closeout/360memory code consolidated (H-17)
- [ ] Stale `.pyc` files cleaned
- [ ] Dependency graph refreshed
- [ ] Every deletion documented with investigation notes
- [ ] Test suite still GREEN: ~1414 passed, ~342 skipped, 0 failed
- [ ] `npm run build` still succeeds in `frontend/` (if node_modules are available — skip if npm is broken)

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit (split by domain)
```bash
# Commit 1: Backend dead code
git add src/ api/
git commit -m "cleanup(0750f): Remove verified dead backend code — methods, schemas, stale refs"

# Commit 2: Frontend dead code
git add frontend/
git commit -m "cleanup(0750f): Remove verified dead frontend code — dead functions, orphan emits, unused props"

# Commit 3: Artifacts + graph refresh
git add docs/cleanup/dependency_graph.json tests/
git commit -m "cleanup(0750f): Clean stale artifacts, refresh dependency graph"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, update session `0750f`:
- Set `"status": "complete"`
- Set timestamps
- Fill in `"tasks_completed"` — list every item removed with verification method
- Fill in `"notes_for_next"`: what dead code was left (if any), new orphan count, graph state
- Fill in `"summary"`: 2-3 sentences

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, update `phases[5]`:
- Set `"status": "complete"`
- Set `"commits"` array
- Set `"notes"` with lines removed count

### Step 6: Done
Do NOT spawn the next terminal.
Print "0750f COMPLETE" as your final message with lines removed count.
