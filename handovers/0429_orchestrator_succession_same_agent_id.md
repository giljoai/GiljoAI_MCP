# Handover: Orchestrator Succession with Same Agent ID

**Date:** 2025-01-21
**From Agent:** Claude Opus 4.5 (Architecture Discussion Session)
**To Agent:** TDD-Implementor or System-Architect
**Priority:** High
**Estimated Complexity:** 8-12 hours
**Status:** Not Started

---

## Task Summary

Implement orchestrator succession that preserves the same `agent_id` across instances, enabling seamless message continuity and agent communication without re-introductions. When an orchestrator runs out of context window, a successor instance spawns with the same identity but fresh context.

**Why it matters:** Agents spawned by orchestrator #1 have its `agent_id` in their prompts. If successor gets a NEW agent_id, post-succession messages go to the wrong recipient. Same agent_id = messages just work.

---

## Context and Background

### The Problem

When orchestrator context window fills up:
1. User clicks "Hand Over" to spawn successor
2. Current implementation creates NEW `agent_id` for successor
3. Existing agents still have OLD `agent_id` in their prompts
4. Post-succession messages sent to OLD agent_id are not received by successor

### Agreed Architecture (From Discussion)

| Decision | Implementation |
|----------|---------------|
| **Same agent_id** | Successor reuses `current_execution.agent_id` |
| **Composite uniqueness** | `(agent_id, instance_number)` instead of `agent_id` alone |
| **Backend-generated summary** | Query agent states, todos, messages from DB |
| **Continuation prompt** | Different from staging prompt (don't re-stage) |
| **Warning dialog** | "Ensure agents have completed before proceeding" |
| **No new MCP tool** | Summary embedded in successor's launch prompt |

### Data Model (Dual-Model Architecture)

```
AgentJob = Work Order (persists across succession)
AgentExecution = Executor Instance (one per instance)

Current:
  Instance 1: agent_id=AAA, job_id=JJJ, instance_number=1
  Instance 2: agent_id=BBB, job_id=JJJ, instance_number=2  <- NEW agent_id (WRONG)

Target:
  Instance 1: agent_id=AAA, job_id=JJJ, instance_number=1
  Instance 2: agent_id=AAA, job_id=JJJ, instance_number=2  <- SAME agent_id (CORRECT)
```

---

## Technical Details

### Files to Modify

**1. Database Constraint Change**
- File: `src/giljo_mcp/models/agent_identity.py`
- Change: Unique constraint from `agent_id` alone to composite `(agent_id, instance_number)`
- Impact: Allows multiple rows with same agent_id if instance_number differs

**2. Succession Logic**
- File: `src/giljo_mcp/orchestrator_succession.py`
- Method: `create_successor()` (lines 160-234)
- Change: Line 205 from `agent_id=str(uuid4())` to `agent_id=current_execution.agent_id`

**3. Query Audit - Add Instance Filter**
- Files that query by `agent_id` expecting one result need `ORDER BY instance_number DESC LIMIT 1`
- Key files to audit:
  - `src/giljo_mcp/services/orchestration_service.py` (line 1958)
  - `api/endpoints/agent_jobs/succession.py` (lines 108-113, 124-138)
  - Any code doing `WHERE agent_id = X` on AgentExecution

**4. Handover Summary Enhancement**
- File: `src/giljo_mcp/orchestrator_succession.py`
- Method: `generate_handover_summary()` (lines 236-351)
- Add: Query current agent execution statuses and todo lists (not just messages)

**5. Continuation Prompt**
- File: `src/giljo_mcp/thin_prompt_generator.py`
- Change: Detect `instance_number > 1` and generate continuation prompt instead of staging prompt
- Content difference:
  - Staging: "Call get_orchestrator_instructions() to begin staging workflow"
  - Continuation: "You are continuing work. Check receive_messages(), get_workflow_status(). Do NOT re-stage."

**6. UI Warning Dialog**
- File: `frontend/src/components/projects/LaunchSuccessorDialog.vue`
- Add: Warning alert at top of dialog: "Ensure all agents have completed their work before proceeding"

### Database Changes

**Current unique constraint:**
```python
class AgentExecution(Base):
    agent_id = Column(String, primary_key=True)  # Unique by itself
```

**Target composite constraint:**
```python
class AgentExecution(Base):
    agent_id = Column(String, nullable=False)
    instance_number = Column(Integer, default=1)

    __table_args__ = (
        UniqueConstraint('agent_id', 'instance_number', name='uq_agent_instance'),
        # Primary key might need to change - investigate
    )
```

### Key Code Sections

**orchestrator_succession.py line 205 (current):**
```python
successor_execution = AgentExecution(
    agent_id=str(uuid4()),  # NEW agent_id - WRONG
    job_id=current_execution.job_id,
    ...
)
```

**orchestrator_succession.py line 205 (target):**
```python
successor_execution = AgentExecution(
    agent_id=current_execution.agent_id,  # SAME agent_id - CORRECT
    job_id=current_execution.job_id,
    instance_number=current_execution.instance_number + 1,
    ...
)
```

**Query pattern to find (needs audit):**
```python
# BEFORE (assumes agent_id is unique):
stmt = select(AgentExecution).where(AgentExecution.agent_id == executor_id)

# AFTER (get latest instance):
stmt = select(AgentExecution).where(
    AgentExecution.agent_id == executor_id
).order_by(AgentExecution.instance_number.desc()).limit(1)
```

---

## Implementation Plan

### Phase 1: Database Schema (TDD)

1. Write failing test for composite uniqueness
2. Update `AgentExecution` model with composite constraint
3. Run `python install.py` to apply migration
4. Verify constraint works (same agent_id + different instance_number = OK)

### Phase 2: Succession Logic (TDD)

1. Write failing test: `test_create_successor_preserves_agent_id()`
2. Modify `create_successor()` to reuse agent_id
3. Verify test passes
4. Write test for instance_number increment

### Phase 3: Query Audit (TDD)

1. Search codebase: `grep -r "AgentExecution.agent_id ==" src/ api/`
2. For each query expecting single result, add instance filter
3. Write tests verifying correct instance is returned

### Phase 4: Continuation Prompt (TDD)

1. Write failing test: `test_thin_prompt_detects_continuation_instance()`
2. Modify `ThinClientPromptGenerator.generate()` to detect `instance_number > 1`
3. Create continuation prompt template (different from staging)
4. Verify test passes

### Phase 5: Handover Summary Enhancement (TDD)

1. Write failing test: `test_handover_summary_includes_agent_states()`
2. Enhance `generate_handover_summary()` to query:
   - AgentExecution statuses for all project agents
   - Todo lists (progress.todo_items) for each agent
3. Verify structured state in summary

### Phase 6: UI Warning (Frontend)

1. Add `v-alert` to LaunchSuccessorDialog.vue
2. Warning text: "Ensure all agents have completed their work before spawning successor"
3. Add unit test for warning visibility

**Recommended Sub-Agent:** tdd-implementor (for phases 1-5), ux-designer (for phase 6)

---

## Testing Requirements

### Unit Tests

```python
# tests/test_orchestrator_succession.py

@pytest.mark.asyncio
async def test_create_successor_preserves_agent_id(db_session, test_tenant):
    """Successor should have SAME agent_id as predecessor"""
    manager = OrchestratorSuccessionManager(db_session, test_tenant)

    # Create initial execution
    current = await create_test_execution(agent_id="orch-123", instance_number=1)

    # Create successor
    successor = await manager.create_successor(current, reason="manual")

    # CRITICAL: Same agent_id
    assert successor.agent_id == current.agent_id == "orch-123"
    # Different instance
    assert successor.instance_number == 2
    assert current.instance_number == 1


@pytest.mark.asyncio
async def test_composite_uniqueness_allows_same_agent_id(db_session):
    """Two executions with same agent_id but different instance_number should be allowed"""
    exec1 = AgentExecution(agent_id="orch-123", instance_number=1, ...)
    exec2 = AgentExecution(agent_id="orch-123", instance_number=2, ...)

    db_session.add_all([exec1, exec2])
    await db_session.commit()  # Should NOT raise


@pytest.mark.asyncio
async def test_query_returns_latest_instance(db_session, test_tenant):
    """Query by agent_id should return highest instance_number"""
    # Create multiple instances
    await create_test_execution(agent_id="orch-123", instance_number=1)
    await create_test_execution(agent_id="orch-123", instance_number=2)

    # Query should return instance 2
    result = await get_current_execution("orch-123", test_tenant)
    assert result.instance_number == 2


def test_continuation_prompt_differs_from_staging():
    """Instance > 1 should get continuation prompt, not staging prompt"""
    generator = ThinClientPromptGenerator(db, tenant_key)

    staging_prompt = await generator.generate(project_id, instance_number=1)
    continuation_prompt = await generator.generate(project_id, instance_number=2)

    assert "staging" in staging_prompt["prompt"].lower() or "get_orchestrator_instructions" in staging_prompt["prompt"]
    assert "continuation" in continuation_prompt["prompt"].lower() or "do not re-stage" in continuation_prompt["prompt"].lower()
```

### Integration Tests

```python
# tests/integration/test_succession_flow.py

@pytest.mark.asyncio
async def test_full_succession_flow_preserves_messaging(db_session, test_tenant):
    """Messages to agent_id should be readable by successor"""
    # Setup: Create orchestrator, spawn agent
    orch1 = await create_orchestrator(agent_id="orch-123", instance_number=1)
    agent = await spawn_agent(parent_id="orch-123")

    # Agent sends message to orchestrator
    await send_message(from_agent=agent.agent_id, to_agents=["orch-123"], content="Status update")

    # Trigger succession
    orch2 = await trigger_succession(orch1)
    assert orch2.agent_id == "orch-123"  # Same ID
    assert orch2.instance_number == 2

    # Successor should receive the message
    messages = await receive_messages(agent_id="orch-123", tenant_key=test_tenant)
    assert len(messages) == 1
    assert messages[0]["content"] == "Status update"
```

### Manual Testing

1. Create project, launch orchestrator (instance #1)
2. Spawn some agents via orchestrator
3. Click "Hand Over" button
4. Verify warning dialog appears
5. Trigger succession
6. Verify successor in Jobs tab has SAME agent_id as predecessor
7. Verify successor's launch prompt says "continuation" not "staging"
8. Launch successor (instance #2)
9. Verify successor can read messages sent to the agent_id

---

## Dependencies and Blockers

**Dependencies:**
- None - this is self-contained

**Known Blockers:**
- Primary key on `agent_id` might need to change to composite or separate column
- Query audit scope unknown until grep search completed

**Questions Needing Answers:**
- Is `agent_id` currently the primary key, or is there a separate `id` column?
- Are there any foreign key constraints referencing `agent_id` that would break?

---

## Success Criteria

**Definition of Done:**

- [ ] `agent_id` persists across succession instances
- [ ] Composite uniqueness on `(agent_id, instance_number)` works
- [ ] All queries return correct (latest) instance
- [ ] Continuation prompt generated for instance > 1
- [ ] Handover summary includes agent states and todos
- [ ] UI warning dialog present
- [ ] All tests pass (unit, integration)
- [ ] Manual testing verified
- [ ] No regressions in existing functionality

---

## Rollback Plan

**If Things Go Wrong:**

1. Revert model changes: `git checkout -- src/giljo_mcp/models/agent_identity.py`
2. Revert succession changes: `git checkout -- src/giljo_mcp/orchestrator_succession.py`
3. Re-run `python install.py` to restore schema
4. Succession will create new agent_ids (current behavior)

**Database rollback:**
- If constraint change causes issues, drop and recreate constraint
- Data is not destroyed, only constraint logic changes

---

## Additional Resources

**Related Files:**
- `src/giljo_mcp/orchestrator_succession.py` - Core succession logic
- `src/giljo_mcp/thin_prompt_generator.py` - Launch prompt generation
- `src/giljo_mcp/services/orchestration_service.py` - Service layer
- `api/endpoints/agent_jobs/succession.py` - API endpoints
- `frontend/src/components/projects/LaunchSuccessorDialog.vue` - UI component

**Related Handovers:**
- 0080 - Original orchestrator succession architecture
- 0366b - Dual-model architecture (AgentJob + AgentExecution)
- 0509 - Succession UI components

**Documentation:**
- `docs/ORCHESTRATOR.md` - Orchestrator architecture
- `docs/SERVICES.md` - Service layer patterns

---

## Continuation Prompt Template

For reference, the successor's launch prompt should include:

```markdown
I am Orchestrator #{instance_number} for GiljoAI Project "{project_name}" (CONTINUATION).

My predecessor (instance #{instance_number - 1}) ran out of context window.
I am taking over active work with the SAME identity.

## IDENTITY
- agent_id: {agent_id} (SAME as predecessor)
- job_id: {job_id}
- project_id: {project_id}
- tenant_key: {tenant_key}

## FIRST ACTIONS (DO NOT RE-STAGE)
1. Call receive_messages(agent_id="{agent_id}", tenant_key="{tenant_key}")
   - Read any messages from agents and predecessor's handover notes
2. Call get_workflow_status(project_id="{project_id}", tenant_key="{tenant_key}")
   - See which agents are active, completed, or pending
3. Check in with ACTIVE agents before spawning new ones

## RULES
- Do NOT call get_orchestrator_instructions() staging workflow
- Do NOT re-write the project mission
- Do NOT re-introduce yourself to agents (they already know you)
- Check existing agent progress before spawning new agents

## HANDOVER CONTEXT FROM BACKEND
{backend_generated_summary}

## AVAILABLE TOOLS
- receive_messages() - Check what agents have reported
- send_message() - Communicate with agents
- get_workflow_status() - See overall progress
- spawn_agent_job() - Create new agents if needed
- complete_job() - Mark yourself complete when project done
```

---

**Remember:** A good handover enables the next agent to succeed. This architecture ensures orchestrator succession is seamless for both the user and the spawned agents.
