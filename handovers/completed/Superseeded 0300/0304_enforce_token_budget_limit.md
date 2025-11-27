---
**Handover**: 0304 - Enforce Token Budget Limit
**Type**: Backend + Testing
**Effort**: 6-8 hours
**Priority**: P1
**Status**: Planning
---

# Handover 0304: Enforce Token Budget Limit

## Problem Statement

**Critical Gap**: Backend logs token usage but NEVER enforces the 2000 token budget limit, defeating field priorities.

**PDF Slide 18**: "Fields are included top-to-bottom until token budget (2000) is reached"

**Current Code (mission_planner.py:683-884)**:
```python
# Line 683-692: MANDATORY sections added WITHOUT budget check
total_tokens += name_tokens
total_tokens += vision_tokens
total_tokens += desc_tokens

# Line 745-776: Codebase added WITHOUT budget check
total_tokens += codebase_tokens

# Line 779-828: Architecture added WITHOUT budget check
total_tokens += arch_tokens

# Line 861-866: Context prioritization metrics LOGGED but NOT ENFORCED
logger.info(f"Context built: {total_tokens} tokens ({reduction_pct:.1f}% reduction)")
```

**Problem**: Context can grow unbounded. A 50KB vision document + 30KB codebase + 10KB architecture = 90KB (22,500 tokens) with ZERO enforcement.

**Impact**:
- Orchestrator missions exceed Claude API limits (200K context window wasted)
- Field priorities meaningless (all fields included regardless of priority)
- Context prioritization claims (70%) false (no actual enforcement)
- Cost overruns (paying for massive context without benefit)

---

## Scope

### In Scope
- ✅ Separate MANDATORY vs OPTIONAL sections in `_build_context_with_priorities()`
- ✅ Enforce budget on OPTIONAL sections (stop adding when budget reached)
- ✅ Return metadata: `{sections_included, sections_skipped, budget_used}`
- ✅ Comprehensive unit tests (12+ test cases covering edge cases)
- ✅ Integration tests (E2E budget enforcement with realistic data)
- ✅ Budget headroom calculation (warn at 90%)

### Out of Scope
- ❌ Changing MANDATORY sections (product name, vision, project description always included)
- ❌ User-configurable budget (2000 tokens fixed in config/defaults.py)
- ❌ Dynamic budget adjustment (future: could scale based on project complexity)
- ❌ Token estimation algorithms (using existing `_count_tokens()` method)

---

## Tasks

### Phase 1: Write Failing Tests (RED) - 2-3 hours

- [ ] **Test 1**: MANDATORY fields ALWAYS included (regardless of budget)
  - Vision document = 5000 tokens (exceeds budget)
  - Verify: product name, vision, project description ALL present
  - Assert: total_tokens > budget (MANDATORY sections exempt)

- [ ] **Test 2**: Optional fields stop when budget reached
  - Budget = 2000 tokens
  - MANDATORY = 1500 tokens (product + vision + desc)
  - Optional fields: codebase (300), architecture (400), serena (500)
  - Verify: Only codebase added (total = 1800), architecture skipped
  - Assert: metadata.sections_skipped includes "architecture"

- [ ] **Test 3**: Fields added in priority order (10→7→4→1)
  - Product.config_data with priority fields: P10, P7, P4, P1
  - Budget tight (2000 tokens)
  - Verify: P10 added first, P7 added, P4 skipped, P1 skipped
  - Assert: sections_included = ["P10", "P7"], sections_skipped = ["P4", "P1"]

- [ ] **Test 4**: Partial field inclusion (budget hit mid-section)
  - Budget = 2000 tokens
  - MANDATORY = 1200 tokens
  - Codebase summary = 900 tokens (exceeds remaining 800 budget)
  - Verify: Codebase NOT included (atomic section addition)
  - Assert: sections_skipped = ["codebase_summary"]
  - Note: No partial sections (all-or-nothing per field)

- [ ] **Test 5**: Budget enforcement with different budgets
  - Test with budgets: 1000, 2000, 5000 tokens
  - Same product/project data
  - Verify: More fields included with higher budget
  - Assert: sections_included.length correlates with budget size

- [ ] **Test 6**: Budget overflow logged but not raised as error
  - MANDATORY sections = 3000 tokens (exceeds 2000 budget)
  - Verify: No exception raised (MANDATORY exempt from budget)
  - Assert: log contains "MANDATORY sections exceed budget"
  - Assert: metadata.budget_used = 3000, metadata.budget_exceeded = True

- [ ] **Test 7**: Empty optional sections (only MANDATORY)
  - Product with no config_data, no codebase_summary
  - Budget = 2000 tokens
  - MANDATORY = 500 tokens
  - Verify: Only MANDATORY sections present
  - Assert: sections_included = ["product_name", "vision", "description"]

- [ ] **Test 8**: Serena context budget enforcement
  - Serena enabled, returns 1500 tokens of context
  - Budget = 2000, MANDATORY = 1000
  - Verify: Serena context NOT added (1000 + 1500 = 2500 > budget)
  - Assert: sections_skipped = ["serena_context"]

- [ ] **Test 9**: Budget headroom calculation
  - Budget = 2000, tokens used = 1800
  - Verify: headroom = 200 tokens (10% remaining)
  - Assert: metadata.headroom_tokens = 200
  - Assert: metadata.headroom_pct = 10.0

- [ ] **Test 10**: Zero budget (edge case)
  - Budget = 0 (invalid config)
  - Verify: MANDATORY sections still added (budget ignored)
  - Assert: log contains "WARNING: Invalid budget (0), using default"

- [ ] **Test 11**: Negative budget (edge case)
  - Budget = -500 (invalid config)
  - Verify: MANDATORY sections added, default budget used (2000)
  - Assert: log contains "WARNING: Invalid budget (-500), using default"

- [ ] **Test 12**: Integration test (E2E realistic scenario)
  - Product with 10KB vision, 5KB codebase, 3KB architecture, 2KB config
  - Budget = 2000 tokens (~8KB limit)
  - Verify: Vision + codebase included, architecture skipped
  - Assert: total_tokens ≤ 2000 (ignoring MANDATORY exemption)

### Phase 2: Implement Enforcement (GREEN) - 2-3 hours

- [ ] **Step 1**: Extract budget validation method
  ```python
  def _validate_budget(self, budget: int) -> int:
      """Validate and return budget, or default if invalid."""
      if budget <= 0:
          logger.warning(f"Invalid budget ({budget}), using default (2000)")
          return 2000
      return budget
  ```

- [ ] **Step 2**: Add metadata return type
  ```python
  @dataclass
  class ContextMetadata:
      sections_included: list[str]
      sections_skipped: list[str]
      budget_used: int
      budget_limit: int
      budget_exceeded: bool
      headroom_tokens: int
      headroom_pct: float
      mandatory_tokens: int
      optional_tokens: int
  ```

- [ ] **Step 3**: Separate MANDATORY vs OPTIONAL sections
  ```python
  # MANDATORY (always included, no budget check)
  mandatory_sections = []
  mandatory_tokens = 0

  # Add product name
  product_name_section = f"## Product\n**Name**: {product.name}"
  mandatory_sections.append(("product_name", product_name_section))
  mandatory_tokens += self._count_tokens(product_name_section)

  # Add vision (MANDATORY)
  if vision_text:
      formatted_vision = f"## Product Vision\n{vision_text}"
      mandatory_sections.append(("vision", formatted_vision))
      mandatory_tokens += self._count_tokens(formatted_vision)

  # Add project description (MANDATORY)
  if desc_text:
      formatted_desc = f"## Project Description\n{desc_text}"
      mandatory_sections.append(("description", formatted_desc))
      mandatory_tokens += self._count_tokens(formatted_desc)

  # OPTIONAL (budget enforced)
  optional_sections = []
  optional_tokens = 0
  budget_remaining = budget - mandatory_tokens
  ```

- [ ] **Step 4**: Add budget check before each optional section
  ```python
  # Codebase Summary (OPTIONAL)
  if codebase_priority > 0:
      codebase_text = self._get_codebase_text(project, codebase_priority)
      if codebase_text:
          formatted_codebase = f"## Codebase\n{codebase_text}"
          codebase_tokens = self._count_tokens(formatted_codebase)

          # BUDGET CHECK
          if self._can_fit_in_budget(codebase_tokens, budget_remaining):
              optional_sections.append(("codebase_summary", formatted_codebase))
              optional_tokens += codebase_tokens
              budget_remaining -= codebase_tokens
          else:
              logger.debug(
                  f"Skipping codebase_summary: {codebase_tokens} tokens exceeds remaining budget ({budget_remaining})"
              )
              skipped_sections.append("codebase_summary")
  ```

- [ ] **Step 5**: Extract budget check method
  ```python
  def _can_fit_in_budget(self, section_tokens: int, budget_remaining: int) -> bool:
      """
      Check if section fits in remaining budget.

      Args:
          section_tokens: Tokens required for section
          budget_remaining: Remaining token budget

      Returns:
          True if section fits, False otherwise
      """
      return section_tokens <= budget_remaining
  ```

- [ ] **Step 6**: Return metadata
  ```python
  # Build final context
  all_sections = mandatory_sections + optional_sections
  context = "\n\n".join([section for name, section in all_sections])

  total_tokens = mandatory_tokens + optional_tokens
  budget_exceeded = mandatory_tokens > budget  # MANDATORY can exceed
  headroom_tokens = max(0, budget - total_tokens)
  headroom_pct = (headroom_tokens / budget) * 100 if budget > 0 else 0.0

  metadata = ContextMetadata(
      sections_included=[name for name, _ in all_sections],
      sections_skipped=skipped_sections,
      budget_used=total_tokens,
      budget_limit=budget,
      budget_exceeded=budget_exceeded,
      headroom_tokens=headroom_tokens,
      headroom_pct=headroom_pct,
      mandatory_tokens=mandatory_tokens,
      optional_tokens=optional_tokens
  )

  return context, metadata
  ```

- [ ] **Step 7**: Update `_build_context_with_priorities()` signature
  ```python
  async def _build_context_with_priorities(
      self,
      product: Product,
      project: Project,
      field_priorities: dict = None,
      user_id: Optional[str] = None,
      include_serena: bool = False
  ) -> tuple[str, ContextMetadata]:
      """
      Build context respecting user's field priorities and token budget.

      Returns:
          Tuple of (context_string, metadata)
      """
  ```

- [ ] **Step 8**: Update all callers to handle tuple return
  - `_generate_agent_mission()`: Unpack `context, metadata = await self._build_context_with_priorities(...)`
  - Log metadata for debugging: `logger.info(f"Context metadata: {metadata}")`

### Phase 3: Refactor (REFACTOR) - 1-2 hours

- [ ] **Refactor 1**: Extract budget headroom calculation
  ```python
  def _calculate_budget_headroom(self, budget_used: int, budget_limit: int) -> tuple[int, float]:
      """Calculate remaining budget headroom."""
      headroom_tokens = max(0, budget_limit - budget_used)
      headroom_pct = (headroom_tokens / budget_limit) * 100 if budget_limit > 0 else 0.0
      return headroom_tokens, headroom_pct
  ```

- [ ] **Refactor 2**: Add budget warning at 90%
  ```python
  if headroom_pct < 10.0:
      logger.warning(
          f"Budget headroom low: {headroom_pct:.1f}% ({headroom_tokens} tokens remaining)",
          extra={"budget_used": budget_used, "budget_limit": budget_limit}
      )
  ```

- [ ] **Refactor 3**: Improve logging granularity
  ```python
  logger.debug(
      f"Budget enforcement: {budget_used}/{budget_limit} tokens used",
      extra={
          "mandatory_tokens": mandatory_tokens,
          "optional_tokens": optional_tokens,
          "sections_included": len(sections_included),
          "sections_skipped": len(sections_skipped),
          "budget_exceeded": budget_exceeded
      }
  )
  ```

- [ ] **Refactor 4**: Add structured logging for analytics
  ```python
  logger.info(
      "Context built with budget enforcement",
      extra={
          "product_id": str(product.id),
          "project_id": str(project.id),
          "budget_used": total_tokens,
          "budget_limit": budget,
          "headroom_pct": headroom_pct,
          "sections_included": sections_included,
          "sections_skipped": skipped_sections,
          "mandatory_tokens": mandatory_tokens,
          "optional_tokens": optional_tokens,
      }
  )
  ```

---

## Implementation Algorithm

```python
def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    field_priorities: dict = None,
    user_id: Optional[str] = None,
    include_serena: bool = False
) -> tuple[str, ContextMetadata]:
    """
    Build context with token budget enforcement.

    Algorithm:
    1. Validate budget (reject invalid values)
    2. Add MANDATORY sections (product, vision, description) - NO budget check
    3. Calculate remaining budget = budget - mandatory_tokens
    4. For each OPTIONAL section (ordered by priority 10→1):
        a. Estimate tokens for section
        b. If tokens <= budget_remaining:
            - Add section
            - Subtract tokens from budget_remaining
        c. Else:
            - Skip section
            - Log skipped section
    5. Build final context from mandatory + optional sections
    6. Return (context, metadata)
    """
    # 1. Validate budget
    budget = self._validate_budget(field_priorities.get("token_budget", 2000))

    # 2. MANDATORY sections (always included)
    mandatory_sections = []
    mandatory_tokens = 0

    # Product name
    product_name_section = f"## Product\n**Name**: {product.name}"
    if product.description:
        product_name_section += f"\n**Description**: {product.description}"
    mandatory_sections.append(("product_name", product_name_section))
    name_tokens = self._count_tokens(product_name_section)
    mandatory_tokens += name_tokens

    # Vision
    vision_text = product.primary_vision_text
    if vision_text:
        formatted_vision = f"## Product Vision\n{vision_text}"
        mandatory_sections.append(("vision", formatted_vision))
        vision_tokens = self._count_tokens(formatted_vision)
        mandatory_tokens += vision_tokens

    # Project description
    desc_text = project.description or ""
    if desc_text:
        formatted_desc = f"## Project Description\n{desc_text}"
        mandatory_sections.append(("description", formatted_desc))
        desc_tokens = self._count_tokens(formatted_desc)
        mandatory_tokens += desc_tokens

    # 3. Calculate remaining budget
    budget_remaining = budget - mandatory_tokens
    if budget_remaining < 0:
        logger.warning(
            f"MANDATORY sections ({mandatory_tokens} tokens) exceed budget ({budget} tokens)"
        )

    # 4. OPTIONAL sections (budget enforced)
    optional_sections = []
    optional_tokens = 0
    skipped_sections = []

    # Codebase summary (priority-based detail level)
    codebase_priority = field_priorities.get("codebase_summary", 0)
    if codebase_priority > 0 and budget_remaining > 0:
        codebase_detail = self._get_detail_level(codebase_priority)
        codebase_original = project.codebase_summary or ""

        if codebase_detail == "full" or codebase_detail == "moderate":
            codebase_text = codebase_original
        elif codebase_detail == "abbreviated":
            codebase_text = self._abbreviate_codebase_summary(codebase_original)
        else:  # minimal
            codebase_text = self._minimal_codebase_summary(codebase_original)

        if codebase_text:
            formatted_codebase = f"## Codebase\n{codebase_text}"
            codebase_tokens = self._count_tokens(formatted_codebase)

            if self._can_fit_in_budget(codebase_tokens, budget_remaining):
                optional_sections.append(("codebase_summary", formatted_codebase))
                optional_tokens += codebase_tokens
                budget_remaining -= codebase_tokens
            else:
                logger.debug(
                    f"Skipping codebase_summary: {codebase_tokens} tokens > {budget_remaining} remaining"
                )
                skipped_sections.append("codebase_summary")

    # Architecture section
    arch_priority = field_priorities.get("architecture", 0)
    if arch_priority > 0 and budget_remaining > 0 and product.config_data:
        arch_detail = self._get_detail_level(arch_priority)

        # Extract architecture text
        arch_text = ""
        if isinstance(product.config_data, dict):
            arch_value = product.config_data.get("architecture", "")

            if isinstance(arch_value, str):
                arch_text = arch_value
            elif isinstance(arch_value, dict):
                pattern = arch_value.get("pattern", "")
                api_style = arch_value.get("api_style", "")
                design_patterns = arch_value.get("design_patterns", "")
                notes = arch_value.get("notes", "")
                parts = [p for p in [pattern, api_style, design_patterns, notes] if p]
                arch_text = "\n".join(parts)

        if arch_text and isinstance(arch_text, str):
            # Apply detail level
            if arch_detail == "full" or arch_detail == "moderate":
                formatted_arch = arch_text
            elif arch_detail == "abbreviated":
                paragraphs = arch_text.split("\n\n")
                formatted_arch = paragraphs[0] if paragraphs else arch_text
            else:  # minimal
                sentences = arch_text.split(". ")
                formatted_arch = sentences[0] + "." if sentences else arch_text

            if formatted_arch:
                formatted_section = f"## Architecture\n{formatted_arch}"
                arch_tokens = self._count_tokens(formatted_section)

                if self._can_fit_in_budget(arch_tokens, budget_remaining):
                    optional_sections.append(("architecture", formatted_section))
                    optional_tokens += arch_tokens
                    budget_remaining -= arch_tokens
                else:
                    logger.debug(
                        f"Skipping architecture: {arch_tokens} tokens > {budget_remaining} remaining"
                    )
                    skipped_sections.append("architecture")

    # Serena codebase context (if enabled)
    if include_serena and budget_remaining > 0:
        serena_context = await self._fetch_serena_codebase_context(
            project_id=str(project.id),
            tenant_key=product.tenant_key
        )
        if serena_context:
            formatted_serena = f"## Codebase Context (Serena)\n{serena_context}"
            serena_tokens = self._count_tokens(formatted_serena)

            if self._can_fit_in_budget(serena_tokens, budget_remaining):
                optional_sections.append(("serena_context", formatted_serena))
                optional_tokens += serena_tokens
                budget_remaining -= serena_tokens
            else:
                logger.debug(
                    f"Skipping serena_context: {serena_tokens} tokens > {budget_remaining} remaining"
                )
                skipped_sections.append("serena_context")

    # 5. Build final context
    all_sections = mandatory_sections + optional_sections
    context_sections = [section for name, section in all_sections]
    context = "\n\n".join(context_sections)

    # 6. Calculate metadata
    total_tokens = mandatory_tokens + optional_tokens
    budget_exceeded = mandatory_tokens > budget
    headroom_tokens, headroom_pct = self._calculate_budget_headroom(total_tokens, budget)

    sections_included = [name for name, _ in all_sections]

    metadata = ContextMetadata(
        sections_included=sections_included,
        sections_skipped=skipped_sections,
        budget_used=total_tokens,
        budget_limit=budget,
        budget_exceeded=budget_exceeded,
        headroom_tokens=headroom_tokens,
        headroom_pct=headroom_pct,
        mandatory_tokens=mandatory_tokens,
        optional_tokens=optional_tokens
    )

    # Log budget enforcement
    logger.info(
        f"Context built: {total_tokens}/{budget} tokens ({headroom_pct:.1f}% headroom)",
        extra={
            "product_id": str(product.id),
            "project_id": str(project.id),
            "budget_used": total_tokens,
            "budget_limit": budget,
            "sections_included": sections_included,
            "sections_skipped": skipped_sections,
            "mandatory_tokens": mandatory_tokens,
            "optional_tokens": optional_tokens,
        }
    )

    if headroom_pct < 10.0:
        logger.warning(
            f"Budget headroom low: {headroom_pct:.1f}% ({headroom_tokens} tokens remaining)"
        )

    return context, metadata
```

---

## Files to Modify

### Core Implementation
- `src/giljo_mcp/mission_planner.py`
  - Add `ContextMetadata` dataclass
  - Modify `_build_context_with_priorities()` to return tuple
  - Add `_validate_budget()` method
  - Add `_can_fit_in_budget()` method
  - Add `_calculate_budget_headroom()` method
  - Update all callers of `_build_context_with_priorities()`

### Tests (NEW)
- `tests/integration/test_token_budget_enforcement.py`
  - 12+ test cases covering all scenarios
  - Edge case testing (zero/negative budget)
  - E2E integration test with realistic data

### Existing Tests (MODIFY)
- `tests/unit/test_mission_planner_priority.py`
  - Update tests to handle tuple return from `_build_context_with_priorities()`
  - Add metadata assertions

---

## Success Criteria

### Functional Requirements
- ✅ MANDATORY sections ALWAYS included (regardless of budget)
- ✅ Optional sections stop when budget reached
- ✅ Fields added in priority order
- ✅ Budget overflow logged (warning, not error)
- ✅ Metadata returned with budget usage details

### Test Coverage
- ✅ All 12 test cases pass (100% coverage for new code)
- ✅ Existing tests updated and passing
- ✅ Integration test covers E2E realistic scenario

### Performance
- ✅ No performance regression (<5ms overhead for budget checks)
- ✅ Token counting efficient (reuse existing `_count_tokens()` method)

### Logging
- ✅ Budget enforcement logged at INFO level
- ✅ Skipped sections logged at DEBUG level
- ✅ Budget headroom warnings at <10%

---

## Testing Strategy

### Unit Tests (tests/integration/test_token_budget_enforcement.py)

**Test Structure**:
```python
import pytest
from src.giljo_mcp.mission_planner import MissionPlanner, ContextMetadata
from src.giljo_mcp.models import Product, Project

class TestTokenBudgetEnforcement:
    """Test token budget enforcement in mission planner."""

    @pytest.fixture
    def mission_planner(self, mock_db_manager):
        return MissionPlanner(mock_db_manager)

    @pytest.mark.asyncio
    async def test_mandatory_fields_always_included(self, mission_planner):
        """Test MANDATORY fields included regardless of budget."""
        # Create product with 5000 token vision (exceeds budget)
        product = create_product_with_large_vision(5000)
        project = create_simple_project()

        field_priorities = {"token_budget": 2000}

        context, metadata = await mission_planner._build_context_with_priorities(
            product, project, field_priorities
        )

        # Assertions
        assert "## Product" in context
        assert "## Product Vision" in context
        assert "## Project Description" in context
        assert metadata.budget_exceeded == True
        assert metadata.mandatory_tokens > 2000
        assert metadata.budget_used > 2000

    @pytest.mark.asyncio
    async def test_optional_fields_stop_at_budget(self, mission_planner):
        """Test optional fields stop when budget reached."""
        product = create_product_with_config()
        project = create_project_with_codebase()

        field_priorities = {
            "token_budget": 2000,
            "codebase_summary": 6,  # 300 tokens
            "architecture": 4       # 400 tokens (won't fit)
        }

        context, metadata = await mission_planner._build_context_with_priorities(
            product, project, field_priorities
        )

        # Assertions
        assert "## Codebase" in context
        assert "## Architecture" not in context
        assert "codebase_summary" in metadata.sections_included
        assert "architecture" in metadata.sections_skipped
        assert metadata.budget_used <= 2000

    # ... (10+ more test cases)
```

### Integration Test (Realistic Scenario)

```python
@pytest.mark.asyncio
async def test_e2e_realistic_budget_enforcement(self, mission_planner):
    """E2E integration test with realistic product/project data."""
    # Create realistic product (10KB vision, 5KB codebase, 3KB architecture)
    product = Product(
        id="prod_realistic",
        tenant_key="tenant_1",
        name="GiljoAI MCP Server",
        description="Multi-tenant AI agent orchestration platform",
        vision_documents=[
            VisionDocument(
                content="[10KB vision document content]" * 100,
                vision_type="markdown",
                chunk_count=4
            )
        ],
        config_data={
            "tech_stack": {
                "languages": ["Python 3.11+", "TypeScript 5.0"],
                "backend": ["FastAPI", "SQLAlchemy", "PostgreSQL 18"],
                "frontend": ["Vue 3", "Vuetify", "WebSockets"],
                "database": ["PostgreSQL 18", "Redis (optional)"],
                "infrastructure": ["Docker", "Kubernetes", "AWS"]
            },
            "architecture": {
                "pattern": "Microservices with event-driven design",
                "api_style": "RESTful with OpenAPI 3.0",
                "design_patterns": ["Repository", "Factory", "Observer"],
                "notes": "[3KB architecture notes]" * 30
            }
        }
    )

    project = Project(
        id="proj_realistic",
        tenant_key="tenant_1",
        name="Add Agent Monitoring",
        description="Implement real-time agent monitoring with cancellation",
        codebase_summary="[5KB codebase summary]" * 50
    )

    field_priorities = {
        "token_budget": 2000,
        "codebase_summary": 6,
        "architecture": 4
    }

    context, metadata = await mission_planner._build_context_with_priorities(
        product, project, field_priorities, include_serena=False
    )

    # Assertions
    assert metadata.budget_used <= 2500  # Allow MANDATORY overage
    assert "## Product Vision" in context
    assert "## Codebase" in context
    assert len(metadata.sections_skipped) > 0  # Some sections skipped
    assert metadata.headroom_pct >= 0.0
```

---

## Rollback Plan

### If Tests Fail
1. Revert `mission_planner.py` changes
2. Keep test file for future implementation
3. Document failures in handover notes

### If Performance Issues
1. Profile `_count_tokens()` calls (potential bottleneck)
2. Add caching for token counts (memoization)
3. Fall back to estimation (1 token ≈ 4 characters) if tiktoken fails

### If Budget Too Restrictive
1. Increase default budget to 3000 tokens (config/defaults.py)
2. Add user-configurable budget in My Settings
3. Implement dynamic budget scaling (future)

---

## Related Documentation

- **PDF Slide 18**: Field Priorities & Token Budget
- **config/defaults.py**: `DEFAULT_FIELD_PRIORITY` (token_budget = 2000)
- **mission_planner.py**: `_build_context_with_priorities()` method
- **Handover 0048**: Product Field Priority Configuration
- **Handover 0086B**: Serena Integration (budget enforcement for Serena context)

---

## Notes

### Design Decisions

**Q: Why separate MANDATORY vs OPTIONAL?**
A: MANDATORY fields (product name, vision, description) are foundational context that orchestrator needs to function. Skipping them would render missions useless. Budget enforcement only applies to "nice-to-have" sections (codebase, architecture, Serena).

**Q: Why atomic section addition (all-or-nothing)?**
A: Partial sections (e.g., half of codebase summary) would be confusing and incomplete. Better to skip entire section and add it at lower detail level (abbreviated/minimal).

**Q: Why log warnings instead of raising errors?**
A: MANDATORY sections exceeding budget is expected for complex products. Raising exceptions would block mission generation. Warnings allow monitoring without blocking.

**Q: Why 90% headroom threshold for warnings?**
A: 10% headroom provides buffer for estimation errors and allows detecting budget pressure before hitting limit.

### Future Enhancements (Out of Scope)

1. **User-Configurable Budget**: Allow users to set budget in My Settings (1000-5000 tokens)
2. **Dynamic Budget Scaling**: Increase budget for complex projects (auto-detect based on product.config_data size)
3. **Smart Summarization**: Use LLM to condense MANDATORY sections if they exceed budget
4. **Budget Analytics**: Track budget usage over time, identify products consistently exceeding budget
5. **Priority-Based Summarization**: Apply different summarization strategies based on field priority (P10 = full, P1 = ultra-minimal)

---

**Created**: 2025-11-16
**Status**: Planning → Active (after tests written)
**Owner**: TDD Implementor Agent
