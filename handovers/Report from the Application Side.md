# Report: MCP Tool Usage in Agent Templates & Prompts

**Date**: 2025-12-16
**Status**: Research Complete
**Scope**: Templates and prompts ONLY (code is working)

---

## Executive Summary

Spawned agents have access to MCP tools but fail to use them because they don't recognize MCP tools as **native tool calls** (like Read, Write, Bash). Instead, agents attempt curl/HTTP requests or Python SDK calls.

**Root Cause**: The thin spawn prompt and agent templates use function-call syntax without explaining that MCP tools work exactly like Claude Code's built-in tools.

---

## Problem Statement

When agents are spawned via `spawn_agent_job`, they receive a thin prompt that says:

```
INSTRUCTIONS:
1. Fetch mission: get_agent_mission(agent_job_id='xxx', tenant_key='yyy')
2. Execute mission
3. Report progress: update_job_progress('xxx', percent, message)
4. Coordinate via: send_message(to_agent_id, content)
```

**Issues**:
1. No `mcp__giljo-mcp__` prefix on tool names
2. Function-call syntax looks like Python code
3. No explanation that these are native tool calls (like Read/Write/Bash)
4. Agent templates (`.claude/agents/*.md`) have ZERO MCP guidance

---

## Root Causes (Verified by Diagnostic Agent)

| Issue | Original Behavior | Expected Behavior |
|-------|-------------------|-------------------|
| Tool format | `mcp.call_tool("...")` Python syntax | Native tool call format |
| Access method | Agents tried curl/HTTP endpoints | "Use like Read, Write, Bash tools" |
| MCP prefix | `get_agent_mission()` | `mcp__giljo-mcp__get_agent_mission` |
| Agent templates | NO MCP guidance (0 mentions in 12 files) | Add MCP invocation section |

### Diagnostic Evidence

A diagnostic agent was spawned and confirmed:
- All 30+ GiljoAI MCP tools ARE available to subagents
- Health check succeeded (server v3.1.0, database connected)
- Tools work when called correctly as native tool calls

| Tool | Test Result |
|------|-------------|
| `mcp__giljo-mcp__get_agent_mission` | SUCCESS |
| `mcp__giljo-mcp__acknowledge_job` | SUCCESS |
| `mcp__giljo-mcp__report_progress` | SUCCESS |
| `mcp__giljo-mcp__complete_job` | SUCCESS |

---

## Files Requiring Updates

### Phase 1+1b: Thin Spawn Prompt (CRITICAL)

| File | Location | Change |
|------|----------|--------|
| `src/giljo_mcp/services/orchestration_service.py` | lines 394-410 | Fix thin_agent_prompt |
| `src/giljo_mcp/tools/orchestration.py` | lines 816-832 | Fix thin_agent_prompt (duplicate) |

**Current** (problematic):
```python
thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type})...

INSTRUCTIONS:
1. Fetch mission: get_agent_mission(agent_job_id='{agent_job_id}', tenant_key='{tenant_key}')
2. Execute mission
3. Report progress: update_job_progress('{agent_job_id}', percent, message)
4. Coordinate via: send_message(to_agent_id, content)
"""
```

**Fixed**:
```python
thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type})...

## MCP TOOLS (CRITICAL)
MCP tools are NATIVE tool calls, exactly like Read, Write, or Bash.
Do NOT use curl, HTTP requests, or Python imports.

## INSTRUCTIONS:
1. Fetch mission:
   Tool: mcp__giljo-mcp__get_agent_mission
   Parameters: {{"agent_job_id": "{agent_job_id}", "tenant_key": "{tenant_key}"}}

2. Execute mission tasks

3. Report progress:
   Tool: mcp__giljo-mcp__report_progress
   Parameters: {{"job_id": "{agent_job_id}", "progress": {{"percent": 50, "message": "..."}}}}

4. Complete job:
   Tool: mcp__giljo-mcp__complete_job
   Parameters: {{"job_id": "{agent_job_id}", "result": {{"summary": "..."}}}}
"""
```

### Phase 2: 6-Phase Protocol

| File | Location | Change |
|------|----------|--------|
| `src/giljo_mcp/services/orchestration_service.py` | lines 47-101 | Fix _generate_agent_protocol |

The `_generate_agent_protocol` function returns the 6-phase lifecycle in `get_agent_mission()` response. Currently uses function-call syntax.

**Current** (problematic):
```
report_progress(job_id="{job_id}", progress={...})
complete_job(job_id="{job_id}", result={...})
```

**Fixed**:
```
Tool: mcp__giljo-mcp__report_progress
Parameters: {"job_id": "{job_id}", "progress": {...}}

Tool: mcp__giljo-mcp__complete_job
Parameters: {"job_id": "{job_id}", "result": {...}}
```

### Phase 3: Agent Templates

| File | Change |
|------|--------|
| `.claude/agents/backend-integration-tester.md` | Add MCP guidance section |
| `.claude/agents/database-expert.md` | Add MCP guidance section |
| `.claude/agents/deep-researcher.md` | Add MCP guidance section |
| `.claude/agents/documentation-manager.md` | Add MCP guidance section |
| `.claude/agents/frontend-tester.md` | Add MCP guidance section |
| `.claude/agents/installation-flow-agent.md` | Add MCP guidance section |
| `.claude/agents/network-security-engineer.md` | Add MCP guidance section |
| `.claude/agents/orchestrator-coordinator.md` | Add MCP guidance section |
| `.claude/agents/system-architect.md` | Add MCP guidance section |
| `.claude/agents/tdd-implementor.md` | Add MCP guidance section |
| `.claude/agents/ux-designer.md` | Add MCP guidance section |
| `.claude/agents/version-manager.md` | Add MCP guidance section |

**Section to add** (after core identity/mission):

```markdown
## CRITICAL: MCP Tool Usage

MCP tools are **NATIVE tool calls**, exactly like Read, Write, Bash, or Glob.
Do NOT use curl, HTTP requests, or Python SDK calls.

### Getting Your Mission
```
Tool: mcp__giljo-mcp__get_agent_mission
Parameters:
  - agent_job_id: "your-job-id"
  - tenant_key: "your-tenant-key"
```

### Reporting Progress
```
Tool: mcp__giljo-mcp__report_progress
Parameters:
  - job_id: "your-job-id"
  - progress: {"percent": 50, "message": "Completed step X"}
```

### Completing Your Job
```
Tool: mcp__giljo-mcp__complete_job
Parameters:
  - job_id: "your-job-id"
  - result: {"summary": "...", "artifacts": [...]}
```
```

### Phase 4: Documentation Templates

| File | Change |
|------|--------|
| `docs/agent-templates/analyzer.md` | Fix mcp.call_tool examples |
| `docs/agent-templates/documenter.md` | Fix mcp.call_tool examples |
| `docs/agent-templates/implementer.md` | Fix mcp.call_tool examples |
| `docs/agent-templates/reviewer.md` | Fix mcp.call_tool examples |
| `docs/agent-templates/tester.md` | Fix mcp.call_tool examples |

**Change pattern**:
```python
# FROM:
mcp.call_tool("mcp__giljo_mcp__update_job_status", {
    "job_id": "your-job-id",
    "new_status": "active"
})

# TO:
Tool: mcp__giljo-mcp__acknowledge_job
Parameters:
  - job_id: "your-job-id"
  - agent_id: "your-agent-id"

NOTE: This is a NATIVE tool call (like Read/Write/Bash).
```

---

## Additional Finding: Naming Convention Inconsistency

**26 files** use underscore convention (`mcp__giljo_mcp__`) instead of hyphen (`mcp__giljo-mcp__`).

| Category | Files |
|----------|-------|
| Agent-facing | `api/endpoints/claude_export.py`, `api/endpoints/downloads.py` |
| Templates | `src/giljo_mcp/template_seeder.py`, `export_claude_templates.py` |
| Docs | `docs/agent-templates/*.md` (5 files), `docs/developer_guides/code_patterns.md` |
| Tests | Various test files |
| Historical | `handovers/completed/` files |

**Note**: This is a documentation/template issue. The code works with either convention.

---

## Implementation Order

1. **Phase 1+1b**: Fix thin spawn prompts (immediate impact)
2. **Phase 2**: Fix _generate_agent_protocol (mission response)
3. **Phase 3**: Add MCP guidance to `.claude/agents/*.md` (redundant protection)
4. **Phase 4**: Fix `docs/agent-templates/*.md` (consistency)

---

## Success Criteria

- [ ] Spawned agents call `mcp__giljo-mcp__get_agent_mission` natively (not curl/HTTP)
- [ ] No `mcp.call_tool()` Python examples in agent-facing templates
- [ ] `.claude/agents/*.md` templates include MCP guidance section
- [ ] Thin prompt includes explicit "native tool call" explanation

---

## Testing Plan

1. After Phase 1+1b: Spawn a test agent via Task tool, verify it uses native MCP calls
2. After Phase 2: Call `get_agent_mission` directly, verify protocol format is correct
3. After Phase 3: Spawn agent using `.claude/agents/` template, verify MCP usage
4. End-to-end: Full workflow with orchestrator spawning agents, confirm `workflow_status` shows "working"

---

## Estimated Effort

| Phase | Files | Estimate |
|-------|-------|----------|
| Phase 1+1b | 2 files | 15 min |
| Phase 2 | 1 function | 10 min |
| Phase 3 | 12 templates | 30 min |
| Phase 4 | 5 docs | 15 min |
| **Total** | **20 files** | **~1 hour** |

---

## Appendix: Diagnostic Agent Output

```
FINDINGS SUMMARY

Root Cause Confirmed

The original agents failed because:

| Issue         | Original Instructions                             | Corrected Instructions                            |
|---------------|---------------------------------------------------|---------------------------------------------------|
| Tool format   | Templates show mcp.call_tool("...") Python syntax | Explicit: "Call mcp__giljo-mcp__* as native tool" |
| Access method | Agents tried curl/HTTP endpoints                  | Told: "Use like Read, Write, Bash tools"          |
| Examples      | Abstract code snippets                            | Direct parameter examples                         |

Test Results

| Tool                              | Result     |
|-----------------------------------|------------|
| mcp__giljo-mcp__get_agent_mission | SUCCESS    |
| mcp__giljo-mcp__acknowledge_job   | SUCCESS    |
| mcp__giljo-mcp__report_progress   | SUCCESS    |
| mcp__giljo-mcp__complete_job      | SUCCESS    |
```

---

## Related Documentation

- Plan file: `C:\Users\giljo\.claude\plans\vivid-swinging-yao.md`
- Orchestrator workflow: `docs/ORCHESTRATOR.md`
- Thin client architecture: `docs/guides/thin_client_migration_guide.md`
- Agent templates: `.claude/agents/*.md`
