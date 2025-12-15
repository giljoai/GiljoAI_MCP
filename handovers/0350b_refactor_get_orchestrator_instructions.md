# Handover 0350b: Refactor get_orchestrator_instructions to Framing-Based Architecture

**Series**: 0350 (Context Management On-Demand Architecture)
**Date**: 2025-12-15
**Status**: PROPOSED
**Priority**: HIGH
**Context**: Handover 0350a (fetch_context() unified tool), Handover 0347 (Context Management v2.0)

## Executive Summary

Refactor `get_orchestrator_instructions()` MCP tool from monolithic inline context delivery (~4-8K tokens, up to 50K with vision) to a framing-based architecture (~500 tokens). Instead of embedding ALL context inline, return framing instructions that tell the orchestrator WHICH fetch tools to call and WHY.

**Problem**: Current implementation causes:
- Token overflow when vision docs (50K) or agent templates (40K) are included
- Truncation risk in Claude Code CLI
- Inability to re-fetch context mid-session
- Violates thin-client architecture principles (context lives on server, not clipboard)

**Solution**: Return identity + framing instructions instead of inline context. Orchestrator calls MCP fetch tools dynamically based on project needs.

---

## Why On-Demand Architecture (The Concrete Problem)

### Token Limit Error

When prompts exceed 25K tokens, Claude Code returns this error:

```
Error: File content (66498 tokens) exceeds maximum allowed tokens (25000).
Please use offset and limit parameters to read specific portions of the file,
or use the GrepTool to search for specific content.
```

**This is why a monolithic `get_orchestrator_instructions` CANNOT inline all context.**

### Token Budget Analysis

| Context Source | Potential Size | Monolithic Impact |
|---------------|----------------|-------------------|
| Vision Document | **50K tokens** | TRUNCATION/ERROR |
| Agent Templates | 5K x 8 = **40K tokens** | TRUNCATION/ERROR |
| 360 Memory | **10K+ tokens** | OVERFLOW |
| Inline Total | **100K+** | IMPOSSIBLE |

**Solution**: Return ~500 token framing instructions; orchestrator fetches what it needs via unified `fetch_context()` MCP tool.

---

## CRITICAL: Project Description Always Inline

**MUST PRESERVE**: The "Project Description" (formerly "Project Context") is:
- ✅ **HARDCODED** as CRITICAL in `get_orchestrator_instructions()`
- ✅ **NOT TOGGLEABLE** - users cannot change priority or disable it
- ✅ **ALWAYS INLINE** - injected directly, never a fetch pointer
- ✅ **UI shows**: "Project Description - Always Critical" (locked chip)

**Why?** The orchestrator MUST know what project it's working on before it can decide which other tools to call. This is the ONE field that stays inline.

### Response Structure

```
┌────────────────────────────────────────────────────────────────┐
│  INLINE (always in response)        FRAMING (single tool)     │
│  ─────────────────────────────      ───────────────────────── │
│  • project_description              • fetch_context()         │
│  • mission (if exists)                - categories param      │
│  • identity (IDs, keys)               - depth_config param    │
│                                       - apply_user_config     │
│  (~100-200 tokens)                                            │
│                                     Categories available:     │
│                                     • product_core            │
│                                     • vision_documents        │
│                                     • tech_stack              │
│                                     • architecture            │
│                                     • testing                 │
│                                     • memory_360              │
│                                     • git_history             │
│                                     • agent_templates         │
│                                     • project                 │
│                                                               │
│  Total Response: ~500 tokens (under 25K limit)                │
└────────────────────────────────────────────────────────────────┘
```

---

## Architecture Transformation

### Before (Monolithic Inline - Current State)

```json
// get_orchestrator_instructions() response
{
  "orchestrator_id": "uuid",
  "mission": "MASSIVE INLINE CONTEXT WITH VISION DOCS, TECH STACK, EVERYTHING EMBEDDED...",
  "field_priorities": {"vision_documents": 2, "tech_stack": 1},
  "estimated_tokens": 8000  // Can spike to 50K with vision
}
```

**Problems**:
- All context embedded in `mission` field (4-8K base, up to 50K with vision)
- No way to re-fetch updated context mid-session
- Violates thin-client principle (context should live on server)
- Truncation risk when vision/templates enabled

### After (Framing-Based - Target State)

```json
// get_orchestrator_instructions() response
{
  "identity": {
    "orchestrator_id": "uuid",
    "project_id": "uuid",
    "tenant_key": "tk_xxx",
    "project_name": "My Project",
    "instance_number": 1
  },
  "project_context_inline": {
    "description": "User's project description (ALWAYS inline - MANDATORY)",
    "mission": "Orchestrator's mission plan from staging"
  },
  "context_fetch_instructions": {
    "critical": [
      {
        "field": "product_core",
        "tool": "fetch_context",
        "params": {"category": "product_core", "product_id": "uuid", "tenant_key": "tk_xxx"},
        "framing": "REQUIRED: Product name, description, and core features. Essential foundation for all work.",
        "estimated_tokens": 100
      },
      {
        "field": "tech_stack",
        "tool": "fetch_context",
        "params": {"category": "tech_stack", "product_id": "uuid", "tenant_key": "tk_xxx"},
        "framing": "REQUIRED: Programming languages, frameworks, and databases. Critical for implementation decisions.",
        "estimated_tokens": 200
      }
    ],
    "important": [
      {
        "field": "architecture",
        "tool": "fetch_context",
        "params": {"category": "architecture", "product_id": "uuid", "tenant_key": "tk_xxx"},
        "framing": "RECOMMENDED: System architecture patterns and design principles. Highly valuable for planning.",
        "estimated_tokens": 400
      },
      {
        "field": "vision_documents",
        "tool": "fetch_context",
        "params": {"category": "vision_documents", "product_id": "uuid", "tenant_key": "tk_xxx", "offset": 0, "limit": 10},
        "framing": "RECOMMENDED: Product vision and strategic direction. Use pagination for large documents.",
        "estimated_tokens": 5000,
        "supports_pagination": true
      }
    ],
    "reference": [
      {
        "field": "memory_360",
        "tool": "fetch_context",
        "params": {"category": "memory_360", "product_id": "uuid", "tenant_key": "tk_xxx", "limit": 5},
        "framing": "OPTIONAL: Historical project outcomes. Reference when building on previous work.",
        "estimated_tokens": 2000
      }
    ]
  },
  "mcp_tools_available": [
    "fetch_context",
    "spawn_agent_job",
    "get_available_agents",
    "send_message",
    "check_succession_status"
  ],
  "context_budget": 150000,
  "context_used": 0,
  "thin_client": true
}
```

**Benefits**:
- Response is ~500 tokens (vs 4-8K current, 50K worst-case)
- Orchestrator fetches context on-demand via `fetch_context()` tool
- Can re-fetch context mid-session (e.g., updated settings)
- Respects user's depth configuration (stored server-side)
- No truncation risk

---

## 3-Tier Priority System

| Priority | Tier Label | Framing Language | When to Call |
|----------|------------|------------------|--------------|
| 1 | CRITICAL | "REQUIRED: You MUST call this tool before proceeding." | Always - needed for basic operation |
| 2 | IMPORTANT | "RECOMMENDED: You SHOULD call this tool for best results." | High value - call unless budget constrained |
| 3 | REFERENCE | "OPTIONAL: Call if project scope requires this context." | Use as needed - specific scenarios only |
| 4 | EXCLUDED | (not mentioned) | Never - user explicitly disabled |

**Tier Assignment Logic**:
- User's `field_priorities` dict maps fields to priority (1-4)
- Priority 1 → `critical` tier
- Priority 2 → `important` tier
- Priority 3 → `reference` tier
- Priority 4 → Excluded (not mentioned in instructions)

---

## Implementation Plan

### Phase 1: Add New Method to MissionPlanner

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py`

Add new method `_build_fetch_instructions()` that maps field priorities to fetch tool configs:

```python
def _build_fetch_instructions(
    self,
    product: Product,
    project: Project,
    field_priorities: dict,
    depth_config: dict
) -> dict:
    """
    Build framing instructions for context fetch tools (Handover 0351).

    Maps user's field priorities to tier-based fetch instructions.
    Each instruction includes: tool name, params, framing text, token estimate.

    Args:
        product: Product model with metadata
        project: Project model with metadata
        field_priorities: Dict mapping field names to priority (1-4)
        depth_config: Dict mapping field names to depth levels

    Returns:
        {
            "critical": [{"field": "product_core", "tool": "fetch_context", ...}],
            "important": [...],
            "reference": [...]
        }
    """
    instructions = {"critical": [], "important": [], "reference": []}
    tier_map = {1: "critical", 2: "important", 3: "reference"}

    # Tool configuration mapping
    tool_configs = {
        "product_core": {
            "tool": "fetch_context",
            "category": "product_core",
            "framing": "REQUIRED: Product name, description, and core features. Essential foundation for all work.",
            "estimated_tokens": 100
        },
        "vision_documents": {
            "tool": "fetch_context",
            "category": "vision_documents",
            "framing": "Product vision and strategic direction. Use pagination for large documents.",
            "estimated_tokens": 5000,
            "supports_pagination": True,
            "depth_aware": True  # Uses depth_config
        },
        "tech_stack": {
            "tool": "fetch_context",
            "category": "tech_stack",
            "framing": "Programming languages, frameworks, and databases. Critical for implementation decisions.",
            "estimated_tokens": 200
        },
        "architecture": {
            "tool": "fetch_context",
            "category": "architecture",
            "framing": "System architecture patterns, API style, and design principles.",
            "estimated_tokens": 400
        },
        "testing": {
            "tool": "fetch_context",
            "category": "testing",
            "framing": "Quality standards, testing strategy, and frameworks.",
            "estimated_tokens": 300
        },
        "memory_360": {
            "tool": "fetch_context",
            "category": "memory_360",
            "framing": "Historical project outcomes and cumulative product knowledge.",
            "estimated_tokens": 2000,
            "depth_aware": True  # Uses depth_config["memory_360"] for limit
        },
        "git_history": {
            "tool": "fetch_context",
            "category": "git_history",
            "framing": "Recent git commits aggregated across projects.",
            "estimated_tokens": 1500,
            "depth_aware": True  # Uses depth_config["git_history"] for limit
        },
        "agent_templates": {
            "tool": "fetch_context",
            "category": "agent_templates",
            "framing": "Available agent templates for spawning specialized agents.",
            "estimated_tokens": 400,
            "depth_aware": True  # Uses depth_config["agent_templates"] (type_only vs full)
        }
    }

    # Iterate through field priorities and build instructions
    for field, priority in field_priorities.items():
        if priority >= 4:  # Excluded
            continue

        config = tool_configs.get(field)
        if not config:
            logger.warning(f"No fetch tool config for field: {field}")
            continue

        tier = tier_map.get(priority, "reference")

        # Build instruction entry
        instruction = {
            "field": field,
            "tool": config["tool"],
            "params": {
                "category": config["category"],
                "product_id": str(product.id),
                "tenant_key": product.tenant_key
            },
            "framing": self._get_tier_framing(tier, config["framing"]),
            "estimated_tokens": config["estimated_tokens"]
        }

        # Add depth-specific params if applicable
        if config.get("depth_aware"):
            if field == "vision_documents":
                # Vision docs use offset/limit for pagination
                instruction["params"]["offset"] = 0
                instruction["params"]["limit"] = depth_config.get("vision_documents", 10)
                instruction["supports_pagination"] = True
            elif field == "memory_360":
                instruction["params"]["limit"] = depth_config.get("memory_360", 5)
            elif field == "git_history":
                instruction["params"]["limit"] = depth_config.get("git_history", 20)
            elif field == "agent_templates":
                instruction["params"]["depth"] = depth_config.get("agent_templates", "type_only")

        instructions[tier].append(instruction)

    return instructions

def _get_tier_framing(self, tier: str, base_framing: str) -> str:
    """Add tier-specific prefix to framing text."""
    prefixes = {
        "critical": "REQUIRED: ",
        "important": "RECOMMENDED: ",
        "reference": "OPTIONAL: "
    }
    prefix = prefixes.get(tier, "")

    # Add prefix if not already present
    if not base_framing.startswith(prefix):
        return prefix + base_framing
    return base_framing
```

### Phase 2: Refactor get_orchestrator_instructions()

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py`

Replace the call to `_build_context_with_priorities()` with `_build_fetch_instructions()`:

```python
async def get_orchestrator_instructions(self, orchestrator_id: str, tenant_key: str) -> dict[str, Any]:
    """Fetch orchestrator mission with framing instructions (Handover 0351)"""
    try:
        async with self.db_manager.get_session_async() as session:
            # ... (existing validation and data fetching) ...

            # Generate framing instructions (NEW - replaces inline context)
            planner = MissionPlanner(self.db_manager)
            fetch_instructions = planner._build_fetch_instructions(
                product=product,
                project=project,
                field_priorities=field_priorities,
                depth_config=depth_config
            )

            # Build response with framing structure
            response = {
                "identity": {
                    "orchestrator_id": orchestrator_id,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "tenant_key": tenant_key,
                    "instance_number": orchestrator.instance_number or 1
                },
                "project_context_inline": {
                    "description": project.description or "",
                    "mission": orchestrator.mission or ""
                },
                "context_fetch_instructions": fetch_instructions,
                "mcp_tools_available": [
                    "fetch_context",
                    "spawn_agent_job",
                    "get_available_agents",
                    "send_message",
                    "check_succession_status",
                    "create_successor_orchestrator",
                    "report_progress",
                    "complete_job"
                ],
                "context_budget": orchestrator.context_budget or 150000,
                "context_used": orchestrator.context_used or 0,
                "thin_client": True,
                "architecture": "framing_based",  # Version flag
            }

            # Add CLI mode rules if applicable
            execution_mode = getattr(project, 'execution_mode', None) or metadata.get("execution_mode", "multi_terminal")
            if execution_mode == "claude_code_cli":
                response["cli_mode_rules"] = {
                    # ... (existing CLI mode rules) ...
                }

            return response

    except Exception as e:
        logger.exception(f"Failed to get orchestrator instructions: {e}")
        return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}
```

### Phase 3: Staging Prompt Update

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\prompt_generation\thin_client_prompt_generator.py`

Update staging prompt to instruct orchestrator to fetch context:

```python
def _build_staging_prompt(self, orchestrator_id: str, tenant_key: str, ...) -> str:
    """Generate staging prompt for orchestrator (Handover 0246a)"""

    prompt = f"""
You are the Orchestrator for this project. Your mission is to understand context, plan work, and spawn agents.

## STEP 1: Fetch Your Instructions

Call this tool FIRST to get your mission and context framing:
```
get_orchestrator_instructions(
    orchestrator_id="{orchestrator_id}",
    tenant_key="{tenant_key}"
)
```

This returns:
- Your project description and mission
- Framing instructions for context fetch tools (what to call and why)
- Available MCP tools

## STEP 2: Fetch Required Context

Based on the framing instructions, call `fetch_context()` for CRITICAL tier items:
- These are marked "REQUIRED" - you MUST fetch them
- Example: fetch_context(category="product_core", product_id="...", tenant_key="...")

## STEP 3: Fetch Recommended Context

Call `fetch_context()` for IMPORTANT tier items if your context budget allows:
- These are marked "RECOMMENDED" - highly valuable
- Skip only if budget constrained

## STEP 4: Optionally Fetch Reference Context

Call `fetch_context()` for REFERENCE tier items if project scope requires:
- These are marked "OPTIONAL" - use as needed
- Example: Historical memory when building on previous work

## STEP 5-7: Continue with 7-Task Staging Workflow

[Rest of staging workflow - agent discovery, spawning, activation]
```

---

## Tool Implementation: fetch_context()

**IMPORTANT**: This handover does NOT implement the `fetch_context()` tool. That is **Handover 0350a** (prerequisite - must be completed first).

This handover focuses on REFACTORING `get_orchestrator_instructions()` to RETURN FRAMING INSTRUCTIONS instead of inline context.

The framing instructions will reference `fetch_context()` tool with this signature:

```python
async def fetch_context(
    product_id: str,
    tenant_key: str,
    project_id: Optional[str] = None,
    categories: List[str] = ["all"],  # Can specify multiple: ["product_core", "tech_stack"]
    depth_config: Optional[Dict[str, str]] = None,  # Per-category depth overrides
    apply_user_config: bool = True,  # Whether to apply user's saved settings
    format: str = "structured"  # "structured" or "flat"
) -> dict:
    """
    Unified context fetch tool (Handover 0350a - PREREQUISITE).

    Single entry point for all context categories.
    Respects user's depth settings from Settings -> Context UI.
    Returns actual context data, not framing instructions.

    See Handover 0350a for full implementation details.
    """
```

---

## Migration Strategy

### Backward Compatibility

To ensure smooth transition, maintain both approaches temporarily:

```python
async def get_orchestrator_instructions(self, orchestrator_id: str, tenant_key: str, mode: str = "framing") -> dict[str, Any]:
    """
    Fetch orchestrator mission.

    Args:
        mode: "framing" (new) or "inline" (legacy) - default framing
    """
    if mode == "inline":
        # Legacy path: Use _build_context_with_priorities()
        condensed_mission = await planner._build_context_with_priorities(...)
        return {
            "mission": condensed_mission,
            "field_priorities": field_priorities,
            # ... (existing format)
        }
    else:
        # New path: Use _build_fetch_instructions()
        fetch_instructions = planner._build_fetch_instructions(...)
        return {
            "identity": {...},
            "context_fetch_instructions": fetch_instructions,
            # ... (new format)
        }
```

**Rollout Plan**:
1. Week 1: Deploy with `mode="framing"` default
2. Week 2: Monitor orchestrator behavior, verify fetch calls
3. Week 3: Remove legacy path if no issues

### Testing Strategy

**Unit Tests** (`tests/unit/test_mission_planner.py`):
```python
async def test_build_fetch_instructions_tier_assignment():
    """Test that field priorities map correctly to tiers"""
    planner = MissionPlanner(db_manager)

    field_priorities = {
        "product_core": 1,    # CRITICAL tier
        "tech_stack": 2,      # IMPORTANT tier
        "memory_360": 3,      # REFERENCE tier
        "excluded_field": 4   # Omitted
    }

    instructions = planner._build_fetch_instructions(
        product=mock_product,
        project=mock_project,
        field_priorities=field_priorities,
        depth_config={}
    )

    assert "product_core" in [i["field"] for i in instructions["critical"]]
    assert "tech_stack" in [i["field"] for i in instructions["important"]]
    assert "memory_360" in [i["field"] for i in instructions["reference"]]
    assert "excluded_field" not in str(instructions)

async def test_build_fetch_instructions_depth_params():
    """Test that depth config translates to fetch params"""
    planner = MissionPlanner(db_manager)

    depth_config = {
        "vision_documents": 20,      # limit=20
        "memory_360": 10,            # limit=10
        "agent_templates": "full"    # depth=full
    }

    instructions = planner._build_fetch_instructions(
        product=mock_product,
        project=mock_project,
        field_priorities={"vision_documents": 2, "memory_360": 3, "agent_templates": 2},
        depth_config=depth_config
    )

    # Find vision_documents instruction
    vision_instr = next(i for tier in instructions.values() for i in tier if i["field"] == "vision_documents")
    assert vision_instr["params"]["limit"] == 20
    assert vision_instr["supports_pagination"] == True

    # Find agent_templates instruction
    agent_instr = next(i for tier in instructions.values() for i in tier if i["field"] == "agent_templates")
    assert agent_instr["params"]["depth"] == "full"
```

**Integration Tests** (`tests/integration/test_orchestrator_instructions.py`):
```python
async def test_get_orchestrator_instructions_framing_response():
    """Test that get_orchestrator_instructions returns framing structure"""
    tool_accessor = ToolAccessor(db_manager, tenant_manager)

    result = await tool_accessor.get_orchestrator_instructions(
        orchestrator_id=test_orchestrator_id,
        tenant_key=test_tenant_key
    )

    # Verify framing structure
    assert "identity" in result
    assert "project_context_inline" in result
    assert "context_fetch_instructions" in result
    assert "thin_client" in result
    assert result["architecture"] == "framing_based"

    # Verify tier structure
    assert "critical" in result["context_fetch_instructions"]
    assert "important" in result["context_fetch_instructions"]
    assert "reference" in result["context_fetch_instructions"]

    # Verify token reduction
    import json
    response_text = json.dumps(result)
    token_count = len(response_text) // 4  # Rough estimate
    assert token_count < 1000  # Should be ~500 tokens, not 4-8K
```

---

## Success Criteria

1. **Token Reduction**: `get_orchestrator_instructions()` response is <1,000 tokens (target: ~500)
2. **No Inline Context**: Only project description/mission inline, everything else via framing
3. **Tier Assignment**: All fields correctly mapped to critical/important/reference tiers
4. **Depth Params**: Depth config correctly translates to fetch tool params
5. **Backward Compatible**: Legacy orchestrators still work during transition
6. **Test Coverage**: >90% coverage for new methods

---

## Files Modified

### Primary Changes

1. **`F:\GiljoAI_MCP\src\giljo_mcp\mission_planner.py`**
   - Add `_build_fetch_instructions()` method (~150 lines)
   - Add `_get_tier_framing()` helper method (~15 lines)
   - Keep `_build_context_with_priorities()` for backward compatibility (mark deprecated)

2. **`F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py`**
   - Refactor `get_orchestrator_instructions()` method
   - Replace `_build_context_with_priorities()` call with `_build_fetch_instructions()`
   - Update response structure to framing-based format

3. **`F:\GiljoAI_MCP\src\giljo_mcp\prompt_generation\thin_client_prompt_generator.py`**
   - Update `_build_staging_prompt()` to instruct orchestrator to fetch context
   - Add instructions for CRITICAL/IMPORTANT/REFERENCE tier handling

### Test Files

4. **`F:\GiljoAI_MCP\tests\unit\test_mission_planner.py`**
   - Add `test_build_fetch_instructions_tier_assignment()`
   - Add `test_build_fetch_instructions_depth_params()`
   - Add `test_build_fetch_instructions_framing_text()`

5. **`F:\GiljoAI_MCP\tests\integration\test_orchestrator_instructions.py`**
   - Add `test_get_orchestrator_instructions_framing_response()`
   - Add `test_get_orchestrator_instructions_token_count()`

### Documentation

6. **`F:\GiljoAI_MCP\docs\ORCHESTRATOR.md`**
   - Update "Context Delivery" section with framing architecture
   - Add examples of framing-based responses
   - Document tier system (CRITICAL/IMPORTANT/REFERENCE)

7. **`F:\GiljoAI_MCP\CLAUDE.md`**
   - Update "Orchestrator Workflow Pipeline" section
   - Add note about framing-based architecture (v3.2+)

---

## Rollback Plan

If framing-based approach causes issues:

1. Change default mode to `mode="inline"` in `get_orchestrator_instructions()`
2. Revert staging prompt to NOT instruct fetch calls
3. Keep framing code for future use (don't delete)

**Rollback Command**:
```python
# In tool_accessor.py
async def get_orchestrator_instructions(self, orchestrator_id: str, tenant_key: str, mode: str = "inline") -> dict[str, Any]:
    # Change default from "framing" to "inline"
```

---

## Related Handovers

- **Handover 0350a**: Create Unified `fetch_context()` Tool (PREREQUISITE - must complete first)
- **Handover 0350c**: Frontend 3-Tier UI + Field Rename (companion - UI changes)
- **Handover 0350d**: Documentation Updates (companion - docs)
- **Handover 0347**: Context Management v2.0 (field priorities, depth config)
- **Handover 0246a**: 7-Task Staging Workflow (updated with framing instructions)
- **Handover 0088**: Thin Client Architecture (original vision)

---

## Token Impact Analysis

### Current State (Inline)
- Base response: ~4,000 tokens
- With vision docs: ~50,000 tokens (TRUNCATION RISK)
- With agent templates (full): ~8,000 tokens
- **Total worst-case**: ~60,000 tokens

### Target State (Framing)
- Base response: ~500 tokens
- Framing instructions: ~200 tokens
- Project description inline: ~100 tokens
- **Total**: ~800 tokens (92% reduction)

### Fetch Calls (Deferred)
- Orchestrator calls `fetch_context()` 3-8 times
- Each fetch: 100-5,000 tokens (depends on category)
- **Benefit**: Orchestrator controls when/what to fetch based on task needs

---

## Developer Notes

### Why Framing Instead of Inline?

1. **Token Budget Control**: Orchestrator decides what context to fetch based on task complexity
2. **Re-fetch Capability**: Can re-fetch updated context mid-session (e.g., user changes settings)
3. **Thin-Client Principle**: Context lives on server (via MCP tools), not in clipboard prompts
4. **Auditability**: Each fetch call is logged, trackable via MCP tool calls
5. **Scalability**: No truncation risk as context grows (vision docs, memory, templates)

### Why 3 Tiers Instead of 4?

User's field priorities use 4 levels (1-4), but framing uses 3 tiers (critical/important/reference):
- **Priority 1 → CRITICAL tier**: Must fetch (REQUIRED)
- **Priority 2 → IMPORTANT tier**: Should fetch (RECOMMENDED)
- **Priority 3 → REFERENCE tier**: Can fetch if needed (OPTIONAL)
- **Priority 4 → Excluded**: Not mentioned (orchestrator doesn't know it exists)

This simplifies decision-making for the orchestrator (3 clear levels vs 4 ambiguous levels).

### What About Serena MCP?

Serena integration is orthogonal to framing architecture:
- If `include_serena=True`, add Serena notice to `project_context_inline.mission`
- Serena instructions remain inline (they're small ~200 tokens)
- Codebase context fetched via Serena's own tools (not `fetch_context()`)

---

## Approval Required

**BEFORE IMPLEMENTING**, confirm:
- [ ] Approach aligns with product vision (thin-client architecture)
- [ ] Handover 0352 (`fetch_context()` implementation) is scheduled/prioritized
- [ ] Token reduction target (~500 tokens) is acceptable
- [ ] 3-tier system (critical/important/reference) is clear enough for orchestrators
- [ ] Backward compatibility plan is sufficient

**Orchestrator Coordinator**: Please review and approve before TDD Implementor begins work.
