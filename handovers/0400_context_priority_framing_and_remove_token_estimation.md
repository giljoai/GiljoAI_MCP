# Handover 0400: Context Priority/Framing System & Remove Token Estimation

## Summary

This document describes how the context priority and framing system works, based on live testing with Claude Code orchestrator. It also specifies removing the `estimated_tokens` field as unnecessary.

---

## 1. Tool Used for Context Fetching

The orchestrator fetches context using:

```
mcp__giljo-mcp__get_orchestrator_instructions(job_id, tenant_key)
```

This returns:
- `identity` - job/agent/project IDs
- `project_description_inline` - always-on project description
- `context_fetch_instructions` - prioritized categories with fetch params
- `agent_templates` - available agents for spawning
- `field_priorities` - numeric priority map
- `context_budget` / `context_used` - token budget tracking

---

## 2. How User Configures Context (UI Flow)

The user configures context through the web frontend with:

### 2.1 Nine Context Categories
1. **Project Description** - Always on, user cannot toggle (priority always 1)
2. **Product Description** (product_core)
3. **Tech Stack**
4. **Architecture**
5. **Testing**
6. **Vision Documents** - Has depth config (light/medium/full)
7. **360 Memory** - Has limit config (1/3/5 projects)
8. **Git History** - Has limit config (5/10/25/50 commits)
9. **Agent Templates** - Has depth config (type_only/with_descriptions/full)

### 2.2 Priority Levels (User Selects)
| UI Label | Priority Number | Framing Text | Agent Behavior |
|----------|-----------------|--------------|----------------|
| CRITICAL | 1 | "REQUIRED: ..." | Fetch first, cannot skip |
| IMPORTANT | 2 | "RECOMMENDED: ..." | Strongly fetch, skip only if token-starved |
| REFERENCE | 3 | "OPTIONAL: ..." | Optional, fetch if budget allows |

### 2.3 Depth/Limit Configurations
Some categories have additional depth settings:

| Category | Options | Effect |
|----------|---------|--------|
| Vision Documents | light (33%), medium (66%), full (100%) | Controls summary length |
| 360 Memory | 1, 3, 5 projects | How many historical projects |
| Git History | 5, 10, 25, 50 commits | How many recent commits |
| Agent Templates | type_only, with_descriptions, full | Detail level |

---

## 3. How Priority/Framing Appears in API Response

When user sets all categories to IMPORTANT (priority 2):

```json
{
  "context_fetch_instructions": {
    "critical": [],
    "important": [
      {
        "field": "product_core",
        "tool": "fetch_context",
        "params": {
          "category": "product_core",
          "product_id": "...",
          "tenant_key": "..."
        },
        "framing": "RECOMMENDED: Product name, description, and core features.",
        "estimated_tokens": 100  // <-- REMOVE THIS FIELD
      },
      // ... other categories
    ],
    "reference": []
  },
  "field_priorities": {
    "product_core": 2,
    "tech_stack": 2,
    "architecture": 2,
    "testing": 2,
    "vision_documents": 2,
    "memory_360": 2,
    "git_history": 2,
    "agent_templates": 2,
    "project_description": 1  // Always 1
  }
}
```

---

## 4. Verified Behavior (Live Testing Results)

During testing, we confirmed:

| User Action | Server Response Change |
|-------------|------------------------|
| Set Vision Docs: medium → light | `depth: "medium"` → `depth: "light"`, framing changed to "33%" |
| Set all to REFERENCE (3) | All categories moved to `reference` bucket, framing = "OPTIONAL" |
| Set all to IMPORTANT (2) | All categories moved to `important` bucket, framing = "RECOMMENDED" |
| Set 360 Memory limit: 1 → 3 | `limit: 1` → `limit: 3` in params |
| Set Git History: 5 → 25 | `limit: 5` → `limit: 25` in params |

**All UI changes propagate correctly to API response in real-time.**

---

## 5. Task: Remove Token Estimation

### 5.1 Why Remove
1. **Maintenance burden** - Estimates become stale as content changes
2. **Priority/framing already guides agent behavior** - Numeric priority + framing text is sufficient
3. **False precision** - Static estimates don't reflect actual content size
4. **Actual usage tracked elsewhere** - `context_budget` and `context_used` provide real tracking

### 5.2 What to Remove
Remove `estimated_tokens` field from all context_fetch_instructions entries.

**Before:**
```json
{
  "field": "vision_documents",
  "framing": "RECOMMENDED: 66% summarized vision document.",
  "estimated_tokens": 8000  // REMOVE
}
```

**After:**
```json
{
  "field": "vision_documents",
  "framing": "RECOMMENDED: 66% summarized vision document."
}
```

### 5.3 Files to Modify
Search the codebase for `estimated_tokens` - likely locations:
- `src/giljo_mcp/services/orchestration_service.py` - where context instructions are built
- `src/giljo_mcp/services/context_service.py` - if token estimation logic exists
- Any context builder or prioritization module

### 5.4 Optional Enhancement
If lightweight size hints are desired (not required), could replace with qualitative labels:
```json
"size_hint": "small"   // <500 tokens
"size_hint": "medium"  // 500-5K tokens
"size_hint": "large"   // 5K+ tokens
```

But this is optional - priority/framing alone is sufficient for agent decision-making.

---

## 6. Summary for Implementing Agent

1. **Tool**: `get_orchestrator_instructions(job_id, tenant_key)` returns prioritized context
2. **Priority system works**: UI priority (CRITICAL/IMPORTANT/REFERENCE) → numeric (1/2/3) → framing (REQUIRED/RECOMMENDED/OPTIONAL)
3. **Depth configs work**: light/medium/full, limits all propagate correctly
4. **Remove `estimated_tokens`**: Search codebase, remove from all context instruction builders
5. **Keep**: `context_budget`, `context_used`, priority numbers, framing text

---

## References
- Architecture slides: `F:\GiljoAI_MCP\handovers\Reference_docs\Workflow PPT to JPG\Slide2-4.JPG`
- Agent instructions: `F:\GiljoAI_MCP\handovers\Agent instructions and where they live.md`
