# Context Tools API Reference

**Version**: v3.0 (On-Demand Fetch Architecture)
**Last Updated**: 2025-12-21 (Corrected for Handover 0351 single-category enforcement)
**Implementation**: Handover 0350a-c, 0351 (single-category enforcement)

## Overview

GiljoAI uses an on-demand context fetch architecture with a **single unified `fetch_context()` tool** that replaces 9 individual tools. This approach:

- Saves ~720 tokens in MCP schema overhead
- Prevents context truncation for large vision documents
- Enables smart priority-based fetching

## Architecture

### On-Demand Fetch Pattern

```
1. Orchestrator calls get_orchestrator_instructions()
           ↓
2. Receives framing (~500 tokens) with priority indicators:
   {
     "context_fetch_instructions": {
       "critical": [{"field": "product_core", "tool": "fetch_context", ...}],
       "important": [{"field": "tech_stack", ...}],
       "reference": [{"field": "memory_360", ...}]
     }
   }
           ↓
3. Orchestrator calls fetch_context SEPARATELY for each category:
   - fetch_context(categories=["product_core"])
   - fetch_context(categories=["tech_stack"])
   - fetch_context(categories=["memory_360"])
           ↓
4. Context assembled without truncation risk
```

### 3-Tier Priority System

| Tier | Label | Framing | Orchestrator Action |
|------|-------|---------|---------------------|
| **Priority 1** | CRITICAL | "REQUIRED" | MUST call `fetch_context()` |
| **Priority 2** | IMPORTANT | "RECOMMENDED" | SHOULD call if budget allows |
| **Priority 3** | REFERENCE | "OPTIONAL" | MAY call if project requires |
| **Priority 4** | OFF | (excluded) | Never call tool |

---

## Unified fetch_context() Tool

### Signature

```python
async def fetch_context(
    product_id: str,              # Product UUID (required)
    tenant_key: str,              # Tenant isolation key (required)
    project_id: Optional[str],    # Project UUID (required for 'project' category)
    categories: List[str],        # MUST contain exactly ONE category (enforced in code)
    depth_config: Optional[Dict], # Override depth settings
    apply_user_config: bool,      # Apply saved priority/depth settings (default: True)
    format: str,                  # "structured" (nested) or "flat" (merged)
    db_manager: Optional[...]     # Database manager instance
) -> Dict[str, Any]
```

**CRITICAL (Handover 0351)**: The `categories` parameter is an array type, but the implementation **enforces exactly ONE category per call**. Multi-category calls will return an error. This is code-level enforcement for token budget control in SaaS environments.

### Available Categories

| Category | Description | Token Range |
|----------|-------------|-------------|
| `product_core` | Product name, description, features | ~100 tokens |
| `vision_documents` | Vision document chunks (paginated) | 0-24K tokens |
| `tech_stack` | Programming languages, frameworks, databases | 200-400 tokens |
| `architecture` | Architecture patterns, API style | 300-1.5K tokens |
| `testing` | Testing strategy, frameworks | 0-400 tokens |
| `memory_360` | Sequential project history (closeouts) | 500-5K tokens |
| `git_history` | Aggregated git commits | 500-5K tokens |
| `agent_templates` | Agent template library | 400-2.4K tokens |
| `project` | Current project metadata | ~300 tokens |

### Depth Options

| Category | Depth Options | Default |
|----------|--------------|---------|
| `vision_documents` | none / light / medium / full | medium |
| `tech_stack` | required / all | all |
| `architecture` | overview / detailed | overview |
| `testing` | none / basic / full | full |
| `memory_360` | 1 / 3 / 5 / 10 (projects) | 5 |
| `git_history` | 10 / 25 / 50 / 100 (commits) | 25 |
| `agent_templates` | minimal / standard / full | standard |

---

## Usage Examples

> **ANTI-PATTERN WARNING (Handover 0351)**
>
> The `categories` parameter is **array-typed** but **MUST contain exactly ONE category**. Multi-category calls will fail with `SINGLE_CATEGORY_REQUIRED` error.
>
> ❌ **WRONG**: `categories=["product_core", "tech_stack"]` - Will return error
> ❌ **WRONG**: `categories=["all"]` - Not allowed
> ✅ **CORRECT**: `categories=["product_core"]` - One category per call
>
> To fetch multiple categories, make **multiple separate calls**.

### Basic Usage (Single Category)

```python
# Fetch core product context
result = await fetch_context(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    categories=["product_core"]  # Exactly ONE category
)

# Fetch tech stack (separate call)
result = await fetch_context(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    categories=["tech_stack"]  # Exactly ONE category
)
```

### With Depth Configuration

```python
# Fetch vision documents with light depth
result = await fetch_context(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    categories=["vision_documents"],  # Exactly ONE category
    depth_config={"vision_documents": "light"}  # Summaries only
)

# Fetch 360 memory (last 3 projects)
result = await fetch_context(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    categories=["memory_360"],  # Exactly ONE category
    depth_config={"memory_360": 3}
)
```

### With Project Context

```python
# Fetch project-specific data
result = await fetch_context(
    product_id="123e4567-e89b-12d3-a456-426614174000",
    tenant_key="tenant_abc",
    project_id="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    categories=["project"]  # Exactly ONE category
)
```

### Multiple Categories Requires Multiple Calls

```python
# CORRECT: Call fetch_context separately for each category
product_core = await fetch_context(
    product_id=PRODUCT_ID,
    tenant_key=TENANT_KEY,
    categories=["product_core"]
)

tech_stack = await fetch_context(
    product_id=PRODUCT_ID,
    tenant_key=TENANT_KEY,
    categories=["tech_stack"]
)

# WRONG: Multi-category call will fail with error
result = await fetch_context(
    product_id=PRODUCT_ID,
    tenant_key=TENANT_KEY,
    categories=["product_core", "tech_stack"]  # ❌ ERROR: SINGLE_CATEGORY_REQUIRED
)

# WRONG: categories=["all"] is not allowed
result = await fetch_context(
    product_id=PRODUCT_ID,
    tenant_key=TENANT_KEY,
    categories=["all"]  # ❌ ERROR: ALL_NOT_ALLOWED
)
```

---

## Response Schema

### Structured Format (default)

```json
{
  "source": "fetch_context",
  "categories_requested": ["product_core"],
  "categories_returned": ["product_core"],
  "data": {
    "product_core": {
      "product_name": "GiljoAI MCP",
      "product_description": "Multi-tenant server orchestrating...",
      "core_features": ["Feature 1", "Feature 2"]
    }
  },
  "metadata": {
    "product_id": "uuid",
    "tenant_key": "tenant_abc",
    "estimated_tokens": 100,
    "format": "structured",
    "apply_user_config": true,
    "depth_config_applied": {}
  }
}
```

**Note**: Since only one category is allowed per call, the `data` object will always contain exactly one key.

### Individual Category Schemas

#### product_core

```json
{
  "product_name": "GiljoAI MCP",
  "product_description": "Multi-tenant server orchestrating AI agents...",
  "project_path": "/path/to/project",
  "core_features": ["Feature 1", "Feature 2"],
  "is_active": true,
  "created_at": "2025-11-01T10:00:00"
}
```

#### vision_documents

```json
{
  "documents": [
    {
      "name": "product_vision.md",
      "summary": "Overview of product goals...",
      "content": "# Vision\n\n...",
      "tokens": 1500
    }
  ],
  "total": 3,
  "page": 1,
  "has_more": false
}
```

#### tech_stack

```json
{
  "languages": ["Python", "JavaScript"],
  "frameworks": {
    "backend": ["FastAPI", "SQLAlchemy"],
    "frontend": ["Vue 3", "Vuetify"]
  },
  "databases": ["PostgreSQL"],
  "tools": ["pytest", "ruff", "black"],
  "version_constraints": {
    "python": "3.11+",
    "node": "18+"
  }
}
```

#### architecture

```json
{
  "primary_pattern": "Modular monolith with service layer",
  "api_style": "REST + JSON, WebSockets for real-time",
  "design_patterns": ["Repository", "Dependency Injection", "Factory"],
  "notes": "Local-first, zero-config deployment..."
}
```

#### testing

```json
{
  "strategy": "TDD with >80% coverage",
  "coverage_target": 80,
  "frameworks": ["pytest", "pytest-asyncio", "Vitest"],
  "quality_standards": "Production-grade code required"
}
```

#### memory_360

```json
{
  "sequential_history": [
    {
      "sequence": 1,
      "type": "project_closeout",
      "project_id": "uuid",
      "summary": "Completed feature X...",
      "git_commits": [...],
      "timestamp": "2025-11-16T10:00:00Z"
    }
  ],
  "total": 10,
  "returned": 5
}
```

#### git_history

```json
{
  "commits": [
    {
      "hash": "59db3da6",
      "message": "fix: Complete dynamic tier assignment...",
      "author": "Claude Opus",
      "date": "2025-12-15T10:00:00Z",
      "project_id": "uuid"
    }
  ],
  "total": 100,
  "returned": 25
}
```

#### agent_templates

```json
{
  "templates": [
    {
      "name": "backend-integration-tester",
      "description": "Tests backend integrations...",
      "protocol": "6-phase lifecycle...",
      "capabilities": ["api_testing", "db_validation"]
    }
  ],
  "total": 12
}
```

#### project

```json
{
  "project_name": "Setup project structure",
  "project_description": "This project is about setting up...",
  "project_path": "F:\\TinyContacts",
  "status": "active",
  "created_at": "2025-12-01T10:00:00Z"
}
```

---

## Multi-Tenant Isolation

All context tools enforce multi-tenant isolation:

```python
# All queries filter by tenant_key
stmt = select(Product).where(
    Product.id == product_id,
    Product.tenant_key == tenant_key
)
```

**Security**: Agents cannot access context from other tenants, even with valid product_id.

---

## Error Handling

### Single-Category Enforcement Errors (Handover 0351)

```json
// Error: categories parameter missing or None
{
  "error": "SINGLE_CATEGORY_REQUIRED",
  "message": "fetch_context requires exactly ONE category per call. Call multiple times for multiple categories.",
  "valid_categories": ["product_core", "vision_documents", "tech_stack", "architecture", "testing", "memory_360", "git_history", "agent_templates", "project"],
  "example": "fetch_context(categories=['tech_stack'], ...)",
  "metadata": {"estimated_tokens": 0}
}

// Error: categories=["all"] not allowed
{
  "error": "ALL_NOT_ALLOWED",
  "message": "categories=['all'] is not allowed. Call fetch_context once per category to stay within token budget.",
  "valid_categories": ["product_core", "vision_documents", ...],
  "example": "fetch_context(categories=['vision_documents'], ...)",
  "metadata": {"estimated_tokens": 0}
}

// Error: Multiple categories in array
{
  "error": "SINGLE_CATEGORY_REQUIRED",
  "message": "Only ONE category per call allowed. You requested 2: ['product_core', 'tech_stack']",
  "valid_categories": ["product_core", "vision_documents", ...],
  "example": "Call fetch_context separately for each category",
  "metadata": {"estimated_tokens": 0}
}
```

### Common Error Responses

```json
{
  "source": "fetch_context",
  "categories_requested": ["product_core"],
  "categories_returned": [],
  "data": {},
  "metadata": {
    "error": "product_not_found",
    "estimated_tokens": 0
  }
}
```

**Error Codes**:
- `SINGLE_CATEGORY_REQUIRED`: Missing category, or multiple categories in array (code-enforced)
- `ALL_NOT_ALLOWED`: categories=["all"] not permitted (code-enforced)
- `product_not_found`: Product ID + tenant key combination invalid
- `project_not_found`: Project ID not found for tenant
- `invalid_category`: Category name not recognized
- `invalid_depth`: Depth parameter not recognized
- `database_error`: Database query failed

---

## Token Estimation

Token estimates use the heuristic: **1 token ≈ 4 characters**

```python
def estimate_tokens(data: Any) -> int:
    import json
    text = json.dumps(data)
    return len(text) // 4
```

**Accuracy**: ~90% accurate for JSON responses, may vary for markdown content.

---

## Priority System Integration

When `get_orchestrator_instructions()` returns framing, it includes priority indicators:

```json
{
  "context_fetch_instructions": {
    "critical": [
      {"field": "product_core", "tool": "fetch_context", "framing": "REQUIRED: Call fetch_context(['product_core'])"}
    ],
    "important": [
      {"field": "tech_stack", "tool": "fetch_context", "framing": "RECOMMENDED: Call fetch_context(['tech_stack'])"}
    ],
    "reference": [
      {"field": "memory_360", "tool": "fetch_context", "framing": "OPTIONAL: Call fetch_context(['memory_360']) if project requires"}
    ]
  }
}
```

### Orchestrator Decision Logic

```python
# Example orchestrator logic - ONE category per call
context_data = {}

# CRITICAL: Always fetch (one call per category)
for field_info in context_fetch_instructions["critical"]:
    category = field_info["field"]
    result = await fetch_context(
        product_id=PRODUCT_ID,
        tenant_key=TENANT_KEY,
        categories=[category]  # Exactly ONE category
    )
    context_data[category] = result["data"][category]

# IMPORTANT: Fetch if budget allows (one call per category)
if tokens_remaining > 10000:
    for field_info in context_fetch_instructions["important"]:
        category = field_info["field"]
        result = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=[category]  # Exactly ONE category
        )
        context_data[category] = result["data"][category]

# REFERENCE: Fetch only if specifically needed (one call per category)
for field_info in context_fetch_instructions["reference"]:
    category = field_info["field"]
    if mission_requires(category):
        result = await fetch_context(
            product_id=PRODUCT_ID,
            tenant_key=TENANT_KEY,
            categories=[category]  # Exactly ONE category
        )
        context_data[category] = result["data"][category]
```

---

## Internal Architecture

The `fetch_context()` tool internally dispatches to specialized helper functions (not exposed via MCP):

```
fetch_context(categories=["product_core"])  # Single category only (Handover 0351)
    ↓
┌─────────────────────────────────────────────────┐
│ Single-Category Enforcement (Code-Level)        │
│                                                 │
│  1. Validate categories array has exactly ONE   │
│  2. Reject ["all"] and multi-category calls     │
│  3. Dispatch to internal helper function:       │
│                                                 │
│  get_product_context()  → product_core          │
│  get_vision_document()  → vision_documents      │
│  get_tech_stack()       → tech_stack            │
│  get_architecture()     → architecture          │
│  get_testing()          → testing               │
│  get_360_memory()       → memory_360            │
│  get_git_history()      → git_history           │
│  get_agent_templates()  → agent_templates       │
│  get_project()          → project               │
└─────────────────────────────────────────────────┘
    ↓
Single-category response
```

**Token Savings**: ~720 tokens (9 tool schemas × ~80 tokens vs 1 schema × ~180 tokens)
**Security**: Code-level enforcement prevents LLM from bypassing single-category rule via prompt injection

---

## See Also

- [CLAUDE.md](../../CLAUDE.md#context-management-v30---on-demand-fetch) - Context Management section
- [ORCHESTRATOR.md](../ORCHESTRATOR.md) - Orchestrator workflow documentation
- [thin_client_migration_guide.md](../guides/thin_client_migration_guide.md) - Migration from fat prompts

---

**Code Reference**: `src/giljo_mcp/tools/context_tools/fetch_context.py`
