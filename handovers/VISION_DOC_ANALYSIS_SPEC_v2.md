# Vision Document Analysis — Lean Implementation Spec v2.0

> **Status:** Approved | **Target:** CE launch, end of April 2026
> **Estimated effort:** ~8 agent-hours
> **Supersedes:** v1.0 (provider architecture version — discarded)

---

## Design Principle

GiljoAI is a passive orchestrator. It stores the document, provides the extraction prompt, and exposes an MCP write tool. The user's AI coding tool does the reasoning. GiljoAI never runs inference.

---

## 1. User Journey

```
User uploads vision document (.md, .txt)
         │
         ▼
  GiljoAI stores document, chunks to 20K if needed, runs Sumy immediately
         │
         ▼
  UI prompt: "Want AI to analyze this and populate your product config?"
         │
    ┌────┴─────┐
    ▼          ▼
 YES          NO
    │          │
    │          └──▶ Sumy summaries ready. User fills fields manually.
    │
    ▼
 Prompt staged for user's CLI tool.
 Agent calls /gil_get_vision_doc → reads document + extraction instructions.
 Agent's LLM reasons about document.
 Agent calls /gil_write_product → writes fields + summaries.
 WebSocket notifies UI: "14 fields populated. Review your config."
 User reviews and edits in normal setup wizard.
```

Both paths end the same way: product fields populated, summaries stored, context manager depth toggles work identically (full / 66% / 33%).

---

## 2. MCP Tools — Two Tools

### 2.1 gil_get_vision_doc

Returns vision document content with baked extraction prompt. The prompt is embedded in the response so GiljoAI controls it — if the prompt improves, every user gets the upgrade automatically.

```json
{
  "name": "gil_get_vision_doc",
  "description": "Retrieve a product's vision document with extraction instructions. Use this when asked to analyze a vision document and populate product fields.",
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
  "extraction_instructions": "... baked prompt (see Section 3) ...",
  "write_tool": "gil_write_product",
  "product_id": "abc-123",
  "product_name": "TinyContacts"
}
```

### 2.2 gil_write_product

One flat tool. Every product field is optional. Only fields present in the call get written. Missing fields are untouched.

```json
{
  "name": "gil_write_product",
  "description": "Write product configuration fields and vision document summaries. Only include fields extracted from the document. Omit fields you could not determine.",
  "parameters": {
    "product_id":             { "type": "string",  "required": true },

    "product_name":           { "type": "string",  "required": false },
    "product_description":    { "type": "string",  "required": false,
                                "description": "2-3 sentence factual description" },
    "core_features":          { "type": "string",  "required": false,
                                "description": "Main features, one per line" },

    "programming_languages":  { "type": "string",  "required": false },
    "frontend_frameworks":    { "type": "string",  "required": false },
    "backend_frameworks":     { "type": "string",  "required": false },
    "databases":              { "type": "string",  "required": false },
    "infrastructure":         { "type": "string",  "required": false },
    "target_platforms":       { "type": "array",   "required": false,
                                "items": { "type": "string" } },

    "architecture_pattern":   { "type": "string",  "required": false },
    "design_patterns":        { "type": "string",  "required": false },
    "api_style":              { "type": "string",  "required": false },
    "architecture_notes":     { "type": "string",  "required": false,
                                "description": "Key constraints and decisions" },

    "quality_standards":      { "type": "string",  "required": false },
    "testing_strategy":       { "type": "string",  "required": false,
                                "description": "TDD|BDD|integration-first|manual|mixed" },
    "testing_frameworks":     { "type": "string",  "required": false },
    "test_coverage_target":   { "type": "integer", "required": false },

    "summary_33":             { "type": "string",  "required": false,
                                "description": "~33% executive summary of vision doc" },
    "summary_66":             { "type": "string",  "required": false,
                                "description": "~66% technical summary of vision doc" }
  }
}
```

**Server-side behavior:**
1. Validate product_id exists and belongs to tenant
2. For each field present: write to products table
3. For summary_33 / summary_66: write to vision_document_summaries table with `source = "ai"`
4. Return `{ "success": true, "fields_written": 14, "fields": [...] }`
5. Push WebSocket notification to UI

---

## 3. Baked Extraction Prompt

Shipped with GiljoAI. Returned by `/gil_get_vision_doc`. Users can append custom instructions via product settings.

```python
VISION_EXTRACTION_PROMPT = """You are analyzing a product vision document for a software
development orchestration platform. Extract structured information and generate summaries.

RULES:
- Extract ONLY information explicitly stated in the document
- If a field cannot be determined from the document, OMIT it entirely
- Do NOT guess, invent, or infer information not present
- Keep descriptions concise and factual, not promotional
- product_description should be 2-3 sentences maximum
- For summaries: preserve technical specs, architecture decisions, and constraints
- For summaries: remove marketing prose, user personas, and storytelling

After reading the document, call the gil_write_product tool with all fields you were
able to extract. Include summary_33 (concise ~33% executive summary focusing on what
a developer needs to build this) and summary_66 (thorough ~66% technical summary
preserving decisions, architecture, and feature descriptions).

{custom_instructions}

Here is the document to analyze:

{document_content}"""
```

---

## 4. Database Changes

### 4.1 New table: vision_document_summaries

```sql
CREATE TABLE vision_document_summaries (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(255) NOT NULL,
    document_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    source VARCHAR(20) NOT NULL,            -- "sumy" | "ai"
    ratio DECIMAL(3,2) NOT NULL,            -- 0.33 | 0.66
    summary TEXT NOT NULL,
    tokens_original INTEGER NOT NULL,
    tokens_summary INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_vds_lookup (tenant_key, document_id, source, ratio),
    FOREIGN KEY (document_id) REFERENCES vision_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

### 4.2 Products table addition

```sql
-- Add column:
ALTER TABLE products ADD COLUMN extraction_custom_instructions TEXT;
```

### 4.3 Context Manager query logic

```sql
-- depth_config: "full"  → serve from vision_documents (unchanged)
-- depth_config: "medium" → SELECT summary WHERE ratio = 0.66
--                          ORDER BY (source = 'ai') DESC, created_at DESC LIMIT 1
-- depth_config: "light"  → same but ratio = 0.33
-- AI summaries preferred over Sumy when both exist.
```

---

## 5. What Does NOT Change

- Vision document upload + storage — existing
- 20K token chunking — existing
- Sumy 33% / 66% extractive summaries — still runs on every upload
- Context Manager depth_config toggles — unchanged, just reads from new table
- Product fields and setup wizard UI — fields are fields regardless of who wrote them
- All other MCP tools — unchanged

---

## 6. Build Sequence

| Step | Task | Hours | Depends on |
|------|------|-------|------------|
| 1 | DB migration: vision_document_summaries + extraction_custom_instructions | 0.5 | — |
| 2 | Wire Sumy output into summaries table | 1 | Step 1 |
| 3 | Context Manager: read summaries from new table, prefer AI over Sumy | 1 | Step 2 |
| 4 | MCP tool: /gil_get_vision_doc | 1 | Step 1 |
| 5 | MCP tool: /gil_write_product (flat fields + summaries) | 1.5 | Step 1 |
| 6 | Baked extraction prompt (finalize + store) | 0.5 | — |
| 7 | Upload UI: analysis banner + stage button + WebSocket notification | 1.5 | Steps 4,5 |
| 8 | Product settings: custom instructions text area | 0.5 | — |
| 9 | End-to-end test with Claude Code | 0.5 | All |
| | **Total** | **~8 hrs** | |

---

## 7. Edge Cases

**No CLI tool connected:** "Stage Analysis" shows with helper text: "Requires a connected AI coding tool." Sumy summaries always available. User fills fields manually.

**Document > 20K tokens:** Existing chunker splits. `/gil_get_vision_doc` returns all chunks. Agent's LLM handles chunking strategy — GiljoAI provides content, agent decides how to consume.

**Agent writes bad data:** User reviews and edits in web UI. The prompt says "OMIT fields you can't determine, do NOT guess." HITL safety net is the existing edit form.

**User re-uploads new doc:** New document replaces old. Sumy reruns. "Stage Analysis" available again. Agent overwrites fields on re-analysis.

---

## 8. SaaS Upgrade Path

CE: User's CLI tool analyzes docs. Costs user's tokens. Requires connected tool.

SaaS adds: Server-side Haiku call. Same extraction prompt. Same write logic. No CLI needed. Included in subscription. One new endpoint: `POST /api/products/{id}/vision/analyze`.

The upsell: "CE — your AI analyzes your docs. SaaS — we do it for you."
