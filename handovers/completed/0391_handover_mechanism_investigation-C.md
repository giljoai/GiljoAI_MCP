# Handover 0391: Handover Mechanism Investigation

**Status**: IN PROGRESS
**Date**: 2026-01-18
**Triggered By**: MCP Enhancement List item #27 (gil_handover parameter mismatch)

---

## Context

While reviewing MCP_ENHANCEMENT_LIST.md item #27, we discovered confusion about the handover mechanism. The enhancement list claims `gil_handover()` MCP tool rejects `tenant_key`, but deeper investigation reveals architectural questions about what this tool even does and whether it's still needed.

## Key Discovery: Passive Architecture Limitation

**Fundamental Issue**: Agents cannot self-detect context exhaustion.

- MCP server is passive (HTTP request/response only)
- Context % is shown to USER by CLI tool (Claude Code, Cursor, etc.)
- The LLM (agent) has no introspection into its own context usage
- Therefore, auto-triggering succession is architecturally impossible

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CLI Tool      │     │   LLM (Agent)   │     │   MCP Server    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ Shows 73% used  │     │ No introspection│     │ Passive, no     │
│ to USER only    │     │ capability      │     │ visibility      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Current Code State (Pre-Investigation)

### MCP HTTP Schema (mcp_http.py lines 435-449)
```python
{
    "name": "gil_handover",
    "inputSchema": {
        "properties": {
            "job_id": {...},
            "reason": {"enum": ["context_limit", "manual", "phase_transition"]},
            "tenant_key": {...},  # Required in schema
        },
        "required": ["tenant_key"],
    },
}
```

### ToolAccessor.gil_handover() (tool_accessor.py line 1163)
```python
async def gil_handover(self, job_id: str = None, reason: str = "manual"):
    # NO tenant_key parameter - uses self.tenant_manager instead
    # Also passes reason= to handler, but handler ignores it
```

### handle_gil_handover() (handover.py)
```python
async def handle_gil_handover(
    db_session, tenant_key, project_id=None, orchestrator_job_id=None
):
    # NO reason parameter - always uses "manual"
```

### check_succession_status() (tool_accessor.py lines 1110-1159)
- Reads `execution.context_used` and `execution.context_budget` from database
- Returns `should_trigger: true` at 90% threshold
- **Problem**: These fields are never populated because agents can't know their context usage

## Questions to Investigate

1. **Is `gil_handover` still exposed as MCP tool?** Or was it removed like `gil_activate`/`gil_launch`?

2. **Dashboard handover icon**: Where is it? When does it appear? What does it trigger?

3. **Project closeout protocol**: How does it interact with orchestrator succession?

4. **Succession flow**: What's the intended user journey when context is exhausted?

5. **Historical context**: What did Handover 0080 (Orchestrator Succession) actually implement?

## User's Understanding

> "We have an icon on the dashboard, and I think it triggers when the current orchestrator reports its work as 'completed'. We have a project closeout protocol but it works in tandem with this handover."

This suggests:
- Handover is UI-triggered, not MCP-tool-triggered
- It's tied to orchestrator completion status, not context exhaustion
- May be conflating two different flows:
  1. **Context exhaustion handover** (mid-project, continue with fresh context)
  2. **Project completion** (end of project, closeout and archive)

## Next Steps

1. Subagent investigation of current implementation
2. Clarify the two distinct flows (if they exist)
3. Determine what needs fixing vs what's working as designed
4. Update documentation to match reality

---

## Investigation Results

### 1. gil_handover MCP Status
**Was exposed, now removed.** The tool existed in both schema (lines 434-450) and tool_map (line 637) of `mcp_http.py`. Removed in this handover because:
- Users trigger succession via UI "Hand Over" button (REST API)
- MCP tool had `tenant_key` parameter mismatch bug
- Agents cannot self-detect context exhaustion anyway

### 2. UI Handover Button
**Location**: JobsTab.vue (lines 195-210) - hand-wave icon (`mdi-hand-wave`)

**Visibility conditions**:
- Agent is `orchestrator`
- Status is `working` (or `complete`/`completed`)
- No context threshold (Handover 0506 removed this - user decides when)

**Click flow**:
```
Click → LaunchSuccessorDialog modal →
POST /api/agent-jobs/{job_id}/trigger-succession →
Returns launch prompt → User copies to fresh terminal
```

### 3. Two Distinct Flows Confirmed

| Flow | Trigger | Purpose |
|------|---------|---------|
| **Succession** | User clicks handover button | Same job_id, new agent_id, fresh context |
| **Completion** | Agent calls complete_job() | Job closed, write_360_memory, project ends |

### 4. Key Architecture Insight
Agents cannot self-detect context exhaustion:
- MCP server is passive (HTTP request/response)
- Context % shown to USER by CLI tool
- LLM has no introspection into own context usage

Therefore, succession is **user-triggered**, not auto-triggered.

---

## Resolution

**Action Taken**: Removed `gil_handover` from MCP exposure
- Schema removed from tools list
- Entry removed from tool_map
- ToolAccessor method marked DEPRECATED
- REST API endpoint unchanged (UI button still works)

**Files Modified**:
- `api/endpoints/mcp_http.py` - removed schema and tool_map entry
- `src/giljo_mcp/tools/tool_accessor.py` - marked method deprecated

**Status**: COMPLETE
