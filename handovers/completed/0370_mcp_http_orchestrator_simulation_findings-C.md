# Handover 0370: MCP-over-HTTP Orchestrator Simulation Findings

**Date**: 2025-12-21
**Status**: PAUSED - Awaiting Further Research
**Type**: Diagnostic / Research

---

## Context

Simulated a remote laptop connecting to GiljoAI MCP Server over HTTP to test the orchestrator startup sequence as documented in workflow slides (Slide2-4.JPG).

**Test Environment:**
- Server URL: `http://10.1.0.164:7272`
- Orchestrator ID: `60e8bd2b-64fb-41f0-80cb-08f5e8a309be`
- Project ID: `b934ec55-ed0e-4110-bb16-2210f5161e17`
- Tenant Key: `***REMOVED***`

---

## What Was Tested

### Startup Sequence (Steps 1-3 of 7)

| Step | Tool | Result |
|------|------|--------|
| 1 | `health_check()` | PASS - Server healthy, DB connected, v3.1.0 |
| 2 | `get_orchestrator_instructions()` | PASS - Identity, context instructions, agent templates returned |
| 3 | `fetch_context()` x3 | PASS - All 3 CRITICAL categories fetched |

### Steps NOT Tested (Paused Before)
- Step 4: `update_project_mission()` - Create mission plan
- Step 5: `spawn_agent_job()` - Spawn specialist agents
- Step 6: `send_message()` - Broadcast STAGING_COMPLETE
- Step 7: Execution phase monitoring

---

## Findings

### PASSED

1. **Identity Isolation** - Both `job_id` and `agent_id` correctly isolated in response:
   ```json
   {
     "identity": {
       "job_id": "60e8bd2b-64fb-41f0-80cb-08f5e8a309be",
       "agent_id": "cd185a52-7ec0-48a0-b620-c356308886fa"
     }
   }
   ```

2. **fetch_context() Functional** - All 3 CRITICAL categories returned valid data:
   - `testing`: 197 tokens (coverage target 85%, pytest frameworks)
   - `tech_stack`: 223 tokens (Python 3.11+, FastAPI, React 19+, PostgreSQL)
   - `agent_templates`: 7,465 tokens (5 full templates with MCP protocol)

3. **3-Tier Priority System Working** - Instructions correctly categorized:
   - CRITICAL (Priority 1): testing, tech_stack, agent_templates
   - IMPORTANT (Priority 2): memory_360, architecture, vision_documents
   - REFERENCE (Priority 3): git_history, product_core

4. **Thin Client Architecture** - Response confirms `thin_client: true`

5. **CLI Mode Rules Present** - Instructions include:
   - `agent_name` = SINGLE SOURCE OF TRUTH (template filename)
   - `agent_type` = Display category only
   - Allowed agents: `['analyzer', 'documenter', 'implementer', 'tester', 'reviewer']`

---

## ANOMALY DETECTED (NOW RESOLVED)

### Issue: `fetch_context()` Uses `product_id` Instead of `agent_id`

**Current Implementation (0350a):**
```python
fetch_context(
    product_id="abe2e069-713e-4004-86e7-7080b693eded",  # <-- Uses product_id
    tenant_key="...",
    categories=["testing"]
)
```

**Expected per 0366c Spec:**
```python
fetch_context(
    agent_id="cd185a52-7ec0-48a0-b620-c356308886fa",  # <-- Should use agent_id
    tenant_key="...",
    categories=["testing"]
)
```

**Impact (original hypothesis):**
- Context fetching appeared to be NOT executor-specific
- Could not see how to track which agent requested which context
- Suggested that the 0366 Agent Identity Refactor might be incomplete for context tools

### Resolution

Further investigation shows this is a **design distinction**, not a bug:

- The call pattern observed in the simulation is the **0350a product/project-level dispatcher** in
  `src/giljo_mcp/tools/context_tools/fetch_context.py`, which is correctly keyed by `product_id` (and optionally `project_id`)
  and is meant for orchestrator-level context.
- The 0366c RED-phase spec refers to a **separate, executor-level context API** implemented in `src/giljo_mcp/tools/context.py`:
  - `fetch_context(agent_id, tenant_key, categories)`
  - `update_context_usage(agent_id, tenant_key, tokens_used)`
  - `get_context_history(agent_id, tenant_key)`
  - `get_succession_context(agent_id, tenant_key)`
- These executor-level functions operate on `AgentExecution` using `agent_id` (WHO) and are covered by
  `tests/tools/test_context_0366c.py`, which now pass (when run alone) and use the global `DatabaseManager` (no hardcoded test DB URLs).

In short:

- Orchestrator context is fetched via `context_tools.fetch_context(product_id, project_id, ...)` (product/project scope).
- Executor-specific context windows and history are handled via `context.fetch_context(agent_id, ...)` and the related tools.

---

## Proposed Research & Fixes

### Research Needed

1. **0366 Series Status Check**
   - Review 0366a, 0366b, 0366c handovers
   - Determine if Agent Identity refactor is complete or in-progress
   - Check if `fetch_context()` was intentionally excluded from refactor

2. **Database Schema Audit**
   - Verify `mcp_agent_jobs` table has proper `agent_id` tracking
   - Check if context requests are logged with agent attribution

3. **Parameter Semantics Clarification**
   - `product_id` = Product-level context (shared across all agents)
   - `agent_id` = Executor-specific context (per-agent tracking)
   - Determine correct semantic for fetch_context use case

### Potential Fixes

| Priority | Fix | Scope |
|----------|-----|-------|
| P1 | Document the two `fetch_context` surfaces (product-level vs executor-level) and when to use each | Docs (`HANDOVERS`, `CLAUDE.md`) |
| P2 | Wire executor-level context tools (`context.fetch_context`, `update_context_usage`, etc.) into any future agent-side flows that need per-executor tracking | `src/giljo_mcp/tools/context.py`, agent templates |
| P3 | (Optional) Add audit logging so executor-level context calls are tagged with `agent_id` + `job_id` | Context service / DB audit trail |

---

## Files to Review

- `src/giljo_mcp/tools/context_tools.py` - fetch_context implementation
- `handovers/completed/0366*` - Agent Identity refactor series
- `handovers/completed/0350*` - Context Management v2.0 series
- `src/giljo_mcp/services/context_service.py` - Context service layer

---

## Next Steps

1. **DONE (this session)**  
   - Verified 0366 context tools are implemented in `context.py` and pass `tests/tools/test_context_0366c.py` when run alone.  
   - Confirmed that `context_tools.fetch_context(product_id, ...)` is intentionally product/project-scoped and correctly used by the orchestrator.  
   - Updated this handover to mark the anomaly as resolved and captured the design distinction.

2. **DONE (follow-up implementation, 2025-12-22)**  
   - Updated `CLAUDE.md` “Core Rules & Expectations” with a **Context API** clarification:
     - Orchestrators use the unified MCP tool `fetch_context(product_id, tenant_key, project_id=None, categories=[...])` implemented in `src/giljo_mcp/tools/context_tools/fetch_context.py` for product/project-level context.  
     - Executor agents use `fetch_context(agent_id, tenant_key, categories=[...])` and its companion tools (`update_context_usage`, `get_context_history`, `get_succession_context`) from `src/giljo_mcp/tools/context.py`, keyed by `AgentExecution.agent_id` + `tenant_key`.  
   - Verified that executor-level context tools are wired to the global `DatabaseManager` (no test-only DB URLs) and respect tenant isolation.

3. **Recommended follow-up (still open)**  
   - Implement richer per-category data for executor-level `fetch_context(agent_id, ...)` (today it returns placeholder `\"Context for {category}\"` stubs).  
   - Optionally add lightweight audit logging so executor-level context calls record both `agent_id` and `job_id` for future debugging and analytics.

---

## Session Log

```
Step 1: health_check()
  Result: {"status": "healthy", "database": "connected", "version": "3.1.0"}

Step 2: get_orchestrator_instructions(job_id, tenant_key)
  Result: Identity block, 5 agent templates, 3-tier priority instructions

Step 3: fetch_context() x3 (CRITICAL tier)
  - testing: 197 tokens
  - tech_stack: 223 tokens
  - agent_templates: 7,465 tokens (full depth)

Step 4-7: NOT EXECUTED (paused for diagnostics)
```

---

**Handover Author**: Orchestrator Simulation Agent
**Resume Point**: Step 4 (CREATE MISSION) after anomaly resolution
