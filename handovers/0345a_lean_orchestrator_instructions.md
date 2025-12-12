# Handover 0345a: Lean Orchestrator Instructions

**Date:** 2025-12-11
**From Agent:** Planning Session
**To Agent:** TDD Implementor
**Priority:** CRITICAL
**Estimated Complexity:** 1 day
**Status:** Ready for Implementation

---

## Task Summary

Remove vision document body from `get_orchestrator_instructions` MCP tool response, replacing it with a minimal overview + fetch instructions. This unblocks orchestrators that currently receive truncated 25K+ token responses.

**Why:** Orchestrators can't see all agent templates because vision documents consume the entire context budget.

**Expected Outcome:** Response drops from 25K+ tokens to ~2-3K tokens while preserving ALL other context.

---

## Context and Background

### The Problem
`get_orchestrator_instructions()` calls `_build_context_with_priorities()` which:
1. Fetches ALL vision chunks with `max_tokens=None` (line 1335-1343 in mission_planner.py)
2. Reassembles them: `vision_text = "\n\n".join(chunk_texts)` (line 1348)
3. Returns 25K+ tokens, exceeding Claude Code's ingest limit

### Evidence
An orchestrator trying to stage agents picked "implementer" for documentation because:
> "The get_orchestrator_instructions() response was truncated at ~25,000 tokens, so I didn't see the complete list of available agent templates."

### Critical Constraint
**ONLY vision documentation is removed** - all other context MUST remain:
- Mission metadata
- Project context
- Available agents list
- Field priorities
- Orchestrator instructions

---

## Technical Details

### Files to Modify

#### 1. `src/giljo_mcp/mission_planner.py` (lines 1327-1412)

**Current Code (problematic):**
```python
# Line 1335-1343
if product_has_chunks:
    async with self.db_manager.get_session_async() as session:
        vision_chunks = await self._get_relevant_vision_chunks(
            session=session,
            product=product,
            project=project,
            max_tokens=None,  # Fetch ALL chunks - no limit <- THE ISSUE
        )
```

**Required Change:**
```python
# Replace fetching all chunks with overview generation
if product_has_chunks:
    async with self.db_manager.get_session_async() as session:
        vision_overview = await self._get_vision_overview(
            session=session,
            product=product,
        )
        # vision_overview = {
        #   "total_chunks": 5,
        #   "total_tokens": 125000,
        #   "fetch_instruction": "You have 5 vision chunks (~125K tokens). Use fetch_vision_document(chunk=N) to read them."
        # }
```

**New Method to Add:**
```python
async def _get_vision_overview(
    self,
    session: AsyncSession,
    product: Product,
) -> dict:
    """Generate minimal vision overview instead of full content."""
    # Query chunk metadata only (not content)
    stmt = (
        select(
            func.count(MCPContextIndex.id).label("chunk_count"),
            func.sum(MCPContextIndex.token_count).label("total_tokens"),
        )
        .where(
            MCPContextIndex.tenant_key == product.tenant_key,
            MCPContextIndex.product_id == product.id,
        )
    )
    result = await session.execute(stmt)
    row = result.one()

    if row.chunk_count == 0:
        return None

    return {
        "total_chunks": row.chunk_count,
        "total_tokens": row.total_tokens or 0,
        "fetch_instruction": f"You have {row.chunk_count} vision chunks (~{row.total_tokens:,} tokens). Use fetch_vision_document(chunk=N) to read them."
    }
```

#### 2. `src/giljo_mcp/tools/orchestration.py` (lines 1893-1894)

**Required Change:**
Include vision_overview in response instead of vision_text:
```python
# In condensed_mission response structure
"vision_overview": vision_overview,  # Instead of full vision_text
```

#### 3. `src/giljo_mcp/tools/context_tools/get_vision_document.py`

**Verify:** Pagination already works (chunk index support)
**Add if missing:** Token budget per depth level:
- light: 10,000 tokens
- moderate: 17,500 tokens
- heavy: 24,000 tokens

---

## Implementation Plan

### Phase 1: TDD Setup (30 min)
Write failing tests first:

```python
# tests/test_mission_planner_vision.py
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestLeanOrchestratorInstructions:
    """Test suite for lean orchestrator instructions (0345a)."""

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_excludes_vision_body(
        self, mission_planner, mock_product_with_vision
    ):
        """Vision document body should NOT be in response."""
        result = await mission_planner._build_context_with_priorities(
            product=mock_product_with_vision,
            project=MagicMock(),
            field_priorities={},
            user_id="test-user",
        )

        # Should NOT contain actual vision content
        assert "Chapter 1: Product Vision" not in result
        assert len(result) < 5000  # Under 5K tokens (~20K chars)

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_includes_vision_overview(
        self, mission_planner, mock_product_with_vision
    ):
        """Response should include chunk count and fetch instructions."""
        result = await mission_planner._build_context_with_priorities(
            product=mock_product_with_vision,
            project=MagicMock(),
            field_priorities={},
            user_id="test-user",
        )

        assert "vision_overview" in result or "vision chunks" in result.lower()
        assert "fetch_vision_document" in result

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_preserves_all_other_context(
        self, mission_planner, mock_product_with_vision, mock_project
    ):
        """Project, agents, priorities MUST remain - CRITICAL."""
        result = await mission_planner._build_context_with_priorities(
            product=mock_product_with_vision,
            project=mock_project,
            field_priorities={"product_name": 1, "tech_stack": 2},
            user_id="test-user",
        )

        # These MUST be present
        assert mock_product_with_vision.name in result
        assert mock_project.description in result or mock_project.name in result

    @pytest.mark.asyncio
    async def test_vision_overview_has_chunk_count_and_token_estimate(
        self, mission_planner, mock_product_with_vision
    ):
        """Overview should contain: 'You have N chunks (~X tokens)'"""
        overview = await mission_planner._get_vision_overview(
            session=AsyncMock(),
            product=mock_product_with_vision,
        )

        assert "total_chunks" in overview
        assert "total_tokens" in overview
        assert overview["total_chunks"] > 0

    @pytest.mark.asyncio
    async def test_response_under_5k_tokens_without_vision(
        self, mission_planner, mock_product_with_large_vision
    ):
        """Total response size must be < 5K tokens (~20K chars)."""
        result = await mission_planner._build_context_with_priorities(
            product=mock_product_with_large_vision,  # 150K token vision doc
            project=MagicMock(),
            field_priorities={},
            user_id="test-user",
        )

        # Rough token estimate: 1 token ~= 4 chars
        estimated_tokens = len(result) // 4
        assert estimated_tokens < 5000, f"Response too large: {estimated_tokens} tokens"
```

### Phase 2: Implementation (2-3 hours)
1. Add `_get_vision_overview()` method to MissionPlanner
2. Modify `_build_context_with_priorities()` to use overview instead of full content
3. Update response structure in orchestration.py
4. Run tests until all pass

### Phase 3: Integration Testing (1-2 hours)
1. Start server with `python startup.py --dev`
2. Call `get_orchestrator_instructions` via MCP
3. Verify response < 5K tokens
4. Verify all other context present
5. Test `fetch_vision_document(chunk=N)` works

---

## Testing Requirements

### Unit Tests
- [ ] `test_get_orchestrator_instructions_excludes_vision_body`
- [ ] `test_get_orchestrator_instructions_includes_vision_overview`
- [ ] `test_get_orchestrator_instructions_preserves_all_other_context`
- [ ] `test_vision_overview_has_chunk_count_and_token_estimate`
- [ ] `test_vision_overview_has_fetch_instruction`
- [ ] `test_response_under_5k_tokens_without_vision`

### Integration Tests
- [ ] MCP tool returns valid response
- [ ] Orchestrator can parse vision_overview
- [ ] fetch_vision_document pagination works

### Manual Testing
1. Upload large vision document (100K+ tokens)
2. Create project and stage orchestrator
3. Verify orchestrator instructions response < 5K tokens
4. Verify orchestrator can call fetch_vision_document

---

## Dependencies and Blockers

### Dependencies
- None - this is a standalone fix

### Known Blockers
- None

---

## Success Criteria

- [ ] `get_orchestrator_instructions` response < 5K tokens
- [ ] All existing orchestrator context preserved
- [ ] Vision overview contains chunk count + fetch instructions
- [ ] `fetch_vision_document` pagination verified working
- [ ] All tests pass
- [ ] No breaking changes to existing flows

---

## Rollback Plan

**If Things Go Wrong:**
Revert single line change in `_build_context_with_priorities()`:
```python
max_tokens=None  # Restore original behavior
```

---

## Related Handovers

- **0336**: Vision chunking rollback (created this problem)
- **0345b**: Sumy LSA integration (depends on this)
- **0345c**: Settings UI (depends on this)
- **0338**: CPU-based summarization (reference)

---

## Recommended Agent

**TDD Implementor** - This task requires:
1. Writing tests first (TDD approach)
2. Backend Python changes
3. Database query optimization
4. Integration testing
