# 0382 - Orchestrator Prompt Improvements (Claude Code Mode)

## Context

During alpha testing of the Claude Code CLI orchestrator flow, several assumptions had to be made due to unclear or missing guidance in the launch prompt. This handover documents improvements to remove those assumptions and create a fail-fast startup experience.

**Testing Session:** TinyContacts project staging
**Mode:** Claude Code CLI (Mode A)
**Tester Role:** Orchestrator

---

## Issue 1: Agent Template Export Status Validation

### Problem

The orchestrator prompt provides `allowed_agent_names` from MCP but does not validate whether:
1. Agent templates have been exported to local `.claude/agents/*.md` files
2. Exported templates are current (not stale vs MCP server version)

This leads to potential silent failures during implementation phase when `Task(subagent_type="X")` cannot find the template file.

### Current Behavior

```
Orchestrator receives: allowed_agent_names = ["analyzer", "implementer", "documenter", "reviewer"]
Orchestrator assumes: .claude/agents/analyzer.md exists locally
Reality: File may be missing, stale, or never exported
```

### Proposed Solution

**Enhance `get_orchestrator_instructions()` response to include export status:**

```json
{
  "agent_templates": [
    {
      "name": "analyzer",
      "role": "analyzer",
      "description": "...",
      "export_status": "synced",
      "last_exported": "2025-12-30T10:00:00Z",
      "mcp_updated": "2025-12-30T09:00:00Z"
    },
    {
      "name": "implementer",
      "export_status": "stale",
      "last_exported": "2025-12-20T10:00:00Z",
      "mcp_updated": "2025-12-28T15:00:00Z"
    },
    {
      "name": "documenter",
      "export_status": "never_exported",
      "last_exported": null,
      "mcp_updated": "2025-12-25T12:00:00Z"
    }
  ]
}
```

**Export Status Values:**
- `synced`: MCP template version matches last export, safe to use
- `stale`: MCP template updated since last export, needs re-export
- `never_exported`: Template exists on MCP but has never been exported locally

### Orchestrator Startup Gate Check

Add to startup sequence (between Step 1 and Step 2):

```markdown
1. Verify MCP: health_check()

1.5 VALIDATE AGENT TEMPLATES:
    Review agent_templates from get_orchestrator_instructions()

    IF any agent has export_status = "stale" or "never_exported":
      → STOP IMMEDIATELY
      → Output to user:
        "CANNOT PROCEED - Agent templates require sync:

         | Agent       | Status         | MCP Updated  | Last Export  |
         |-------------|----------------|--------------|--------------|
         | implementer | stale          | 2025-12-28   | 2025-12-20   |
         | documenter  | never_exported | 2025-12-25   | never        |

         ACTION REQUIRED:
         1. Run /gil_get_claude_agents to export templates
         2. RESTART Claude Code (required for templates to load)
         3. Re-run this orchestrator prompt

         Staging cannot proceed until templates are synced."
      → DO NOT proceed to Step 2

    IF all agents have export_status = "synced":
      → Proceed with staging

2. Fetch context: get_orchestrator_instructions(...)
```

### Additional Validation (Belt and Suspenders)

Since `export_status` only tracks MCP→export action (not file existence), orchestrator should also verify local files exist:

```
After confirming export_status = "synced" for all agents:
  Use Glob(".claude/agents/*.md") to verify files exist

  IF any expected file is missing:
    → Warn user: "Template file missing despite 'synced' status.
                  Please run /gil_get_claude_agents and restart."
```

### Implementation Tasks

1. **Backend:** Add `export_status`, `last_exported`, `mcp_updated` fields to `get_orchestrator_instructions()` response
   - Location: `src/giljo_mcp/services/orchestration_service.py`
   - Pull from Agent Template Manager's existing export tracking

2. **Prompt Generator:** Add Step 1.5 gate check logic to orchestrator launch prompt
   - Location: `src/giljo_mcp/thin_prompt_generator.py`

3. **Documentation:** Update orchestrator workflow docs to include export validation step

---

## Issue 2: fetch_context Single Category Limitation

### Problem

Orchestrator attempted `fetch_context(categories=["tech_stack", "testing"])` and received error:
```json
{
  "error": "SINGLE_CATEGORY_REQUIRED",
  "message": "Only ONE category per call allowed"
}
```

### Current Status

**Known technical debt - POSTPONED**

The error message is clear and actionable. Orchestrator can call fetch_context separately for each category (in parallel).

### Future Improvement (Deferred)

Allow multi-category fetch in single call for efficiency.

---

## Issue 3: Task Tool Reference in Staging Prompt - Clarification

### Original Confusion

The staging prompt includes Task tool syntax:
```markdown
Example Task call:
  Task(subagent_type="{agent_name}", instructions="...")
```

This caused confusion: "Should I use Task tool during staging?"

### Clarification (No Change Needed)

The Task tool reference is **intentional context**, not an action to take during staging.

**Purpose:** Inform orchestrator that:
- Execution mode = Claude Code CLI
- Implementation will use Task tool for agent invocation
- Orchestrator should plan accordingly when writing execution plan:
  - Can agents run in parallel? (multiple Task calls simultaneously)
  - Must they be sequential? (dependencies between agents)
  - What handoff messages are needed?

**The orchestrator uses this context when:**
- Step 6: Writing execution plan via `update_agent_mission()`
- Deciding parallel vs sequential agent execution
- Planning coordination checkpoints

### Suggested Prompt Clarification

Add framing to the CLI MODE section:

```markdown
CLI MODE CONTEXT (for planning, not immediate execution):
This project uses Claude Code CLI. During IMPLEMENTATION phase, you will spawn agents using:

  Task(subagent_type="{agent_name}", prompt=spawn_agent_job().agent_prompt)

Use this context when writing your execution plan (Step 6):
- Determine if agents can run in parallel or must be sequential
- Plan coordination checkpoints between agent phases
- Document handoff message content

NOTE: Do NOT invoke Task tool during staging. Only plan for its use.
```

---

## Issue 4: Phase Boundary Clarity (HIGH PRIORITY)

### Problem

Steps 1-7 are staging, Step 8 describes "monitoring" which felt like implementation. The orchestrator was unclear when staging ends and what triggers implementation. This ambiguity can lead to:
- Orchestrator attempting to invoke Task tool during staging
- Confusion about session boundaries
- Unclear handoff between staging and implementation phases

### Root Cause

The current prompt includes Step 8 (monitoring patterns) in the same prompt as Steps 1-7 (staging). This implies continuous execution rather than distinct phases with a session boundary.

### Required Change: EXPLICIT PHASE BOUNDARY

The staging prompt MUST clearly delineate:
1. What happens in THIS session (staging only)
2. What triggers the next phase (/gil_launch)
3. What the orchestrator should NOT do during staging

### Suggested Addition to Prompt (MUST IMPLEMENT)

Add this block prominently near the top of the prompt, after IDENTITY section:

```markdown
════════════════════════════════════════════════════════════════════════════════
                              PHASE BOUNDARY - READ CAREFULLY
════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGING PHASE (Steps 1-7): THIS SESSION                                     │
│                                                                             │
│ Your job RIGHT NOW:                                                         │
│ - Analyze requirements, create mission plan                                 │
│ - Spawn agent jobs (creates DATABASE RECORDS only)                          │
│ - Write your execution plan for future retrieval                            │
│ - Broadcast STAGING_COMPLETE                                                │
│                                                                             │
│ DO NOT:                                                                     │
│ - Invoke Task tool to run agents                                            │
│ - Execute any agent work                                                    │
│ - Start implementation                                                      │
│                                                                             │
│ END THIS SESSION WITH:                                                      │
│ "Staging complete. N agents spawned. Ready for /gil_launch"                 │
└─────────────────────────────────────────────────────────────────────────────┘

                    ══════ SESSION BOUNDARY ══════
                         User runs /gil_launch
                    ══════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│ IMPLEMENTATION PHASE (Step 8+): FUTURE SESSION (after /gil_launch)          │
│                                                                             │
│ A fresh orchestrator instance will:                                         │
│ - Retrieve YOUR execution plan via get_agent_mission()                      │
│ - Invoke Task tool for each agent per your plan                             │
│ - Monitor via receive_messages()                                            │
│ - Coordinate handoffs between agents                                        │
│ - Complete job when all agents finish                                       │
│                                                                             │
│ NOTE: Step 8 instructions are CONTEXT for planning, not for this session.   │
└─────────────────────────────────────────────────────────────────────────────┘

KEY PRINCIPLE: Staging orchestrator creates jobs. It does NOT execute them.
════════════════════════════════════════════════════════════════════════════════
```

### Why This Matters

1. **Session Isolation**: Claude Code sessions don't persist. Staging and implementation are DIFFERENT sessions.
2. **State in Database**: The orchestrator's execution plan survives session restart via `update_agent_mission()`
3. **Clear Termination**: Orchestrator knows exactly when to stop and what to output
4. **No Premature Execution**: Prevents Task tool invocation during staging

### Implementation Tasks

1. **Prompt Generator**: Add PHASE BOUNDARY block to `_build_orchestrator_staging_prompt()` or equivalent
   - Location: `src/giljo_mcp/thin_prompt_generator.py`
   - Position: After IDENTITY section, before STARTUP SEQUENCE

2. **Remove Step 8 from staging prompt OR clearly mark it as "CONTEXT FOR PLANNING ONLY"**
   - Current prompt includes monitoring patterns that imply continuous execution
   - Either move to implementation prompt, or add explicit "This is context for your execution plan, not actions for this session"

3. **Standardize termination message**: All staging orchestrators should end with consistent phrasing:
   ```
   "Staging complete. [N] agents spawned. Execution plan saved. Ready for /gil_launch"
   ```

---

## Summary of Changes

| Issue | Priority | Action |
|-------|----------|--------|
| 1. Export status validation | HIGH | Implement gate check in orchestrator startup |
| 2. fetch_context multi-category | LOW | Deferred (known technical debt) |
| 3. Task tool context framing | MEDIUM | Add "for planning, not execution" clarification |
| 4. Phase boundary clarity | **HIGH** | Add PHASE BOUNDARY block at top of prompt, explicit session separation |

---

## Testing Checklist

**Issue 1: Export Status Validation**
- [ ] `get_orchestrator_instructions()` returns `export_status` per agent
- [ ] Orchestrator stops if any agent is stale/never_exported
- [ ] Clear remediation message shown to user
- [ ] After export + restart, orchestrator proceeds normally

**Issue 4: Phase Boundary**
- [ ] PHASE BOUNDARY block appears prominently in staging prompt
- [ ] Orchestrator does NOT attempt Task tool during staging
- [ ] Orchestrator outputs standard termination message
- [ ] Step 8 clearly marked as "context for planning" not "actions for this session"
- [ ] Implementation phase prompt (after /gil_launch) correctly retrieves saved execution plan

---

## Related Handovers

- 0349: Thin client architecture
- 0353: Agent instruction slimming
- 0380: update_agent_mission tool
- 0381: Agent/job separation cleanup
