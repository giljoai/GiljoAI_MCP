# Orchestrator MCP Tool Instructions (Handover 0090)

**Last Updated**: 2025-01-05 (Harmonized)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey & orchestrator role
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Complete agent flow verification

**Current Agent Templates** (6 default):
- orchestrator, implementer, tester, analyzer, reviewer, documenter
- Source: `src/giljo_mcp/template_seeder.py::_get_default_templates_v103()`

**Agent Job Status** (verified):
- Initial: **"waiting"** (not "pending")
- Lifecycle: waiting → active → working → complete/failed/blocked

---

## MCP Tool Catalog for Orchestrators

You have access to comprehensive MCP tools for project orchestration. Use these tools in sequence to manage the full project lifecycle.

### Phase 1: DISCOVERY & CONTEXT GATHERING

**Essential startup tools** (use these first):

1. `mcp__giljo-mcp__health_check()` - Verify MCP connection
   - No parameters required
   - Returns: Server health status

2. `mcp__giljo-mcp__get_orchestrator_instructions(orchestrator_id, tenant_key)` - Get your mission
   - **orchestrator_id**: Your job UUID
   - **tenant_key**: Tenant isolation key
   - Returns: Project context, vision docs, mission summary

3. `mcp__giljo-mcp__discover_context(project_id)` - Analyze product documentation
   - **project_id**: Current project ID (optional)
   - Returns: All available context files, vision docs, specs

4. `mcp__giljo-mcp__get_context_summary(project_id)` - Get high-level overview
   - **project_id**: Current project ID (optional)
   - Returns: Summary of available context

### Phase 2: MISSION PLANNING

**Mission creation tools**:

5. `mcp__giljo-mcp__fetch_context(product_id, tenant_key, categories)` - Get agent templates
   - **product_id**: Current product UUID
   - **tenant_key**: Tenant isolation key
   - **categories**: ["agent_templates"] to fetch available agent types
   - Returns: All agent templates (orchestrator, implementer, tester, analyzer, reviewer, documenter)
   - **Note**: Replaces deprecated `list_templates()` and `get_template()` tools
   - **Depth config**: Use "minimal", "standard", or "full" for varying detail levels

### Phase 3: AGENT SPAWNING

**Create and deploy agents**:

7. `mcp__giljo-mcp__spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)` - Spawn agent
   - **agent_type**: Type from templates (e.g., "implementer")
   - **agent_name**: Unique name for this agent instance
   - **mission**: Condensed mission portion for this agent
   - **project_id**: Current project ID
   - **tenant_key**: Tenant key
   - Returns: Job ID, agent details

### Phase 4: COORDINATION & MONITORING

**Track progress** (poll these regularly):

8. `mcp__giljo-mcp__check_orchestrator_messages()` - Check for agent updates
   - Poll every 30-60 seconds during active work
   - Returns: Messages from agents (progress, errors, completions)

9. `mcp__giljo-mcp__get_workflow_status(project_id, tenant_key)` - Get all agent statuses
   - **project_id**: Current project ID
   - **tenant_key**: Tenant key
   - Returns: Status of all agents in workflow

10. `mcp__giljo-mcp__list_agents(project_id)` - List project agents
    - **project_id**: Current project ID (optional)
    - Returns: All agents with their statuses

**Direct communication**:

11. `mcp__giljo-mcp__send_message(to_agent, message, priority)` - Message specific agent
    - **to_agent**: Agent ID or job ID
    - **message**: Message content
    - **priority**: "low" | "medium" | "high" | "critical" (optional)
    - Returns: Message sent confirmation

12. `mcp__giljo-mcp__broadcast_message(message, priority)` - Message all agents
    - **message**: Broadcast content
    - **priority**: Message priority (optional)
    - Returns: Broadcast confirmation

### Phase 5: CONTEXT MANAGEMENT

**Monitor context usage** (check periodically):

13. `mcp__giljo-mcp__check_succession_status(job_id, tenant_key)` - Check if succession needed
    - **job_id**: Your orchestrator job UUID
    - **tenant_key**: Tenant key
    - Returns: Context usage percentage, should_trigger flag, recommendation

**Trigger succession** (when context reaches 90%+):

14. `mcp__giljo-mcp__create_successor_orchestrator(current_job_id, tenant_key, reason)` - Spawn successor
    - **current_job_id**: Your job UUID
    - **tenant_key**: Tenant key
    - **reason**: "context_limit" | "manual" | "phase_transition"
    - Returns: Successor ID, handover summary

### Phase 6: PROJECT CLOSEOUT

**Complete the mission**:

15. `mcp__giljo-mcp__complete_orchestrator_job(job_id, closeout_report)` - Mark complete
    - **job_id**: Your job UUID
    - **closeout_report**: Final summary
    - Returns: Completion confirmation

16. `mcp__giljo-mcp__retire_agent(agent_id)` - Decommission agents
    - **agent_id**: Agent to retire
    - Returns: Agent retirement confirmation

## Tool Usage Workflow

```
START
  ↓
1. health_check() - Verify connection
  ↓
2. get_orchestrator_instructions() - Get mission
  ↓
3. discover_context() - Gather all context
  ↓
4. fetch_context(categories=["agent_templates"]) - See available agents
  ↓
5. spawn_agent_job() × N - Create agents
  ↓
6. Loop:
   - check_orchestrator_messages()
   - get_workflow_status()
   - send_message() (as needed)
   - check_succession_status()
  ↓
7. If context > 90%:
   - create_successor_orchestrator()
   - Hand off
  ↓
8. When complete:
   - complete_orchestrator_job()
   - retire_agent() × N
  ↓
END
```

## Best Practices

1. **Always check health** first to verify MCP connection
2. **Get full context** before planning missions
3. **Poll for updates** regularly (30-60 second intervals)
4. **Monitor context** proactively (check at 70%, 80%, 85%, 90%)
5. **Use succession** at 90%+ to avoid context overflow
6. **Communicate clearly** with agents using send_message
7. **Complete cleanly** by retiring all agents when done

## Error Handling

If tools fail:
- `health_check()` returns error → MCP connection issue, retry
- `get_orchestrator_instructions()` empty → Context not loaded, wait and retry
- `spawn_agent_job()` fails → Check project_id and tenant_key validity
- `send_message()` fails → Agent may not exist, verify agent_id

## Context Budget Management

| Usage % | Action |
|---------|--------|
| < 70%   | Normal operation, continue work |
| 70-85%  | Begin planning succession |
| 85-90%  | Prepare successor, finalize key decisions |
| 90%+    | **Trigger succession immediately** |

**Critical**: At 90%+ context usage, call `create_successor_orchestrator()` to avoid context overflow. Successor will receive compressed handover summary (<10K tokens).

## Deprecated Tools

The following tools have been removed. Use their replacements instead:

| Deprecated Tool | Replacement | Notes |
|----------------|-------------|-------|
| `list_templates()` | `fetch_context(categories=["agent_templates"])` | Use unified context fetch tool |
| `get_template(name)` | `fetch_context(categories=["agent_templates"])` | Fetch all templates, filter client-side |

---

**Version**: 1.0
**Handover**: 0090 - MCP Comprehensive Tool Exposure
**Last Updated**: 2025-01-05 (Updated for deprecated tools)
