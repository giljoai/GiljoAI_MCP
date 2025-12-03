# Handover 0106c: Multi-CLI Workflow Comparison & User Guide

**Date**: 2025-11-05
**Status**: 📝 DISCUSSION PLACEHOLDER
**Priority**: Medium (Documentation)
**Estimated Complexity**: 3-4 hours (discussion + documentation)

---

## Purpose

**Discussion session** to create comprehensive comparison between:
- Codex CLI workflow (multi-terminal)
- Gemini CLI workflow (multi-terminal)
- Claude Code workflow (single-terminal with subagents)

**Output**: Append detailed comparison to `handovers/start_to_finish_agent_FLOW.md`

---

## Topics to Cover in Discussion

### 1. **Detailed Flow Comparison**

**Questions to Answer**:
- How does agent spawning differ between CLIs?
- What are the user actions for each?
- Where does automation differ?
- What's the terminal experience for each?

**Deliverable**: Side-by-side flow diagrams

---

### 2. **Template Differences per CLI Tool**

**Questions to Answer**:
- Do templates need different instructions for Codex vs Claude Code?
- What's CLI-specific vs universal?
- How does agent ID assignment differ?
- What about check-in protocols?

**Deliverable**: Template configuration matrix

---

### 3. **User Decision Guide**

**Questions to Answer**:
- When should users choose Claude Code subagent mode?
- When should users choose multi-terminal mode?
- What are pros/cons of each?
- How to switch between modes?

**Deliverable**: Decision tree or comparison table

---

### 4. **Orchestrator Succession with Dynamic Spawning**

**Questions to Answer**:
- What happens if orchestrator spawns 6 agents, then hits context limit?
- Does successor orchestrator know about dynamically spawned agents?
- How does `/gil_handover` handle this?
- What prompt engineering is needed?

**Deliverable**: Succession flow documentation + prompt instructions

---

## Discussion Format

**Collaborative Session**:
1. User and Claude discuss each topic
2. User provides product vision and requirements
3. Claude asks clarifying questions
4. Together we build comparison documentation
5. Claude appends complete section to `start_to_finish_agent_FLOW.md`

---

## Expected Output Location

**Primary**: Append to `F:\GiljoAI_MCP\handovers\start_to_finish_agent_FLOW.md`

**Sections to Add**:
- Multi-CLI Workflow Comparison
- Template Configuration Matrix
- User Decision Guide
- Orchestrator Succession Edge Cases

---

## Dependencies

**Related Handovers**:
- 0105 (Implementation tab toggle)
- 0106 (Template instructions)
- 0106b (Claude Code spawning guide)
- 0107 (Check-in protocol)

---

## Success Criteria

- [ ] All 4 topics discussed and documented
- [ ] Flow diagrams created for each CLI
- [ ] Decision guide clear and actionable
- [ ] Succession edge cases addressed
- [ ] Content appended to start_to_finish_agent_FLOW.md

---

## Background Context (From User)

**Origin Story**:
- Legacy mode from F:\AKE-MCP project
- Original flow: Orchestrator created mission → user reviewed → prompts generated for each agent
- User opened multiple terminal windows, pasted each agent's ID, mission, instructions
- Worked extremely well
- Claude introduced subagents → now leveraging this capability
- BUT: Codex, Gemini, or even Claude can STILL use multi-terminal mode (developer-managed)
- Trade-off: Multi-terminal = more control vs Subagents = more convenience but requires highly tuned templates

---

## DISCUSSION QUESTIONS (To Be Answered)

### **1. Template Differences**

**Q1a**: Do agent templates need ANY differences between multi-terminal mode vs Claude Code subagent mode?

Understanding:
- Same 8 agent types (orchestrator, implementer, tester, etc.)
- Same MCP coordination instructions (acknowledge_job, report_progress, etc.)
- Same check-in protocol

Possibly different:
- Claude Code templates might have subagent-specific instructions?
- Multi-terminal templates might have "you are independent" emphasis?

**Or are they 100% identical and just spawned differently?**

**ANSWER**: _[User to fill in]_

---

### **2. Template Export Differences**

**Q2a**: When user clicks "Export Agents" in dashboard, do we generate DIFFERENT files for:
- Claude Code (one format)
- Codex CLI (different format)
- Gemini CLI (different format)

**Or**: Same YAML/Markdown files work for all CLI tools?

**ANSWER**: _[User to fill in]_

**Q2b**: In Handover 0041 (Agent Template Management), there's a `cli_tool` field. Does this mean:
- Users mark templates as "for Claude Code" vs "for Codex"?
- OR: Same templates, just different export format?

**ANSWER**: _[User to fill in]_

---

### **3. Implementation Tab Toggle Behavior**

**Q3a**: The "Using Claude Code subagents" toggle on Implementation tab:

**When OFF** (Multi-terminal mode):
- All agent prompt buttons active
- User copies each prompt individually
- Opens multiple terminals manually
- Pastes in each terminal

**Confirm**: This works for Claude Code, Codex, Gemini, ANY CLI tool?

**ANSWER**: _[User to fill in]_

**Q3b**: When this toggle is OFF, does orchestrator STILL spawn agent jobs via `spawn_agent_job()` MCP tool?

**Or**: Does orchestrator just generate prompt text without backend registration?

Assumption:
- Orchestrator ALWAYS calls `spawn_agent_job()` (creates job records)
- Toggle only affects UI (which buttons are active)
- Agent IDs assigned regardless of mode

**Correct?**

**ANSWER**: _[User to fill in]_

---

### **4. Orchestrator Prompt Differences**

**Q4a**: In multi-terminal mode, does orchestrator:
- Still use Claude Code Task tool to spawn? (NO, right?)
- OR: Just output prompt text for user to copy?

Understanding:
```
Multi-terminal mode:
1. Orchestrator calls spawn_agent_job() (backend registration)
2. Orchestrator outputs prompt text to user
3. User copies prompt → pastes in new terminal
4. Agent starts, calls acknowledge_job()

Claude Code subagent mode:
1. Orchestrator calls spawn_agent_job() (backend registration)
2. Orchestrator uses Task tool (spawns in same terminal)
3. Subagent auto-starts, calls acknowledge_job()
```

**Correct?**

**ANSWER**: _[User to fill in]_

---

### **5. Orchestrator Succession Edge Case**

**Q5a**: When orchestrator hits context limit and `/gil_handover` triggers:

**Scenario**:
```
Orchestrator-1 spawns 6 agents
  ↓
Orchestrator-1 hits 90% context
  ↓
/gil_handover creates Orchestrator-2
  ↓
Question: Does Orchestrator-2 know about the 6 agents?
```

Understanding:
- Agents are linked to `project_id` (not `orchestrator_id`)
- Orchestrator-2 queries: "Get all active agents for project_id"
- Orchestrator-2 sees all 6 agents automatically

**But does Orchestrator-2 need special instructions?**

Like:
```markdown
# Orchestrator-2 Handover Context

You are taking over from Orchestrator-1.

EXISTING AGENTS (already working):
- implementer-abc123: Working on auth endpoints (45% complete)
- tester-def456: Waiting for implementer to finish
- frontend-ghi789: Building login UI (60% complete)
...

Continue coordinating these agents. DO NOT respawn them.
```

**Is this handled by**:
- `/gil_handover` prompt generation?
- MCP tool that fetches active agents?
- Both?

**ANSWER**: _[User to fill in]_

---

### **6. Trade-offs & User Guidance**

**Q6a**: When should users choose multi-terminal vs Claude Code subagents?

**Draft comparison** (confirm if accurate):

| Factor | Multi-Terminal | Claude Code Subagents |
|--------|----------------|----------------------|
| **Control** | More (manual spawn/stop) | Less (Claude manages) |
| **Convenience** | Less (multiple windows) | More (single window) |
| **CLI Support** | All (Claude, Codex, Gemini) | Claude Code only |
| **Resource Usage** | Higher (multiple processes) | Lower (single process) |
| **Debugging** | Easier (see each agent separately) | Harder (mixed logs) |
| **Template Tuning** | Less critical | Critical (templates control behavior) |

**Q6b**: Any other trade-offs missing?

**ANSWER**: _[User to fill in]_

**Q6c**: Do you have a RECOMMENDED default for users?

**ANSWER**: _[User to fill in]_

---

### **7. Switching Between Modes**

**Q7a**: Can user switch mid-project?

**Scenario**:
```
User starts with multi-terminal mode (3 agents in separate terminals)
  ↓
User switches toggle to "Claude Code subagents"
  ↓
What happens?
```

**Options**:
- A) Can't switch (toggle locked once agents spawned)
- B) Can switch, but requires respawning all agents
- C) Can switch, existing agents unaffected, NEW agents use new mode

**Which is it?**

**ANSWER**: _[User to fill in]_

---

### **8. Codex/Gemini Specific Differences**

**Q8a**: Do Codex CLI or Gemini CLI have ANY unique behaviors compared to Claude Code (multi-terminal)?

Like:
- Different MCP command syntax?
- Different agent ID format?
- Different prompt format requirements?

**Or**: They're 100% identical to "Claude Code in multi-terminal mode"?

**ANSWER**: _[User to fill in]_

---

### **9. Dynamic Spawning in Multi-Terminal**

**Q9a**: If orchestrator realizes it needs a 4th agent mid-execution (in multi-terminal mode):

**Flow**:
```
1. Orchestrator calls spawn_agent_job() ✅
2. Agent card appears in UI ✅
3. Orchestrator outputs prompt for user ← How?
```

**Question**: How does orchestrator communicate to USER "Hey, I need you to spawn this agent"?

**Options**:
- A) Message to user via UI notification
- B) Orchestrator logs it (user checks dashboard)
- C) Orchestrator can't dynamically spawn in multi-terminal mode
- D) Something else?

**ANSWER**: _[User to fill in]_

---

### **10. Orchestrator in Multi-Terminal Mode**

**Q10a**: In multi-terminal mode, does the ORCHESTRATOR itself run:
- In its own dedicated terminal?
- In the same terminal where user ran "Stage Project"?

**ANSWER**: _[User to fill in]_

**Q10b**: Does orchestrator have a prompt button on Implementation tab, or just sub-agents?

**ANSWER**: _[User to fill in]_

---

## Notes

**Status**: Questions saved - awaiting user answers
**Requires**: User to fill in answers above
**Duration**: Estimated 1-2 hours discussion + 1-2 hours documentation

**When Ready**: User fills in answers, then Claude will document and append to `start_to_finish_agent_FLOW.md`
