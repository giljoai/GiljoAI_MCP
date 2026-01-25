# Handover 0461b: Database Schema Cleanup

**Series**: Handover Simplification Series (0461)
**Color**: Blue (#2196F3)
**Estimated Effort**: 4-6 hours
**Subagents**: `database-expert`, `tdd-implementor`
**Dependencies**: 0461a (need clean docs before DB changes)

---

## Mission Statement

Mark complex succession-related database columns as deprecated and add support for the new `session_handover` entry type in 360 Memory. This prepares for the simplified handover architecture without breaking existing data.

**Key Principle**: Mark columns as DEPRECATED (not delete) to preserve data and enable rollback.

---

## Background

### Current Complex Succession Schema

The `AgentExecution` table has columns supporting "Agent ID Swap" succession:

| Column | Purpose | Issue |
|--------|---------|-------|
| `instance_number` | Track succession instances (1, 2, 3...) | Overly complex for simple handover |
| `succeeded_by` | Points to successor agent_id | Part of complex chain tracking |
| `spawned_by` | Points to parent agent_id | **KEEP** - still useful for agent lineage |
| `decommissioned_at` | Timestamp when decommissioned | Part of Agent ID Swap |
| `succession_reason` | Why succession happened | Can be stored in 360 Memory instead |
| `handover_summary` | JSONB handover context | Should move to 360 Memory |

### New Simple Architecture

Instead of complex Agent ID Swap with multiple rows per agent:
1. Single `AgentExecution` row per agent (no succession rows)
2. Handover context stored in 360 Memory as `session_handover` entry
3. New session reads 360 Memory to get context

---

## Tasks

### Task 1: Add Deprecation Comments to AgentExecution Model

**File**: `src/giljo_mcp/models/agent_identity.py`

Update the following column definitions with deprecation comments:

```python
# Line ~183: instance_number
instance_number = Column(
    Integer,
    default=1,
    nullable=False,
    comment="DEPRECATED (Handover 0461b): Will be removed in v4.0. Use single instance per agent.",
)

# Line ~199: decommissioned_at
decommissioned_at = Column(
    DateTime(timezone=True),
    nullable=True,
    comment="DEPRECATED (Handover 0461b): Will be removed in v4.0. Agents no longer decommissioned.",
)

# Line ~207: succeeded_by
succeeded_by = Column(
    String(36),
    nullable=True,
    comment="DEPRECATED (Handover 0461b): Will be removed in v4.0. Use 360 Memory for handover tracking.",
)

# Line ~277: succession_reason
succession_reason = Column(
    String(100),
    nullable=True,
    comment="DEPRECATED (Handover 0461b): Will be removed in v4.0. Use 360 Memory session_handover entry.",
)

# Line ~282: handover_summary
handover_summary = Column(
    JSONB,
    nullable=True,
    comment="DEPRECATED (Handover 0461b): Will be removed in v4.0. Use 360 Memory session_handover entry.",
)
```

**Note**: Keep `spawned_by` - it's still useful for tracking who spawned whom (orchestrator → agent relationship).

### Task 2: Update Class Docstring

**File**: `src/giljo_mcp/models/agent_identity.py`

Update `AgentExecution` class docstring (starting at line ~136) to note deprecations:

```python
class AgentExecution(Base):
    """
    Executor instance - represents an active agent.

    Represents the WHO (which agent instance is executing).

    Handover 0461b DEPRECATION NOTICE:
    The following columns are deprecated and will be removed in v4.0:
    - instance_number: Use single instance per agent
    - decommissioned_at: Agents no longer decommissioned
    - succeeded_by: Use 360 Memory for handover tracking
    - succession_reason: Use 360 Memory session_handover entry
    - handover_summary: Use 360 Memory session_handover entry

    NOTE: The `messages` JSONB column is also DEPRECATED (Handover 0387i).
    Use `messages_sent_count`, `messages_waiting_count`, `messages_read_count` instead.

    Relationships:
    - job: Many executions → One job (work order)
    - spawned_by: Points to parent agent_id (who spawned this executor) - STILL ACTIVE

    Multi-tenant Isolation:
    - All queries MUST filter by tenant_key
    """
```

### Task 3: Add `session_handover` Entry Type Support

**File**: `src/giljo_mcp/tools/write_360_memory.py`

The 360 Memory system already supports `project_completion` and `handover_closeout` entry types. Add `session_handover`:

1. Find the entry type validation (look for `entry_type` parameter validation)
2. Add `session_handover` to the allowed values

Example structure for `session_handover` entry:

```python
{
    "entry_type": "session_handover",
    "project_id": "uuid",
    "summary": "Session handover context...",
    "key_outcomes": ["Work done so far..."],
    "decisions_made": ["Decisions made..."],
    "metrics": {
        "session_context": {
            "context_used": 135000,
            "context_budget": 150000,
            "active_agents": [...],
            "pending_work": [...],
            "next_steps": "..."
        }
    }
}
```

**Implementation**:

```python
# In write_360_memory.py, update the entry_type validation
VALID_ENTRY_TYPES = {"project_completion", "handover_closeout", "session_handover"}

# Validate entry_type
if entry_type not in VALID_ENTRY_TYPES:
    return {"error": f"Invalid entry_type. Must be one of: {VALID_ENTRY_TYPES}"}
```

### Task 4: Document `session_handover` Schema

**File**: `docs/360_MEMORY_MANAGEMENT.md`

Add documentation for the new entry type:

```markdown
### Entry Type: session_handover

Used when an orchestrator session ends and context needs to be preserved for a continuation session.

**Fields**:
- `summary`: 2-3 paragraph overview of current session state
- `key_outcomes`: List of completed work items
- `decisions_made`: List of decisions made during session
- `metrics.session_context`: Object containing:
  - `context_used`: Tokens used in ended session
  - `context_budget`: Total token budget
  - `active_agents`: List of agent IDs still working
  - `pending_work`: List of incomplete items
  - `next_steps`: Recommended actions for continuation

**Example**:
```python
await write_360_memory(
    project_id="...",
    summary="Completed frontend implementation. Backend API endpoints working...",
    key_outcomes=["Vue components created", "API integration tested"],
    decisions_made=["Used Vuetify for UI", "JWT for auth"],
    entry_type="session_handover",
    metrics={
        "session_context": {
            "context_used": 135000,
            "context_budget": 150000,
            "active_agents": ["agent-123", "agent-456"],
            "pending_work": ["Error handling", "Unit tests"],
            "next_steps": "Complete error handling in API endpoints"
        }
    }
)
```
```

### Task 5: Update ProductMemoryRepository (if needed)

**File**: `src/giljo_mcp/repositories/product_memory_repository.py`

Verify that `session_handover` entries can be created and queried. The repository should already handle any entry type, but verify:

1. `create_entry()` accepts arbitrary entry types
2. `get_entries()` can filter by entry type
3. No hardcoded entry type lists that would reject `session_handover`

---

## Verification

### Database Schema
```bash
# Verify model loads without errors
python -c "from src.giljo_mcp.models.agent_identity import AgentExecution; print('OK')"
```

### 360 Memory Entry Type
```bash
# Run 360 memory tests
pytest tests/ -k "360_memory or write_360_memory" -v
```

### Full Test Suite
```bash
pytest tests/ -v
```

---

## Files Modified Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `src/giljo_mcp/models/agent_identity.py` | Add deprecation comments | ~30 lines |
| `src/giljo_mcp/tools/write_360_memory.py` | Add entry type | ~10 lines |
| `docs/360_MEMORY_MANAGEMENT.md` | Document schema | ~40 lines |
| `src/giljo_mcp/repositories/product_memory_repository.py` | Verify (likely no changes) | ~0 lines |

**Total**: ~5 files, ~80 lines changed

---

## Success Criteria

- [ ] `instance_number` column has deprecation comment
- [ ] `decommissioned_at` column has deprecation comment
- [ ] `succeeded_by` column has deprecation comment
- [ ] `succession_reason` column has deprecation comment
- [ ] `handover_summary` column has deprecation comment
- [ ] `AgentExecution` docstring updated with deprecation notice
- [ ] `session_handover` entry type accepted by `write_360_memory()`
- [ ] Documentation updated with `session_handover` schema
- [ ] All tests pass
- [ ] Existing data preserved (no migrations that drop columns)

---

## Important Notes

### DO NOT:
- Delete any columns (mark deprecated only)
- Create migrations that alter column structure
- Remove existing functionality

### DO:
- Add deprecation comments to columns
- Add new entry type support
- Document the new schema
- Preserve backward compatibility

---

## Rollback

Schema changes are comment-only. To rollback:
```bash
git checkout HEAD -- src/giljo_mcp/models/agent_identity.py
```

---

## Next Handover

After 0461b completes, proceed to **0461c: Backend Simplification**.
