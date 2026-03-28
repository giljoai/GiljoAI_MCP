# Handover 0842k: Paginated Vision Document Chunk Delivery

**Series:** 0842 Vision Document Analysis
**Status:** COMPLETE
**Branch:** `feature/0842-vision-doc-analysis`
**Edition Scope:** CE

---

## Problem Statement

The `gil_get_vision_doc` MCP tool returned the entire raw vision document (289K chars) in a single response, exceeding Claude Code's MCP tool output limit (~25K tokens). The agent had to read a saved file fallback instead of receiving structured data through the tool interface.

## Root Cause

`gil_get_vision_doc` concatenated all active vision documents into `document_content` and embedded the full text inside the extraction prompt. For large documents, the combined response (document + extraction instructions) exceeded MCP output limits.

The backend already chunked documents during upload (via `auto_chunk=true` into `mcp_context_index`), but the MCP tool ignored the pre-processed chunks and served the raw blob.

## Solution: Paginated Chunk Delivery

Changed `gil_get_vision_doc` to support pagination via an optional `chunk` parameter:

**Without `chunk` (metadata only):**
```json
{
  "total_chunks": 2,
  "total_tokens": 21910,
  "extraction_instructions": "...",
  "write_tool": "gil_write_product",
  "product_id": "...",
  "product_name": "...",
  "usage": "Call again with chunk=1 through chunk=2 to retrieve content"
}
```

**With `chunk=1` (single chunk content):**
```json
{
  "total_chunks": 2,
  "total_tokens": 21910,
  "chunk": 1,
  "content": "... chunk text ...",
  "chunk_token_count": 12450,
  "extraction_instructions": "...",
  "write_tool": "gil_write_product",
  "product_id": "...",
  "product_name": "..."
}
```

**Agent workflow:**
1. `gil_get_vision_doc(product_id="...")` -- get metadata + total_chunks
2. `gil_get_vision_doc(product_id="...", chunk=1)` -- read chunk 1
3. `gil_get_vision_doc(product_id="...", chunk=2)` -- read chunk 2
4. `gil_write_product(product_id="...", ...)` -- write extracted fields

**Fallback:** If no chunks exist in `mcp_context_index` (legacy unchunked documents), the tool falls back to raw content served as a single chunk.

## Additional Fix: testing_strategy Enum

The `gil_write_product` tool accepted freetext for `testing_strategy`, but the UI uses a dropdown with fixed values. Agents wrote long descriptive strings that exceeded the 50-char DB column limit and didn't match dropdown options.

**Fix:** Added `"enum": ["TDD", "BDD", "Integration-First", "E2E-First", "Manual", "Hybrid"]` to the MCP tool schema and added a rule to the extraction prompt listing valid values.

## Additional Fix: crypto.randomUUID on Non-Secure Contexts

`notifications.js` used `crypto.randomUUID()` which is unavailable on HTTP + non-localhost (LAN/WAN IP). The `vision:analysis_complete` WebSocket handler crashed in `addNotification()`, preventing the UI from unlocking after AI analysis. Fixed with a `Date.now()` + `Math.random()` fallback.

## Additional Fix: WebSocket UI Unlock

`ProductForm.vue` now listens for the `vision-analysis-complete` window event (dispatched by the WebSocket router). On receipt, it fetches the updated product from the API, populates all form fields with AI-extracted data, and unlocks the "Next" button.

## Files Changed

| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/vision_analysis.py` | Paginated `chunk` param; extraction prompt no longer embeds document; `testing_strategy` enum rule |
| `src/giljo_mcp/tools/tool_accessor.py` | Pass `chunk` param through to `gil_get_vision_doc` |
| `api/endpoints/mcp_http.py` | `chunk` in tool schema + `_TOOL_SCHEMA_PARAMS` allowlist; `testing_strategy` enum |
| `frontend/src/components/products/ProductForm.vue` | WebSocket listener for `vision-analysis-complete`; toast on copy; `useProductStore` for fetch |
| `frontend/src/stores/notifications.js` | `crypto.randomUUID()` fallback |
| `tests/test_0842c_vision_analysis_tools.py` | Updated for paginated response shape |
| `tests/test_0842e_vision_doc_e2e.py` | Updated for paginated response shape |

## Commits

- `63230b6d` — Initial chunked delivery (all chunks in one response)
- `6bfb01c0` — WebSocket unlock, testing_strategy enum, crypto.randomUUID fallback
- `7db49c25` — Green toast on Stage Analysis prompt copy
- `e25ccadb` — Paginated chunk delivery (one chunk per call)
