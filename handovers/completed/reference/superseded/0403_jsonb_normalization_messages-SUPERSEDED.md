# Handover 0403: JSONB Normalization - Messages Field Cleanup

**Date:** 2026-01-02
**From Agent:** Deep Researcher Analysis (Handover 0402)
**To Agent:** database-expert, backend-tester
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** SUPERSEDED by Handover 0387

> **Note:** This handover has been merged into Handover 0387 (Broadcast Fan-out at Write) as Phase 4. See 0387 for the combined implementation plan.

---

## Task Summary

Normalize high-priority JSONB fields identified during Handover 0402 analysis. The `messages` JSONB array in `AgentExecution` duplicates the existing `Message` table, causing data inconsistency and storage bloat.

**Why:** JSONB fields that grow unbounded or duplicate normalized tables cause:
- Data inconsistency (two sources of truth)
- Storage bloat (same data stored twice)
- Query inefficiency (can't use proper indexes)
- SaaS scalability issues

---

## Analysis Findings

### Priority Matrix (from deep-researcher)

| Priority | Field | Table | Issue | Recommendation |
|----------|-------|-------|-------|----------------|
| **HIGHEST** | `messages` | AgentExecution | Duplicates Message table | Remove, use FK relationship |
| **HIGH** | `sequential_history` | Product.product_memory | Grows unbounded | Separate table |
| **MEDIUM** | `to_agents` | Message | Array of UUIDs | Junction table after fan-out |
| **MEDIUM** | `acknowledged_by` | Message | Array of UUIDs | Junction table |
| **LOW** | `completed_by` | Message | Array of UUIDs | Consider normalizing |

### Fields Appropriate as JSONB (18 fields)

These should remain JSONB:
- Config objects (`field_priorities`, `depth_config`, `user_context_config`)
- Metadata (`job_metadata`, `context_metadata`)
- Flexible schemas (`result`, `progress_data`)
- User preferences (`theme_config`, `notification_settings`)

---

## Phase 1: AgentExecution.messages Cleanup (HIGHEST Priority)

### Current State

```python
# AgentExecution model (agent_identity.py)
messages = Column(JSONB, default=list)  # Stores message objects inline
```

The `messages` array duplicates what's already in the `Message` table, leading to:
- Message counts calculated from JSONB array
- Inconsistent data if Message table updated separately
- Bloated execution records

### Target State

```python
# AgentExecution model - REMOVE messages column
# messages = Column(JSONB, default=list)  # DELETED

# Add relationship to Message table
messages = relationship(
    "Message",
    primaryjoin="AgentExecution.agent_id == foreign(Message.to_agent_id)",
    lazy="dynamic",
    viewonly=True,
)
```

### Migration Steps

1. **Verify Message table has agent linkage**
   - Check `Message.to_agent_id` or similar FK exists
   - If not, add `agent_id` column to Message table

2. **Update code that reads `execution.messages`**
   - `api/endpoints/agent_jobs/table_view.py` - lines 201-206
   - `frontend/src/stores/agentJobsStore.js` - message counters

3. **Update code that writes to `execution.messages`**
   - Find all places appending to messages array
   - Replace with Message table inserts

4. **Migration script**
   - Backup JSONB data
   - Verify all messages exist in Message table
   - Remove column (or mark deprecated)

### Files to Modify

| File | Changes |
|------|---------|
| `src/giljo_mcp/models/agent_identity.py` | Remove `messages` column, add relationship |
| `api/endpoints/agent_jobs/table_view.py` | Query Message table for counts |
| `src/giljo_mcp/services/message_service.py` | Verify writes go to Message table |
| `frontend/src/stores/agentJobsStore.js` | May need adjustment if message format changes |

---

## Phase 2: Product.product_memory.sequential_history (HIGH Priority)

### Current State

```python
# Product model
product_memory = Column(JSONB, default=dict)
# Contains: { "sequential_history": [...unbounded array...] }
```

### Target State

New table: `product_history_entries`

```sql
CREATE TABLE product_history_entries (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    tenant_key VARCHAR(64) NOT NULL,
    sequence INT NOT NULL,
    entry_type VARCHAR(50) NOT NULL,  -- 'project_closeout', 'milestone', etc.
    project_id UUID REFERENCES projects(id),
    summary TEXT,
    git_commits JSONB,  -- Array of commit objects (appropriate for JSONB)
    decisions_made JSONB,  -- Array of strings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(product_id, sequence)
);
```

---

## Phase 3: Message Table Fan-out Fields (MEDIUM Priority)

### Dependency: Handover 0387

This phase depends on **Handover 0387: Broadcast Fan-out at Write**, which implements the industry-standard pattern for handling broadcast messages.

After 0387 is complete:
- `to_agents` array replaced with one row per recipient
- `acknowledged_by` becomes a simple boolean `acknowledged`
- `completed_by` becomes a simple boolean `completed`

**Recommendation:** Defer Phase 3 until after 0387 implementation.

---

## Testing Requirements

### Unit Tests
- `test_execution_message_relationship` - verify FK relationship works
- `test_message_counts_from_table` - verify counts match JSONB counts
- `test_backward_compatibility` - existing code continues to work

### Integration Tests
- Create execution, send messages, verify relationship works
- WebSocket events include correct message counts
- Dashboard displays accurate message counters

### Data Validation
- Before migration: count messages in JSONB vs Message table
- After migration: verify counts match

---

## Success Criteria

### Phase 1 (AgentExecution.messages)
- [ ] JSONB `messages` column removed or deprecated
- [ ] Message counts derived from Message table
- [ ] No data loss during migration
- [ ] WebSocket events still include message info
- [ ] Dashboard message counters work

### Phase 2 (sequential_history)
- [ ] New `product_history_entries` table created
- [ ] Migration script moves existing data
- [ ] 360 Memory features continue to work
- [ ] Proper indexes for sequence queries

### Phase 3 (Message fan-out)
- [ ] Deferred to post-0387 implementation

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | HIGH | Backup JSONB before removing, verify counts match |
| Breaking existing queries | MEDIUM | Run both old and new code paths in parallel during transition |
| Performance regression | LOW | Add proper indexes, test with realistic data volumes |

---

## Related

- Handover 0402: Agent TODO Items Table (triggered this analysis)
- Handover 0387: Broadcast Fan-out at Write (dependency for Phase 3)
- Handover 0366: Agent Identity Refactor (created AgentExecution model)

---

## Progress Updates

### 2026-01-02 - Initial Creation
**Status:** Ready for Implementation
**Notes:** Created from JSONB analysis during Handover 0402. Prioritized based on data duplication severity and SaaS scalability impact.
