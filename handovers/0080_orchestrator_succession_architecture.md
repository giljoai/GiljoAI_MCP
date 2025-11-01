# Handover 0080: Orchestrator Succession Architecture

**Date**: 2025-10-31
**Status**: Design Complete - Implementation Pending
**Priority**: Medium
**Scope**: Agent Job Management, Orchestrator Lifecycle, Context Window Management

## Executive Summary

Implements automatic orchestrator succession when context windows approach capacity limits. When an orchestrator agent's context usage reaches 90%, it spawns a successor orchestrator, performs a handover summary, and decommissions itself gracefully. This enables unlimited project duration without context window limitations.

## Problem Statement

**Current Limitation**: Orchestrator agents have finite context windows (typically 150K tokens). Long-running projects can exhaust this capacity, causing orchestrator failure and project interruption.

**Business Impact**:
- Projects cannot exceed orchestrator context capacity
- No graceful degradation when limits approached
- Manual intervention required for context overflow
- Loss of project continuity and state

## Solution Architecture

### High-Level Flow

```
[Orchestrator Instance 1]
     ↓ (Context: 135K/150K = 90%)
     ↓ Detects threshold breach
     ↓
[Create Successor via MCP]
     ↓
[Orchestrator Instance 2 Created]
     ↓ (Fresh context: 5K/150K = 3%)
[Handover Summary Sent]
     ↓
[Instance 1 → Complete]
[Instance 2 → Waiting (Manual Launch)]
```

### Detailed Workflow

#### Step 1: Context Threshold Detection

**Orchestrator monitors context usage:**
```python
current_usage = orchestrator.context_used
threshold = orchestrator.context_budget * 0.90  # 90% threshold

if current_usage >= threshold:
    initiate_succession()
```

**Trigger Conditions**:
- Context usage ≥ 90% of budget
- OR manual handover request from user
- OR critical mission phase transition

#### Step 2: Successor Creation

**Orchestrator uses MCP tool:**
```python
from giljo_mcp.tools import create_agent_job

result = create_agent_job(
    agent_type="orchestrator",
    mission=generate_handover_summary(),
    spawned_by=self.job_id,  # Parent linkage
    context_chunks=critical_context_refs,
    project_id=self.project_id
)

successor_id = result['job_id']  # New UUID generated
```

**Database Record Created**:
```sql
INSERT INTO mcp_agent_jobs (
    tenant_key,
    job_id,              -- New UUID: orch-a1b2c3d4-5e6f...
    agent_type,          -- 'orchestrator'
    mission,             -- Handover summary
    status,              -- 'waiting'
    spawned_by,          -- Parent UUID: orch-6adbec5c...
    project_id,          -- Same project
    instance_number,     -- 2 (incremented)
    context_used,        -- 0
    context_budget,      -- 150000
    created_at           -- NOW()
);
```

#### Step 3: Handover Summary Generation

**Critical State Transfer**:
```python
handover_summary = {
    "project_status": "60% complete",
    "active_agents": [
        {"job_id": "...", "type": "frontend-dev", "status": "working"},
        {"job_id": "...", "type": "backend-api", "status": "waiting"}
    ],
    "completed_phases": ["requirements", "architecture", "database-schema"],
    "pending_decisions": [
        "API endpoint naming convention",
        "Authentication method selection"
    ],
    "critical_context_refs": ["chunk-123", "chunk-456"],
    "message_count": 42,
    "unresolved_blockers": [],
    "next_steps": "Implement API endpoints, then frontend integration"
}
```

**Compression Strategy**:
- Extract only actionable state
- Reference context chunks (not full text)
- Summarize completed work (not replay)
- Highlight pending decisions only
- Target: <10K tokens for handover

#### Step 4: MCP Message Sent

**Agent-to-Agent Communication**:
```json
{
    "type": "handover",
    "from": "orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
    "to": "orch-a1b2c3d4-5e6f-7890-1234-567890abcdef",
    "timestamp": "2025-10-31T05:22:00Z",
    "payload": {
        "summary": "...",
        "context_refs": ["chunk-123", "chunk-456"],
        "pending_tasks": [...],
        "agent_status": {...}
    }
}
```

**Stored in Database**:
```sql
UPDATE mcp_agent_jobs
SET messages = messages || '[{handover_message}]'::jsonb
WHERE job_id = 'orch-a1b2c3d4...';
```

#### Step 5: UI Updates (Frontend)

**Jobs Tab Display** (ProjectTabs → JobsTab):

```vue
<!-- TWO Orchestrator Cards Shown -->
<div class="orchestrators-grid">
  <!-- Instance 1: Complete/Handed Over -->
  <AgentCardEnhanced
    :agent="{
      agent_id: 'orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124',
      agent_type: 'orchestrator',
      status: 'complete',
      instance_number: 1,
      handover_to: 'orch-a1b2c3d4...'
    }"
    mode="jobs"
  />

  <!-- Instance 2: Waiting (Highlighted NEW) -->
  <AgentCardEnhanced
    :agent="{
      agent_id: 'orch-a1b2c3d4-5e6f-7890-1234-567890abcdef',
      agent_type: 'orchestrator',
      status: 'waiting',
      instance_number: 2,
      spawned_by: 'orch-6adbec5c...'
    }"
    :show-new-badge="true"
    mode="jobs"
    @launch-agent="handleLaunchSuccessor"
  />
</div>
```

**Visual Indicators**:
- ✨ "NEW" badge on successor card
- 📊 Context usage bars show 97% → 3%
- 🔗 Link between cards showing succession
- ⚠️ "Handed Over" status on Instance 1

#### Step 6: User Launches Successor

**User Action**: Clicks "Launch Agent" on Instance 2 card

**Prompt Generated**:
```bash
# Generated MCP-enabled prompt
export GILJO_MCP_SERVER_URL=http://10.1.0.164:7272
export GILJO_AGENT_JOB_ID=orch-a1b2c3d4-5e6f-7890-1234-567890abcdef
export GILJO_PROJECT_ID=6adbec5c-9e11-46b4-ad8b-060c69a8d124

# Handover Summary:
# Project Status: 60% complete
# Active Agents: frontend-dev (working), backend-api (waiting)
# Pending Decisions: API endpoint naming, Auth method
# Next Steps: Implement API endpoints, then frontend integration

# Start Claude Code with MCP connection:
codex mcp add giljo-orchestrator
```

**User Flow**:
1. User copies prompt from UI
2. Opens terminal
3. Pastes and executes
4. Successor orchestrator starts with handover context
5. Instance 2 status changes to "working"

#### Step 7: Instance 1 Decommissioned

**Database Update**:
```sql
UPDATE mcp_agent_jobs
SET
    status = 'complete',
    completed_at = NOW(),
    handover_to = 'orch-a1b2c3d4-5e6f-7890-1234-567890abcdef',
    handover_summary = '{compressed_state}'::jsonb
WHERE job_id = 'orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124';
```

**Historical Preservation**:
- ALL messages kept in database (JSONB)
- Mission history preserved
- Decisions and context references stored
- Lineage tracked via `spawned_by` chain
- Available for forensic analysis

## Database Schema Changes

### New Fields in `mcp_agent_jobs`

```sql
ALTER TABLE mcp_agent_jobs
ADD COLUMN instance_number INTEGER DEFAULT 1,
ADD COLUMN handover_to VARCHAR(36) NULL,
ADD COLUMN handover_summary JSONB NULL,
ADD COLUMN handover_context_refs TEXT[] NULL,
ADD COLUMN succession_reason VARCHAR(100) NULL;  -- 'context_limit', 'manual', 'phase_transition'

CREATE INDEX idx_agent_jobs_instance ON mcp_agent_jobs(project_id, agent_type, instance_number);
CREATE INDEX idx_agent_jobs_handover ON mcp_agent_jobs(handover_to);
```

### Example Data

```sql
-- Instance 1 (Complete)
job_id: 'orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124'
agent_type: 'orchestrator'
status: 'complete'
instance_number: 1
context_used: 145000
context_budget: 150000
handover_to: 'orch-a1b2c3d4-5e6f-7890-1234-567890abcdef'
succession_reason: 'context_limit'

-- Instance 2 (Active)
job_id: 'orch-a1b2c3d4-5e6f-7890-1234-567890abcdef'
agent_type: 'orchestrator'
status: 'working'
instance_number: 2
spawned_by: 'orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124'
context_used: 5000
context_budget: 150000
```

## Benefits

### Technical Benefits

✅ **Unlimited Project Duration**: Context limits no longer constrain project scope
✅ **Graceful Degradation**: Automatic succession prevents hard failures
✅ **Full Lineage Tracking**: `spawned_by` chain preserves complete history
✅ **State Preservation**: Handover summary ensures continuity
✅ **Multi-Instance Support**: Database handles N successive orchestrators
✅ **Zero Data Loss**: All messages and context preserved in database

### Operational Benefits

✅ **User Control**: Manual launch prevents unexpected spawns
✅ **Transparency**: UI clearly shows succession chain
✅ **Forensic Analysis**: Historical orchestrators available for review
✅ **Cost Optimization**: Fresh context windows reduce token waste
✅ **Flexibility**: Supports manual handover for phase transitions

## Edge Cases and Error Handling

### Multiple Successive Handovers

**Scenario**: Project requires 4 orchestrator instances

```sql
Instance 1 → Instance 2 → Instance 3 → Instance 4
(Complete)  (Complete)  (Working)   (Waiting)
```

**Handling**:
- Database tracks via `instance_number`
- UI shows all instances in timeline view
- Each handover preserves lineage via `spawned_by`

### Concurrent Orchestrators During Transition

**Scenario**: Instance 2 launched before Instance 1 completes

**Handling**:
```sql
-- Both briefly active
Instance 1: status = 'completing'  -- Grace period
Instance 2: status = 'working'     -- Taking over

-- After grace period
Instance 1: status = 'complete'
Instance 2: status = 'working'
```

**Conflict Prevention**:
- Status flags prevent dual active orchestrators
- WebSocket broadcasts coordinate UI updates
- Grace period allows message queue drain

### Failed Succession

**Scenario**: Successor creation fails (network, database error)

**Handling**:
```sql
UPDATE mcp_agent_jobs
SET
    status = 'blocked',
    block_reason = 'Successor creation failed: {error_message}'
WHERE job_id = 'orch-6adbec5c...';
```

**User Notification**:
- Alert shown in UI
- Manual retry option provided
- Original orchestrator remains active (degraded mode)

### Context Overflow Before Succession

**Scenario**: Orchestrator exceeds 100% context during succession

**Handling**:
- Emergency truncation of message history
- Handover summary generated from recent context only
- Warning logged in database
- User notified via UI alert

## Implementation Plan

### Phase 1: Database Schema (Week 1)

- [ ] Add new columns to `mcp_agent_jobs`
- [ ] Create indexes for succession queries
- [ ] Migration script for existing records
- [ ] Backward compatibility verification

### Phase 2: Backend Logic (Week 2)

- [ ] Context monitoring in orchestrator agent code
- [ ] `create_successor_agent()` MCP tool
- [ ] Handover summary generation algorithm
- [ ] State compression for context efficiency
- [ ] Agent-to-agent message system

### Phase 3: UI Updates (Week 3)

- [ ] Multi-instance orchestrator card display
- [ ] Succession timeline visualization
- [ ] "Launch Successor" prompt generation
- [ ] Status badges and visual indicators
- [ ] WebSocket real-time updates

### Phase 4: Testing & Validation (Week 4)

- [ ] Unit tests for succession logic
- [ ] Integration tests for handover flow
- [ ] Load testing with multiple successions
- [ ] Edge case validation
- [ ] User acceptance testing

## Testing Strategy

### Unit Tests

```python
def test_context_threshold_detection():
    orchestrator = create_orchestrator(context_budget=150000)
    orchestrator.context_used = 135000

    assert orchestrator.should_trigger_succession() == True
    assert orchestrator.succession_reason == 'context_limit'

def test_handover_summary_generation():
    summary = orchestrator.generate_handover_summary()

    assert len(summary['critical_context_refs']) > 0
    assert 'next_steps' in summary
    assert summary['token_estimate'] < 10000

def test_successor_creation():
    successor_id = orchestrator.create_successor()

    assert successor_id != orchestrator.job_id
    assert successor.instance_number == orchestrator.instance_number + 1
    assert successor.spawned_by == orchestrator.job_id
```

### Integration Tests

```python
async def test_full_succession_workflow():
    # Setup
    orch1 = await create_orchestrator(project_id="test-project")
    orch1.context_used = 135000  # Trigger threshold

    # Execute succession
    orch2_id = await orch1.initiate_succession()

    # Verify database state
    orch1_record = await db.get_agent_job(orch1.job_id)
    assert orch1_record.status == 'complete'
    assert orch1_record.handover_to == orch2_id

    orch2_record = await db.get_agent_job(orch2_id)
    assert orch2_record.status == 'waiting'
    assert orch2_record.spawned_by == orch1.job_id
    assert orch2_record.instance_number == 2

async def test_message_preservation():
    # Verify all messages from Instance 1 are preserved
    orch1_messages = await db.get_agent_messages(orch1.job_id)
    assert len(orch1_messages) > 0

    # Verify handover message in Instance 2
    orch2_messages = await db.get_agent_messages(orch2_id)
    handover_msg = next(m for m in orch2_messages if m['type'] == 'handover')
    assert handover_msg['from'] == orch1.job_id
```

## Security Considerations

### Multi-Tenant Isolation

✅ **Succession respects tenant boundaries**:
```python
def create_successor(self):
    # Enforce tenant isolation
    successor = create_agent_job(
        tenant_key=self.tenant_key,  # Same tenant ONLY
        ...
    )
```

### Access Control

✅ **Only orchestrator can spawn successors**:
```python
@require_agent_role('orchestrator')
def create_successor_agent(...):
    # Only orchestrator agents can call this
```

### Audit Trail

✅ **Complete succession history**:
```sql
SELECT
    job_id,
    instance_number,
    spawned_by,
    handover_to,
    succession_reason,
    created_at,
    completed_at
FROM mcp_agent_jobs
WHERE project_id = '...'
    AND agent_type = 'orchestrator'
ORDER BY instance_number;
```

## Performance Considerations

### Context Compression

**Target**: Handover summary <10K tokens (vs 145K in original)

**Techniques**:
- Reference context chunks (IDs only)
- Summarize completed work (bullet points)
- Preserve only pending decisions
- Compress message history (key events only)

### Database Query Optimization

```sql
-- Efficient succession query
CREATE INDEX idx_orchestrator_succession
ON mcp_agent_jobs(project_id, agent_type, instance_number)
WHERE agent_type = 'orchestrator';
```

### WebSocket Broadcast Efficiency

```python
# Only broadcast to relevant subscribers
await ws_manager.broadcast_to_project(
    project_id=project_id,
    event_type='orchestrator_succession',
    data={'new_orchestrator_id': successor_id}
)
```

## Future Enhancements

### Automatic Launch

**Vision**: Auto-launch successor without user intervention

**Implementation**: Optional configuration flag
```python
auto_launch_successors: bool = False  # Default: manual
```

**Considerations**:
- Requires secure token management
- Cost implications for auto-spawned agents
- User notification and override controls

### Predictive Succession

**Vision**: Trigger succession before 90% (machine learning)

**Algorithm**:
```python
def predict_succession_timing():
    # Analyze context growth rate
    rate = calculate_context_growth_rate()

    # Predict when 90% will be reached
    tokens_remaining = context_budget - context_used
    estimated_time = tokens_remaining / rate

    # Trigger early if < 30 minutes
    if estimated_time < 1800:  # seconds
        initiate_succession()
```

### Cross-Project Orchestrator Pools

**Vision**: Reuse idle orchestrators across projects

**Architecture**: Orchestrator as a service (OaaS)
```python
orchestrator = orchestrator_pool.acquire(
    project_id=new_project_id,
    reset_context=True
)
```

## Documentation Requirements

### User Documentation

- [ ] Orchestrator succession overview (end-user guide)
- [ ] How to recognize succession events in UI
- [ ] When to manually trigger handover
- [ ] Troubleshooting failed successions

### Developer Documentation

- [ ] Architecture diagrams (sequence, component)
- [ ] API reference for succession tools
- [ ] Database schema documentation
- [ ] Integration examples

### Operational Documentation

- [ ] Monitoring succession health
- [ ] Performance metrics and thresholds
- [ ] Incident response procedures
- [ ] Backup and recovery for failed handovers

## Rollout Strategy

### Phase 1: Beta (Limited Projects)

- Enable for 3-5 pilot projects
- Monitor succession events closely
- Gather user feedback
- Iterate on handover summary quality

### Phase 2: Gradual Rollout

- Enable for all new projects
- Existing projects opt-in via settings
- Performance monitoring dashboard
- A/B testing of handover strategies

### Phase 3: General Availability

- Default behavior for all orchestrators
- Deprecate single-instance limitation
- Update documentation and training materials
- Success metrics tracking

## Success Metrics

### Technical Metrics

- **Succession Success Rate**: >99% (target)
- **Handover Summary Token Size**: <10K tokens average
- **Context Loss**: <1% of critical state
- **Succession Latency**: <5 seconds (creation to waiting)

### Business Metrics

- **Projects >150K tokens**: Previously 0, now unlimited
- **Project Continuity**: 100% (no interruptions)
- **User Satisfaction**: >90% positive feedback
- **Cost Efficiency**: 70% token reduction vs full context replay

## Related Handovers

- **Handover 0017**: Agent Job Repository (foundation)
- **Handover 0019**: Agent Job Management System
- **Handover 0020**: Orchestrator Enhancement (mission planning)
- **Handover 0073**: Static Agent Grid (UI foundation)
- **Handover 0077**: Hybrid Launch/Jobs Architecture

## Conclusion

Orchestrator succession architecture enables unlimited project duration by automatically managing context window limits. The system preserves full lineage, maintains state continuity, and provides transparent user control over succession events. Implementation is phased to minimize risk and maximize user feedback integration.

**Estimated Effort**: 4 weeks (design → GA)
**Risk Level**: Medium (database schema changes, state management complexity)
**User Impact**: High (enables large-scale projects)

---

**Signed Off By**: Architecture Team
**Review Date**: 2025-10-31
**Next Review**: After Phase 1 Beta Testing
