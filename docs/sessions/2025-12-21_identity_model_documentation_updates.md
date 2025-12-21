# Session: Identity Model Documentation Updates (Handover 0361 Task 4)

**Date**: 2025-12-21
**Agent**: Documentation Manager
**Context**: Update STAGING_WORKFLOW.md and CLAUDE.md to reflect 0366 identity model

## Objective

Update documentation to reflect the unified identity model introduced in Handover 0366:
- `job_id` = Work order UUID (persists across succession)
- `agent_id` = Executor UUID (changes on succession)
- `orchestrator_id` is DEPRECATED - use `agent_id` instead

## Documentation Updates Required

### 1. STAGING_WORKFLOW.md Updates

**Location**: `docs/components/STAGING_WORKFLOW.md`

#### Task 1 Example Output (Lines 143-151)
Replace `Orchestrator ID:` with dual identifier pattern:
```diff
 ✓ Project ID verified: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
 ✓ Project name: "User Authentication System"
 ✓ Product ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
 ✓ Tenant key: user_alice_tenant_001
-✓ Orchestrator ID: 7e57d004-2b97-0e7a-b45f-5387367791cd
+✓ Agent ID (Execution): 7e57d004-2b97-0e7a-b45f-5387367791cd
+✓ Job ID (Work Order): a1b2c3d4-e5f6-7890-abcd-ef1234567890
 ✓ WebSocket: Connected (ws://localhost:7272/ws)
```

#### Task 7 Example Output (Lines 466-470)
Replace `Orchestrator ID:` in orchestration start section:
```diff
 Orchestration Start:
 - Timestamp: 2025-11-24T14:23:17Z
-- Orchestrator ID: 7e57d004-2b97-0e7a-b45f-5387367791cd
+- Agent ID (Execution): 7e57d004-2b97-0e7a-b45f-5387367791cd
+- Job ID (Work Order): a1b2c3d4-e5f6-7890-abcd-ef1234567890
 - Execution mode: claude_code_cli
 - Expected duration: 4-8 hours
```

#### Task 8: Execution Phase Monitoring (Line 477)
Add identity model context:
```diff
-### Task 8: Execution Phase Monitoring (Handover 0355)
+### Task 8: Execution Phase Monitoring (Handovers 0355, 0364)

 **Purpose**: Actively monitor spawned agents, coordinate handoffs, and handle real-time issues during project execution.

+**Identity Model (Handover 0366)**:
+- `job_id` = Work order UUID (persists across succession, identifies WHAT work)
+- `agent_id` = Executor UUID (changes on succession, identifies WHO is working)
+- Use `agent_id` for execution-specific operations (fetch instructions, report progress)
+- Use `job_id` for work-specific operations (complete job, update status)
+
 **Actions**:
```

### 2. CLAUDE.md Updates

**Location**: `CLAUDE.md`

#### Recent Updates Section (Line 31)
Add Handover 0361-0366 series to recent updates:
```diff
-**Recent Updates (v3.2+)**: Orchestrator Workflow & Token Optimization (0246a-0246c) • GUI Redesign Series (0243) • Context Management v2.0 (0312-0316) • ...
+**Recent Updates (v3.2+)**: Identity Model Unification (0361-0366) • Orchestrator Workflow & Token Optimization (0246a-0246c) • GUI Redesign Series (0243) • Context Management v2.0 (0312-0316) • ...
```

#### Context Management Section (Lines 159-162)
Fix `categories=` array pattern to singular `category`:
```diff
 **Solution (Handover 0350a-c)**:
 1. `get_orchestrator_instructions()` returns framing (~500 tokens) with priority indicators
-2. Orchestrator calls unified `fetch_context(categories=[...])` based on priority tier
+2. Orchestrator calls unified `fetch_context(category=...)` based on priority tier
 3. Context is fetched on-demand, never truncated
```

#### Unified fetch_context() Tool Example (Lines 181-188)
Update example to show singular category parameter:
```diff
-fetch_context(
-    categories=["product_core", "tech_stack", "vision_documents"],
-    product_id="uuid",
-    tenant_key="tenant_abc",
-    depth_config={"vision_documents": "light", "memory_360": 5}
-)
+# Handover 0361: Singular category parameter
+fetch_context(
+    category="product_core",  # One category per call
+    product_id="uuid",
+    tenant_key="tenant_abc",
+    depth_config={"vision_documents": "light", "memory_360": 5}
+)
```

#### Thin Client Architecture Section (Lines 239-243)
Update `orchestrator_id` to `agent_id` and add identity model note:
```diff
 **Definition – Thin-Client Prompts**
 - **Thin-client prompts** are *lean* prompts whose primary job is to tell the agent *how to talk to the MCP server*, not to inline all context.
-- Typical pattern: "Read your instructions on the server using `mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}', '{tenant_key}')`" or, for spawned agents, `get_agent_mission(job_id, tenant_key)`.
+- Typical pattern: "Read your instructions on the server using `mcp__giljo-mcp__get_orchestrator_instructions('{agent_id}', '{tenant_key}')`" or, for spawned agents, `get_agent_mission(job_id, tenant_key)`.
 - The full mission and context live on the server (via MCP tools) for **auditability** and **replay**; the user pastes only the thin prompt into Claude Code / other CLIs.
 - Agents can call the same MCP tools again at any time to **re-read their initial instructions** and refresh context instead of relying on a one-shot, giant clipboard prompt.
+
+**Identity Model (Handover 0366)**:
+- `agent_id` = Executor UUID (use for fetching orchestrator instructions)
+- `job_id` = Work order UUID (use for fetching agent mission, persists across succession)
+- `orchestrator_id` is DEPRECATED - use `agent_id` instead
```

## Pattern Search Results

Searched for outdated patterns across docs:

### `orchestrator_id` Occurrences
Found 15 files with `orchestrator_id` references:
- `docs/ORCHESTRATOR.md`
- `docs/guides/thin_client_migration_guide.md`
- `docs/architecture/messaging_contract.md`
- `docs/DOCUMENTATION_REMEDIATION_EXECUTIVE_SUMMARY.md`
- `docs/documentation_remediation_plan_handover_0280.md`
- `docs/testing/ORCHESTRATOR_SIMULATOR.md`
- `docs/archive/handover_docs/HANDOVER_0246c_IMPLEMENTATION_GUIDE.md`
- `docs/references/0045/DEVELOPER_GUIDE.md`
- `docs/STAGE_PROJECT_FEATURE.md`
- `docs/GILJOAI_WORKFLOW_SINGLE_SOURCE_OF_TRUTH_MERGED.md`
- `docs/GILJOAI_WORKFLOW_SINGLE_SOURCE_OF_TRUTH_Variant.md`
- `docs/prompts/orchestrator_mcp_tools.md`
- `docs/api/prompts_endpoints.md`
- `docs/quick_reference/succession_quick_ref.md`
- `docs/developer_guides/orchestrator_succession_developer_guide.md`

**Note**: Most occurrences should remain with deprecation notices. Only update examples/patterns that show current usage.

### `categories=[` Array Pattern
Found 3 files with outdated array syntax:
- `docs/ORCHESTRATOR.md`
- `docs/guides/thin_client_migration_guide.md`
- `docs/api/context_tools.md`

**Action Required**: Update examples to show singular `category` parameter per Handover 0361.

## Related Handovers

- **Handover 0361**: fetch_context() singular category parameter
- **Handover 0364**: Execution phase protocol improvements
- **Handover 0366**: Unified identity model (job_id vs agent_id)

## Follow-Up Actions

1. Apply edits to STAGING_WORKFLOW.md when file is not being concurrently modified
2. Apply edits to CLAUDE.md when file is not being concurrently modified
3. Consider updating:
   - `docs/ORCHESTRATOR.md` - Update categories array patterns
   - `docs/guides/thin_client_migration_guide.md` - Update categories array patterns
   - `docs/api/context_tools.md` - Update categories array patterns (likely already done by other agent)

## Lessons Learned

- **Concurrent Editing**: Multiple agents editing documentation simultaneously requires coordination
- **Session Documents**: When direct edits fail due to concurrent modifications, session documents preserve update intent
- **Pattern Migration**: Large-scale pattern updates (orchestrator_id → agent_id) require systematic sweeps across all documentation
- **Deprecation Strategy**: Not all references should be removed - maintain deprecation notices for backward compatibility context

---

**Status**: Documentation update plan complete
**Next Step**: Apply edits when files are available for modification
**Assignee**: Documentation Manager
