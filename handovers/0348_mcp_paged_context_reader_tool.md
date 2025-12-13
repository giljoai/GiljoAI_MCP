# Handover: 0348 - MCP Paged Context Reader Tool (Cursor-Based)

**Date:** 2025-12-13  
**From Agent:** Codex CLI (GPT-5.2)  
**To Agent:** tdd-implementor (backend) + system-architect (contract review)  
**Priority:** High  
**Estimated Complexity:** 4-8 hours  
**Status:** Ready for Implementation  

---

## Task Summary

When `Vision Documents` depth is set to **FULL**, `get_orchestrator_instructions()` can exceed CLI agent ingestion limits (commonly ~25K tokens). The server already chunks vision documents in storage (`mcp_context_index`), but the context builder re-merges all chunks into one huge string when depth is `full`, defeating chunking.

We need **one HTTP MCP tool** that lets an agent read **as many chunks as it wants** while receiving them **in bounded pieces** (paged responses), with strong multi-tenant isolation.

---

## Current Behavior (Problem)

- `get_orchestrator_instructions()` routes through HTTP MCP → `ToolAccessor.get_orchestrator_instructions()` and uses `MissionPlanner._build_context_with_priorities()`.
- In `src/giljo_mcp/mission_planner.py`, when `vision_depth == "full"`, it fetches **all** chunk rows and does `"\n\n".join(chunk["content"] ...)`, producing a single massive payload.
- The repo already contains a paged fetcher for vision chunks (`src/giljo_mcp/tools/context_tools/get_vision_document.py`) with `offset`/`limit`/`has_more`, but it is **not exposed** via the HTTP MCP tool list (`api/endpoints/mcp_http.py`).

---

## Architecture Context (Reference Slides)

This work aligns with:
- **MCP over HTTP (not stdio)** and multiuser/tenant separation (Slides 2–4).
- Developers primarily use CLI agentic tools that call the MCP HTTP endpoint; therefore, pagination must be available on the MCP surface (not only REST endpoints).

---

## Goals / Non-Goals

### Goals
- Add a **single** HTTP MCP tool that returns chunked context in **pages**.
- Support repeated calls until the agent decides it has enough (agent-controlled continuation).
- Enforce **tenant_key isolation** on every call.
- Provide stable ordering and predictable progress (`has_more`, `cursor_next`).
- Make it generic enough to cover **vision documents now**, and potentially other large context sources later.

### Non-Goals (for this handover)
- No UI work.
- No rewriting chunking algorithms (EnhancedChunker / summarizers).
- No migration work required (use existing tables).

---

## Proposed MCP Tool: `read_context_chunks`

### Why cursor-based instead of offset-based
Offset works but is easier to misuse and can be unstable if ordering changes. Cursor-based pagination keeps the contract clean and prevents cross-tenant/cross-product confusion because the cursor can be validated server-side.

### Tool Contract (Inputs)

```json
{
  "tenant_key": "string",
  "source": "vision_documents",
  "product_id": "string",
  "cursor": "string|null",
  "max_tokens": 8000,
  "max_chunks": 2,
  "include_metadata": true
}
```

**Fields:**
- `tenant_key` (required): user-level tenant isolation key.
- `source` (required): start with enum containing only `"vision_documents"`; can expand later.
- `product_id` (required for `"vision_documents"`): active product to read from.
- `cursor` (optional): opaque continuation token; `null` means “start”.
- `max_tokens` (optional): hard cap per response (defensive, e.g. 5K–15K tokens).
- `max_chunks` (optional): secondary cap to limit chunk count (e.g. 1–5).
- `include_metadata` (optional): include `stats`/`source_ref` in response.

### Tool Contract (Outputs)

```json
{
  "source": "vision_documents",
  "items": [
    {
      "chunk_id": "string",
      "chunk_order": 1,
      "tokens_est": 2400,
      "content": "string"
    }
  ],
  "page": {
    "returned_chunks": 1,
    "returned_tokens_est": 2400
  },
  "has_more": true,
  "cursor_next": "string|null",
  "stats": {
    "total_chunks": 25,
    "total_tokens_est": 150000
  },
  "source_ref": {
    "product_id": "string",
    "vision_document_id": "string|null"
  }
}
```

### Cursor Design (Opaque + Validated)

Cursor should be an **opaque** token (base64 JSON or signed token) containing at minimum:
- `tenant_key`
- `source`
- `product_id`
- `vision_document_id` (optional but recommended if a single active vision doc is selected)
- `next_chunk_order` (or `next_offset`)
- `page_params` (optional “sticky” params like `max_tokens`, `max_chunks` for audit/debug)

**Validation rules:**
- Cursor tenant_key must match request tenant_key.
- Cursor source must match request source.
- Cursor product_id must match request product_id.
- If any mismatch → return `VALIDATION_ERROR` (do not leak info).

---

## Implementation Plan (TDD)

### Phase 0: Sanity / Scope
- Confirm where vision chunks live: `mcp_context_index` rows linked via `vision_document_id`, ordered by `chunk_order`.

### Phase 1: Tests First (Failing)

Add a focused unit test module (examples):

1) Cursor start returns first page
- `test_read_context_chunks_starts_at_beginning_when_cursor_none`

2) Cursor continues and terminates
- `test_read_context_chunks_returns_has_more_and_cursor_next_until_exhausted`

3) Tenant isolation
- `test_read_context_chunks_rejects_cross_tenant_cursor`

4) Max token enforcement
- `test_read_context_chunks_honors_max_tokens_cap`

5) Tool appears on HTTP MCP surface
- `test_mcp_tools_list_includes_read_context_chunks`

Suggested locations:
- Unit: `tests/unit/test_read_context_chunks_tool.py`
- API/MCP: `tests/integration/test_mcp_http_tools_list.py` (or extend existing catalog/list tests)

### Phase 2: Minimal Backend Implementation

**Primary wiring target (HTTP MCP):**
- `api/endpoints/mcp_http.py`
  - Add tool definition to the tools list (`tools/list` response).
  - Route `tools/call` for `read_context_chunks` to a ToolAccessor method.

**Tool surface / business logic:**
- `src/giljo_mcp/tools/tool_accessor.py`
  - Add `async def read_context_chunks(...) -> dict[str, Any]`.
  - Use existing DB manager and SQLAlchemy queries.

**Repository/query layer (optional but recommended):**
- `src/giljo_mcp/repositories/context_repository.py` (if you want reusable query helpers)

### Phase 3: Integrate With Orchestrator Context (Stop Re-merging)

Adjust `src/giljo_mcp/mission_planner.py`:
- For `vision_documents` depth = `full`, return **overview + instruction** to use `read_context_chunks` rather than inlining full concatenated content.
- This keeps `get_orchestrator_instructions()` lean while still making FULL accessible in multiple calls.

### Phase 4: Verification
- `pytest tests/unit/test_read_context_chunks_tool.py -v`
- `pytest tests/integration/ -k mcp_http -v`

---

## Success Criteria

- [ ] `read_context_chunks` appears in HTTP MCP tool list and can be called successfully.
- [ ] Pagination works: repeated calls advance via `cursor_next` until `has_more=false`.
- [ ] Cross-tenant cursor reuse is rejected (no leakage).
- [ ] `max_tokens` and `max_chunks` caps are enforced.
- [ ] `get_orchestrator_instructions()` no longer returns a single massive vision blob when depth is `full`; instead it provides a paged-fetch instruction.

---

## Error Handling (Expected)

Use consistent error envelopes (matching existing MCP tools):
- `VALIDATION_ERROR` for missing/invalid params or cursor mismatch.
- `NOT_FOUND` if product/vision doc/chunks don’t exist for that tenant.
- `INTERNAL_ERROR` for unexpected exceptions (with server-side logging).

---

## Security / Multi-Tenant Notes (Critical)

Tenant = user-level isolation. Every DB query must filter by `tenant_key` and `product_id`. Cursor must be validated to match tenant and product. Never accept a cursor that could cause reading another tenant’s chunks.

---

## Related Existing Code (Reuse Opportunities)

- Existing paged chunk fetcher (not on HTTP MCP surface):
  - `src/giljo_mcp/tools/context_tools/get_vision_document.py` (offset/limit/has_more)
- Existing chunk metadata and ordering:
  - `mcp_context_index` (`vision_document_id`, `chunk_order`, `token_count`)
- Existing “lean overview” concept:
  - `MissionPlanner._get_vision_overview()` in `src/giljo_mcp/mission_planner.py`

Recommendation: reuse query logic patterns from `get_vision_document.py`, but expose the new capability via HTTP MCP with a cursor contract that is stable and safe.

---

## Git Snapshot (At Time of Writing)

`git status --porcelain`: clean  
Recent commits:
- `7e23a3fa` fix: MCP tool fetches fresh user config instead of frozen job_metadata
- `d11d8a2a` fix: Update existing tests to use vision_documents field name
- `f2680bd8` feat: Standardize vision document depth field to vision_documents (Handover 0346)
- `8a9482af` test: Add failing tests for depth config field standardization (Handover 0346)
- `dfef11ab` feat: Sumy LSA multi-level summarization for context depth staging

---

## Recommended Sub-Agents

- **tdd-implementor**: write tests and implement MCP tool + cursor logic.
- **system-architect**: review contract shape and ensure compatibility with thin-client prompts and existing MCP conventions.

