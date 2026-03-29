# Handover 0842c: Vision Document Analysis — MCP Tools & Extraction Prompt

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** tdd-implementor
**Priority:** High
**Estimated Complexity:** 2 hours
**Status:** Not Started
**Series:** 0842a-e (Vision Document Analysis Feature)
**Spec:** `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md`
**Depends on:** 0842a

---

## Task Summary

Implement two new MCP tools: `gil_get_vision_doc` (returns document content + baked extraction prompt) and `gil_write_product` (writes extracted fields + AI summaries). Store the baked extraction prompt as a constant. These are the tools the user's AI coding agent will call.

---

## Context and Background

GiljoAI is a **passive orchestrator** — it never runs inference. The user's connected AI coding tool (Claude Code, Codex CLI, Gemini CLI) does the reasoning. GiljoAI provides:
1. The vision document content
2. A baked extraction prompt telling the agent what to extract
3. A write endpoint for the agent to submit extracted fields

The flow: User clicks "Stage Analysis" in UI → prompt staged → user's CLI agent calls `gil_get_vision_doc` → agent's LLM reasons → agent calls `gil_write_product` → WebSocket notifies UI.

---

## Technical Details

### Tool 1: `gil_get_vision_doc`

**MCP tool definition:**
```json
{
  "name": "gil_get_vision_doc",
  "description": "Retrieve a product's vision document with extraction instructions.",
  "parameters": {
    "product_id": { "type": "string", "required": true }
  }
}
```

**Returns:**
```json
{
  "document_content": "... full document text or chunks ...",
  "document_tokens": 18500,
  "extraction_instructions": "... baked prompt (Section 3 of spec) ...",
  "write_tool": "gil_write_product",
  "product_id": "abc-123",
  "product_name": "TinyContacts"
}
```

**Server-side behavior:**
1. Validate `product_id` exists and belongs to tenant
2. Fetch all active vision documents for the product
3. Return full document content (all chunks if chunked)
4. Embed the extraction prompt with `{custom_instructions}` replaced from `Product.extraction_custom_instructions`
5. Include `{document_content}` placeholder replaced with actual content

### Tool 2: `gil_write_product`

**MCP tool definition** (see spec Section 2.2 for full schema — 16 optional fields):

**Server-side behavior:**
1. Validate `product_id` exists and belongs to tenant
2. For each product field present: write to appropriate table
   - `product_name`, `product_description`, `core_features` → `products` table
   - `programming_languages`, `frontend_frameworks`, `backend_frameworks`, `databases`, `infrastructure`, `target_platforms` → `product_tech_stacks` table
   - `architecture_pattern`, `design_patterns`, `api_style`, `architecture_notes` → `product_architectures` table
   - `quality_standards`, `testing_strategy`, `testing_frameworks`, `test_coverage_target` → `product_test_configs` table
3. For `summary_33` / `summary_66`: write to `vision_document_summaries` with `source="ai"`
4. Return `{ "success": true, "fields_written": N, "fields": [...] }`
5. Push WebSocket notification to UI (event: `vision_analysis_complete`)

### Baked Extraction Prompt

Store as constant in a new file `src/giljo_mcp/tools/vision_analysis.py`:

```python
VISION_EXTRACTION_PROMPT = """You are analyzing a product vision document...
(full prompt from spec Section 3)
"""
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/vision_analysis.py` | **NEW** — `VISION_EXTRACTION_PROMPT` constant + `gil_get_vision_doc()` + `gil_write_product()` async tool functions |
| `src/giljo_mcp/tools/tool_accessor.py` | Add wrapper methods `get_vision_doc()` and `write_product_from_analysis()` that import from `vision_analysis.py` and inject `db_manager` + `_websocket_manager` |
| `api/endpoints/mcp_http.py` | **3 registrations per tool**: (a) JSON schema in a `_build_vision_analysis_tools()` function called from `handle_tools_list`, (b) dispatch map entries in `handle_tools_call` tool_map dict (~line 988-1027), (c) `_TOOL_SCHEMA_PARAMS` allowlist entries (~line 211-306) |
| `src/giljo_mcp/services/product_service.py` | Add `merge_update_from_extraction(product_id, fields_dict)` method — reads existing values, overlays only provided fields, then writes merged result. See "Merge-Write Pattern" below. |

**Do NOT modify `src/giljo_mcp/tools/__init__.py`** — it is documentation only, not a registry.

### MCP Tool Registration Pattern (4 Steps)

There are **no decorators** in this codebase. MCP tools are plain async functions registered manually across 3 layers:

1. **Tool implementation** → `src/giljo_mcp/tools/vision_analysis.py` — async function with `db_manager: DatabaseManager` parameter
2. **ToolAccessor facade** → `src/giljo_mcp/tools/tool_accessor.py` — wrapper method that imports the function and injects runtime deps (`self.db_manager`, `self._websocket_manager`)
3. **MCP HTTP endpoint** → `api/endpoints/mcp_http.py`:
   - **Schema**: Add `_build_vision_analysis_tools()` returning JSON Schema for both tools. Call it from `handle_tools_list`.
   - **Dispatch**: Add entries to `tool_map` dict in `handle_tools_call` mapping tool name strings to `ToolAccessor` methods
   - **Allowlist**: Add entries to `_TOOL_SCHEMA_PARAMS` dict whitelisting accepted parameters per tool

**Reference examples**: `write_360_memory.py`, `submit_tuning_review.py` — both are write tools following this exact pattern.

### Merge-Write Pattern (CRITICAL)

**Problem**: `ProductService._update_config_relations()` does a **full replace** on child rows. If the AI agent sends `tech_stack={"programming_languages": "Python"}`, it will blank `frontend_frameworks`, `databases_storage`, etc. to `""`.

**Solution**: `merge_update_from_extraction()` must:
1. Load the existing Product with eagerly loaded `tech_stack`, `architecture`, `test_config`
2. For each child table group present in the input:
   - Read current values from the existing child row (or empty dict if row is None)
   - Overlay only the fields the agent sent
   - Write the merged result
3. For direct Product fields (`name`, `description`, `core_features`): write only if present in input

```python
# Pseudocode for merge-write
existing_tech = product.tech_stack
merged_tech = {}
if existing_tech:
    merged_tech = {col: getattr(existing_tech, col) for col in tech_columns}
# Overlay only agent-provided fields
for key, value in agent_tech_fields.items():
    merged_tech[mapped_key] = value
# Now pass merged_tech to _update_config_relations
```

### WebSocket Emission

Use `ToolAccessor._websocket_manager` (Pattern A — direct access). The websocket_manager is injected into ToolAccessor at init and stored as `self._websocket_manager`.

```python
if self._websocket_manager:
    event = EventFactory.tenant_envelope(
        event_type="vision:analysis_complete",
        tenant_key=tenant_key,
        data={"product_id": product_id, "fields_written": N, "fields": [...]},
    )
    await self._websocket_manager.broadcast_event_to_tenant(tenant_key=tenant_key, event=event)
```

On the frontend, add `'vision:analysis_complete'` to `EVENT_MAP` in `frontend/src/stores/websocketEventRouter.js`.

### Key Existing Code

- **ToolAccessor**: `src/giljo_mcp/tools/tool_accessor.py` — facade with `_websocket_manager`, `db_manager`
- **MCP HTTP endpoint**: `api/endpoints/mcp_http.py` — tool schema builders (~line 766), dispatch map (~line 988), allowlist (~line 211)
- **Write tool precedent**: `src/giljo_mcp/tools/write_360_memory.py`, `src/giljo_mcp/tools/submit_tuning_review.py`
- **ProductTechStack model**: `src/giljo_mcp/models/products.py:338-369`
- **ProductArchitecture model**: `src/giljo_mcp/models/products.py:372-395`
- **ProductTestConfig model**: same file
- **Product service**: `src/giljo_mcp/services/product_service.py` — `_update_config_relations()` at risk of blanking fields
- **EventFactory**: `api/events/schemas.py` — `EventFactory.tenant_envelope()` for ad-hoc events
- **WebSocket event router (frontend)**: `frontend/src/stores/websocketEventRouter.js` — `EVENT_MAP` dict

### Field Mapping (spec fields → normalized tables)

**Name translations** (spec name ≠ column name):

| Spec Field | Target Table | Target Column | Name Translation |
|-----------|-------------|---------------|-----------------|
| `product_name` | products | `name` | ⚠️ `product_name` → `name` |
| `product_description` | products | `description` | ⚠️ `product_description` → `description` |
| `core_features` | products | `core_features` | direct |
| `programming_languages` | product_tech_stacks | `programming_languages` | direct |
| `frontend_frameworks` | product_tech_stacks | `frontend_frameworks` | direct |
| `backend_frameworks` | product_tech_stacks | `backend_frameworks` | direct |
| `databases` | product_tech_stacks | `databases_storage` | ⚠️ `databases` → `databases_storage` |
| `infrastructure` | product_tech_stacks | `infrastructure` | direct |
| `target_platforms` | products | `target_platforms` | ⚠️ Array on products table, NOT boolean columns on tech_stacks (see note below) |
| `architecture_pattern` | product_architectures | `primary_pattern` | ⚠️ `architecture_pattern` → `primary_pattern` |
| `design_patterns` | product_architectures | `design_patterns` | direct |
| `api_style` | product_architectures | `api_style` | direct |
| `architecture_notes` | product_architectures | `architecture_notes` | direct |
| `quality_standards` | product_test_configs | `quality_standards` | ⚠️ See dual-location note |
| `testing_strategy` | product_test_configs | `test_strategy` | ⚠️ `testing_strategy` → `test_strategy` |
| `testing_frameworks` | product_test_configs | `testing_frameworks` | direct |
| `test_coverage_target` | product_test_configs | `coverage_target` | ⚠️ `test_coverage_target` → `coverage_target` |
| `summary_33` | vision_document_summaries | `summary` (ratio=0.33, source=ai) | separate table |
| `summary_66` | vision_document_summaries | `summary` (ratio=0.66, source=ai) | separate table |

### target_platforms

`target_platforms` is an `ARRAY(String)` column directly on the `products` table (default `{all}`). It is NOT the boolean columns on `product_tech_stacks`. The spec sends it as an array `["web", "ios"]` — write directly to `Product.target_platforms`.

The boolean columns on `product_tech_stacks` (`target_windows`, `target_linux`, etc.) are a separate normalized representation. Sync them from the array if needed, but the primary field is the array on products.

### quality_standards Dual Location

`quality_standards` exists in TWO places:
- `Product.quality_standards` (direct column, legacy from handover 0316)
- `ProductTestConfig.quality_standards` (normalized table)

**Write to `ProductTestConfig.quality_standards` only** — this is where `_update_config_relations()` and the tuning system write. The direct Product column is legacy and should not be updated by new code.

### Shared Write Logic with Tuning (0831)

The tuning system (`ProductTuningService._apply_value_to_product()`) writes to the exact same 13 fields. Extract field-writing logic into a shared utility (e.g., `product_field_writer.py` or a method on `ProductService`) to prevent divergence. Both `gil_write_product` and tuning acceptance should use the same writer.

---

## Implementation Plan

### Phase 1: Extraction Prompt & Constants

1. Create `src/giljo_mcp/tools/vision_analysis.py`
2. Add `VISION_EXTRACTION_PROMPT` from spec Section 3
3. Add field mapping constants

### Phase 2: `gil_get_vision_doc` Tool (TDD)

1. Write test: returns document content + extraction prompt for valid product
2. Write test: returns 404 for nonexistent product
3. Write test: tenant isolation — can't read another tenant's docs
4. Write test: custom instructions injected into prompt
5. Write test: chunked documents return all chunks
6. Implement tool function

### Phase 3: `gil_write_product` Tool (TDD)

1. Write test: writes product core fields
2. Write test: writes tech stack fields to `product_tech_stacks`
3. Write test: writes architecture fields to `product_architectures`
4. Write test: writes test config fields to `product_test_configs`
5. Write test: writes summaries to `vision_document_summaries` with source="ai"
6. Write test: only provided fields are written, missing fields untouched
7. Write test: tenant isolation
8. Write test: WebSocket notification emitted
9. Implement tool + `bulk_update_from_extraction()` service method

### Phase 4: Tool Registration (4 Steps, No Decorators)

1. Add wrapper methods to `ToolAccessor` in `src/giljo_mcp/tools/tool_accessor.py`
2. Add `_build_vision_analysis_tools()` function in `api/endpoints/mcp_http.py` returning JSON Schema for both tools
3. Call `_build_vision_analysis_tools()` from `handle_tools_list` aggregation
4. Add dispatch entries to `tool_map` dict in `handle_tools_call` (~line 988-1027)
5. Add `_TOOL_SCHEMA_PARAMS` allowlist entries (~line 211-306)
6. Verify tools appear in MCP `tools/list` response

---

## Testing Requirements

- `gil_get_vision_doc`: 5 tests (happy path, 404, tenant isolation, custom instructions, chunked)
- `gil_write_product`: 8 tests (4 table groups, summaries, partial write, tenant isolation, WebSocket)
- All existing tests pass

## Success Criteria

- [ ] `gil_get_vision_doc` returns document + baked prompt
- [ ] `gil_write_product` writes to all 4 normalized tables + summaries
- [ ] Only provided fields written, missing untouched
- [ ] Tenant isolation enforced on both tools
- [ ] WebSocket notification on successful write
- [ ] Tools registered and visible in MCP tool list
- [ ] ~13 new tests passing

## Edge Cases

- **No vision document uploaded yet**: `gil_get_vision_doc` returns clear error: "No vision documents found for this product"
- **Document > 20K tokens**: Return all chunks. Agent's LLM handles consumption strategy.
- **No tech_stack/architecture/test_config row exists**: Create the row on first write (upsert pattern)
- **target_platforms contains unknown values**: Ignore unknown, only map recognized platforms

## Rollback Plan

- Remove entries from `mcp_http.py` (schema, dispatch, allowlist)
- Remove wrapper methods from `tool_accessor.py`
- Delete `vision_analysis.py`
- No schema changes in this handover

---

## MANDATORY: Pre-Work Reading

Before writing ANY code, you MUST read these documents:

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, TDD protocol, code discipline
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — system architecture overview
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow and MCP tool patterns
4. `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md` — the feature specification (Sections 2 and 3)

**Use subagent**: Spawn `tdd-implementor` for all implementation work.

**IMPORTANT**: Study existing write tools (`write_360_memory.py`, `submit_tuning_review.py`) and their registration in `mcp_http.py` and `tool_accessor.py` to understand the exact pattern before writing code.

---

## Chain Execution Instructions

This is handover **3 of 5** in the 0842 Vision Document Analysis chain.

### Step 1: Read Chain Log
Read `prompts/0842_chain/chain_log.json`.
- Check `orchestrator_directives` for any STOP instructions — if STOP, halt immediately
- Review 0842a AND 0842b sessions' `notes_for_next` — you need to know exact model/repo method signatures from 0842a
- Verify 0842a status is `complete` (direct dependency) — if blocked/failed, STOP and report to user
- 0842b completion is NOT required for this handover (parallel-safe)

### Step 2: Mark Session Started
Update your session entry in the chain log:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover Tasks
Complete all phases above using TDD. Commit after each phase passes.

### Step 4: Update Chain Log
Before spawning next terminal, update your session in `prompts/0842_chain/chain_log.json`:
- `tasks_completed`: List what you actually did
- `deviations`: Any changes from plan
- `blockers_encountered`: Issues hit
- `notes_for_next`: Critical info for 0842d agent (e.g., exact WebSocket event type used, tool names as registered)
- `cascading_impacts`: Changes that affect 0842d/e
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<current ISO timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0842d - Frontend UI\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0842d. READ FIRST: F:\GiljoAI_MCP\handovers\0842d_VISION_DOC_ANALYSIS_FRONTEND.md — Read the ENTIRE document including Chain Execution Instructions at the bottom. You are session 4 of 5 in the 0842 chain. CRITICAL: Use ux-designer subagent for ALL implementation work.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS.** Only ONE agent should spawn the next terminal.
