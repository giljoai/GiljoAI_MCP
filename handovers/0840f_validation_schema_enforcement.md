# Handover 0840f: Validation & Schema Enforcement

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Planning Session)
**To Agent:** Next Session (tdd-implementor + backend-tester)
**Priority:** Medium
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Final handover in the 0840 series. Add Pydantic validation models for all remaining JSONB columns. Fix schema drift between frontend forms and backend readers. Run comprehensive end-to-end verification. Update the Alembic baseline. Update the handover catalogue.

**Prerequisite:** Handover 0840e (Project Meta + Minor Cleanups) must be complete. Check chain log.

## Context and Background

After 0840a-e, many JSONB columns have been replaced with proper columns/tables. The remaining JSONB columns (AgentTemplate.meta_data, AgentJob.job_metadata, Settings.settings_data, Organization.settings, MCPSession.session_data, ProductMemoryEntry arrays, SetupState configs) are legitimate uses — but they lack write-time validation. This handover adds Pydantic models to enforce schemas at the application layer.

## Technical Details

### Remaining JSONB Columns After 0840a-e

These are the JSONB columns that intentionally remain. Each needs a Pydantic validation model:

**Actively Written + Read:**
1. `agent_jobs.job_metadata` — `{field_priorities, depth_config, template_name}`
2. `settings.settings_data` — Per-category settings dict
3. `organizations.settings` — Org-level settings
4. `mcp_sessions.session_data` — Session state
5. `agent_templates.meta_data` (JSONB after 0840e) — `{capabilities, expertise, typical_tasks, tools}`
6. `product_memory_entries.key_outcomes` — Array of strings
7. `product_memory_entries.decisions_made` — Array of strings
8. `product_memory_entries.git_commits` — Array of `{sha, message, author}`
9. `product_memory_entries.deliverables` — Array of strings
10. `product_memory_entries.metrics` — `{test_coverage, lines_added, lines_deleted}`
11. `product_memory_entries.tags` — Array of strings
12. `api_keys.permissions` — Array of strings
13. `setup_state.features_configured` — Nested dict
14. `setup_state.tools_enabled` — Array of strings
15. `setup_state.config_snapshot` — Full config snapshot
16. `setup_state.validation_failures` — Array of `{message, timestamp}`
17. `setup_state.validation_warnings` — Array of `{message, timestamp}`

**Assess whether still needed after 0840c:**
18. `products.product_memory` — Check if 0840c addressed this
19. `products.tuning_state` — Check if 0840c addressed this

### Pydantic Models to Create

Create in `src/giljo_mcp/schemas/jsonb_validators.py` (or similar):

```python
from pydantic import BaseModel
from typing import Optional

class AgentJobMetadata(BaseModel):
    field_priorities: Optional[dict] = None
    depth_config: Optional[dict] = None
    template_name: Optional[str] = None

class AgentTemplateMetadata(BaseModel):
    capabilities: list[str] = []
    expertise: list[str] = []
    typical_tasks: list[str] = []
    tools: list[str] = []

class GitCommitEntry(BaseModel):
    sha: str
    message: str
    author: Optional[str] = None

class MemoryEntryMetrics(BaseModel):
    test_coverage: Optional[float] = None
    lines_added: Optional[int] = None
    lines_deleted: Optional[int] = None

class SetupValidationEntry(BaseModel):
    message: str
    timestamp: Optional[str] = None

# etc. for each remaining JSONB column
```

### Schema Drift Fixes

The audit identified these drift issues:

1. **ThinPromptGenerator reads `tech_stack.frameworks`** but form writes `tech_stack.frontend`, `tech_stack.backend` — after 0840c this should be resolved. Verify and fix if still drifting.

2. **`validate_config_data()` in context_manager.py** validates a schema that doesn't match what the form writes — after 0840c this function should be removed or rewritten. Verify.

3. **`depth_config` key naming mismatch** — database stores `memory_last_n_projects` / `git_commits` but protocol_builder normalizes to `memory_360` / `git_history`. After 0840d these should be direct columns. Verify the naming is consistent.

### Baseline Update Assessment

After 0840a-e, the models and baseline migration may have diverged significantly. Assess whether a baseline squash is needed:
- Count how many incremental migrations were added (0840a through 0840e)
- If 5+ migrations, create a new baseline `baseline_v34_unified.py`
- Update `install.py` stamp logic to handle old→new baseline transition
- Verify fresh install: drop DB, `python install.py`, server starts, `/welcome` works

### Handover Catalogue Update

Update `handovers/HANDOVER_CATALOGUE.md`:
- Add 0840a-f entries to Active/Recently Closed section
- Mark all as COMPLETE (or note any that stopped)

## Implementation Plan

### Phase 1: Read Chain Log and Assess State
1. Read chain log for ALL previous sessions
2. Note any deviations, blockers, or partial completions
3. Verify the database is in expected state

### Phase 2: Pydantic Validation Models
1. Create `src/giljo_mcp/schemas/jsonb_validators.py`
2. Add validator models for all remaining JSONB columns
3. Wire validators into write paths (service layer — validate before saving)

### Phase 3: Schema Drift Fixes
1. Verify and fix any remaining drift issues from the audit
2. Remove dead validation code

### Phase 4: Comprehensive Test Suite
1. Run ALL tests: `pytest tests/ --timeout=60`
2. Fix any failures from the full 0840 series
3. Add validation tests for new Pydantic models
4. Run `ruff check src/ api/` — zero issues

### Phase 5: Baseline Assessment
1. Count incremental migrations from 0840 series
2. If warranted, create new baseline
3. Test fresh install flow

### Phase 6: Documentation
1. Update handover catalogue
2. Write completion summary in this handover document
3. Update chain log with final status

### Phase 7: Final Verification
1. Start the server: `python -m uvicorn api.main:app --reload`
2. Verify frontend loads, product form works, settings work
3. Verify messages send/receive correctly
4. Verify statistics dashboard works

## Success Criteria

- [ ] Pydantic models for all remaining JSONB columns
- [ ] Write-time validation wired in
- [ ] Schema drift fixed
- [ ] ALL tests pass (full suite)
- [ ] `ruff check` clean
- [ ] Baseline updated if needed
- [ ] Handover catalogue updated
- [ ] Server starts and core flows work
- [ ] Committed to `feature/0840-jsonb-normalization`
- [ ] Chain log marked as complete

## Rollback Plan

Individual migration rollbacks. Git revert.

## Coding Principles

- TDD, Clean Code, Tenant isolation, Exception-based errors
- No function exceeds 200 lines
- Delete dead code, don't comment out

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0840_chain/chain_log.json`. Verify ALL previous sessions (0840a-e) are `complete`. Read ALL `notes_for_next` — you are the final integrator.

### Step 2: Mark Session Started

### Step 3: Execute Handover Tasks

### Step 4: Update Chain Log — FINAL
Update your session AND set:
- `"chain_summary"`: Full summary of the 0840 series
- `"final_status"`: "complete" (or "partial" if issues remain)

### Step 5: Commit Work
```bash
git add -A
git commit -m "feat: Add JSONB validation models + schema enforcement — completes 0840 series (0840f)"
```

### Step 6: CHAIN COMPLETE
This is the last handover. Do NOT spawn another terminal.

Instead, output a summary of the entire 0840 chain for the user to review when they check in.

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
