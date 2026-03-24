# Multi-Tool Terminal Orchestration Proposal

**Edition Scope:** CE
**Status:** Proposal (not yet implemented)
**Date:** 2026-03-19
**Context:** Alpha trial of multi-terminal execution (Codex CLI + Gemini CLI + Claude Code) revealed coordination gaps when agents across independent terminal sessions communicate exclusively through the MCP server.

---

## Problem Statement

In multi-terminal mode, each AI coding agent (Claude Code, Codex CLI, Gemini CLI) runs in its own terminal with its own agent session. These terminals **cannot communicate directly** -- the GiljoAI MCP server is the only coordination layer. This creates several gaps:

1. **No polling mechanism** -- Once an orchestrator completes staging, it has no way to periodically check on spawned agents. It either blocks waiting or exits.
2. **Completed agents are dead** -- When Agent A finishes and another agent sends it a "fix this" message, Agent A cannot re-enter a working state. The status transition `complete -> working` does not exist.
3. **TODO overwrite risk** -- When a reactivated agent recalibrates its work plan, `report_progress(todo_items=[...])` replaces the entire list instead of appending new items.
4. **Messages show UUIDs, not names** -- Agents see `"from agent 45514577-a579-..."` instead of `"from Code Analyzer"` because `receive_messages` does not resolve sender display names.

---

## Architecture Analysis

### What Exists Today

| Component | Current Behavior | File |
|-----------|-----------------|------|
| Agent status transitions | `waiting -> working -> complete` (terminal). No backward transition. | `models/agent_identity.py:291-295` |
| MCP session after completion | **Stays alive** (24h expiry). Session is decoupled from job status. | `api/endpoints/mcp_session.py:122-204` |
| Tool access after completion | Most tools still work. `report_progress` and `complete_job` fail (query for active execution). | `orchestration_service.py:1399-1410` |
| Message to completed agent | By display name: fails (filtered to active statuses). By UUID: succeeds but sits undelivered. | `message_service.py:201-202` |
| Sleep/poll patterns | Silence detector runs `asyncio.sleep(60)` loop server-side. No agent-side polling exists. | `silence_detector.py:73-93` |
| Prompt injection | CH1-CH5 protocol injected via `protocol_builder.py`. User-configurable field toggles and depth settings. | `protocol_builder.py:555-1149` |
| TODO tracking | `AgentTodoItem` table with `content`, `status`, `sequence`. Sent via `report_progress(todo_items=[...])`. | `models/agent_identity.py:310-388` |
| Settings UI pattern | `v-switch` + `v-tooltip` with `mdi-information-outline` icon. Used in `ContextPriorityConfig.vue`. | `frontend/src/components/settings/ContextPriorityConfig.vue:67-162` |

### What's Missing

1. **No agent-side sleep-wake loop** -- Agents run linearly: do work, complete, exit. No mechanism to say "sleep 5 minutes, then check messages."
2. **No `complete -> working` transition** -- Status is terminal. No `reactivate_job` tool or service method.
3. **No TODO append mode** -- `report_progress` accepts a full `todo_items` array that replaces the previous state.
4. **No sender name enrichment** -- `receive_messages` returns raw `meta_data._from_agent` (often a UUID) without resolving to `agent_display_name`.
5. **No prompt instructions for reactivation** -- Even if we add the status transition, agents need protocol guidance on what to do when waking from completion.

---

## Proposed Features

### Feature 1: Sleep-Wake Polling via Prompt Protocol

**Concept:** Inject a "sleep-wake" instruction into the agent's protocol that tells it: after completing your work, instead of exiting, sleep for N minutes, then call `receive_messages()` and `get_workflow_status()`. If new work is found, reactivate and continue. If not, sleep again (up to a max cycle count to bound token cost).

**Why prompt-based, not server-side:** The MCP server is passive (stateless HTTP). It cannot push to agents. Agents must pull. The sleep loop runs inside the agent's terminal session, driven by the LLM following protocol instructions.

**Implementation:**

1. **New user setting: `sleep_wake`** (stored in `user_settings` table)
   ```json
   {
     "sleep_wake": {
       "enabled": false,
       "interval_minutes": 5,
       "max_cycles": 6,
       "applies_to": "all"
     }
   }
   ```
   - `enabled`: Master toggle (default off -- saves tokens)
   - `interval_minutes`: How long to sleep between checks (1-30, default 5)
   - `max_cycles`: Maximum wake-check cycles before final exit (1-20, default 6)
   - `applies_to`: `"orchestrator"` | `"agents"` | `"all"` (who gets the instruction)

2. **Protocol injection** -- Add a new section to the protocol builder output (after CH5):
   ```
   ## SLEEP-WAKE PROTOCOL (ACTIVE)
   After completing your work via complete_job(), DO NOT exit immediately.
   Instead, follow this cycle:
   1. Wait approximately {interval_minutes} minutes
   2. Call receive_messages(agent_id=your_id) to check for new messages
   3. Call get_workflow_status(project_id=your_project) to check peer agent statuses
   4. If you have new messages requiring action:
      a. Call reactivate_job(job_id=your_job_id)
      b. APPEND new steps to your existing TODO list (do NOT replace it)
      c. Resume work on the new items
      d. Call complete_job() again when done
      e. Return to step 1
   5. If no action needed, repeat from step 1
   6. After {max_cycles} cycles with no new work, exit permanently.

   TOKEN COST NOTE: Each wake cycle consumes tokens for the tool calls.
   This protocol is user-configured and can be disabled.
   ```

3. **Conditional injection** -- `protocol_builder.py` reads the user's `sleep_wake` config and only injects this section when `enabled=true` and the agent role matches `applies_to`.

**Files impacted:**
- `src/giljo_mcp/services/protocol_builder.py` -- New `_build_sleep_wake_protocol()` method, inject after CH5
- `src/giljo_mcp/services/orchestration_service.py` -- `get_orchestrator_instructions()` passes setting to builder
- `api/endpoints/user_settings.py` -- Persist `sleep_wake` config (may already support arbitrary JSON)
- `frontend/src/components/settings/` -- New UI section (see Feature 5)

---

### Feature 2: Agent Self-Reactivation (`reactivate_job` Tool)

**Concept:** New MCP tool that transitions a completed job back to active, allowing the agent to resume work.

**Implementation:**

1. **New service method: `OrchestrationService.reactivate_job()`**
   ```python
   async def reactivate_job(self, job_id: str, tenant_key: str, reason: str = "") -> dict:
       # 1. Find the completed execution
       execution = await self._find_execution(job_id, tenant_key,
           allowed_statuses=["complete"])  # Only allow reactivation from "complete"

       # 2. Transition execution: complete -> working
       execution.status = "working"
       execution.completed_at = None
       execution.progress = max(execution.progress - 5, 50)  # Slight regression to indicate resumed work

       # 3. Transition job: completed -> active (if it was completed)
       job = await self._find_job(job_id, tenant_key)
       if job.status == "completed":
           job.status = "active"
           job.completed_at = None

       # 4. Log the reactivation
       logger.info(f"Job {job_id} reactivated: {reason}")

       # 5. Broadcast WebSocket event for UI
       await self._broadcast("agent:reactivated", {
           "job_id": job_id, "agent_id": execution.agent_id, "reason": reason
       })

       # 6. Return confirmation with reactivation instructions
       return {
           "status": "reactivated",
           "job_id": job_id,
           "agent_id": execution.agent_id,
           "instruction": "APPEND new work items to your TODO list. Do NOT replace existing completed items."
       }
   ```

2. **New MCP tool definition** (add to `_build_agent_coordination_tools()`):
   ```python
   {
       "name": "reactivate_job",
       "description": "Reactivate a completed job to resume work (e.g., after receiving a fix request). "
                      "Only works on jobs in 'complete' status. After reactivating, APPEND new steps to "
                      "your existing TODO list -- do not overwrite completed items.",
       "inputSchema": {
           "type": "object",
           "properties": {
               "job_id": {"type": "string", "description": "Job ID to reactivate"},
               "reason": {"type": "string", "description": "Why the job is being reactivated (e.g., 'fix request from Orchestrator')"}
           },
           "required": ["job_id"]
       }
   }
   ```

3. **Re-enable `report_progress` for reactivated agents** -- The current `report_progress` query filters `status.not_in(["complete", "decommissioned"])`. After reactivation, status is "working" again, so this automatically works. No change needed.

4. **Re-enable `complete_job`** -- Same: after reactivation the execution is "working", so re-completion works naturally.

5. **Prompt instructions for reactivated agents** -- The `reactivate_job` tool response itself includes the instruction to APPEND to the TODO list. Additionally, the sleep-wake protocol section (Feature 1) includes this guidance. The agent receives both signals.

**Files impacted:**
- `src/giljo_mcp/services/orchestration_service.py` -- New `reactivate_job()` method
- `src/giljo_mcp/tools/tool_accessor.py` -- New `reactivate_job()` delegation
- `api/endpoints/mcp_http.py` -- Tool definition, schema params, handler registration

---

### Feature 3: TODO Append Mode in `report_progress`

**Concept:** Add an `append` parameter to `report_progress` so agents can add new items without overwriting completed ones.

**Current behavior:** `report_progress(todo_items=[...])` replaces the entire TODO state. If an agent had 5 completed items and calls with 2 new ones, the 5 completed items are lost from the progress tracking.

**Implementation:**

1. **New parameter: `todo_append`** on `report_progress`
   ```python
   async def report_progress(
       self, job_id, progress=None, tenant_key=None,
       todo_items=None,
       todo_append: list[dict] | None = None,  # NEW: items to append
   ):
   ```

2. **Append logic** (in `orchestration_service.py`):
   ```python
   if todo_append is not None:
       # Fetch existing TODO items from last progress report
       existing_todos = execution.last_progress.get("todo_items", []) if execution.last_progress else []

       # Calculate next sequence number
       max_seq = max((t.get("sequence", i) for i, t in enumerate(existing_todos)), default=-1)

       # Append new items with incremented sequence
       for i, item in enumerate(todo_append):
           item.setdefault("status", "pending")
           item["sequence"] = max_seq + 1 + i

       # Merge: existing + new
       todo_items = existing_todos + todo_append
   ```

3. **Tool schema update** (in `_build_agent_coordination_tools()`):
   ```json
   "todo_append": {
     "type": "array",
     "description": "Items to APPEND to existing TODO list (use instead of todo_items when adding work to a reactivated job)",
     "items": {
       "type": "object",
       "properties": {
         "content": {"type": "string"},
         "status": {"type": "string", "enum": ["pending", "in_progress"]}
       },
       "required": ["content"]
     }
   }
   ```

4. **Schema params allowlist** -- Add `"todo_append"` to `_TOOL_SCHEMA_PARAMS["report_progress"]`.

**Files impacted:**
- `src/giljo_mcp/services/orchestration_service.py` -- `report_progress()` append logic
- `api/endpoints/mcp_http.py` -- Schema definition update, params allowlist
- `src/giljo_mcp/tools/tool_accessor.py` -- Pass-through for new parameter

---

### Feature 4: Sender Display Name in Messages

**Problem:** When an agent calls `receive_messages()`, the `from_agent` field contains whatever was stored in `meta_data._from_agent` at send time -- often a raw UUID like `45514577-a579-4159-97a2-3eb5de08b06c` instead of a human-readable name like "Code Analyzer".

**Root cause:** `message_service.py:239` stores the sender reference as-is:
```python
meta_data={"_from_agent": from_agent or "orchestrator", ...}
```
And `message_service.py:1086` reads it back without lookup:
```python
"from_agent": msg.meta_data.get("_from_agent", "")
```

**Implementation:**

1. **Enrich at send time** -- When creating a message, resolve the sender's display name and store it alongside the UUID:
   ```python
   # In send_message(), after resolving sender identity:
   sender_display = sender_execution.agent_display_name if sender_execution else from_agent
   meta_data = {
       "_from_agent": from_agent or "orchestrator",
       "_from_display_name": sender_display,
   }
   ```

2. **Enrich at receive time** (fallback for existing messages without `_from_display_name`):
   ```python
   # In receive_messages(), when formatting message dicts:
   from_agent_raw = msg.meta_data.get("_from_agent", "") if msg.meta_data else ""
   from_display = msg.meta_data.get("_from_display_name", "") if msg.meta_data else ""

   # Fallback: if no display name stored, try to resolve UUID
   if not from_display and from_agent_raw and "-" in from_agent_raw:
       # Batch-resolve UUIDs to display names (single query for all messages)
       from_display = sender_name_map.get(from_agent_raw, from_agent_raw)

   messages_list.append({
       "from_agent": from_display or from_agent_raw,
       "from_agent_id": from_agent_raw,
       ...
   })
   ```

3. **Batch resolution query** -- Before the message formatting loop, collect all unique sender UUIDs and resolve them in one query:
   ```python
   sender_ids = {msg.meta_data.get("_from_agent") for msg in pending_messages if msg.meta_data}
   uuid_ids = [s for s in sender_ids if s and "-" in s and len(s) == 36]
   if uuid_ids:
       result = await session.execute(
           select(AgentExecution.agent_id, AgentExecution.agent_display_name)
           .where(AgentExecution.agent_id.in_(uuid_ids))
       )
       sender_name_map = {row.agent_id: row.agent_display_name for row in result}
   ```

**Files impacted:**
- `src/giljo_mcp/services/message_service.py` -- Enrich at send (line ~239) and receive (line ~1086)

---

### Feature 5: Sleep-Wake Settings UI

**Concept:** Add a "Multi-Terminal Polling" section to the Context Protocol settings with toggles, interval selector, and token cost tooltip.

**Implementation:**

Following the existing pattern in `ContextPriorityConfig.vue`:

```
[Multi-Terminal Polling]

  Sleep-Wake Cycle    [OFF/ON toggle]  (i) "When enabled, agents will periodically
                                           wake after completing to check for new
                                           messages. Each wake cycle costs ~500-1000
                                           tokens per agent."

  Check Interval      [5 min v]        Dropdown: 1, 2, 5, 10, 15, 30 minutes

  Max Cycles          [6 v]            Dropdown: 1, 3, 6, 12, 20

  Applies To          (o) Orchestrator only
                      (o) All agents        (i) "Applying to all agents increases
                                                 token usage proportionally to the
                                                 number of spawned agents."
```

**Files impacted:**
- `frontend/src/components/settings/ContextPriorityConfig.vue` or new sibling component
- `api/endpoints/user_settings.py` -- Persist sleep_wake config
- Backend settings retrieval in protocol_builder.py

---

## Token Cost Analysis

| Action | Estimated Token Cost | Notes |
|--------|---------------------|-------|
| Single wake cycle (receive_messages + get_workflow_status) | ~500-1,000 tokens | Two tool calls + LLM reasoning |
| Reactivation cycle (reactivate + receive + plan + work + complete) | ~2,000-5,000 tokens | Full work resumption |
| Orchestrator polling (5 min interval, 6 cycles = 30 min) | ~3,000-6,000 tokens | If no action needed each cycle |
| All-agents polling (5 agents x 6 cycles) | ~15,000-30,000 tokens | Worst case, all agents polling |

**Mitigation:** Default `enabled=false`. User must explicitly opt in. Tooltip clearly states token cost. `max_cycles` bounds total spend.

---

## Implementation Priority

| Phase | Feature | Effort | Impact |
|-------|---------|--------|--------|
| **Phase 1** | Display name in messages (Feature 4) | Small | Quality-of-life fix, no architecture change |
| **Phase 2** | `reactivate_job` tool (Feature 2) | Medium | Enables the core capability |
| **Phase 3** | TODO append mode (Feature 3) | Small | Required for clean reactivation UX |
| **Phase 4** | Sleep-wake prompt protocol (Feature 1) | Medium | The coordination pattern itself |
| **Phase 5** | Settings UI (Feature 5) | Medium | User-facing configurability |

Phases 1-3 can be implemented independently. Phases 4-5 depend on Phase 2.

---

## Message Routing Consideration: Completed Agent Name Resolution

Currently, `send_message(to_agents=["Code Analyzer"])` resolves display names by querying only active executions (`status IN ("waiting", "working", "blocked")`). A completed agent is invisible by name.

**For sleep-wake to work**, agents must be addressable by name even after completion. Two options:

- **Option A:** Expand the name resolution query to include `"complete"` status (risk: messages to truly-done agents that won't wake up)
- **Option B:** Only expand when `sleep_wake.enabled=true` in user settings (clean gate)

**Recommendation:** Option B -- gate expanded name resolution behind the sleep-wake toggle. When sleep-wake is off, completed agents remain invisible by name (current behavior). When on, they become addressable because they are expected to wake and check.

**File impacted:** `src/giljo_mcp/services/message_service.py:201-202` -- the status filter in name resolution query.

---

## Summary of All Files Impacted

| File | Changes |
|------|---------|
| `src/giljo_mcp/services/orchestration_service.py` | `reactivate_job()` method, `report_progress()` append mode |
| `src/giljo_mcp/services/message_service.py` | Display name enrichment (send + receive), name resolution query expansion |
| `src/giljo_mcp/services/protocol_builder.py` | Sleep-wake protocol section injection |
| `src/giljo_mcp/tools/tool_accessor.py` | `reactivate_job()` delegation, `report_progress()` pass-through |
| `src/giljo_mcp/models/agent_identity.py` | No schema changes needed (status values already support the transitions) |
| `api/endpoints/mcp_http.py` | `reactivate_job` tool definition + handler, `report_progress` schema update |
| `api/endpoints/user_settings.py` | `sleep_wake` config persistence |
| `frontend/src/components/settings/` | Sleep-wake toggle UI with tooltips |
