# Kickoff: Handover 0700i - instance_number Column Removal

**Series:** 0700 Code Cleanup Series
**Handover:** 0700i
**Risk Level:** MEDIUM-HIGH
**Estimated Scope:** ~500 lines, 40-50 files, 8 test files deleted
**Date:** 2026-02-05

---

## Mission Statement

Remove the vestigial `instance_number` column from `AgentExecution` and ALL code that references it. This column was part of the **succession system** which was removed in 0700d. With succession gone, all agents are effectively "instance 1" and this column serves no purpose.

**SURGICAL APPROACH REQUIRED**: This touches ~40 ORDER BY queries across critical services. Each change must be verified individually. Do NOT batch changes blindly.

---

## CRITICAL: Dependency Analysis First

**BEFORE making any code changes**, you MUST:

1. **Build a dependency visualization** of instance_number usage:
   ```bash
   # Find all references
   grep -rn "instance_number" src/ api/ frontend/ --include="*.py" --include="*.vue" --include="*.js" | head -100
   ```

2. **Categorize by impact tier**:
   - **Tier 1 (Model)**: Column definition, constraints, indexes
   - **Tier 2 (Query)**: ORDER BY patterns - MOST CRITICAL
   - **Tier 3 (API)**: Response schemas, parameters
   - **Tier 4 (Frontend)**: Display components
   - **Tier 5 (Tests)**: Fixtures, assertions

3. **Create a dependency index** showing which files depend on which:
   - Model changes affect ALL downstream
   - Query changes affect API responses
   - API changes affect frontend

4. **Identify the replacement pattern** for each ORDER BY:
   ```python
   # FROM (vestigial):
   .order_by(AgentExecution.instance_number.desc()).limit(1)

   # TO (semantically correct):
   .order_by(AgentExecution.started_at.desc()).limit(1)
   ```

---

## Phase 1: Context Acquisition

### Required Reads

1. **Your Spec**: `handovers/0700_series/0700i_instance_number_cleanup.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`
4. **Dependencies**: 0700d MUST be complete (succession removal)

### Verify Preconditions

```bash
# Confirm succession code is gone (0700d completed)
grep -r "trigger_succession" src/ api/
# Should return: NOTHING

# Confirm instance_number still exists (our target)
grep -rn "instance_number" src/giljo_mcp/models/agent_identity.py
# Should return: Column definition lines
```

---

## Phase 2: Surgical Execution Order

### Step 1: Model Changes (src/giljo_mcp/models/agent_identity.py)

**DO NOT SKIP THIS STEP** - Model changes break imports until queries are updated.

Remove from AgentExecution:
- [ ] Column definition (lines 180-185)
- [ ] Index: `idx_agent_executions_instance`
- [ ] UniqueConstraint: `uq_agent_instance`
- [ ] CheckConstraint: `instance_number >= 1`
- [ ] Relationship order_by on AgentJob (line 114)
- [ ] `__repr__` method instance reference

**Replacement for relationship order_by:**
```python
# FROM:
executions = relationship("AgentExecution", order_by="AgentExecution.instance_number")
# TO:
executions = relationship("AgentExecution", order_by="AgentExecution.started_at")
```

### Step 2: Query Refactors (CRITICAL PATH)

**Each query must be examined individually.** The research spec lists 40+ usages. Key files:

| Service | Query Count | Notes |
|---------|-------------|-------|
| orchestration_service.py | 8 | Core orchestrator queries |
| message_service.py | 5 | Message routing |
| agent_job_manager.py | 5 | Job lifecycle |
| agent_health_monitor.py | 6 | **SPECIAL CASE**: Uses subquery with func.max() |
| thin_prompt_generator.py | 2 | Prompt generation |

**Standard replacement:**
```python
# Every .order_by(AgentExecution.instance_number.desc())
# becomes .order_by(AgentExecution.started_at.desc())
```

**Special case - agent_health_monitor.py:**
```python
# FROM:
func.max(AgentExecution.instance_number).label("max_instance")
# TO:
func.max(AgentExecution.started_at).label("latest_started")
```

**Edge case handling:**
```python
# If started_at could be NULL for historical data:
.order_by(
    AgentExecution.started_at.desc().nullslast()
).limit(1)
```

### Step 3: API Layer Updates

Remove from schemas and responses:
- [ ] `api/schemas/prompt.py` - Remove instance_number field
- [ ] `api/endpoints/agent_jobs/models.py` - Remove from response models
- [ ] All endpoint files that return instance_number in responses

### Step 4: Frontend Updates

Remove from Vue components:
- [ ] `AgentTableView.vue` - Remove Instance column
- [ ] `LaunchSuccessorDialog.vue` - Remove instance reference
- [ ] `MessageStream.vue` - Remove instance display
- [ ] `agentJobsStore.js` - Remove from state

**Consider deletion:**
- `SuccessionTimeline.vue` - May be entirely dead after 0700d

### Step 5: Test Cleanup

**Delete succession test files** (already dead after 0700d):
- tests/integration/test_succession_*.py (4 files)
- tests/performance/test_succession_performance.py
- tests/security/test_succession_security.py
- tests/smoke/test_succession_smoke.py
- tests/fixtures/succession_fixtures.py

**Update remaining test fixtures:**
- Remove instance_number=1 from all fixture creation
- Update assertions that check instance_number

### Step 6: Migration and Install

- [ ] Update `migrations/versions/baseline_v32_unified.py` - Remove column
- [ ] Update `install.py` lines 1095, 1121 - Remove instance_number from demo data

---

## Phase 3: Verification

### Grep Verification (Zero References)

```bash
# After all changes, these should return NOTHING:
grep -rn "instance_number" src/ --include="*.py"
grep -rn "instance_number" api/ --include="*.py"
grep -rn "instance_number" frontend/src/ --include="*.vue" --include="*.js"

# Exceptions allowed:
# - migrations/archive/ (historical, read-only)
# - comments explaining removal
```

### Functional Verification

```bash
# Server starts
python api/run_api.py --port 7272

# Tests pass
pytest tests/services/ -v
pytest tests/endpoints/ -v
pytest tests/integration/ -v -k "not succession"  # succession tests should be deleted

# Frontend builds
cd frontend && npm run build
```

### Query Verification

For each refactored query, verify:
1. Query returns results in correct order (most recent first)
2. No NULL-related sorting issues
3. Performance is acceptable (started_at should be indexed)

---

## Phase 4: Communication

### Write to comms_log.json

```json
{
  "id": "0700i-complete-001",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0700i",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "instance_number column removal complete",
  "message": "Removed vestigial instance_number column from AgentExecution. Refactored X ORDER BY queries from instance_number.desc() to started_at.desc(). Deleted Y succession test files. All services verified working.",
  "files_affected": ["[list files]"],
  "action_required": false,
  "context": {
    "queries_refactored": "[COUNT]",
    "test_files_deleted": "[COUNT]",
    "lines_removed": "[ESTIMATE]",
    "replacement_pattern": "started_at.desc()"
  }
}
```

---

## Risk Mitigation

### Why MEDIUM-HIGH Risk?

- 40+ ORDER BY queries across critical services
- Model change breaks imports until queries updated
- Query semantic change (instance_number → started_at)
- Potential NULL handling edge cases

### Mitigations

1. **Surgical approach** - One file at a time, verify each change
2. **Dependency visualization** - Understand impact before changing
3. **started_at already exists** - No new column needed
4. **No external users** - Can't break backwards compatibility
5. **Git revert** - Easy rollback if needed

### Pre-Flight Checklist

- [ ] 0700d is complete (succession system removed)
- [ ] started_at column exists and is populated
- [ ] Understand each ORDER BY query's purpose before changing
- [ ] Identify any NULL started_at edge cases

---

## Success Criteria

- [ ] instance_number column removed from model
- [ ] All constraints/indexes removed
- [ ] All 40+ ORDER BY queries refactored to started_at.desc()
- [ ] API responses no longer include instance_number
- [ ] Frontend no longer displays Instance #N
- [ ] All succession test files deleted
- [ ] All remaining tests pass
- [ ] Server starts successfully
- [ ] Frontend builds successfully
- [ ] Zero grep matches for instance_number (excluding archives/comments)
- [ ] comms_log entry written
- [ ] Changes committed with proper message

---

## Commit Message Template

```
cleanup(0700i): Remove vestigial instance_number column from AgentExecution

Removed instance_number column and all references after succession system
removal (0700d). Column was only used for orchestrator lineage tracking
which no longer exists.

Changes:
- Removed column, constraints, indexes from AgentExecution model
- Refactored X ORDER BY queries: instance_number.desc() -> started_at.desc()
- Removed from API response schemas
- Removed Instance #N display from frontend
- Deleted Y succession test files (dead after 0700d)
- Updated Z test fixtures

Verification:
- All services start successfully
- All tests pass
- Zero active references remain

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Files Reference (from spec)

### Priority Order (do in this sequence):

**1. Model (breaks everything until done):**
- src/giljo_mcp/models/agent_identity.py

**2. Core Services (query refactors):**
- src/giljo_mcp/services/orchestration_service.py (8 queries)
- src/giljo_mcp/services/message_service.py (5 queries)
- src/giljo_mcp/services/agent_job_manager.py (5 queries)
- src/giljo_mcp/monitoring/agent_health_monitor.py (6 queries - special case)
- src/giljo_mcp/thin_prompt_generator.py (2 queries)
- src/giljo_mcp/services/project_service.py

**3. Other Backend:**
- src/giljo_mcp/job_monitoring.py
- src/giljo_mcp/slash_commands/handover.py
- src/giljo_mcp/repositories/agent_job_repository.py
- src/giljo_mcp/tools/*.py (6 files)

**4. API Layer:**
- api/endpoints/prompts.py
- api/endpoints/agent_jobs/*.py (7 files)
- api/endpoints/projects/*.py (2 files)
- api/schemas/prompt.py
- api/websocket.py

**5. Frontend:**
- frontend/src/components/*.vue (8 files)
- frontend/src/stores/*.js (2 files)

**6. Tests (delete/update):**
- tests/integration/test_succession_*.py (DELETE)
- tests/performance/test_succession_performance.py (DELETE)
- tests/security/test_succession_security.py (DELETE)
- tests/smoke/test_succession_smoke.py (DELETE)
- tests/fixtures/succession_fixtures.py (DELETE)
- All other test fixtures (UPDATE)

**7. Migration/Install:**
- migrations/versions/baseline_v32_unified.py
- install.py

---

**Remember:** SURGICAL. Build the dependency index FIRST. Visualize impact BEFORE changing. One file at a time. Verify each change.

**Start time:** When you begin Phase 2 (Surgical Execution)
