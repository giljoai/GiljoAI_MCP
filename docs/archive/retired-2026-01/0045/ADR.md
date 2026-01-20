# Architecture Decision Records - Multi-Tool Agent Orchestration

**Handover**: 0045
**Version**: 3.1.0
**Date**: 2025-10-25

---

## ADR-0045-001: Use Existing `preferred_tool` Field in AgentTemplate

**Date**: 2025-10-25
**Status**: Accepted

### Context

Need to configure which AI tool each agent should use. Two options:
1. Add new `tool` field to Agent model
2. Use existing `preferred_tool` field in AgentTemplate model

### Decision

Use existing `preferred_tool` field in AgentTemplate model.

### Rationale

**Advantages**:
- Templates already exist in database (Handover 0041)
- Tool selection is a template concern (behavioral configuration)
- Avoids database migration to Agent table for tool selection
- Tool can be changed per-template without affecting agents
- Consistent with template-based configuration pattern

**Disadvantages**:
- Requires template resolution for every agent spawn
- Cannot override tool per-agent instance (must use template)

**Alternatives Considered**:
- **Option A**: Add `tool` field to Agent model
  - Rejected: Duplicates template configuration, requires migration
- **Option B**: Store tool in `meta_data` JSONB field
  - Rejected: Unstructured, no database constraints

### Consequences

- ✅ No database migration needed for tool selection
- ✅ Tool configuration centralized in templates
- ✅ Tool can be changed by updating template (affects future agents)
- ❌ Cannot override tool per-agent without creating new template
- ❌ Template must be resolved before routing agent spawn

### Implementation

```python
# Get template
template = await self._get_agent_template(role, project_id)

# Route based on preferred_tool
if template.preferred_tool == "claude":
    return await self._spawn_claude_code_agent(...)
elif template.preferred_tool == "codex":
    return await self._spawn_generic_agent(..., tool="codex")
```

---

## ADR-0045-002: Option A (Dual Record) Architecture for Agent-Job Linking

**Date**: 2025-10-25
**Status**: Accepted

### Context

Need to link Agent records with MCPAgentJob records for status synchronization. Three architecture options:

**Option A: Dual Record** - Create both Agent + MCPAgentJob, link via `Agent.job_id`
**Option B: Single Record** - Use only MCPAgentJob, deprecate Agent model
**Option C: Join Table** - Separate AgentJobMapping table for many-to-many relationship

### Decision

Option A: Dual Record architecture with `Agent.job_id` field linking to `MCPAgentJob.id`.

### Rationale

**Advantages**:
- Preserves existing Agent model (backward compatibility)
- Clean separation: Agent = identity, MCPAgentJob = work tracking
- Minimal migration (add `job_id` field, no data loss)
- One-to-one relationship (simplest to query)
- No impact on existing code using Agent model

**Disadvantages**:
- Two database writes per agent spawn
- Potential for desynchronization if not careful
- Redundant data (agent_id in both tables)

**Alternatives Considered**:
- **Option B (Single Record)**: Merge into MCPAgentJob only
  - Rejected: Would require massive refactoring, breaks existing code
- **Option C (Join Table)**: Separate mapping table
  - Rejected: Overkill for one-to-one relationship, adds query complexity

### Consequences

- ✅ Existing Agent queries continue to work
- ✅ Can query jobs independently of agents
- ✅ Clear ownership: Agent owns identity, Job owns work status
- ❌ Must maintain synchronization (Agent.status ↔ Job.status)
- ❌ Two database writes increase latency slightly

### Implementation

```python
# Create Agent
agent = Agent(
    id=generate_uuid(),
    name="Implementer-001",
    mode="codex",
    job_id=None  # Set after job created
)

# Create Job
job = await agent_job_manager.create_job(
    agent_id=agent.id,
    mission="...",
    status="waiting_acknowledgment"
)

# Link Agent → Job
agent.job_id = job.id
await session.commit()
```

---

## ADR-0045-003: Event-Driven Sync (Not Polling) for Agent-Job Status

**Date**: 2025-10-25
**Status**: Accepted

### Context

Need to synchronize status between Agent and MCPAgentJob. Two approaches:
1. **Event-Driven**: Update Agent.status when Job.status changes (and vice versa)
2. **Polling**: Background task periodically syncs status

### Decision

Event-driven synchronization using database triggers and application-level callbacks.

### Rationale

**Advantages**:
- Real-time synchronization (no delay)
- No polling overhead (CPU/memory)
- Simpler implementation (fewer moving parts)
- Guaranteed consistency (synchronous updates)

**Disadvantages**:
- Tight coupling between Agent and Job updates
- Transaction failures affect both records

**Alternatives Considered**:
- **Polling approach**: Background task syncs every 30 seconds
  - Rejected: Delay in status updates, wasteful CPU usage

### Consequences

- ✅ Instant status synchronization
- ✅ No background tasks needed
- ✅ Lower resource usage
- ❌ Requires careful transaction management
- ❌ Failure in one update can cascade

### Implementation

```python
async def complete_job(self, job_id, summary):
    """Complete job and update linked agent."""
    async with self.db_manager.get_session_async() as session:
        # Update job
        job = await session.get(MCPAgentJob, job_id)
        job.status = "completed"
        job.summary = summary

        # Update linked agent (event-driven sync)
        agent = await session.get(Agent, job.agent_id)
        agent.status = "decommissioned"

        await session.commit()

        # Broadcast WebSocket event
        await self.websocket_manager.broadcast_event(...)
```

---

## ADR-0045-004: Graceful Template Export Degradation

**Date**: 2025-10-25
**Status**: Accepted

### Context

Template export for Claude Code may fail due to:
- Template content > 100KB
- Template has invalid variables
- Template missing required fields

Two approaches:
1. **Strict**: Fail entire export if any template invalid
2. **Graceful**: Skip invalid templates, export valid ones with warnings

### Decision

Graceful degradation with warnings.

### Rationale

**Advantages**:
- User gets partial export (better than nothing)
- Warnings identify which templates failed and why
- Most common case: 5/6 templates valid → user gets 5 templates
- User can fix invalid templates and re-export

**Disadvantages**:
- User may not notice warnings (if not reading carefully)
- Partial export may cause confusion

**Alternatives Considered**:
- **Strict validation**: Export fails if any template invalid
  - Rejected: Poor UX (all-or-nothing approach)

### Consequences

- ✅ Users always get some templates (even if not all)
- ✅ Clear error messages for invalid templates
- ✅ Can export before fixing all templates
- ❌ User must read warnings to know about failures
- ❌ Partial export may be incomplete

### Implementation

```python
async def export_templates_for_claude_code(self, tenant_key):
    """Export templates with graceful degradation."""
    templates = await self.get_all_templates(tenant_key)

    valid_templates = []
    warnings = []

    for template in templates:
        try:
            # Validate template
            self._validate_template(template)
            valid_templates.append(template)
        except ValidationError as e:
            warnings.append({
                "template": template.name,
                "error": str(e)
            })

    # Export valid templates (even if some failed)
    export_zip = self._create_export_zip(valid_templates)

    return {
        "export_id": generate_uuid(),
        "templates_count": len(valid_templates),
        "warnings": warnings,
        "download_url": f"/api/v1/exports/{export_id}/download"
    }
```

---

## ADR-0045-005: MCP as Universal Coordination Protocol

**Date**: 2025-10-25
**Status**: Accepted

### Context

Need coordination protocol for agents across different AI tools (Claude Code, Codex, Gemini). Options:
1. **Tool-Specific**: Different coordination for each tool (Claude uses X, Codex uses Y)
2. **Universal MCP**: Same MCP protocol for all tools

### Decision

MCP as universal coordination protocol for all tools.

### Rationale

**Advantages**:
- Single protocol to learn and maintain
- Tool-agnostic (works with any AI coding tool)
- Consistent experience for users
- Easy to add new tools (just implement MCP integration)
- Code reuse (same MCP endpoints for all tools)

**Disadvantages**:
- May not leverage tool-specific features
- One-size-fits-all may not be optimal for each tool

**Alternatives Considered**:
- **Tool-Specific Protocols**: Claude uses MCP, Codex uses custom protocol
  - Rejected: Fragmentation, maintenance burden, poor UX

### Consequences

- ✅ All tools use same 7 MCP coordination tools
- ✅ Adding new tool requires only 1 integration point (MCP)
- ✅ Users learn MCP once, works everywhere
- ❌ Cannot leverage tool-specific coordination features
- ❌ May need workarounds for tool limitations

### Implementation

All tools use these MCP endpoints:
- `get_pending_jobs`
- `acknowledge_job`
- `report_progress`
- `get_next_instruction`
- `complete_job`
- `report_error`
- `send_message`

**Hybrid mode** (Claude Code): Automatic MCP calls
**Legacy CLI mode** (Codex/Gemini): Manual MCP calls via HTTP

---

## ADR-0045-006: Add `mode` Field to Track Agent's AI Tool

**Date**: 2025-10-25
**Status**: Accepted

### Context

After routing agent to tool, need to track which tool the agent is using. Options:
1. Store in `meta_data` JSONB field
2. Add dedicated `mode` VARCHAR field

### Decision

Add dedicated `mode` VARCHAR(20) field to Agent model.

### Rationale

**Advantages**:
- Typed field (database constraint: claude | codex | gemini)
- Indexed for fast queries (filter by tool)
- Easy to query: `SELECT * FROM agents WHERE mode = 'codex'`
- No JSON parsing overhead
- Clear schema (self-documenting)

**Disadvantages**:
- Requires database migration (add column)
- Additional storage (20 bytes per agent)

**Alternatives Considered**:
- **meta_data JSONB**: Store as `{"tool": "codex"}`
  - Rejected: No type safety, no indexes, harder to query

### Consequences

- ✅ Fast queries by tool
- ✅ Database-level validation (enum constraint)
- ✅ Easy reporting and analytics
- ❌ Database migration required
- ❌ Schema change (minor)

### Implementation

```sql
-- Migration
ALTER TABLE agents
ADD COLUMN mode VARCHAR(20) DEFAULT 'claude';

CREATE INDEX idx_agent_mode ON agents(mode);
```

```python
# Usage
agent = Agent(
    name="Implementer-001",
    mode="codex",  # Tracked explicitly
    ...
)
```

---

## Summary

| ADR | Decision | Impact |
|-----|----------|--------|
| 001 | Use `preferred_tool` in AgentTemplate | Tool configuration in templates |
| 002 | Dual Record architecture (Agent + Job) | Minimal migration, backward compatible |
| 003 | Event-driven status sync | Real-time synchronization |
| 004 | Graceful template export degradation | Better UX, partial exports allowed |
| 005 | MCP as universal protocol | Single protocol for all tools |
| 006 | Add `mode` field to Agent | Explicit tool tracking with indexes |

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
