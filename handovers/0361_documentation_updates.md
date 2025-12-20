# Handover 0361: Documentation Updates for 0366 Identity Model & Alpha Trial Feedback

**Date**: 2025-12-20  
**Status**: READY FOR IMPLEMENTATION  
**Agent**: Documentation Manager  
**Estimated Effort**: 2–3 hours  
**Depends On**: 0350 series (context tools), 0345/0347 series (context depth), 0364 (protocol message handling), 0366a/b/c (identity refactor), 0356 (tenant/identity consistency)

---

## Context

The original 0361 handover highlighted several documentation gaps:
- Confusing `fetch_context` syntax (arrays vs single category strings).
- Missing guidance on message polling frequency and patterns.
- Lack of a central reference for which MCP tools require `tenant_key`.
- No concise protocol quick reference for agents.
- Undocumented message content conventions.

Since then:
- **0364** solidified the agent protocol and message handling behavior.
- **0366a/b/c** introduced the **AgentJob/AgentExecution identity model** and standardized MCP tool parameters (`job_id` vs `agent_id`).
- **0356** (this series) focuses on aligning tool signatures and schemas with that model.

This updated 0361 handover now has two jobs:
1. **Fix the original alpha-trial documentation issues.**
2. **Update all examples and reference docs to use the 0366 identity and tenant_key semantics.**

---

## Documentation Problems (Updated View)

### 1. `fetch_context` Syntax & Semantics

Current reality (from the code):

```python
async def fetch_context(
    product_id: str,
    tenant_key: str,
    category: str,
    project_id: Optional[str] = None,
    depth_config: Optional[dict] = None,
    apply_user_config: bool = True,
    format: str = "structured",
    db_manager: Optional[DatabaseManager] = None,
) -> dict[str, Any]:
```

Key points:
- **`category` is singular** – one category per call (`"product_core"`, `"tech_stack"`, etc.).
- `tenant_key` is always required for context access.
- `project_id` is optional and scopes project‑level context when provided.

The alpha trial docs still show:
- Array notation (`categories=[...]`).
- Ambiguous or missing `tenant_key` usage.

### 2. Agent Lifecycle & Polling Guidance

We now have:
- A clear protocol from 0364 / `orchestration_service.py`:
  - Initialization → mission fetch → work → progress → messaging → completion.
- A developer guide (`docs/developer_guides/agent_monitoring_developer_guide.md`) that describes monitoring patterns.

But:
- Documentation is scattered across multiple files.
- Examples still use pre‑0366 identifiers (`job_id` in places that should now be `agent_id`).
- There is no single quick reference that shows recommended polling intervals and when to call `receive_messages()` vs `list_messages()`.

### 3. `tenant_key` Requirements

Post‑0366:
- All stateful MCP tools should require `tenant_key` (0356).
- Some legacy docs still imply it’s optional or rely on implicit context.

We need a **canonical table** that says:
- Tool name.
- Identity parameters (`agent_id`, `job_id`, `project_id`).
- Whether `tenant_key` is required.
- Short description of what the tool does.

### 4. Identity Semantics in Docs

Many existing documents:
- Use `job_id` ambiguously (sometimes work, sometimes worker).
- Refer to `orchestrator_id` instead of `agent_id`.

After 0366:
- This is no longer acceptable – we must document:
  - `job_id` = work order (AgentJob).
  - `agent_id` = executor instance (AgentExecution).

---

## Objectives

1. **Correct and clarify `fetch_context` documentation** (syntax + semantics).
2. **Create or update the MCP protocol quick reference** to reflect:
   - 0364 protocol phases.
   - 0366 identity semantics (`agent_id` vs `job_id`).
   - `tenant_key` requirements.
3. **Provide a clear table of MCP tools and their required parameters** (including tenant_key).
4. **Standardize message content conventions and polling guidance** in the docs.

---

## Scope

### In Scope

1. `docs/api/context_tools.md`
   - Fix `fetch_context` examples to use:
     - `category="product_core"` (singular).
     - Explicit `tenant_key`.
   - Add a short explanation of context categories and how they map to `field_priority_config`.

2. `docs/architecture/messaging_contract.md`
   - Update message routing examples to use `agent_id`.
   - Document message types (`direct`, `progress`, `system`, etc.) and content conventions.
   - Clarify how `send_message` and `receive_messages` behave post‑0366.

3. `docs/components/STAGING_WORKFLOW.md`
   - Update orchestrator examples to:
     - Use `agent_id` for orchestrator executions.
     - Reference the 0364 protocol for execution‑phase behavior.

4. **New Quick Reference**  
   - `docs/guides/mcp_protocol_quick_reference.md` (new file)
   - One‑page cheat sheet covering:
     - Agent lifecycle phases.
     - Common MCP calls and parameter sets.
     - Polling recommendations.
     - Identity semantics.
     - `tenant_key` rules.

5. `CLAUDE.md` (or equivalent root developer guide)
   - Update snippets and references to:
     - Clarify `agent_id` vs `job_id`.
     - Link to the new quick reference.

### Out of Scope

- Changing the underlying protocol behavior (covered by 0364).
- Changing the MCP tools’ actual signatures (covered by 0356/0360/0366c).

---

## Detailed Work Plan

### 1. `fetch_context` Documentation Fix (30–45 min)

File: `docs/api/context_tools.md`

Tasks:
1. Replace all array‑style examples:
   - From: `categories=["product_core", "tech_stack"]`
   - To: separate examples with single `category` value:

   ```python
   # Example: get core product context
   await fetch_context(
       product_id=PRODUCT_ID,
       tenant_key=TENANT_KEY,
       category="product_core",
       format="structured",
   )
   ```

2. Explicitly document parameters:
   - `product_id`, `tenant_key`, `category`, `project_id`, `depth_config`, `apply_user_config`, `format`.
   - Explain that multi‑category usage should be done by *multiple calls* or by dedicated orchestration helpers.

3. Add a short “anti‑pattern” note:
   - Calling `fetch_context` with arrays will result in validation errors.

### 2. MCP Protocol Quick Reference (45–60 min)

File: `docs/guides/mcp_protocol_quick_reference.md` (NEW)

Content sections:

1. **Identity Model**
   - `job_id` (AgentJob) vs `agent_id` (AgentExecution).
   - Short table mapping common tools to which identifier they require.

2. **Core Lifecycle Calls**
   - `get_agent_mission(agent_id, tenant_key)`
   - `get_orchestrator_instructions(agent_id, tenant_key)`
   - `report_progress(job_id or agent_id, progress, tenant_key)` – clarify which we are using in the current implementation and how it maps to job/execution.
   - `receive_messages(agent_id, tenant_key, ...)`
   - `send_message(to_agent_id, content, project_id, tenant_key, ...)`

3. **Polling Guidance**
   - Suggested pattern:
     - On startup: `receive_messages()` once.
     - Between major steps: `report_progress()` followed by `receive_messages()`.
     - Avoid tight loops – recommend minimum intervals.

4. **Tenant Key Rules**
   - Tools that **must** receive `tenant_key`.
   - Reminder: all MCP HTTP traffic is per‑tenant; never omit `tenant_key` in user‑facing examples.

5. **Message Content Conventions**
   - Recommended prefixes:
     - `READY:`, `BLOCKER:`, `COMPLETE:`, `QUESTION:`.
   - Note they are conventions, not protocol‑enforced, but strongly recommended for human readability.

### 3. Messaging Contract Update (30–45 min)

File: `docs/architecture/messaging_contract.md`

Tasks:
1. Update identity references:
   - Replace `job_id` used as “recipient” with `agent_id`.
   - Clarify that message routing is via `MessageService0366b` and uses `AgentExecution.agent_id`.
2. Clarify message types and counters:
   - Describe “Messages Waiting/Sent/Read” in terms of the new identity model.
   - Link to the alpha‑trial message counter fixes (0362) where appropriate.
3. Add a small section on **team messaging**:
   - Reference `get_team_agents()` (0360) once implemented.

### 4. Staging Workflow & Orchestrator Docs (30–45 min)

File: `docs/components/STAGING_WORKFLOW.md`

Tasks:
1. Update orchestrator references to:
   - Use `agent_id` for orchestrator execution.
   - Use `job_id` for the orchestrator job/work.
2. Incorporate 0364’s “execution‑phase monitoring” step:
   - Link to 0365 handover for orchestrator succession behavior.
3. Ensure examples of thin prompts:
   - Instruct orchestrators to call `get_orchestrator_instructions(agent_id, tenant_key)` with the correct IDs.

---

## Tool & Parameter Reference Table

As part of this handover, create a concise table (in the quick reference) like:

| Tool | Identity Params | Requires `tenant_key`? | Purpose |
|------|-----------------|------------------------|---------|
| `get_agent_mission` | `agent_id` | Yes | Fetch agent mission + protocol |
| `get_orchestrator_instructions` | `agent_id` | Yes | Fetch orchestrator staging/execution instructions |
| `report_progress` | `job_id` (current), `tenant_key` | Yes | Report job/execution progress (see notes) |
| `receive_messages` | `agent_id` | Yes | Retrieve pending messages for an execution |
| `send_message` | `to_agent_id`, `project_id` | Yes | Send message to one or more agents |
| `fetch_context` | `product_id`, `category` | Yes | Fetch prioritized context slice |

The exact list should be derived from the MCP schemas after 0356/0360/0366c alignment.

---

## Success Criteria

1. All examples of `fetch_context` in the docs:
   - Use `category` (singular).
   - Pass `tenant_key`.
   - Do not show array syntax.

2. There is a **single quick reference page** that:
   - Correctly describes the 0364 protocol and 0366 identity semantics.
   - Shows recommended polling patterns and message conventions.

3. Messaging docs (`messaging_contract.md`) align with:
   - `MessageService0366b` behavior.
   - The identity and tenant model from 0366.

4. Staging/orchestrator docs reference:
   - `agent_id` vs `job_id` correctly.
   - The execution‑phase monitoring behavior from 0364/0365.

5. No documentation remains that:
   - Uses `categories=[...]` for `fetch_context`.
   - Treats `job_id` as both work and worker.
   - Omits `tenant_key` from MCP tool examples.

---

## Developer Checklist

- [ ] Update `docs/api/context_tools.md` for `fetch_context`.
- [ ] Create or update `docs/guides/mcp_protocol_quick_reference.md`.
- [ ] Update `docs/architecture/messaging_contract.md` with identity & tenant semantics.
- [ ] Update `docs/components/STAGING_WORKFLOW.md` to reference 0364/0365 and `agent_id`.
- [ ] Sweep `CLAUDE.md` and other entry‑point docs for outdated examples.
- [ ] Run a quick doc search (`rg "categories\[" docs` and `rg "orchestrator_id" docs`) to ensure no old patterns remain.

Once implemented, the documentation will match the current server behavior, guiding alpha‑trial and production users toward the correct use of `fetch_context`, identity parameters, and tenant_key across the MCP toolset.

