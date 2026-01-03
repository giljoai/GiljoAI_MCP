# Handover: Broadcast Message Fan-out at Write

**Date:** 2026-01-02
**From Agent:** Documentation Manager
**To Agent:** Backend Integration Tester / Database Expert
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation

---

## Task Summary

Implement "Fan-out at Write" pattern for broadcast messages to fix critical bugs in the current broadcast system. When `to_agents=["all"]` is passed to `send_message()`, the system currently stores "all" literally in the database and uses complex query logic in `receive_messages()` to match broadcasts. This causes multiple issues:

1. **Literal "all" storage**: `to_agents=["all"]` is stored as-is instead of expanding to actual recipients
2. **Complex broadcast matching**: `receive_messages()` has intricate JSONB query logic prone to bugs
3. **Premature acknowledgment**: When first agent reads a broadcast, status changes to "acknowledged", blocking other agents
4. **Sender exclusion bugs**: Comparison of `_from_agent` to `job.job_type` may not match correctly

**Solution**: Expand `to_agents=["all"]` into individual Message records at send time (industry standard pattern used by Twitter, Slack, Discord).

---

## Context and Background

### Current Implementation Issues

**Location**: `src/giljo_mcp/services/message_service.py`

**Bug 1: Literal "all" Storage** (lines 164-207)
```python
if agent_ref == 'all':
    resolved_to_agents.append('all')  # ❌ Stores literal "all"
```

**Bug 2: Complex Broadcast Matching** (lines 619-630)
```python
or_(
    # Direct message: JSONB array contains agent_id
    func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
    # Broadcast: JSONB array contains 'all' BUT exclude sender
    and_(
        func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB)),
        func.coalesce(
            Message.meta_data.op('->')('_from_agent').astext,
            func.cast('', String)
        ) != job.job_type  # ❌ job_type may not match _from_agent format
    )
)
```

**Bug 3: Premature Acknowledgment** (lines 686-697)
```python
# AUTO-ACKNOWLEDGE: Bulk update all retrieved messages (Handover 0326)
for msg in messages:
    msg.status = "acknowledged"  # ❌ Changes status for ALL recipients
```

### Industry Standard Pattern: Fan-out at Write

**How it works**:
1. When `to_agents=["all"]`, query all active project agents
2. Exclude: sender (self), completed agents
3. Create individual Message records for each recipient
4. No special broadcast logic in `receive_messages()` - just match `agent_id`

**Benefits**:
- ✅ Simple read queries (direct `agent_id` match)
- ✅ Per-recipient delivery tracking built-in
- ✅ Each agent gets independent Message record with own status
- ✅ Easier debugging (one message = one recipient)
- ✅ No complex JSONB queries
- ✅ Sender exclusion happens naturally during expansion

---

## Technical Details

### Files to Modify

**1. `src/giljo_mcp/services/message_service.py`**

**Method: `send_message()` (lines 164-207)**
- Detect `to_agents=["all"]`
- Query active agents in project (exclude sender, exclude completed agents)
- Create individual Message records for each recipient
- Keep existing logic for direct messages (non-broadcast)

**Method: `receive_messages()` (lines 619-630)**
- Remove broadcast `OR` clause from query
- Simplify to: `Message.to_agents.contains([agent_id])`
- Remove sender exclusion logic (handled at write time)

### Database Schema

**No schema changes required!** The existing `Message` table already supports this:
- `to_agents`: JSONB array (will contain single agent_id per message)
- `message_type`: VARCHAR (broadcast vs direct)
- `status`: VARCHAR (per-recipient acknowledgment)

### Key Code Sections

**Current Code (Lines 164-193):**
```python
# BEFORE (Bug: stores literal "all")
for agent_ref in to_agents:
    if agent_ref == 'all':
        resolved_to_agents.append('all')  # ❌ Literal storage
```

**Proposed Fix:**
```python
# AFTER (Fan-out pattern)
for agent_ref in to_agents:
    if agent_ref == 'all':
        # Query all active agents in project
        exec_result = await session.execute(
            select(AgentExecution).join(AgentJob).where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.status.in_(["waiting", "working", "blocked"]),
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.agent_id != from_agent  # Exclude sender
                )
            )
        )
        executions = exec_result.scalars().all()

        # Add each active agent as individual recipient
        for execution in executions:
            resolved_to_agents.append(execution.agent_id)
            self._logger.info(
                f"[FANOUT] Expanded broadcast to agent_id '{execution.agent_id}'"
            )
```

**Current Broadcast Matching (Lines 619-630):**
```python
# BEFORE (Complex JSONB query)
or_(
    func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
    and_(
        func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB)),
        func.coalesce(...) != job.job_type  # ❌ Buggy sender exclusion
    )
)
```

**Proposed Simplification:**
```python
# AFTER (Simple array match)
conditions = [
    Message.tenant_key == tenant_key,
    Message.project_id == job.project_id,
    Message.status == "pending",
    func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB))
    # No special broadcast logic needed!
]
```

---

## Implementation Plan

### Phase 1: Send Message Fan-out (2-3 hours)
**File**: `src/giljo_mcp/services/message_service.py` (lines 164-207)

**Actions**:
1. Detect `to_agents=["all"]` in send_message()
2. Query active AgentExecution records in project
3. Exclude sender via `agent_id != from_agent`
4. Exclude completed agents via `status.in_(["waiting", "working", "blocked"])`
5. Expand resolved_to_agents list with individual agent_ids
6. Create individual Message records in a loop (one per recipient)
7. Update logging to show fan-out count

**Expected Outcome**:
- Broadcast to 5 agents creates 5 individual Message records
- Each message has `to_agents=[agent_id]` (single recipient)
- No literal "all" stored in database

**Testing Criteria**:
- Query `SELECT * FROM messages WHERE to_agents @> '["all"]'::jsonb` returns 0 rows
- Broadcast to N agents creates N Message records
- Each Message has different `to_agents` value (unique recipient)

### Phase 2: Simplify Receive Messages (1-2 hours)
**File**: `src/giljo_mcp/services/message_service.py` (lines 619-630)

**Actions**:
1. Remove broadcast `OR` clause from receive_messages() query
2. Simplify to single condition: `to_agents` contains `agent_id`
3. Remove sender exclusion logic (no longer needed)
4. Test acknowledgment per-recipient (each agent gets own status)

**Expected Outcome**:
- Query simplified by ~10 lines
- No more JSONB `'all'` matching logic
- Each agent receives only their own Message records

**Testing Criteria**:
- Agent A reads broadcast: status changes for Agent A's message only
- Agent B still sees pending message (different Message record)
- No sender receives their own broadcast

### Phase 3: Integration Testing (1-2 hours)
**Actions**:
1. Write unit test: `test_broadcast_fanout_creates_individual_messages()`
2. Write integration test: `test_broadcast_per_recipient_acknowledgment()`
3. Write edge case test: `test_broadcast_excludes_sender()`
4. Write edge case test: `test_broadcast_excludes_completed_agents()`
5. Manual test: Send broadcast via UI, verify in database
6. Manual test: Multiple agents read broadcast independently

**Expected Outcome**:
- All tests pass
- Manual verification confirms fan-out behavior
- No regressions in direct messaging

**Testing Criteria**:
- 4 new unit/integration tests added
- All existing message tests still pass
- Coverage remains >80%

**Recommended Sub-Agent**: Backend Integration Tester + Database Expert (pair programming)

---

## Testing Requirements

### Unit Tests

**File**: `tests/services/test_message_service.py`

**Test 1: Fan-out Creates Individual Messages**
```python
async def test_broadcast_fanout_creates_individual_messages(db_manager, tenant_manager):
    """Broadcast to 'all' should create one Message per active agent"""
    # Setup: Create project with 3 active agents + 1 completed agent
    # Action: send_message(to_agents=["all"])
    # Assert: Query messages table, expect 3 records (not 1)
    # Assert: Each to_agents contains single agent_id (not "all")
```

**Test 2: Per-Recipient Acknowledgment**
```python
async def test_broadcast_per_recipient_acknowledgment(db_manager, tenant_manager):
    """Each agent should acknowledge independently"""
    # Setup: Send broadcast to 3 agents
    # Action: Agent A calls receive_messages()
    # Assert: Agent A's message status = acknowledged
    # Assert: Agent B's message status = pending
    # Assert: Agent C's message status = pending
```

**Test 3: Sender Exclusion**
```python
async def test_broadcast_excludes_sender(db_manager, tenant_manager):
    """Sender should not receive their own broadcast"""
    # Setup: Orchestrator sends broadcast
    # Action: send_message(from_agent=orchestrator_id, to_agents=["all"])
    # Assert: Query messages where to_agents contains orchestrator_id = 0 rows
```

**Test 4: Completed Agents Exclusion**
```python
async def test_broadcast_excludes_completed_agents(db_manager, tenant_manager):
    """Completed agents should not receive broadcasts"""
    # Setup: Create project with 2 active agents + 1 completed agent
    # Action: send_message(to_agents=["all"])
    # Assert: Only 2 messages created (completed agent excluded)
```

### Integration Tests

**File**: `tests/integration/test_broadcast_workflow.py`

**Test 1: End-to-End Broadcast Flow**
```python
async def test_e2e_broadcast_workflow(api_client, test_project):
    """Full broadcast lifecycle: send → receive → acknowledge"""
    # Setup: Project with orchestrator + 3 executor agents
    # Action 1: Orchestrator sends broadcast via MCP tool
    # Action 2: Each agent calls receive_messages()
    # Assert: Each agent receives exactly 1 message
    # Assert: Acknowledgment doesn't affect other agents
```

### Manual Testing

**Procedure**:
1. Open GiljoAI dashboard → Project → Jobs tab
2. Select orchestrator → "Send Message" → Select "All Agents"
3. Send test message: "Broadcast test"
4. Open PostgreSQL: `psql -U postgres -d giljo_mcp`
5. Query: `SELECT id, to_agents, status FROM messages ORDER BY created_at DESC LIMIT 10;`
6. Verify: One message per agent (not single message with "all")
7. Click "View Messages" for Agent 1 → Verify message appears
8. Query again → Verify Agent 1's message status = acknowledged
9. Click "View Messages" for Agent 2 → Verify message still appears
10. Query again → Verify Agent 2's message status = pending

**Expected Results**:
- 5 agents in project → 5 Message records created (minus sender)
- Each `to_agents` column contains single UUID
- Independent acknowledgment per agent
- No literal "all" in database

**Known Edge Cases**:
- Project with only 1 agent (sender): No messages created (expected)
- Project with all completed agents: No messages created (expected)
- Sender is also recipient (via direct message): Should still work

---

## Dependencies and Blockers

### Dependencies
- None (self-contained change to message_service.py)
- Existing Message table schema supports this pattern

### Known Blockers
- None identified

### Risks
- **Performance**: Fan-out creates N Message records instead of 1
  - Mitigation: Most projects have <20 agents, negligible impact
  - Benefit: Simpler queries offset write overhead
- **Backward Compatibility**: Existing "all" messages won't be delivered
  - Mitigation: Add migration to expand existing "all" messages (optional)
  - Alternative: Accept that old broadcasts are stale (simple approach)

---

## Success Criteria

**Definition of Done**:
- ✅ `send_message(to_agents=["all"])` creates individual Message records
- ✅ Each Message has `to_agents=[agent_id]` (single recipient)
- ✅ Sender excluded automatically during fan-out
- ✅ Completed agents excluded automatically during fan-out
- ✅ `receive_messages()` simplified (no broadcast OR clause)
- ✅ Per-recipient acknowledgment works independently
- ✅ All 4 unit tests pass
- ✅ Integration test passes
- ✅ Manual testing verified
- ✅ No regressions in direct messaging
- ✅ Code committed with descriptive message
- ✅ Documentation updated (if needed)

**Code Quality**:
- Logging includes fan-out count: `Expanded broadcast to 5 agents`
- Exception handling for empty recipient list
- No dead code (remove old broadcast matching logic)

---

## Rollback Plan

**If Things Go Wrong**:

1. **Revert commit**: `git revert <commit-hash>`
2. **Restore old logic**:
   - Revert `send_message()` to literal "all" storage
   - Revert `receive_messages()` to complex OR query
3. **Database cleanup** (if partial migration):
   ```sql
   -- Delete fan-out messages created during testing
   DELETE FROM messages
   WHERE created_at > '2026-01-02 00:00:00'
   AND message_type = 'broadcast';
   ```

**Fallback Configuration**: None required (code-only change)

---

## Additional Resources

### Links
- **Industry Pattern**: [Database Design - Fan-out vs Fan-in](https://aws.amazon.com/blogs/database/scaling-push-notifications-for-millions-of-devices-with-amazon-dynamodb/)
- **Related Code**: `src/giljo_mcp/services/message_service.py`
- **Database Schema**: `src/giljo_mcp/models.py` (Message model)
- **WebSocket Events**: Handover 0326 (auto-acknowledge simplification)
- **Message Counter Series**: Handovers 0286-0299 (context for messaging system)

### Similar Implementations
- Twitter DMs: Fan-out at write for broadcasts
- Slack channels: Individual delivery records per user
- Discord notifications: Per-user message queue

### GitHub Issues
- TBD (create issue if needed for tracking)

---

## Progress Updates

### 2026-01-02 - Documentation Manager
**Status:** Ready for Implementation
**Work Done:**
- Researched current broadcast bugs via code analysis
- Documented fan-out pattern with code examples
- Created comprehensive test plan
- Defined success criteria and rollback plan

**Next Steps:**
- Assign to Backend Integration Tester + Database Expert
- Implement Phase 1: Send message fan-out
- Implement Phase 2: Simplify receive logic
- Write and run tests (Phase 3)
- Manual verification via UI and database queries

---

## Notes

**Why Fan-out at Write?**
- Industry standard for broadcast systems at scale
- Simpler read path (99% of operations are reads)
- Better observability (one message = one delivery attempt)
- Natural per-recipient tracking (status, timestamps, retries)

**Alternative Considered**: Fan-out at Read
- Keep "all" in database, expand during receive_messages()
- Rejected: Adds complexity to read path, acknowledgment still problematic

**Migration Strategy** (Optional Phase 4):
- If needed, run one-time script to expand existing "all" messages
- Low priority: existing broadcasts are likely stale
- Recommend: Accept fresh start after deployment

---

**Remember**: Test thoroughly! Broadcast messaging is critical for agent coordination. A good test suite now saves debugging time later.

---

## Phase 4: JSONB Normalization (Added from 0403)

**Added:** 2026-01-02 (consolidated from Handover 0403)
**Additional Effort:** 8-12 hours
**Priority:** HIGH - SaaS scalability

### Problem Statement

`AgentExecution.messages` JSONB field duplicates the `Message` table, causing:
- Data inconsistency (two sources of truth)
- Storage bloat (same data stored twice)
- Complex query logic in frontend
- Dashboard reads from JSONB, not Message table

### Current Usage (22+ locations)

**Backend Write Locations (13 places):**
| File | Lines | Usage |
|------|-------|-------|
| `agent_job_manager.py` | 309, 416, 484, 538, 594, 975, 1100 | Appends messages to JSONB |
| `message_service.py` | 1199, 1242 | Initializes empty messages |
| `job_coordinator.py` | 321 | Sets messages |
| `agent_job_repository.py` | 207 | Sets messages |

**Backend Read Locations (9 places):**
| File | Lines | Usage |
|------|-------|-------|
| `message_service.py` | 1307, 1308, 1311, 1317 | Updates message status in JSONB |
| `orchestrator_succession.py` | 269 | Reads messages |
| `orchestration_service.py` | 1508, 1511 | Reads messages |
| `project_service.py` | 235 | Includes messages in response |
| `table_view.py` | 199, 201, 202 | Counts messages for dashboard |

**Frontend Locations (10+ files):**
- `agentJobsStore.js` - 15+ references for message counters
- `JobsTab.vue` - Message sent/waiting/read counts
- `MessageAuditModal.vue` - Display messages array
- `AgentCard.vue`, `OrchestratorCard.vue` - Pending counts

### Implementation Strategy

**Phase 4a: Stop Writing to JSONB (2-3 hours)**
1. Modify `agent_job_manager.py` - remove all `job.messages = ...` writes
2. Modify `message_service.py` - remove JSONB initialization
3. Messages now ONLY go to Message table (via existing code)
4. Keep JSONB column for backward compatibility (read-only)

**Phase 4b: Read from Message Table (3-4 hours)**
1. Update `table_view.py` to query Message table for counts
2. Update `project_service.py` to include messages from Message table
3. Update `orchestration_service.py` to query Message table
4. Update `orchestrator_succession.py` to query Message table

**Phase 4c: Frontend Alignment (2-3 hours)**
1. API already returns message counts - verify frontend uses them
2. Remove any direct JSONB array access in frontend
3. Update WebSocket handlers if needed

**Phase 4d: Cleanup (1-2 hours)**
1. Mark `AgentExecution.messages` column as deprecated
2. Add migration to drop column (future release)
3. Update tests

### Success Criteria (Phase 4)

- [ ] No code writes to `AgentExecution.messages` JSONB
- [ ] All message counts derived from Message table
- [ ] Dashboard message counters still work
- [ ] WebSocket events include correct counts
- [ ] No data loss during transition
- [ ] Column marked deprecated (not removed yet)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data inconsistency during transition | HIGH | Parallel read from both sources initially |
| Frontend relies on JSONB structure | MEDIUM | API abstracts data source |
| Performance regression | LOW | Message table already indexed |

---

## Updated Estimates

| Phase | Effort | Cumulative |
|-------|--------|------------|
| Phase 1: Send fan-out | 2-3 hours | 2-3 hours |
| Phase 2: Simplify receive | 1-2 hours | 3-5 hours |
| Phase 3: Testing | 1-2 hours | 4-7 hours |
| Phase 4a: Stop JSONB writes | 2-3 hours | 6-10 hours |
| Phase 4b: Read from Message table | 3-4 hours | 9-14 hours |
| Phase 4c: Frontend alignment | 2-3 hours | 11-17 hours |
| Phase 4d: Cleanup | 1-2 hours | 12-19 hours |
| **Total** | **12-19 hours** | |

---

## Supersedes

This handover now supersedes **Handover 0403** (JSONB Normalization - Messages).
0403 content has been merged into Phase 4 above.
