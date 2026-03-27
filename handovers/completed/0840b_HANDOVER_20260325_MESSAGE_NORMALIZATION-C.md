# Handover 0840b: Message Table Normalization

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Planning Session)
**To Agent:** Next Session (database-expert + tdd-implementor)
**Priority:** Critical
**Estimated Complexity:** 10-14 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Normalize the `messages` table by extracting JSONB fields into proper columns and junction tables. The `Message` model currently stores sender identity (`_from_agent`, `_from_display_name`) in a `meta_data` JSONB dict, recipients in a `to_agents` JSONB array, and acknowledgments in `acknowledged_by`/`completed_by` JSONB arrays. These are queried with JSONB operators (`->>`, `@>`) in 9+ code locations. This is the highest-volume table and the most impactful normalization.

## Context and Background

Messages are created on every agent interaction. In SaaS with multiple tenants running concurrent agents, JSONB containment queries on `to_agents` and `->>` extraction on `meta_data._from_agent` will become bottlenecks. The `acknowledged_by` field uses a fragile `.append()` mutation pattern that requires SQLAlchemy `flag_modified`.

**Prerequisite:** Handover 0840a (Dead Column Cleanup) must be complete. Check chain log.

## Technical Details

### Current JSONB Fields on `messages` Table

| Column | Type | Current Usage | Problem |
|--------|------|--------------|---------|
| `to_agents` | JSONB | Array of agent IDs `["uuid1", "all"]`, queried with `@>` containment in 6+ places | Should be junction table |
| `acknowledged_by` | JSONB | Array of agent IDs, mutated with `.append()` | Fragile mutation pattern, should be junction table |
| `completed_by` | JSONB | Array of agent IDs | Same pattern as acknowledged_by |
| `meta_data` | JSONB | `{_from_agent: "uuid", _from_display_name: "Name", auto_generated: true}` | Disguised FK, queried with `->>` in SQL WHERE |

### New Schema

```sql
-- New columns on messages table
ALTER TABLE messages ADD COLUMN from_agent_id VARCHAR(36);
ALTER TABLE messages ADD COLUMN from_display_name VARCHAR(255);
ALTER TABLE messages ADD COLUMN auto_generated BOOLEAN DEFAULT FALSE;

-- New junction table for recipients
CREATE TABLE message_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    agent_id VARCHAR(36) NOT NULL,
    tenant_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(message_id, agent_id)
);
CREATE INDEX idx_message_recipients_agent ON message_recipients(agent_id, tenant_key);
CREATE INDEX idx_message_recipients_message ON message_recipients(message_id);

-- New junction table for acknowledgments
CREATE TABLE message_acknowledgments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    agent_id VARCHAR(36) NOT NULL,
    tenant_key VARCHAR(255) NOT NULL,
    acknowledged_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(message_id, agent_id)
);
CREATE INDEX idx_message_acks_agent ON message_acknowledgments(agent_id, tenant_key);
CREATE INDEX idx_message_acks_message ON message_acknowledgments(message_id);

-- New junction table for completions
CREATE TABLE message_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    agent_id VARCHAR(36) NOT NULL,
    tenant_key VARCHAR(255) NOT NULL,
    completed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(message_id, agent_id)
);
CREATE INDEX idx_message_completions_agent ON message_completions(agent_id, tenant_key);
CREATE INDEX idx_message_completions_message ON message_completions(message_id);
```

### Files That Must Change

**Models:**
- `src/giljo_mcp/models/tasks.py` — Add new columns to Message, create MessageRecipient, MessageAcknowledgment, MessageCompletion models

**Services (HEAVIEST IMPACT):**
- `src/giljo_mcp/services/message_service.py` — Rewrite `send_message`, `receive_messages`, `list_messages`, `acknowledge_message`, `complete_message`. Replace all `@>` containment queries with JOINs. Replace `meta_data["_from_agent"]` with `from_agent_id`. Replace `.append()` mutations with INSERT.
- `src/giljo_mcp/services/orchestration_service.py` — Update message creation calls (sets `meta_data._from_agent`)

**Repositories:**
- `src/giljo_mcp/repositories/statistics_repository.py` — Replace `->>` extraction with `from_agent_id` column in per-agent message count queries

**API/Schemas:**
- `src/giljo_mcp/services/service_responses.py` — Update response models (replace `to_agents` list with recipients list, replace `meta_data` with direct fields)

**Frontend:**
- Any Vue component displaying message sender, recipients, or acknowledgment status
- Check `frontend/src/views/MessagesView.vue` and related components

### Migration Data Backfill

The migration must:
1. Create new columns/tables
2. Backfill `from_agent_id` from `meta_data->>'_from_agent'`
3. Backfill `from_display_name` from `meta_data->>'_from_display_name'`
4. Backfill `auto_generated` from `meta_data->>'auto_generated'`
5. Backfill `message_recipients` from `to_agents` array (one row per array element)
6. Backfill `message_acknowledgments` from `acknowledged_by` array
7. Backfill `message_completions` from `completed_by` array
8. DROP old columns (`to_agents`, `acknowledged_by`, `completed_by`, `meta_data`)

**IMPORTANT:** All backfill queries must be tenant-aware. Include `tenant_key` in all INSERT...SELECT operations.

## Implementation Plan

### Phase 1: Database Migration
1. Create Alembic migration with idempotency guards
2. Add new columns to messages
3. Create 3 junction tables with proper indexes
4. Backfill data from JSONB → new columns/tables
5. Drop old JSONB columns

### Phase 2: Model Updates
1. Add `from_agent_id`, `from_display_name`, `auto_generated` columns to Message model
2. Create `MessageRecipient`, `MessageAcknowledgment`, `MessageCompletion` models
3. Add relationships on Message model
4. Remove `to_agents`, `acknowledged_by`, `completed_by`, `meta_data` from Message model

### Phase 3: Service Layer Rewrite
1. **message_service.py** — This is the biggest change:
   - `send_message()`: Create MessageRecipient rows instead of setting `to_agents` array. Set `from_agent_id` directly.
   - `receive_messages()`: JOIN message_recipients instead of `@>` containment query
   - `list_messages()`: JOIN message_recipients, use `from_agent_id` column directly
   - `acknowledge_message()`: INSERT into message_acknowledgments instead of `.append()`
   - `complete_message()`: INSERT into message_completions instead of `.append()`
2. **orchestration_service.py** — Set `from_agent_id=` directly instead of building `meta_data` dict
3. **statistics_repository.py** — Replace `->>` extraction with `from_agent_id` column

### Phase 4: API Response Updates
1. Update response schemas to expose `from_agent_id`, `from_display_name`, `recipients` (list from junction table)
2. Ensure frontend receives the same data shape (or update frontend to match)

### Phase 5: Test Rewrite
**Files requiring REWRITE (directly assert on JSONB structure):**
- `tests/services/test_message_service_contract.py` (4 tests)
- `tests/services/test_message_service_0372_unification.py` (5 tests)
- `tests/services/test_broadcast_self_exclusion.py` (5 tests)
- `tests/services/test_message_display_name_0827a.py` (6 tests)
- `tests/services/test_complete_job_result.py` (5 tests)
- `tests/schemas/test_service_responses_task.py` (~8 tests)
- `tests/unit/test_broadcast_deadlock_retry.py` (16 tests)

**Files requiring UPDATE (fixture/parameter changes):**
- `tests/services/conftest.py` — Update message creation helpers
- `tests/repositories/conftest.py` — Update test message fixtures
- `tests/services/test_message_service_counters_0387f_counter_updates.py`
- `tests/services/test_message_service_counters_0387f_websocket_events.py`
- `tests/services/test_message_service_staging_directive.py`
- `tests/services/test_message_service_websocket_injection.py`
- `tests/services/test_message_service_empty_state.py`
- `tests/services/test_message_tenant_isolation_regression_send_broadcast.py`
- `tests/services/test_message_tenant_isolation_regression_read_complete.py`
- `tests/services/test_message_counter_atomic_self_healing.py`
- `tests/services/test_message_auto_block_0827b.py`
- `tests/services/test_reactivation_0827c.py`
- `tests/services/test_tenant_isolation_services_message_project.py`

### Phase 6: Verify
1. `ruff check src/ api/` — zero lint issues
2. `pytest tests/ -x --timeout=30` — all tests pass
3. Grep for any remaining `to_agents`, `acknowledged_by`, `completed_by` references
4. Grep for any remaining `meta_data.*_from_agent` references

## CRITICAL: Tenant Isolation

Every new table MUST include `tenant_key`. Every query MUST filter by `tenant_key`. Use TenantManager patterns.

## Testing Requirements

- ~49 tests need REWRITE across 7 files
- ~86 tests need UPDATE across 13 files
- All tenant isolation regression tests must pass
- New tests for junction table operations

## Success Criteria

- [ ] 3 junction tables created (message_recipients, message_acknowledgments, message_completions)
- [ ] `from_agent_id`, `from_display_name`, `auto_generated` columns on messages
- [ ] Old JSONB columns dropped (to_agents, acknowledged_by, completed_by, meta_data)
- [ ] All service layer code uses JOINs instead of JSONB operators
- [ ] Data backfilled correctly
- [ ] All tests pass (rewritten + updated)
- [ ] `ruff check` clean
- [ ] Committed to `feature/0840-jsonb-normalization`

## Rollback Plan

`alembic downgrade -1` to restore old columns. Git revert the commit.

## Coding Principles (from HANDOVER_INSTRUCTIONS.md)

- TDD: Write tests FIRST for new junction table operations, then implement
- Clean Code: DELETE old JSONB code completely, no commented-out remnants
- Tenant isolation: EVERY query filters by tenant_key — no exceptions
- Exception-based errors: Raise, don't return dicts
- Search before you build: Use existing TenantManager, MessageService patterns
- Trace full chain: model → repository → service → tool → endpoint → frontend → test
- No function exceeds 200 lines

## STOP CONDITIONS

If any of these occur, STOP and document in chain log for user review:
- Discovery of additional code paths writing to `meta_data` not identified in the audit
- Test failures that indicate undocumented dependencies on JSONB structure
- Frontend components that require major restructuring beyond parameter renaming

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0840_chain/chain_log.json`. Verify 0840a status is `complete`. Read 0840a `notes_for_next`.

### Step 2: Mark Session Started
Update session 0840b: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Use database-expert subagent for migration and tdd-implementor for service rewrite + tests.

### Step 4: Update Chain Log
Update your session with results, deviations, notes_for_next.

### Step 5: Commit Work
```bash
git add -A
git commit -m "feat: Normalize Message table — junction tables replace JSONB arrays (0840b)"
```

### Step 6: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0840c - Product Config Normalization\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0840c. READ FIRST: F:\GiljoAI_MCP\handovers\0840c_product_config_normalization.md then READ: F:\GiljoAI_MCP\prompts\0840_chain\0840c_prompt.md for chain instructions. You are on branch feature/0840-jsonb-normalization. Use database-expert and tdd-implementor subagents.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
