# Agent Messaging Protocol Implementation (Handover 0118)

**Document Type:** AI-Readable Technical Specification
**Target Audience:** Agentic Coding Tools (Claude Code, Codex, Gemini CLI)
**Version:** 1.0.0
**Date:** 2025-11-09
**Status:** Implementation Complete

---

## Implementation Summary

**Problem Solved:** Zero inter-agent messaging during first execution test (EVALUATION_FIRST_TEST.md). System relied on luck-based file coordination instead of explicit messaging protocol.

**Solution Implemented:** Comprehensive messaging protocol embedded in all agent templates with automatic dependency coordination code injection.

**Impact:** Enables complex workflows, multi-terminal mode, user mid-execution interaction, blocker handling, and explicit dependency coordination.

---

## Architecture Overview

### Three-Layer Implementation

**Layer 1: Template-Embedded Protocol (template_seeder.py)**
- All agent templates now include messaging protocol section
- Orchestrator gets enhanced protocol with team coordination
- Protocol instructions embedded in `system_instructions` field (non-editable)

**Layer 2: Dependency Auto-Detection (mission_planner.py)**
- Mission content scanned for dependency keywords
- Dependencies automatically detected: "wait for", "after X completes", "depends on"
- Coordination code auto-injected into missions with dependencies

**Layer 3: Message Hub Infrastructure (Existing)**
- MCP tools: `send_message()`, `receive_messages()`
- Database table: `agent_communication_queue` (JSONB storage)
- WebSocket events: `message:new`, `message:broadcast`

---

## Files Modified

### F:\GiljoAI_MCP\src\giljo_mcp\template_seeder.py

**Changes:**

1. **Added function `_get_agent_messaging_protocol_section()` (lines 1044-1248)**
   - Purpose: Generate standard messaging protocol for all agents
   - Checkpoints: Before starting, during work (every 5-10 actions), if blocked, when complete
   - Message types: DIRECTIVE, BLOCKER, QUESTION, PROGRESS, COMPLETE, ACKNOWLEDGMENT, STATUS, DEPENDENCY_MET, USER, ESCALATION
   - User message handling: 4-step protocol (acknowledge, assess, execute, report)

2. **Added function `_get_orchestrator_messaging_protocol_section()` (lines 1251-1479)**
   - Purpose: Generate orchestrator-specific messaging protocol
   - Message type handling matrix with priorities and response times
   - Team assembly (welcome message after spawning)
   - Coordination loop (check messages every 3-5 actions)
   - Status broadcasts (every 10-15 actions)
   - Escalation handling (blockers >5 minutes)

3. **Updated `seed_tenant_templates()` function (lines 108-136)**
   - Added messaging protocol sections to system_instructions
   - Orchestrator receives `orchestrator_messaging_section`
   - All other agents receive `agent_messaging_section`
   - Build order: MCP + Context Request + Check-In + Messaging Protocol

**Code Structure:**

```python
# Get messaging sections
agent_messaging_section = _get_agent_messaging_protocol_section()
orchestrator_messaging_section = _get_orchestrator_messaging_protocol_section()

# Build system_instructions with messaging
if template_def["role"] == "orchestrator":
    system_instructions = f"{mcp_section}\n\n{context_request_section}\n\n{check_in_section}\n\n{orchestrator_messaging_section}"
else:
    system_instructions = f"{mcp_section}\n\n{context_request_section}\n\n{check_in_section}\n\n{agent_messaging_section}"
```

**Integration Points:**
- `system_instructions` field (protected, non-editable by users)
- All 6 agent roles: implementer, tester, analyzer, reviewer, documenter, orchestrator
- Backward compatible: legacy `template_content` field still populated

---

### F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py

**Changes:**

1. **Added function `_detect_agent_dependencies()` (lines 1118-1174)**
   - Purpose: Detect dependencies from mission content text
   - Patterns: "wait for X", "after X completes", "depends on X", "requires X to finish", "when X is done", "once X finishes"
   - Case-insensitive fuzzy matching against agent role names
   - Returns: List of agent roles this agent depends on

2. **Added function `_add_dependency_coordination_code()` (lines 1176-1335)**
   - Purpose: Inject dependency waiting logic into mission content
   - Generates Python code block with:
     - Message checking loop (check every 30 seconds, max 10 attempts = 5 minutes)
     - COMPLETE message detection from dependencies
     - DEPENDENCY_MET message detection from orchestrator
     - Status updates to orchestrator while waiting
     - Timeout escalation (BLOCKER message if 5 minutes elapsed)
   - Insertion logic: Inserts after first header in mission content
   - Only executes if dependencies detected (non-empty list)

3. **Updated `generate_missions()` function (lines 1452-1489)**
   - Added second pass after mission generation
   - For each agent mission:
     - Detect dependencies using `_detect_agent_dependencies()`
     - If dependencies found, inject coordination code using `_add_dependency_coordination_code()`
     - Update Mission object with enhanced content and detected dependencies
     - Recalculate token count for enhanced mission
   - Logging: Info-level log for each enhanced mission

**Code Structure:**

```python
# Generate all missions (first pass)
for agent_config in selected_agents:
    mission = await self._generate_agent_mission(...)
    missions[agent_config.role] = mission

# Detect dependencies and inject coordination (second pass)
all_agent_roles = [agent.role for agent in selected_agents]

for agent_config in selected_agents:
    mission = missions[agent_config.role]
    detected_deps = self._detect_agent_dependencies(mission.content, agent_config.role, all_agent_roles)

    if detected_deps:
        enhanced_content = self._add_dependency_coordination_code(mission.content, agent_config.role, detected_deps)
        missions[agent_config.role] = Mission(..., content=enhanced_content, dependencies=detected_deps)
```

**Integration Points:**
- `Mission.dependencies` field (was always `None`, now populated)
- Orchestrator will use `dependencies` field to notify dependent agents
- Token count recalculated for missions with injected coordination code

---

## Message Type Reference (AI Agents)

### Standard Message Types

```python
MESSAGE_TYPES = {
    "DIRECTIVE": {
        "from": "orchestrator",
        "to": "agent(s)",
        "priority": "HIGH",
        "action": "Follow immediately",
        "example": "Team assembled. Check messages before starting work."
    },
    "BLOCKER": {
        "from": "agent",
        "to": "orchestrator",
        "priority": "URGENT",
        "action": "Provide guidance or reassign",
        "example": "BLOCKED: Tests failing with import error. Need guidance."
    },
    "QUESTION": {
        "from": "agent",
        "to": "orchestrator",
        "priority": "MEDIUM",
        "action": "Answer from mission context",
        "example": "Need clarification on database schema for user table."
    },
    "PROGRESS": {
        "from": "agent",
        "to": "orchestrator",
        "priority": "LOW",
        "action": "Acknowledge, update tracking",
        "example": "Milestone complete: Folder structure created."
    },
    "COMPLETE": {
        "from": "agent",
        "to": "all",
        "priority": "HIGH",
        "action": "Verify, notify dependents",
        "example": "Work complete. Deliverables: [list]. Ready for next phase."
    },
    "ACKNOWLEDGMENT": {
        "from": "any",
        "to": "any",
        "priority": "LOW",
        "action": "Confirm receipt",
        "example": "Received your message. Reviewing now."
    },
    "STATUS": {
        "from": "agent/orchestrator",
        "to": "orchestrator/all",
        "priority": "LOW",
        "action": "Update status tracking",
        "example": "Waiting for dependencies: implementer. Check 3/10."
    },
    "DEPENDENCY_MET": {
        "from": "orchestrator",
        "to": "agent",
        "priority": "HIGH",
        "action": "Proceed with work",
        "example": "Implementer completed. You may now begin analysis."
    },
    "DEVELOPER_MESSAGE": {
        "from": "developer",
        "to": "agent/orchestrator",
        "priority": "URGENT",
        "action": "Acknowledge, adjust work",
        "example": "Add security section to all documentation files.",
        "detection": "msg.get('from') == 'developer'"
    },
    "ESCALATION": {
        "from": "orchestrator",
        "to": "USER",
        "priority": "URGENT",
        "action": "User intervention required",
        "example": "ATTENTION: Agent blocked >5 min. Please advise."
    }
}
```

---

## Messaging Checkpoints (AI Agents)

### For All Agents

**Checkpoint 1: Before Starting Work**
```python
# Check for orchestrator welcome message
messages = receive_messages(agent_id="<AGENT_ID>", tenant_key="<TENANT_KEY>")
for msg in messages:
    if msg.from_agent == "orchestrator" and msg.message_type == "DIRECTIVE":
        # Acknowledge welcome
        send_message(from_agent="<AGENT_TYPE>", to_agent="orchestrator",
                     message_type="ACKNOWLEDGMENT", content="Welcome received. Beginning work.",
                     tenant_key="<TENANT_KEY>")
```

**Checkpoint 2: During Work (Every 5-10 Actions)**
```python
# Check for new messages
messages = receive_messages(agent_id="<AGENT_ID>", tenant_key="<TENANT_KEY>")
for msg in messages:
    if msg.message_type == "DIRECTIVE":
        # Follow new instructions
    elif msg.get("from") == "developer":
        # Developer/user message - acknowledge and adjust work
    elif msg.message_type == "QUESTION":
        # Respond to question
```

**Checkpoint 3: If Blocked**
```python
# Send blocker message immediately
send_message(from_agent="<AGENT_TYPE>", to_agent="orchestrator",
             message_type="BLOCKER",
             content="BLOCKED: [issue]. Need guidance on [question].",
             tenant_key="<TENANT_KEY>")
# WAIT for orchestrator response (check messages every 30s)
```

**Checkpoint 4: When Complete**
```python
# Broadcast completion to all
send_message(from_agent="<AGENT_TYPE>", to_agent="all",
             message_type="COMPLETE",
             content="Work complete. Deliverables: [summary]. Files: [list].",
             tenant_key="<TENANT_KEY>")
```

### For Orchestrator

**Phase 1: Team Assembly (After Spawning)**
```python
# Send welcome message
send_message(from_agent="orchestrator", to_agent="all",
             message_type="DIRECTIVE",
             content="Team assembled. Check messages before starting. Report progress after milestones. Flag blockers immediately.",
             tenant_key="<TENANT_KEY>")
```

**Phase 2: Coordination Loop (Every 3-5 Actions)**
```python
# Check for messages
messages = receive_messages(agent_id="<ORCHESTRATOR_ID>", tenant_key="<TENANT_KEY>")

# Process by priority
for msg in messages:
    if msg.message_type == "BLOCKER":  # Priority 1
        # Respond immediately with guidance
    elif msg.from_agent == "USER":  # Priority 1
        # Acknowledge and forward to agents
    elif msg.message_type == "COMPLETE":  # Priority 2
        # Verify, notify dependent agents
    elif msg.message_type == "QUESTION":  # Priority 3
        # Answer from mission context
    elif msg.message_type == "PROGRESS":  # Priority 4
        # Acknowledge and track
```

**Phase 3: Dependency Notification**
```python
# When agent completes
if msg.message_type == "COMPLETE":
    # Notify dependent agents
    dependent_agents = get_dependent_agents(msg.from_agent)
    for dependent in dependent_agents:
        send_message(from_agent="orchestrator", to_agent=dependent,
                     message_type="DEPENDENCY_MET",
                     content=f"{msg.from_agent} completed. You may now begin.",
                     tenant_key="<TENANT_KEY>")
```

---

## Dependency Coordination Protocol (AI Agents)

### Auto-Generated Code Structure

When mission content contains: "Wait for implementer and documenter before analyzing"

**Detected Dependencies:** `["implementer", "documenter"]`

**Injected Code:**
```python
# Dependency coordination for analyzer
dependencies_met = False
max_checks = 10  # 5 minutes total (30 sec × 10)
check_count = 0
required_deps = {"implementer", "documenter"}
completed_deps = set()

while not dependencies_met and check_count < max_checks:
    # Check for messages
    messages = receive_messages(agent_id="<AGENT_ID>", tenant_key="<TENANT_KEY>")

    for msg in messages:
        # Check for COMPLETE from dependencies
        if msg.message_type == "COMPLETE" and msg.from_agent in required_deps:
            completed_deps.add(msg.from_agent)
            logger.info(f"Dependency met: {msg.from_agent} completed")

        # Check for DEPENDENCY_MET from orchestrator
        elif msg.message_type == "DEPENDENCY_MET" and msg.to_agent == "<AGENT_TYPE>":
            dependencies_met = True
            logger.info("Orchestrator confirmed all dependencies met")
            break

    # Check if all satisfied
    if required_deps.issubset(completed_deps):
        dependencies_met = True
        break

    # Still waiting
    if not dependencies_met:
        check_count += 1
        still_waiting = required_deps - completed_deps
        send_message(from_agent="<AGENT_TYPE>", to_agent="orchestrator",
                     message_type="STATUS",
                     content=f"Waiting for: {', '.join(still_waiting)}. Check {check_count}/10.",
                     tenant_key="<TENANT_KEY>")
        import time
        time.sleep(30)

# After loop
if not dependencies_met:
    # Timeout - escalate
    send_message(from_agent="<AGENT_TYPE>", to_agent="orchestrator",
                 message_type="BLOCKER",
                 content=f"TIMEOUT: Dependencies not met after 5 min. Still waiting for: {', '.join(required_deps - completed_deps)}",
                 tenant_key="<TENANT_KEY>")
else:
    # Dependencies met - proceed
    send_message(from_agent="<AGENT_TYPE>", to_agent="orchestrator",
                 message_type="ACKNOWLEDGMENT",
                 content=f"All dependencies met. Beginning work.",
                 tenant_key="<TENANT_KEY>")
```

---

## Database Schema (No Changes)

**AgentTemplate Model:**
- `system_instructions` (Text) - Contains messaging protocol (protected)
- `user_instructions` (Text) - Contains role-specific guidance (editable)
- `template_content` (Text) - Legacy field (backward compatibility)

**Mission Model:**
- `dependencies` (list[str]) - Now populated with detected dependencies (was always `None`)

**agent_communication_queue Table:**
- Existing table (no schema changes required)
- JSONB message storage with tenant isolation

---

## Backward Compatibility

**Simple Workflows:**
- No dependencies detected → No coordination code injected
- Messaging protocol present but optional → Agents can ignore if no dependencies
- Existing missions without messaging still work (graceful degradation)

**Template Versioning:**
- Old templates (v1.0.0) → Still supported via legacy `template_content` field
- New templates (v1.0.1+) → Include messaging protocol in `system_instructions`

**API Compatibility:**
- MCP tools: No signature changes
- Mission generation: Backward compatible (dependencies field optional)

---

## Testing Requirements (AI Agents)

### Test Workflow #1: Simple Messaging
**Objective:** Verify basic send/receive functionality

**Steps:**
1. Create project with 2 agents (implementer, documenter)
2. Verify orchestrator sends welcome message
3. Verify agents acknowledge welcome
4. Verify agents send progress updates after milestones
5. Verify agents send completion broadcast
6. Verify orchestrator receives all messages

**Success Criteria:**
- Welcome message appears in message center UI
- ≥2 progress messages from each agent
- Completion messages from both agents
- Orchestrator acknowledges all messages

### Test Workflow #2: Dependency Coordination
**Objective:** Verify dependency waiting mechanism

**Setup:**
- Agent A (implementer): No dependencies, starts immediately
- Agent B (analyzer): Depends on Agent A

**Steps:**
1. Spawn both agents
2. Verify Agent B sends "waiting for dependencies" status
3. Verify Agent B does NOT start work (no files created)
4. Wait for Agent A to complete
5. Verify Agent A sends COMPLETE message
6. Verify orchestrator notifies Agent B (DEPENDENCY_MET)
7. Verify Agent B begins work after notification
8. Verify Agent B completes successfully

**Success Criteria:**
- Agent B waits (no premature file creation)
- "Waiting for dependencies" messages visible
- Agent B starts only after Agent A completes
- Dependency coordination messages logged

### Test Workflow #3: Blocker Handling
**Objective:** Verify blocker escalation

**Setup:**
- Create project with intentional blocker (missing file/wrong path)
- Agent will encounter error

**Steps:**
1. Spawn agent with blocker scenario
2. Verify agent encounters blocker
3. Verify agent sends BLOCKER message to orchestrator
4. Verify orchestrator receives blocker
5. Verify orchestrator responds with guidance
6. Verify agent receives guidance and resolves blocker
7. Verify agent completes after resolution

**Success Criteria:**
- BLOCKER message appears in message center
- Orchestrator responds within reasonable time
- Agent successfully resolves blocker
- Blocker resolution logged in messages

### Test Workflow #4: User Mid-Execution Message
**Objective:** Verify user can send corrections mid-execution

**Steps:**
1. Start project with long-running agent (documenter)
2. While agent is working (50% complete), send user message: "Add security section to all docs"
3. Verify agent receives message
4. Verify agent acknowledges within 30 seconds
5. Verify agent adjusts work (adds security sections)
6. Verify agent completes with user request included

**Success Criteria:**
- Agent acknowledges user message <30 seconds
- Agent adjusts current work
- Final deliverables include user-requested changes
- User receives completion confirmation

### Test Workflow #5: Multi-Terminal Mode
**Objective:** Verify messaging works with separate terminal windows

**Setup:**
- Use Codex or Gemini (not Claude Code subagents)
- 3 agents in 3 separate terminals
- Agent C depends on A and B

**Steps:**
1. Launch orchestrator in Terminal 1
2. Launch Agent A in Terminal 2
3. Launch Agent B in Terminal 3
4. Launch Agent C in Terminal 4
5. Verify all agents communicate via MCP server (not terminal-to-terminal)
6. Verify Agent C waits for A and B
7. Verify messages flow through central hub
8. Verify all agents complete successfully

**Success Criteria:**
- Agents communicate only via MCP (no direct terminal interaction)
- Message center shows all communications
- Dependencies coordinated despite separate terminals
- Project completes successfully

---

## Performance Considerations (AI Agents)

**Message Check Frequency:**
- Agents: Every 5-10 actions (not every action)
- Orchestrator: Every 3-5 actions
- Dependency waiting: Every 30 seconds (max 10 attempts)

**Token Impact:**
- Agent messaging protocol: ~200 lines (~600 tokens)
- Orchestrator messaging protocol: ~300 lines (~900 tokens)
- Dependency coordination code: ~100 lines (~300 tokens) per dependency
- Total overhead: ~1000-1500 tokens per agent mission (acceptable for 70% reduction goal)

**Database Load:**
- Message storage: JSONB (efficient)
- Message retrieval: Indexed by agent_id and tenant_key
- No N+1 queries (batch message fetching)

---

## Troubleshooting Guide (AI Agents)

### Issue: Agent not checking messages
**Symptom:** Zero message hub usage despite protocol in template
**Diagnosis:** Agent not following checkpoint instructions
**Fix:** Verify `system_instructions` field contains messaging protocol

### Issue: Dependency timeout
**Symptom:** Agent reports "TIMEOUT: Dependencies not met after 5 minutes"
**Diagnosis:** Dependency never completed or orchestrator didn't notify
**Fix:** Check if dependency agent completed, verify orchestrator message handling

### Issue: Message not received
**Symptom:** Agent sends message but recipient never sees it
**Diagnosis:** Message routing issue or tenant isolation problem
**Fix:** Verify tenant_key matches, check `agent_communication_queue` table

### Issue: Orchestrator ignores BLOCKER
**Symptom:** Agent blocked but orchestrator doesn't respond
**Diagnosis:** Orchestrator not checking messages frequently enough
**Fix:** Verify orchestrator follows coordination loop (check every 3-5 actions)

---

## Implementation Checklist

- [x] Add messaging protocol functions to template_seeder.py
- [x] Integrate messaging protocol into all agent templates
- [x] Add dependency detection to mission_planner.py
- [x] Add dependency coordination code injection
- [x] Update generate_missions() to detect and inject dependencies
- [x] Backward compatibility verification
- [ ] Test Workflow #1: Simple messaging
- [ ] Test Workflow #2: Dependency coordination
- [ ] Test Workflow #3: Blocker handling
- [ ] Test Workflow #4: User mid-execution messages
- [ ] Test Workflow #5: Multi-terminal mode
- [ ] Production validation with TinyContacts v2

---

## Metrics for Success

**Quantitative:**
- Message hub usage: **>0 messages** (baseline: 0 in first test)
- Agent communication rate: **≥1 message per major milestone**
- Dependency coordination: **100% success rate** when dependencies exist
- User message response time: **<30 seconds** for acknowledgment
- Blocker resolution: **100% escalation rate** when blocked

**Qualitative:**
- Complex workflows complete successfully
- Multi-terminal mode functions correctly
- User interaction mid-execution works
- Message center UI displays relevant messages
- Agents coordinate explicitly (not by luck)

---

## Related Handovers

**Dependencies (Complete):**
- None (this is foundational)

**Dependents (Unblocked):**
- **Handover 0117:** 8-Role Agent System - Can now proceed with messaging in new role templates
- **Handover 0114:** Jobs Tab UI Harmonization - Can now display real messages in message center

---

**Status:** Implementation Complete (Phase 1-3)
**Next:** Testing & Validation (Phase 4)
**Production-Ready:** After test validation

---

*End of AI-Readable Documentation*
