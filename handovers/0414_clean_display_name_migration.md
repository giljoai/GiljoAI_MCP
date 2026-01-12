# Handover 0414: Clean display_name Migration

**Status**: COMPLETED
**Date**: 2026-01-11
**Completed**: 2026-01-11
**Work In**: `master` branch
**Supersedes**: 0413 series (retired to `handovers/completed/0413_retired/`)

## Completion Summary

Migration successfully completed with 9 commits:

| Commit | Description |
|--------|-------------|
| `fc8af7be` | refactor: Rename agent_type to display_name in AgentExecution model |
| `3fd76255` | refactor: Rename agent_type to display_name in service layer |
| `882b73af` | refactor: Rename agent_type to display_name in API endpoints |
| `4c837fa3` | refactor: Rename agent_type to display_name in MCP tools |
| `b6bfc22f` | fix: Update tests to use display_name instead of agent_type |
| `4cd4a755` | refactor: Rename agent_type to display_name in frontend components |
| `04622cfe` | chore: Add idempotent migration for agent_type to display_name rename |
| `cb339763` | fix: Update test fixtures to use display_name instead of agent_type |
| `fdb5a5a2` | fix: Complete migration from agent_type to display_name in all test files |

**Files Changed**: 200+ files across backend, frontend, and tests
**Database**: Already migrated (column is `display_name`), migration file added for idempotency
**Tests**: All test fixtures updated, model verified working

---

## CRITICAL: Branch Reference Guide

| Branch | Commit | Purpose | DO NOT DELETE |
|--------|--------|---------|---------------|
| `master` | `07094eb0` | **WORK HERE** - Clean state, no code changes | N/A |
| `backup/0414-clean-restore-point` | `07094eb0` | Restore point if master gets corrupted | YES |
| `backup/pre-agent-type-to-role-migration` | `75b9a4a9` | TRUE original before any migration | YES |
| `clean-display-name-migration` | `cdc4ec19` | FAILED attempt - review for bloat cleanup | YES |

---

## Context

The 0413 series attempted a complex migration path:
```
agent_type → role → display_name
```

This created confusion, bugs, and semantic pollution. A previous session attempted to fix this but created 377 file changes that failed to merge properly.

**Master has been restored to clean state (`07094eb0`).**

The simple, correct approach:
```
agent_type → display_name (direct rename)
```

---

## Task List for New Agent

### Phase 1: Review Failed Work (Optional but Recommended)

Review the failed branch `clean-display-name-migration` for:

1. **Bloat/Orphan Code Cleanup** (~600 lines removed):
   - Dead `spawn_agent_job` function removal
   - Unused WebSocket broadcast functions
   - Job vs AgentJob naming cleanup

   ```bash
   git diff backup/clean-display-name-migration-safe-copy..clean-display-name-migration --stat
   ```

2. **What went wrong**: The migration mixed cleanup with refactoring, then failed to merge due to conflicts with existing 0413h/0413i commits on master.

### Phase 2: Verify 0413 Files Retired

Check that 0413 files are properly in `handovers/completed/0413_retired/`:

```bash
ls handovers/completed/0413_retired/
# Should show 11 files + README.md
```

### Phase 3: Implement Bloat Cleanup (If Valuable)

If the bloat cleanup from failed branch looks good, cherry-pick or reimplement:
- Remove dead code
- Clean up unused functions
- Test thoroughly

### Phase 4: Implement display_name Migration

#### Step 1: Database Migration

Create `migrations/versions/0414_rename_agent_type_to_display_name.py`:

```python
"""Rename agent_type to display_name

Revision ID: 0414_agent_type_display_name
Create Date: 2026-01-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0414_agent_type_display_name'
down_revision = '<previous_revision>'  # Get from current head
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column(
        'agent_executions',
        'agent_type',
        new_column_name='display_name',
        existing_type=sa.String(100),
        existing_nullable=False
    )

def downgrade():
    op.alter_column(
        'agent_executions',
        'display_name',
        new_column_name='agent_type',
        existing_type=sa.String(100),
        existing_nullable=False
    )
```

#### Step 2: Model Update

**File**: `src/giljo_mcp/models/agent_identity.py`

```python
# BEFORE:
agent_type = Column(
    String(100),
    nullable=False,
    comment="Agent type/role for this execution",
)

# AFTER:
display_name = Column(
    String(100),
    nullable=False,
    comment="UI display label assigned by orchestrator (e.g., 'Backend API Developer')",
)
```

#### Step 3: Code References

Find and replace all references:

```bash
# Find all agent_type references in Python files
grep -rn "agent_type" src/giljo_mcp/ --include="*.py" | grep -v "__pycache__"
grep -rn "agent_type" api/ --include="*.py" | grep -v "__pycache__"

# Find all agent_type references in Vue/JS files
grep -rn "agent_type" frontend/src/ --include="*.vue" --include="*.js"
```

**Replace pattern**:
- `agent_type` → `display_name` (for agent identity/display purposes)
- Keep `agent_type` if it refers to template category (rare - check context)

#### Step 4: Spawn Function Updates

**File**: `src/giljo_mcp/tools/orchestration.py` (and similar)

```python
# BEFORE:
agent_execution = AgentExecution(
    agent_id=agent_id,
    job_id=job_id,
    tenant_key=tenant_key,
    agent_type=agent_type,  # Old name
    agent_name=agent_name,
    ...
)

# AFTER:
agent_execution = AgentExecution(
    agent_id=agent_id,
    job_id=job_id,
    tenant_key=tenant_key,
    display_name=display_name,  # New name
    agent_name=agent_name,
    ...
)
```

#### Step 5: API Schema Updates

**File**: `api/endpoints/agent_jobs/models.py` (and similar)

```python
# BEFORE:
class JobResponse(BaseModel):
    agent_type: str

# AFTER:
class JobResponse(BaseModel):
    display_name: str  # UI label
    agent_name: Optional[str] = None  # Template filename
```

#### Step 6: Frontend Updates

Replace `.agent_type` with `.display_name` in Vue components and stores.

---

## Field Definitions (Canonical)

| Field | Table | Purpose | Example | Set By |
|-------|-------|---------|---------|--------|
| `agent_id` | AgentExecution | Unique instance UUID | `"abc-123-def"` | System |
| `display_name` | AgentExecution | Human-readable UI label | `"Backend API Developer"` | Orchestrator |
| `agent_name` | AgentExecution | Template filename | `"tdd-implementor"` | Orchestrator |
| `job_id` | AgentJob | Work order UUID | `"xyz-789-uvw"` | System |

**Lookup Flow**:
```
agent_name = "tdd-implementor"
    → AgentTemplate.name = "tdd-implementor"
        → color = "#4CAF50"
        → rules = {...}
        → role = "implementer" (template category)
```

---

## What NOT to Change

1. **`AgentTemplate.role`** - This is the template category (implementer, tester, etc.)
2. **Message `role`** - Chat message sender (system, agent, user)
3. **User `role`** - Authorization (admin, user)
4. **`AgentJob.job_type`** - Work order type (keep as-is or evaluate separately)

---

## Verification

After migration:

```bash
# No agent_type in model
grep "agent_type" src/giljo_mcp/models/agent_identity.py
# Should return: nothing

# display_name exists
grep "display_name" src/giljo_mcp/models/agent_identity.py
# Should return: the column definition

# Run tests
pytest tests/ -x -v
```

---

## Implementation Checklist

- [ ] Review failed branch `clean-display-name-migration` for bloat cleanup
- [ ] Verify 0413 files are retired in `handovers/completed/0413_retired/`
- [ ] Implement bloat cleanup (if valuable)
- [ ] Create migration file `0414_rename_agent_type_to_display_name.py`
- [ ] Update `AgentExecution` model
- [ ] Update spawn functions (orchestration.py, orchestration_service.py)
- [ ] Update API schemas
- [ ] Update frontend components
- [ ] Run full test suite
- [ ] Update CLAUDE.md with new field definitions
- [ ] Commit changes to master

---

## Lessons Learned (from 0413 series failure)

1. **Don't rename through an intermediate** - `agent_type → role → display_name` caused confusion
2. **Keep semantic clarity** - `role` was ambiguous (type or label?)
3. **One migration, one purpose** - Don't bundle unrelated changes
4. **Work in master** - Don't do extensive work in branches that may conflict
5. **Test before committing** - Run full test suite before each commit
6. **Never delete backup branches** - They saved this project

---

## Rollback Instructions

If issues arise:

```bash
# Restore master to clean state
git reset --hard backup/0414-clean-restore-point

# Or go back to TRUE original
git reset --hard backup/pre-agent-type-to-role-migration
```

---

**WORK IN MASTER. DO NOT CREATE NEW BRANCHES. KEEP ALL BACKUP BRANCHES.**
