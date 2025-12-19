# Handover: Agent Workflow & UI Fixes

**Date:** 2025-12-18
**From Agent:** Orchestrator (Plan Mode)
**To Agent:** TDD-Implementor, Documentation-Manager
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation

---

## Task Summary

Fix 6 related issues affecting agent behavior, messaging, and UI visibility:
1. Remove outdated "See Handover 0106b" reference from prompts
2. Verify/ensure project closeout doesn't spawn orchestrators
3. Fix broadcast messages delivering to sender (self-inclusion bug)
4. Add mandatory agent workflow instructions (TodoWrite/planning/progress)
5. Fix message read acknowledgement instructions
6. Move "Close Out Project" button to persistent header location

---

## Context and Background

**Research Completed:** Deep-researcher agents analyzed all 6 issues with findings:

1. **0106b Reference:** Hardcoded in `thin_prompt_generator.py:1266` - outdated handover reference
2. **Closeout Spawn:** Verified `project_closeout.py` does NOT spawn orchestrators - succession is separate
3. **Broadcast Bug:** `receive_messages()` query at line 550-564 doesn't filter sender for broadcasts
4. **Agent Workflow:** TodoWrite instruction exists in protocol but buried; not in spawn prompt
5. **Message Ack:** Auto-acknowledgement works when `receive_messages()` called; agents may use wrong tool
6. **Close Out Button:** Only in `JobsTab.vue` - disappears when switching tabs (by design but poor UX)

---

## Technical Details

### Issue 1: Remove 0106b Reference

**Files to Modify:**
- `src/giljo_mcp/thin_prompt_generator.py` (line 1266) - DELETE the reference line
- `tests/thin_prompt/test_execution_prompt_simple.py` (line 248) - REMOVE assertion

**Code to Remove:**
```python
# Line 1266 in thin_prompt_generator.py
"Reference: See Handover 0106b for full sub-agent spawn instructions",
```

### Issue 2: Closeout Verification

**Files to Verify:**
- `src/giljo_mcp/tools/project_closeout.py` - Already confirmed clean
- `api/endpoints/projects/completion.py` - Verify no spawn logic

### Issue 3: Broadcast Self-Exclusion Bug

**File:** `src/giljo_mcp/services/message_service.py` (lines 550-564)

**Current Query (buggy):**
```python
or_(
    func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
    func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB))
)
```

**Fixed Query:**
```python
or_(
    func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
    and_(
        func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB)),
        func.coalesce(
            Message.meta_data.op('->')('_from_agent').astext,
            func.cast('', String)
        ) != job.agent_type
    )
)
```

### Issue 4: Agent Workflow Instructions (3 Layers)

**Layer 1 - Spawn Prompt:** `src/giljo_mcp/tools/orchestration.py` (lines 815-850)
Add to spawn prompt section:
```
WORKFLOW REQUIREMENTS (MANDATORY):
1. IMMEDIATELY create TodoWrite task list before any implementation
2. Mark tasks in_progress when starting, completed when finished
3. Report progress: "Completed step X of Y: [description]"
4. NEVER skip planning - poor planning = poor execution
```

**Layer 2 - Agent Protocol:** `src/giljo_mcp/services/orchestration_service.py` (lines 75-82)
Strengthen existing instruction to MANDATORY

**Layer 3 - Agent Templates:** `.claude/agents/*.md` (12 files)
Add workflow protocol section to each template

### Issue 5: Message Acknowledgement Instructions

**File:** `src/giljo_mcp/services/orchestration_service.py`

Add to protocol:
```
MESSAGE HANDLING:
- ALWAYS use receive_messages() to check messages (NOT list_messages)
- receive_messages() auto-acknowledges and removes from queue
- list_messages() is read-only - messages stay pending
```

### Issue 6: Close Out Button to Header

**Files to Modify:**
- `frontend/src/components/projects/ProjectTabs.vue` - ADD button to header section
- `frontend/src/components/projects/JobsTab.vue` - REMOVE button (or keep both)

**Visibility Logic (preserve):**
```javascript
const showCloseoutButton = computed(() => {
  if (!allAgentsComplete) return false
  const orchestrator = agents?.find((a) => a.agent_type === 'orchestrator')
  return Boolean(orchestrator && orchestrator.status === 'complete')
})
```

---

## Implementation Plan (TDD)

### Phase 1: Backend Fixes (Issues 1, 2, 3, 5)

**Step 1.1: Write Tests First**
```
tests/unit/test_broadcast_self_exclusion.py
tests/unit/test_0106b_reference_removed.py
```

**Step 1.2: Implement Fixes**
- Remove 0106b reference
- Fix broadcast query
- Add protocol instructions

**Step 1.3: Run Tests**
```bash
pytest tests/unit/test_broadcast_self_exclusion.py -v
pytest tests/thin_prompt/ -v
```

### Phase 2: Agent Instructions (Issue 4)

**Step 2.1: Write Template Tests**
Verify TodoWrite instructions present in:
- Spawn prompt output
- Agent protocol output
- Agent template files

**Step 2.2: Update 3 Layers**
- orchestration.py spawn prompt
- orchestration_service.py protocol
- .claude/agents/*.md templates

### Phase 3: Frontend (Issue 6)

**Step 3.1: Move Button**
- Add to ProjectTabs.vue header
- Test visibility conditions
- Remove from JobsTab.vue (or keep dual)

**Step 3.2: Manual Testing**
- Navigate between tabs
- Verify button persists
- Test closeout modal opens

---

## Testing Requirements

### Unit Tests
- `test_broadcast_excludes_sender` - Verify sender not in broadcast recipients
- `test_0106b_reference_removed` - Verify reference not in generated prompts
- `test_workflow_instructions_in_spawn_prompt` - Verify TodoWrite instruction present

### Integration Tests
- Agent receives broadcast from other agent - should work
- Agent sends broadcast - should NOT receive own message
- Close out button visible on both tabs when conditions met

### Manual Testing
1. Spawn agent, verify TodoWrite in prompt
2. Send broadcast, verify sender excluded
3. Navigate tabs, verify Close Out button visible

---

## Success Criteria

- [ ] "See Handover 0106b" reference removed from all prompts
- [ ] Broadcast messages exclude sender in `receive_messages()`
- [ ] Agent spawn prompts include MANDATORY TodoWrite instructions
- [ ] Agent protocol includes message tool clarification
- [ ] Close Out button visible in header bar (both tabs)
- [ ] All tests passing
- [ ] No regressions in existing functionality

---

## Recommended Sub-Agents

| Agent | Responsibility |
|-------|---------------|
| **tdd-implementor** | Issues 1, 3 (backend with tests) |
| **system-architect** | Issue 4 (3-layer instruction design) |
| **ux-designer** | Issue 6 (button placement) |
| **documentation-manager** | Update templates, handover completion |

---

## Progress Updates

### 2025-12-18 - Orchestrator (Planning)
**Status:** Ready for Implementation
**Work Done:**
- Research completed (6 deep-researcher agents)
- Plan documented in plan file
- User clarifications obtained
- Handover document created

### 2025-12-18 - Implementation (TDD)
**Status:** COMPLETED
**Work Done:**

**Issue 1 - 0106b Reference:** ✅
- Removed hardcoded reference from `thin_prompt_generator.py`
- Updated test to verify reference NOT present
- Files: `thin_prompt_generator.py`, `test_execution_prompt_simple.py`

**Issue 2 - Closeout Verification:** ✅
- Verified `project_closeout.py` has no orchestrator spawn logic
- Succession is correctly separate (90% context threshold trigger)

**Issue 3 - Broadcast Self-Exclusion:** ✅
- Fixed query in `message_service.py` lines 550-570
- Added filter: `meta_data['_from_agent'] != job.agent_type`
- Comment references "Issue 0361-3"

**Issue 4 - 3-Layer Workflow Instructions:** ✅
- Layer 1: Updated spawn prompt in `orchestration.py` (2 locations)
- Layer 2: Updated protocol in `orchestration_service.py`
- Layer 3: Updated all 12 agent templates in `.claude/agents/`
- 3 tests created and passing: `test_workflow_instructions_0361.py`

**Issue 5 - Message Acknowledgement Instructions:** ✅
- Added MESSAGE HANDLING section to protocol
- Clarifies `receive_messages()` vs `list_messages()`
- Comment references "Issue 0361-5"

**Issue 6 - Close Out Button:** ✅
- Moved button to `ProjectTabs.vue` header
- Removed from `JobsTab.vue`
- Button now visible on both Launch and Jobs tabs
- Frontend builds successfully

**Tests:** All 3 workflow instruction tests passing
**Build:** Frontend builds with no errors

---

## Rollback Plan

**If Issues Occur:**
1. Git revert specific commits
2. Restore original message_service.py query
3. Restore original thin_prompt_generator.py
4. Restore original Vue components

---

## Additional Resources

- Plan file: `C:\Users\giljo\.claude\plans\quirky-brewing-noodle.md`
- Research findings from deep-researcher agents (session context)
- CLAUDE.md: Agent routing rules and custom agents
