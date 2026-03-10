# Handover 0284: Address get_available_agents MCP Tool

**Date**: 2025-12-02
**Status**: Parked for future implementation
**Priority**: Medium
**Related**: Handover 0246c (Dynamic Agent Discovery)

---

## Context

The `get_available_agents` MCP tool was introduced in Handover 0246c as part of the token reduction strategy (71% savings). It provides dynamic agent discovery without embedding templates in orchestrator prompts.

---

## Current Implementation

**Location**: `src/giljo_mcp/tools/agent_discovery.py:69-150` and `src/giljo_mcp/tools/orchestration.py:1248-1301`

**Purpose**:
- Returns list of available agent templates with version metadata
- Orchestrators call this to discover which agents can be spawned
- Part of thin-client architecture (not embedded in prompts)

**Key Feature - Version Validation**:
The tool returns `version_tag` and `expected_filename` for each agent template. This allows orchestrators to verify that:
1. Agent template on server (e.g., `implementer_1.2.0.md`)
2. Matches imported agent template in `./.claude/agents` or `~/.claude/agents` on user's PC

**Validation Workflow**:
```
Orchestrator calls get_available_agents()
  → Receives: implementer v1.2.0, expected_filename: implementer_1.2.0.md
  → Checks: Does ~/.claude/agents/implementer_1.2.0.md exist?
  → If NO: Warn user "Templates updated on server but not imported to Claude"
  → If YES: Proceed with spawning
```

This is the **reference architecture** for ensuring server-client template synchronization.

---

## Issues to Address

### 1. MCP Tool Description Enhancement

**Current description** (in `mcp_http.py`):
- Tool is NOT exposed via HTTP MCP endpoint
- Only available via internal API calls
- No description in `api/endpoints/mcp_http.py` tool list

**Action Needed**:
- Decide if this should be exposed via MCP HTTP endpoint
- If exposed, add to `mcp_http.py` tool list with enhanced description
- If internal-only, document this clearly

### 2. WHO Calls This Tool

**Question**: Orchestrator only, or can agents call it?

**Current assumption**: Orchestrator only (for planning which agents to spawn)

**Action Needed**:
- Clarify in description: "Called by: Orchestrator only during staging phase"
- Add workflow position: "Call after get_orchestrator_instructions(), before spawn_agent_job()"

### 3. WHEN to Call

**Action Needed**:
- Add explicit timing guidance: "Call during project staging to discover available specialists"
- Add validation workflow: "Use version_tag to verify imported templates match server versions"

### 4. Version Mismatch Handling

**Question**: What should orchestrator do if version mismatch detected?

**Possible actions**:
- a) Warn user via message/WebSocket
- b) Block spawning until templates imported
- c) Auto-download templates to ~/.claude/agents
- d) Proceed with warning (best effort)

**Action Needed**:
- Define and document expected behavior
- Implement validation logic in orchestrator workflow

---

## Proposed Enhanced Description

**If exposed via MCP HTTP**:

```
"Discover available agent templates with version metadata. Called by: Orchestrator only during staging phase (after get_orchestrator_instructions, before spawn_agent_job). Returns agent list with version_tag and expected_filename for validation. Use to verify server templates match imported templates in ~/.claude/agents or ./.claude/agents. If version mismatch detected, prompt user to import updated templates via /gil_import_productagents or /gil_import_personalagents. Token savings: 71% vs embedded templates (Handover 0246c)."
```

---

## Related Work

**Handover 0246c**: Dynamic Agent Discovery (token reduction strategy)
**Handover 0084b**: Agent template import slash commands
**Handover 0093**: Slash command setup tool

---

## Next Steps

1. Decide: Expose via MCP HTTP endpoint or keep internal-only?
2. If exposed: Add to `mcp_http.py` tool list
3. Enhance description with WHO/WHEN/validation workflow
4. Document version mismatch handling strategy
5. Test version validation in orchestrator workflow

---

## Parking Reason

**Why parked**: Focusing first on core 5 orchestration tools that are already exposed via MCP HTTP. This tool requires architectural decision (expose vs internal-only) before description enhancement.

**Return when**: Core tool descriptions complete and tested.
