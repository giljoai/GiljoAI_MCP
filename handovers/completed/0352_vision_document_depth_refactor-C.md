# Handover 0352: Vision Document Depth Refactor

**Status**: In Progress
**Created**: 2025-12-15
**Purpose**: Refactor vision document depth configuration to use Sumy summarization fields

---

## Problem Statement

Current vision document fetching uses **chunk-based pagination** regardless of depth setting. The database has Sumy-summarized fields (`summary_light`, `summary_medium`) that are not being used.

Additionally, there's a **critical bug**: `product_service.py` calls `summaries["moderate"]` but `vision_summarizer.py` returns `summaries["medium"]` causing a KeyError.

---

## Requirements

### Depth Configuration (HOW MUCH to read)

| Depth | Source | Tokens |
|-------|--------|--------|
| **Light** | `VisionDocument.summary_light` | ~33% of original |
| **Medium** | `VisionDocument.summary_medium` | ~66% of original |
| **Full** | Paginated chunks from `MCPContextIndex` | ≤25K per call |

### Priority Configuration (WHEN to read)

| Priority | Meaning | Framing |
|----------|---------|---------|
| **Critical** | Mandatory read | "REQUIRED: ..." |
| **Important** | Read if you need clarity | "RECOMMENDED: ..." |
| **Reference** | Here if you need it | "OPTIONAL: ..." |
| **Off** | Excluded from instructions | (not included) |

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER SETTINGS (UI)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Vision Documents                                                           │
│   ┌──────────────────────┐    ┌──────────────────────┐                      │
│   │ Priority      ▼      │    │ Depth          ▼     │                      │
│   ├──────────────────────┤    ├──────────────────────┤                      │
│   │ ○ Critical (MUST)    │    │ ○ Light   (33%)      │                      │
│   │ ● Important (SHOULD) │    │ ● Medium  (66%)      │                      │
│   │ ○ Reference (MAY)    │    │ ○ Full    (chunks)   │                      │
│   │ ○ Off                │    └──────────────────────┘                      │
│   └──────────────────────┘                                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE (User Settings)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   User.field_priority_config = { "vision_documents": 2 }     ← Important     │
│   User.depth_config = { "vision_documents": "medium" }       ← 66%           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    get_orchestrator_instructions() RESPONSE                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   "context_fetch_instructions": {                                            │
│       "critical": [...],                                                     │
│       "important": [                          ← Priority determines tier     │
│           {                                                                  │
│               "field": "vision_documents",                                   │
│               "tool": "fetch_context",                                       │
│               "params": {                                                    │
│                   "category": "vision_documents",                            │
│                   "depth": "medium"           ← Depth from user config       │
│               },                                                             │
│               "framing": "RECOMMENDED: Read if you need clarity on vision"  │
│           }                                                                  │
│       ],                                                                     │
│       "reference": [...]                                                     │
│   }                                                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR DECIDES (Based on Priority Tier)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Priority = Critical  →  "I MUST call fetch_context for this"               │
│   Priority = Important →  "I SHOULD call fetch_context if I need clarity"   │
│   Priority = Reference →  "I MAY call fetch_context if needed"               │
│   Priority = Off       →  (not in response at all)                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                          (Orchestrator calls)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     fetch_context(depth="medium") CALL                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   fetch_context(                                                             │
│       category="vision_documents",                                           │
│       product_id="...",                                                      │
│       tenant_key="...",                                                      │
│       depth="medium"              ← This determines WHAT is returned         │
│   )                                                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPTH DETERMINES DATA SOURCE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  depth="light"                                                       │   │
│   │  ─────────────                                                       │   │
│   │  → Read: VisionDocument.summary_light                                │   │
│   │  → Tokens: ~33% of original                                          │   │
│   │  → Single response, no pagination needed                             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  depth="medium"                                                      │   │
│   │  ──────────────                                                      │   │
│   │  → Read: VisionDocument.summary_medium                               │   │
│   │  → Tokens: ~66% of original                                          │   │
│   │  → Single response, no pagination needed                             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  depth="full"                                                        │   │
│   │  ────────────                                                        │   │
│   │  → Read: MCPContextIndex chunks (paginated)                          │   │
│   │  → Max 25K tokens per call                                           │   │
│   │  → Returns: { data: [...], has_more: true, next_offset: 3 }          │   │
│   │  → Agent must loop until has_more=false                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Priority × Depth Matrix

```
                        DEPTH (How Much)
                 ┌──────────┬──────────┬──────────┐
                 │  Light   │  Medium  │   Full   │
                 │  (33%)   │  (66%)   │ (chunks) │
    ┌────────────┼──────────┼──────────┼──────────┤
    │ Critical   │  MUST    │  MUST    │  MUST    │
P   │ (MUST)     │  read    │  read    │  read    │
R   │            │  33%     │  66%     │  all     │
I   ├────────────┼──────────┼──────────┼──────────┤
O   │ Important  │  SHOULD  │  SHOULD  │  SHOULD  │
R   │ (SHOULD)   │  read    │  read    │  read    │
I   │            │  33%     │  66%     │  all     │
T   ├────────────┼──────────┼──────────┼──────────┤
Y   │ Reference  │  MAY     │  MAY     │  MAY     │
    │ (MAY)      │  read    │  read    │  read    │
    │            │  33%     │  66%     │  all     │
    ├────────────┼──────────┼──────────┼──────────┤
    │ Off        │    (not included in response)  │
    └────────────┴──────────┴──────────┴──────────┘
```

---

## Expected Response Formats

### Light (33% Summary)
```json
{
  "source": "vision_documents",
  "depth": "light",
  "data": {
    "summary": "TinyContacts is a lightweight contact management app...",
    "tokens": 4200,
    "compression": "33%"
  },
  "pagination": null
}
```

### Medium (66% Summary)
```json
{
  "source": "vision_documents",
  "depth": "medium",
  "data": {
    "summary": "TinyContacts is a lightweight contact management application designed for users who want simplicity...",
    "tokens": 8400,
    "compression": "66%"
  },
  "pagination": null
}
```

### Full (Paginated Chunks)
```json
{
  "source": "vision_documents",
  "depth": "full",
  "data": [
    { "chunk_order": 1, "content": "...", "tokens": 8000 },
    { "chunk_order": 2, "content": "...", "tokens": 8000 },
    { "chunk_order": 3, "content": "...", "tokens": 7500 }
  ],
  "pagination": {
    "total_chunks": 12,
    "offset": 0,
    "limit": 3,
    "has_more": true,
    "next_offset": 3
  }
}
```

---

## Implementation Tasks

### Task 1: Fix Critical Bug in ProductService
**File**: `src/giljo_mcp/services/product_service.py`
**Issue**: Uses `summaries["moderate"]` but summarizer returns `summaries["medium"]`
**Fix**: Update key names to match `vision_summarizer.py` output (`light`, `medium`)

### Task 2: Refactor get_vision_document Tool
**File**: `src/giljo_mcp/tools/context_tools/get_vision_document.py`
**Changes**:
- `depth="light"` → Read `VisionDocument.summary_light`
- `depth="medium"` → Read `VisionDocument.summary_medium`
- `depth="full"` → Paginated chunks from `MCPContextIndex` (≤25K tokens)

### Task 3: Update Response Format
Ensure consistent response structure across all depth levels with proper metadata.

### Task 4: Update Token Estimates
Use actual token counts from database fields:
- `summary_light_tokens`
- `summary_medium_tokens`
- Sum of chunk `token_count` for full

---

## Files to Modify

| File | Purpose |
|------|---------|
| `src/giljo_mcp/services/product_service.py` | Fix KeyError bug (lines ~1202-1245) |
| `src/giljo_mcp/tools/context_tools/get_vision_document.py` | Implement depth-based source selection |
| `src/giljo_mcp/tools/context_tools/fetch_context.py` | Ensure depth parameter flows correctly |

---

## Database Fields (Already Exist)

**VisionDocument Model** (`src/giljo_mcp/models/products.py`):
- `summary_light` - 33% Sumy-summarized content
- `summary_medium` - 66% Sumy-summarized content
- `summary_light_tokens` - Token count for light
- `summary_medium_tokens` - Token count for medium
- `is_summarized` - Flag indicating summarization complete

**MCPContextIndex Model** (`src/giljo_mcp/models/context.py`):
- `content` - Chunk content
- `chunk_order` - Sequential order
- `token_count` - Tokens per chunk
- `vision_document_id` - Link to parent

---

## Testing Checklist

- [ ] Light depth returns `summary_light` content
- [ ] Medium depth returns `summary_medium` content
- [ ] Full depth returns paginated chunks with `has_more`/`next_offset`
- [ ] Token counts are accurate
- [ ] No KeyError in product_service.py
- [ ] Priority tiers correctly place vision_documents in response

---

## Completion Criteria

1. User selects Priority=Important, Depth=Medium in UI
2. `get_orchestrator_instructions()` returns vision_documents in "important" tier with `depth: "medium"`
3. Orchestrator calls `fetch_context(category="vision_documents", depth="medium")`
4. Response contains `VisionDocument.summary_medium` content (~66% of original)
5. Full depth returns paginated chunks ≤25K tokens per call
