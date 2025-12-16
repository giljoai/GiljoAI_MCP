# Handover: 0347b - MissionPlanner JSON Refactor

**Date:** 2025-12-14
**From Agent:** Documentation Manager
**To Agent:** TDD Implementor
**Priority:** High
**Estimated Effort:** 3 hours
**Status:** Ready for Implementation
**Dependencies:** 0347a (JSON Context Builder) must be complete first

---

## Task Summary

Refactor `MissionPlanner._build_context_with_priorities()` to use `JSONContextBuilder` instead of markdown string concatenation. This reduces orchestrator mission context from ~21,000 tokens to ~1,500 tokens (93% reduction) while maintaining full context via fetch-on-demand pointers.

**Key Change:** Replace markdown blob assembly with structured JSON building using priority-tiered architecture.

---

## Current Implementation (Markdown Approach)

**File:** `src/giljo_mcp/mission_planner.py`
**Method:** `_build_context_with_priorities()` (lines 1217-1823)

**Current Pattern:**
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:  # ❌ Returns markdown string
    """Build context respecting user's field priorities and depth configuration."""

    context_sections = []  # ❌ List of markdown strings
    total_tokens = 0

    # Product Core (Priority 1)
    product_core_priority = effective_priorities.get("product_core", 1)
    if product_core_priority != 4:
        product_content = f"**Name**: {product.name}"
        if product.description:
            product_content += f"\n**Description**: {product.description}"

        # ❌ Apply markdown framing
        framed_product = self._apply_priority_framing(
            section_name="Product Context",
            content=product_content,
            priority=product_core_priority,
            category_key="product_core",
        )
        context_sections.append(framed_product)  # ❌ Append markdown

    # ... similar patterns for vision, tech_stack, architecture, etc.

    # ❌ Return concatenated markdown blob
    return "\n\n".join(context_sections)  # ~21,000 tokens
```

**Problems:**
1. Inlines all content regardless of priority
2. Priority buried in markdown headers (`## CRITICAL: ...`)
3. Unstructured text forces Claude to parse manually
4. No separation between inline vs fetch-on-demand content
5. Token-heavy even with depth controls

---

## Proposed Implementation (JSON Approach)

**New Pattern:**
```python
from .json_context_builder import JSONContextBuilder

async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> dict:  # ✅ Returns nested dict
    """Build context respecting user's field priorities and depth configuration."""

    builder = JSONContextBuilder()  # ✅ Use builder pattern

    # === CRITICAL Priority (Priority 1) ===

    # Product Core
    product_core_priority = effective_priorities.get("product_core", 1)
    if product_core_priority == 1:  # CRITICAL
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {
            "name": product.name,
            "description": product.description or "",
            "type": product.config_data.get("product_type", "Software")
        })

    # Tech Stack (if CRITICAL)
    tech_priority = effective_priorities.get("tech_stack", 2)
    if tech_priority == 1:
        builder.add_critical("tech_stack")
        builder.add_critical_content("tech_stack", {
            "languages": product.config_data.get("languages", []),
            "backend": product.config_data.get("backend_frameworks", []),
            "frontend": product.config_data.get("frontend_frameworks", []),
            "database": product.config_data.get("databases", {})
        })

    # === IMPORTANT Priority (Priority 2) ===

    # Architecture
    arch_priority = effective_priorities.get("architecture", 2)
    if arch_priority == 2:
        builder.add_important("architecture")
        arch_data = product.config_data.get("architecture", {})
        builder.add_important_content("architecture", {
            "pattern": arch_data.get("pattern"),
            "api_style": arch_data.get("api_style"),
            "design_patterns": arch_data.get("design_patterns", []),
            "fetch_details": "fetch_architecture()"  # ✅ Fetch pointer
        })

    # Testing
    testing_priority = effective_priorities.get("testing", 2)
    if testing_priority == 2:
        builder.add_important("testing")
        builder.add_important_content("testing", {
            "target": "80% coverage",
            "approach": product.config_data.get("testing_approach", "TDD"),
            "frameworks": product.config_data.get("testing_frameworks", [])
        })

    # Agent Templates (minimal - just pointer)
    builder.add_important("agent_templates")
    builder.add_important_content("agent_templates", {
        "discovery_tool": "get_available_agents()",
        "note": "Fetch agent details on-demand"
    })

    # === REFERENCE Priority (Priority 3) ===

    # Vision Documents
    vision_priority = effective_priorities.get("vision_documents", 4)
    if vision_priority == 3:
        builder.add_reference("vision_documents")
        vision_depth = depth_config.get("vision_documents", "medium")

        # Check if vision doc exists
        if product.vision_documents:
            vision_doc = await self._get_active_vision_doc(product)
            if vision_doc:
                builder.add_reference_content("vision_documents", {
                    "available": True,
                    "depth_setting": vision_depth,
                    "estimated_tokens": vision_doc.original_token_count or 0,
                    "chunks": vision_doc.chunk_count if vision_doc.chunked else 1,
                    "summary": vision_doc.summary_light or "Product vision available",
                    "fetch_tool": f"fetch_vision_document(page=N)  # {vision_doc.chunk_count} pages"
                })

    # 360 Memory
    history_priority = effective_priorities.get("memory_360", 4)
    if history_priority == 3:
        builder.add_reference("memory_360")
        memory_depth = depth_config.get("memory_360", 5)

        history_summary = await self._get_memory_summary(product, max_entries=memory_depth)
        builder.add_reference_content("memory_360", {
            "projects": memory_depth,
            "status": history_summary,
            "fetch_tool": f"fetch_360_memory(limit={memory_depth})"
        })

    # Git History
    git_config = product.product_memory.get("git_integration", {}) if product.product_memory else {}
    if git_config.get("enabled"):
        builder.add_reference("git_history")
        git_depth = depth_config.get("git_history", 20)

        builder.add_reference_content("git_history", {
            "commits": git_depth,
            "repository": git_config.get("repository"),
            "fetch_tool": f"fetch_git_history(limit={git_depth})"
        })

    # ✅ Build and return structured dict
    context_dict = builder.build()

    # Token estimation for logging
    import json
    estimated_tokens = len(json.dumps(context_dict)) // 4

    logger.info(
        f"Context built: {estimated_tokens} tokens (JSON structure)",
        extra={
            "product_id": str(product.id),
            "project_id": str(project.id),
            "total_tokens": estimated_tokens,
            "format": "json",
            "critical_fields": len(builder.critical_fields),
            "important_fields": len(builder.important_fields),
            "reference_fields": len(builder.reference_fields),
            "operation": "build_context_with_priorities",
        },
    )

    return context_dict  # ✅ Returns dict, not string
```

---

## Code Changes

### Change 1: Method Signature

**File:** `src/giljo_mcp/mission_planner.py` (line 1217)

**Before:**
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> str:
```

**After:**
```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    depth_config: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False,
) -> dict:  # Changed: str → dict
```

### Change 2: Import Statement

**File:** `src/giljo_mcp/mission_planner.py` (top of file)

**Add:**
```python
from .json_context_builder import JSONContextBuilder
```

### Change 3: Method Body

**File:** `src/giljo_mcp/mission_planner.py` (lines 1333-1823)

**Replace entire method body** following the pattern in "Proposed Implementation" section above.

Key transformations:
- `context_sections = []` → `builder = JSONContextBuilder()`
- `context_sections.append(framed_content)` → `builder.add_critical_content(field, data)`
- `return "\n\n".join(context_sections)` → `return builder.build()`

### Change 4: Update Orchestration Tool Response

**File:** `src/giljo_mcp/tools/orchestration.py`

**Method:** `get_orchestrator_instructions()`

**Before:**
```python
return {
    "orchestrator_id": str(orchestrator.id),
    "mission": context_str,  # String
    # ...
}
```

**After:**
```python
return {
    "orchestrator_id": str(orchestrator.id),
    "mission": context_dict,  # Dict (nested JSON)
    "mission_format": "json",  # New field
    # ...
}
```

---

## Helper Methods to Add

**File:** `src/giljo_mcp/mission_planner.py`

```python
async def _get_active_vision_doc(self, product: Product) -> Optional[VisionDocument]:
    """Get active vision document for product (helper for JSON builder)."""
    async with self.db_manager.get_session_async() as session:
        from sqlalchemy import select
        from src.giljo_mcp.models.products import VisionDocument

        stmt = select(VisionDocument).where(
            VisionDocument.product_id == product.id,
            VisionDocument.tenant_key == product.tenant_key,
            VisionDocument.is_active == True
        ).order_by(
            VisionDocument.display_order,
            VisionDocument.created_at.desc()
        ).limit(1)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def _get_memory_summary(self, product: Product, max_entries: int = 5) -> str:
    """Get brief summary of 360 memory (for reference pointers)."""
    if not product.product_memory:
        return "No project history available"

    sequential_history = product.product_memory.get("sequential_history", [])
    if not sequential_history:
        return "No project history available"

    # Sort by sequence descending, take max_entries
    sorted_history = sorted(sequential_history, key=lambda x: x.get("sequence", 0), reverse=True)
    recent = sorted_history[:max_entries]

    count = len(recent)
    return f"{count} completed projects in history (most recent: {recent[0].get('summary', 'N/A')[:50]}...)"
```

---

## TDD Test Cases

**File:** `tests/services/test_mission_planner_json.py`

```python
import pytest
from src.giljo_mcp.mission_planner import MissionPlanner

@pytest.mark.asyncio
async def test_build_context_returns_dict_not_string(mission_planner, product, project):
    """Verify context builder returns dict instead of markdown string."""
    context = await mission_planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={"product_core": 1, "tech_stack": 2},
        depth_config={"memory_360": 3, "git_history": 10}
    )

    assert isinstance(context, dict), "Context must be dict, not string"
    assert "priority_map" in context, "Must include priority_map"
    assert "critical" in context, "Must include critical section"
    assert "important" in context, "Must include important section"
    assert "reference" in context, "Must include reference section"

@pytest.mark.asyncio
async def test_critical_priority_fields_inline(mission_planner, product, project):
    """CRITICAL priority fields should have full content inlined."""
    context = await mission_planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={"product_core": 1},  # Priority 1 = CRITICAL
        depth_config={}
    )

    assert "product_core" in context["priority_map"]["critical"]
    assert "product_core" in context["critical"]
    assert "name" in context["critical"]["product_core"]
    assert "description" in context["critical"]["product_core"]

@pytest.mark.asyncio
async def test_reference_fields_have_fetch_pointers(mission_planner, product, project):
    """REFERENCE priority fields should have fetch tool pointers."""
    context = await mission_planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={"vision_documents": 3},  # Priority 3 = REFERENCE
        depth_config={"vision_documents": "medium"}
    )

    if "vision_documents" in context.get("reference", {}):
        vision = context["reference"]["vision_documents"]
        assert "fetch_tool" in vision, "Reference must include fetch tool pointer"
        assert "fetch_vision_document" in vision["fetch_tool"]

@pytest.mark.asyncio
async def test_token_count_under_2000(mission_planner, product, project):
    """JSON structure should be under 2000 tokens (~8000 chars)."""
    import json

    context = await mission_planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={
            "product_core": 1,
            "tech_stack": 2,
            "architecture": 2,
            "vision_documents": 3,
            "memory_360": 3
        },
        depth_config={
            "vision_documents": "medium",
            "memory_360": 3,
            "git_history": 10
        }
    )

    json_str = json.dumps(context)
    estimated_tokens = len(json_str) // 4

    assert estimated_tokens < 2000, f"Token count {estimated_tokens} exceeds 2000 token target"

@pytest.mark.asyncio
async def test_excluded_fields_not_present(mission_planner, product, project):
    """Fields with priority 4 (EXCLUDED) should not appear in output."""
    context = await mission_planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={
            "product_core": 1,
            "vision_documents": 4  # EXCLUDED
        },
        depth_config={}
    )

    # Vision should not appear in any priority tier
    assert "vision_documents" not in context["priority_map"]["critical"]
    assert "vision_documents" not in context["priority_map"]["important"]
    assert "vision_documents" not in context["priority_map"]["reference"]
    assert "vision_documents" not in context.get("critical", {})
    assert "vision_documents" not in context.get("important", {})
    assert "vision_documents" not in context.get("reference", {})

@pytest.mark.asyncio
async def test_depth_config_affects_reference_fields(mission_planner, product, project):
    """Depth configuration should affect detail level in reference fields."""
    context = await mission_planner._build_context_with_priorities(
        product=product,
        project=project,
        field_priorities={"memory_360": 3},
        depth_config={"memory_360": 10}  # Request 10 projects
    )

    if "memory_360" in context.get("reference", {}):
        memory = context["reference"]["memory_360"]
        assert "fetch_tool" in memory
        assert "limit=10" in memory["fetch_tool"], "Depth config should set fetch limit"
```

---

## Migration Strategy

### Step 1: Verify Dependency (0347a complete)

Ensure `src/giljo_mcp/json_context_builder.py` exists with:
- `JSONContextBuilder` class
- Methods: `add_critical()`, `add_important()`, `add_reference()`
- Methods: `add_critical_content()`, etc.
- Method: `build()` returning dict
- Passing tests in `tests/services/test_json_context_builder.py`

### Step 2: Add Helper Methods

Add `_get_active_vision_doc()` and `_get_memory_summary()` to `MissionPlanner`.

### Step 3: Refactor Method Body

Replace `_build_context_with_priorities()` body with JSON builder approach:
- Replace `context_sections = []` with `builder = JSONContextBuilder()`
- Map each field to appropriate priority tier
- Use `builder.add_X()` and `builder.add_X_content()` methods
- Return `builder.build()` instead of `"\n\n".join(context_sections)`

### Step 4: Update Orchestration Tool

Add `"mission_format": "json"` to `get_orchestrator_instructions()` response.

### Step 5: Update Tests

Run existing tests to ensure no regressions:
```bash
pytest tests/services/test_mission_planner.py -v
```

Add new JSON-specific tests:
```bash
pytest tests/services/test_mission_planner_json.py -v
```

### Step 6: Verify Token Reduction

Compare before/after token counts:
```python
import json

# Before (markdown string)
old_mission = await planner._build_context_with_priorities(...)  # ~21,000 tokens

# After (JSON dict)
new_mission = await planner._build_context_with_priorities(...)
json_str = json.dumps(new_mission)
tokens = len(json_str) // 4  # Should be ~1,500 tokens
```

---

## Success Criteria

- [ ] `_build_context_with_priorities()` returns `dict` instead of `str`
- [ ] All CRITICAL fields (priority 1) have content inlined
- [ ] All IMPORTANT fields (priority 2) have structured content
- [ ] All REFERENCE fields (priority 3) have fetch tool pointers
- [ ] Excluded fields (priority 4) do not appear in output
- [ ] Orchestration tool response includes `"mission_format": "json"`
- [ ] Token count < 2,000 (93% reduction from ~21,000)
- [ ] All existing tests pass (no regressions)
- [ ] New JSON tests pass with >80% coverage
- [ ] Depth configuration correctly affects reference fields

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `src/giljo_mcp/mission_planner.py` | 1-50 | Add import: `from .json_context_builder import JSONContextBuilder` |
| `src/giljo_mcp/mission_planner.py` | 1217 | Change return type: `-> str` to `-> dict` |
| `src/giljo_mcp/mission_planner.py` | 1333-1823 | Replace method body with JSON builder pattern |
| `src/giljo_mcp/mission_planner.py` | 1850+ | Add helper methods: `_get_active_vision_doc()`, `_get_memory_summary()` |
| `src/giljo_mcp/tools/orchestration.py` | ~150 | Add `"mission_format": "json"` to response dict |
| `tests/services/test_mission_planner_json.py` | New file | Add JSON-specific test cases |

---

## Risk Assessment

**Low Risk Changes:**
- Adding helper methods (no side effects)
- Adding `mission_format` field to response (additive)

**Medium Risk Changes:**
- Changing return type from `str` to `dict`
  - **Mitigation:** Comprehensive tests, staged rollout
  - **Rollback:** Revert to markdown approach if regressions occur

**High Risk Changes:**
- None (0347a handles builder complexity)

**Rollback Plan:**
```bash
git revert <commit-hash>  # Revert JSON refactor
git checkout backup-0347-yaml-approach  # Or restore from backup if needed
```

---

## Performance Impact

**Token Reduction:** 93% (21,000 → 1,500 tokens)
- **Before:** Markdown blob with all content inlined
- **After:** Structured JSON with fetch pointers

**Processing Time:** Similar (minor improvement)
- JSON serialization is faster than string concatenation
- Dict building is lightweight

**Memory:** Reduced
- Smaller mission payload in database
- Less string allocation overhead

**Network:** Reduced
- Smaller MCP tool responses (~85% reduction in payload size)

---

## Notes for Implementor

1. **Dependency Check:** Verify 0347a (JSONContextBuilder) is complete before starting
2. **Incremental Approach:** Refactor one priority tier at a time (CRITICAL → IMPORTANT → REFERENCE)
3. **Test Coverage:** Write tests FIRST, then refactor (TDD approach)
4. **Token Tracking:** Log token counts before/after for validation
5. **Backward Compatibility:** Consider adding feature flag if needed for gradual rollout

**Estimated Time Breakdown:**
- Helper methods: 30 min
- CRITICAL tier refactor: 45 min
- IMPORTANT tier refactor: 45 min
- REFERENCE tier refactor: 30 min
- Test updates: 30 min
- Integration testing: 30 min
- **Total:** ~3 hours

---

## Related Handovers

- **0347a** - JSON Context Builder (prerequisite)
- **0347c** - Response Fields Enhancement (complete, uses nested dicts)
- **0347d** - Agent Templates Depth Toggle (depends on this)
- **0347e** - Vision Document 4-Level Depth (depends on this)
- **0347f** - Integration & E2E Testing (final validation)
