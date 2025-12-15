---
**Handover**: 0347e - Vision Document 4-Level Depth Configuration
**Type**: Backend + Frontend
**Effort**: 3 hours
**Priority**: P1
**Status**: Planning
**Dependencies**: 0347b (MissionPlanner JSON restructuring)
---

# Handover 0347e: Vision Document 4-Level Depth Configuration

## Problem Statement

**Current Issue**: Users report that orchestrators skip reading vision documents even when "Full" depth is selected. The current binary approach (pointer-only vs full-inline) doesn't provide enough granularity, and the "Full" mode lacks explicit behavioral instructions forcing orchestrators to actually read the content.

**User Impact**:
- Orchestrators make decisions without understanding product vision
- User intent (explicit "Full" configuration) is ignored
- No middle ground between "nothing" and "everything" (~30K tokens)
- Token waste when users want summary-level context

**Root Cause**: Missing explicit instructions in Full mode + lack of graduated depth options.

## Scope

### Included
- ✅ 4-level depth system: Optional/Light/Medium/Full
- ✅ Backend: Vision depth branching logic in `MissionPlanner`
- ✅ Frontend: 4-option dropdown in Context Depth settings
- ✅ Mandatory read instructions for Full mode (REQUIRED_READING)
- ✅ Summarization logic for Light (33%) and Medium (66%) modes
- ✅ Token budget validation for each level
- ✅ TDD test suite covering all 4 levels
- ✅ API endpoint validation for new depth values

### Excluded
- ❌ Actual AI summarization (use placeholder truncation for MVP)
- ❌ Vision chunking modifications (existing chunking remains)
- ❌ Other context fields (this handover is vision-only)
- ❌ Migration of existing user settings (defaults handle this)

## Proposed 4-Level System

| Level | Content Strategy | Orchestrator Behavior | Token Cost | Use Case |
|-------|-----------------|----------------------|------------|----------|
| **Optional** | Pointer + pagination only | Orchestrator decides whether to fetch | ~200 tokens | Trust orchestrator judgment |
| **Light** | 33% summarized content inline | Read what's provided | ~10-12K tokens | High-level context only |
| **Medium** | 66% summarized content inline | Read what's provided | ~20-24K tokens | Balanced detail |
| **Full** | Pointer + MANDATORY read instruction | MUST fetch and read all chunks | ~200 tokens + fetch | User demands complete vision |

### Key Behavioral Difference

**Full Mode** is NOT just "more content" - it's **mandatory compliance**:

```markdown
## Vision Document - REQUIRED READING

**User has configured FULL context depth for this product.**

BEFORE creating your mission plan, you MUST:
1. Fetch ALL vision document chunks using pagination
2. Read and internalize the complete product vision
3. Reference specific vision elements in your mission plan

This is NOT optional. The user explicitly requested full context depth.
Skipping this step violates the user's configuration intent.

### Fetch Commands
fetch_vision_document(product_id="<id>", offset=0, limit=1)  # Chunk 1
fetch_vision_document(product_id="<id>", offset=1, limit=1)  # Chunk 2
# Continue until has_more=false
```

## Tasks

### Backend Implementation (1.5 hours)

- [ ] **Task 1**: Write TDD tests for 4 depth levels (30 min)
  - Test: `test_optional_depth_returns_pointer_only`
  - Test: `test_light_depth_includes_33_percent_summary`
  - Test: `test_medium_depth_includes_66_percent_summary`
  - Test: `test_full_depth_includes_mandatory_read_instruction`
  - Test: `test_full_depth_prohibits_skipping`
  - Test: `test_token_budgets_per_level`

- [ ] **Task 2**: Implement vision depth branching in `MissionPlanner` (45 min)
  - Add `_get_vision_content_by_depth()` method
  - Add `_generate_mandatory_read_instruction()` for Full mode
  - Add `_summarize_vision_content()` stub (placeholder truncation)
  - Update `_build_context_with_priorities()` to call new methods

- [ ] **Task 3**: Update API endpoint validation (15 min)
  - Update `api/endpoints/context.py` valid values list
  - Add OpenAPI schema documentation for 4 levels
  - Validate depth value in settings update endpoint

### Frontend Implementation (1 hour)

- [ ] **Task 4**: Update Context Depth UI component (30 min)
  - Modify `ContextPriorityConfig.vue` dropdown options
  - Add 4 options with descriptive labels and tooltips
  - Update data model to handle new values

- [ ] **Task 5**: Add frontend validation and help text (15 min)
  - Tooltip explaining each level's behavior
  - Warning when Full mode selected (high token cost on fetch)
  - Preview of approximate token impact

- [ ] **Task 6**: Write frontend unit tests (15 min)
  - Test: `test_vision_depth_dropdown_shows_4_options`
  - Test: `test_full_mode_shows_warning`
  - Test: `test_depth_selection_updates_config`

### Integration & Documentation (30 min)

- [ ] **Task 7**: E2E integration test (15 min)
  - Test full workflow: UI selection → API save → MissionPlanner fetch → JSON output

- [ ] **Task 8**: Update documentation (15 min)
  - Update CLAUDE.md context management section
  - Add examples to docs/CONTEXT_MANAGEMENT.md

## Success Criteria

### Functional Requirements
- ✅ All 4 depth levels produce correct token counts (±10% tolerance)
- ✅ Full mode includes "REQUIRED_READING" instruction verbatim
- ✅ Light mode inline content is ~33% of original (10-12K tokens)
- ✅ Medium mode inline content is ~66% of original (20-24K tokens)
- ✅ Optional mode returns pointer only (~200 tokens)

### Behavioral Requirements
- ✅ Full mode instruction explicitly forbids skipping
- ✅ Orchestrators understand "MUST fetch ALL chunks" in Full mode
- ✅ Light/Medium modes provide enough context to avoid unnecessary fetches

### Technical Requirements
- ✅ All TDD tests pass (6 backend + 3 frontend = 9 tests)
- ✅ API rejects invalid depth values (e.g., "high", "maximum")
- ✅ Frontend dropdown shows all 4 options
- ✅ Default depth value is "optional" for backward compatibility

### User Experience
- ✅ Clear labels in UI explaining each level's purpose
- ✅ Token impact visible before selection
- ✅ Warning shown when Full mode selected (potential fetch cost)

## Implementation Details

### File: `src/giljo_mcp/mission_planner.py`

**Location**: Inside `_build_context_with_priorities()` method

```python
async def _build_context_with_priorities(
    self,
    product: Product,
    project: Project,
    config_data: dict
) -> dict:
    """Build context sections based on priority and depth configuration."""

    # ... existing code ...

    # Vision document handling with 4-level depth
    vision_depth = depth_config.get("vision_documents", "optional")

    if vision_depth == "full":
        # MANDATORY read instruction - orchestrator MUST comply
        context_sections["vision_documents"] = {
            "status": "REQUIRED_READING",
            "priority": "CRITICAL",
            "instruction": self._generate_mandatory_read_instruction(product, vision_doc),
            "total_tokens": vision_doc.original_token_count,
            "chunks": vision_doc.chunk_count,
            "fetch_commands": self._generate_fetch_commands(product.id, vision_doc.chunk_count)
        }
    elif vision_depth == "medium":
        # Inline 66% summarized content
        summarized = await self._summarize_vision_content(vision_doc, ratio=0.66)
        context_sections["vision_documents"] = {
            "status": "INLINE_SUMMARY",
            "priority": "IMPORTANT",
            "content": summarized,
            "tokens": self._count_tokens(summarized),
            "coverage": "66% of original vision"
        }
    elif vision_depth == "light":
        # Inline 33% summarized content
        summarized = await self._summarize_vision_content(vision_doc, ratio=0.33)
        context_sections["vision_documents"] = {
            "status": "INLINE_SUMMARY",
            "priority": "IMPORTANT",
            "content": summarized,
            "tokens": self._count_tokens(summarized),
            "coverage": "33% of original vision"
        }
    else:  # "optional" (default)
        # Pointer only - orchestrator decides
        context_sections["vision_documents"] = {
            "status": "AVAILABLE_ON_REQUEST",
            "priority": "NICE_TO_HAVE",
            "available": True,
            "total_tokens": vision_doc.original_token_count,
            "chunks": vision_doc.chunk_count,
            "fetch_tool": "fetch_vision_document(product_id, offset, limit)",
            "when_to_fetch": [
                "Complex feature implementation requiring deep product understanding",
                "UX decisions needing alignment with product philosophy",
                "Architectural choices that should match product vision"
            ]
        }

    return context_sections
```

**New Helper Methods**:

```python
def _generate_mandatory_read_instruction(self, product: Product, vision_doc: VisionDocument) -> str:
    """Generate explicit REQUIRED_READING instruction for Full depth mode."""
    return f"""
## Vision Document - REQUIRED READING

**User has configured FULL context depth for this product.**

BEFORE creating your mission plan, you MUST:
1. Fetch ALL vision document chunks using pagination
2. Read and internalize the complete product vision
3. Reference specific vision elements in your mission plan

This is NOT optional. The user explicitly requested full context depth.
Skipping this step violates the user's configuration intent.

### Product: {product.name}
**Total Content**: {vision_doc.original_token_count} tokens across {vision_doc.chunk_count} chunks
**Status**: MUST BE READ COMPLETELY

### Fetch Commands (execute ALL)
"""
    # Add fetch commands for each chunk
    for i in range(vision_doc.chunk_count):
        instruction += f'fetch_vision_document(product_id="{product.id}", offset={i}, limit=1)  # Chunk {i+1}\n'

    return instruction.strip()

def _generate_fetch_commands(self, product_id: str, chunk_count: int) -> list[str]:
    """Generate list of fetch commands for all chunks."""
    return [
        f'fetch_vision_document(product_id="{product_id}", offset={i}, limit=1)'
        for i in range(chunk_count)
    ]

async def _summarize_vision_content(self, vision_doc: VisionDocument, ratio: float) -> str:
    """
    Summarize vision content to target ratio (0.33 or 0.66).

    MVP Implementation: Simple truncation (placeholder)
    Future: AI-powered summarization
    """
    # Get full content from chunks
    full_content = ""
    for chunk in vision_doc.chunks:
        full_content += chunk.content + "\n\n"

    # Calculate target token count
    target_tokens = int(vision_doc.original_token_count * ratio)

    # Simple truncation (MVP - replace with AI summarization later)
    # Approximate: 1 token ≈ 4 characters
    target_chars = target_tokens * 4

    if len(full_content) <= target_chars:
        return full_content

    # Truncate at sentence boundary
    truncated = full_content[:target_chars]
    last_period = truncated.rfind('.')
    if last_period > target_chars * 0.8:  # At least 80% of target
        truncated = truncated[:last_period + 1]

    return truncated + f"\n\n[Content summarized to {ratio*100:.0f}% - {target_tokens} tokens]"
```

### File: `api/endpoints/context.py`

**Update valid values**:

```python
VALID_VISION_DEPTH_VALUES = ["optional", "light", "medium", "full"]

@router.put("/depth-config")
async def update_depth_config(
    request: UpdateDepthConfigRequest,
    tenant_key: str = Depends(get_tenant_key)
):
    """Update context depth configuration with validation."""

    # Validate vision_documents depth
    vision_depth = request.depth_config.get("vision_documents")
    if vision_depth and vision_depth not in VALID_VISION_DEPTH_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid vision_documents depth: {vision_depth}. "
                   f"Valid values: {', '.join(VALID_VISION_DEPTH_VALUES)}"
        )

    # ... rest of endpoint logic ...
```

### File: `frontend/src/components/settings/ContextPriorityConfig.vue`

**Update depth options**:

```vue
<script setup lang="ts">
// ... existing imports ...

const visionDepthOptions = [
  {
    value: "optional",
    title: "Optional (Orchestrator decides)",
    subtitle: "~200 tokens - Pointer only, fetch if needed"
  },
  {
    value: "light",
    title: "Light (33% summary)",
    subtitle: "~10-12K tokens - High-level context inline"
  },
  {
    value: "medium",
    title: "Medium (66% summary)",
    subtitle: "~20-24K tokens - Balanced detail inline"
  },
  {
    value: "full",
    title: "Full (Mandatory complete read)",
    subtitle: "~200 tokens + fetch cost - Forces orchestrator to read all"
  }
];

// ... existing code ...

function updateVisionDepth(newDepth: string) {
  emit('update:depthConfig', {
    ...props.depthConfig,
    vision_documents: newDepth
  });

  // Show warning for Full mode
  if (newDepth === 'full') {
    showFullModeWarning();
  }
}

function showFullModeWarning() {
  // Display snackbar/alert explaining Full mode behavior
  snackbar.value = {
    show: true,
    color: 'warning',
    message: 'Full mode requires orchestrator to fetch and read all vision chunks. ' +
             'This may increase token usage during mission generation.',
    timeout: 5000
  };
}
</script>

<template>
  <!-- ... existing template ... -->

  <!-- Vision Documents Depth Dropdown -->
  <v-select
    :model-value="depthConfig.vision_documents || 'optional'"
    @update:model-value="updateVisionDepth"
    :items="visionDepthOptions"
    item-title="title"
    item-value="value"
    density="compact"
    variant="outlined"
    hide-details
    label="Vision Documents Depth"
    data-testid="vision-depth-select"
  >
    <template #item="{ item, props }">
      <v-list-item v-bind="props">
        <v-list-item-title>{{ item.raw.title }}</v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          {{ item.raw.subtitle }}
        </v-list-item-subtitle>
      </v-list-item>
    </template>
  </v-select>

  <!-- Full Mode Warning Snackbar -->
  <v-snackbar
    v-model="snackbar.show"
    :color="snackbar.color"
    :timeout="snackbar.timeout"
  >
    {{ snackbar.message }}
  </v-snackbar>
</template>
```

## Testing Strategy (TDD Approach)

### Test File: `tests/unit/test_mission_planner.py`

**Write tests FIRST (they will fail initially)**:

```python
import pytest
from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, VisionDocument

class TestVisionDepth4Levels:
    """TDD tests for 4-level vision depth configuration."""

    @pytest.fixture
    def sample_vision_doc(self):
        """Create sample vision document with known token count."""
        vision_doc = Mock(spec=VisionDocument)
        vision_doc.original_token_count = 30000
        vision_doc.chunk_count = 3
        vision_doc.chunks = [
            Mock(content="Chunk 1 content " * 100),
            Mock(content="Chunk 2 content " * 100),
            Mock(content="Chunk 3 content " * 100),
        ]
        return vision_doc

    @pytest.fixture
    def sample_product(self):
        """Create sample product."""
        product = Mock(spec=Product)
        product.id = "prod_123"
        product.name = "Test Product"
        return product

    @pytest.mark.asyncio
    async def test_optional_depth_returns_pointer_only(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        BEHAVIOR: Optional depth provides pointer without inline content.
        EXPECTED: ~200 tokens, no content field, includes fetch_tool.
        """
        depth_config = {"vision_documents": "optional"}

        context = await mission_planner._build_context_with_priorities(
            sample_product, None, {"depth_config": depth_config}
        )

        vision_section = context["vision_documents"]

        # Assert pointer-only structure
        assert vision_section["status"] == "AVAILABLE_ON_REQUEST"
        assert vision_section["priority"] == "NICE_TO_HAVE"
        assert "content" not in vision_section  # No inline content
        assert vision_section["fetch_tool"] == "fetch_vision_document(product_id, offset, limit)"
        assert "when_to_fetch" in vision_section

        # Assert token count is minimal (~200)
        estimated_tokens = mission_planner._count_tokens(str(vision_section))
        assert 150 <= estimated_tokens <= 300, f"Expected ~200 tokens, got {estimated_tokens}"

    @pytest.mark.asyncio
    async def test_light_depth_includes_33_percent_summary(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        BEHAVIOR: Light depth inlines 33% summarized content.
        EXPECTED: ~10-12K tokens inline content.
        """
        depth_config = {"vision_documents": "light"}

        context = await mission_planner._build_context_with_priorities(
            sample_product, None, {"depth_config": depth_config}
        )

        vision_section = context["vision_documents"]

        # Assert inline summary structure
        assert vision_section["status"] == "INLINE_SUMMARY"
        assert vision_section["priority"] == "IMPORTANT"
        assert "content" in vision_section  # Has inline content
        assert vision_section["coverage"] == "33% of original vision"

        # Assert token count is ~33% of original (30K * 0.33 = ~10K)
        token_count = vision_section["tokens"]
        assert 9000 <= token_count <= 13000, f"Expected ~10-12K tokens, got {token_count}"

    @pytest.mark.asyncio
    async def test_medium_depth_includes_66_percent_summary(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        BEHAVIOR: Medium depth inlines 66% summarized content.
        EXPECTED: ~20-24K tokens inline content.
        """
        depth_config = {"vision_documents": "medium"}

        context = await mission_planner._build_context_with_priorities(
            sample_product, None, {"depth_config": depth_config}
        )

        vision_section = context["vision_documents"]

        # Assert inline summary structure
        assert vision_section["status"] == "INLINE_SUMMARY"
        assert vision_section["priority"] == "IMPORTANT"
        assert "content" in vision_section
        assert vision_section["coverage"] == "66% of original vision"

        # Assert token count is ~66% of original (30K * 0.66 = ~20K)
        token_count = vision_section["tokens"]
        assert 18000 <= token_count <= 25000, f"Expected ~20-24K tokens, got {token_count}"

    @pytest.mark.asyncio
    async def test_full_depth_includes_mandatory_read_instruction(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        BEHAVIOR: Full depth includes explicit REQUIRED_READING instruction.
        EXPECTED: Instruction forbids skipping, lists all fetch commands.
        """
        depth_config = {"vision_documents": "full"}

        context = await mission_planner._build_context_with_priorities(
            sample_product, None, {"depth_config": depth_config}
        )

        vision_section = context["vision_documents"]

        # Assert mandatory read structure
        assert vision_section["status"] == "REQUIRED_READING"
        assert vision_section["priority"] == "CRITICAL"
        assert "instruction" in vision_section

        instruction = vision_section["instruction"]

        # Assert instruction forbids skipping
        assert "MUST" in instruction.upper()
        assert "NOT optional" in instruction or "NOT OPTIONAL" in instruction.upper()
        assert "violates the user's configuration" in instruction.lower()

        # Assert all fetch commands listed
        assert len(vision_section["fetch_commands"]) == sample_vision_doc.chunk_count
        for i, cmd in enumerate(vision_section["fetch_commands"]):
            assert f'offset={i}' in cmd
            assert sample_product.id in cmd

    @pytest.mark.asyncio
    async def test_full_depth_prohibits_skipping(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        BEHAVIOR: Full mode instruction explicitly states skipping is forbidden.
        EXPECTED: Instruction contains strong language about compliance.
        """
        depth_config = {"vision_documents": "full"}

        context = await mission_planner._build_context_with_priorities(
            sample_product, None, {"depth_config": depth_config}
        )

        instruction = context["vision_documents"]["instruction"]

        # Test for strong compliance language
        compliance_phrases = [
            "you must",
            "this is not optional",
            "violates",
            "required",
            "before creating your mission"
        ]

        instruction_lower = instruction.lower()
        matched_phrases = [p for p in compliance_phrases if p in instruction_lower]

        assert len(matched_phrases) >= 3, \
            f"Instruction lacks strong compliance language. Found: {matched_phrases}"

    @pytest.mark.asyncio
    async def test_token_budgets_per_level(
        self, mission_planner, sample_product, sample_vision_doc
    ):
        """
        BEHAVIOR: Each depth level produces predictable token count.
        EXPECTED: Optional/Full ~200, Light ~10-12K, Medium ~20-24K.
        """
        test_cases = [
            ("optional", 150, 300),
            ("light", 9000, 13000),
            ("medium", 18000, 25000),
            ("full", 150, 300),
        ]

        for depth_value, min_tokens, max_tokens in test_cases:
            depth_config = {"vision_documents": depth_value}

            context = await mission_planner._build_context_with_priorities(
                sample_product, None, {"depth_config": depth_config}
            )

            vision_section = context["vision_documents"]

            # Estimate tokens
            if "tokens" in vision_section:
                actual_tokens = vision_section["tokens"]
            else:
                actual_tokens = mission_planner._count_tokens(str(vision_section))

            assert min_tokens <= actual_tokens <= max_tokens, \
                f"Depth '{depth_value}' produced {actual_tokens} tokens, " \
                f"expected {min_tokens}-{max_tokens}"
```

### Test File: `frontend/src/components/settings/__tests__/ContextPriorityConfig.spec.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import ContextPriorityConfig from '../ContextPriorityConfig.vue';

describe('ContextPriorityConfig - Vision Depth 4 Levels', () => {
  it('displays all 4 vision depth options', async () => {
    const wrapper = mount(ContextPriorityConfig, {
      props: {
        depthConfig: { vision_documents: 'optional' }
      }
    });

    const select = wrapper.find('[data-testid="vision-depth-select"]');
    const options = select.findAll('option');

    expect(options).toHaveLength(4);
    expect(options[0].text()).toContain('Optional');
    expect(options[1].text()).toContain('Light');
    expect(options[2].text()).toContain('Medium');
    expect(options[3].text()).toContain('Full');
  });

  it('shows warning when Full mode is selected', async () => {
    const wrapper = mount(ContextPriorityConfig, {
      props: {
        depthConfig: { vision_documents: 'optional' }
      }
    });

    const select = wrapper.find('[data-testid="vision-depth-select"]');
    await select.setValue('full');

    // Wait for snackbar to appear
    await wrapper.vm.$nextTick();

    const snackbar = wrapper.find('.v-snackbar');
    expect(snackbar.exists()).toBe(true);
    expect(snackbar.text()).toContain('Full mode requires orchestrator to fetch');
  });

  it('emits update event when depth selection changes', async () => {
    const wrapper = mount(ContextPriorityConfig, {
      props: {
        depthConfig: { vision_documents: 'optional' }
      }
    });

    const select = wrapper.find('[data-testid="vision-depth-select"]');
    await select.setValue('medium');

    expect(wrapper.emitted('update:depthConfig')).toBeTruthy();
    const emittedValue = wrapper.emitted('update:depthConfig')[0][0];
    expect(emittedValue.vision_documents).toBe('medium');
  });
});
```

## Testing Execution Order (TDD)

**CRITICAL**: Follow this exact order:

1. **Write tests FIRST** (they will fail - this is expected)
   ```bash
   pytest tests/unit/test_mission_planner.py::TestVisionDepth4Levels -v
   # Expected: All 6 tests FAIL
   ```

2. **Implement minimal code to make tests pass**
   - Add helper methods to `MissionPlanner`
   - Update `_build_context_with_priorities()`

3. **Run tests again**
   ```bash
   pytest tests/unit/test_mission_planner.py::TestVisionDepth4Levels -v
   # Expected: All 6 tests PASS
   ```

4. **Refactor if needed** (keep tests passing)

5. **Frontend tests**
   ```bash
   cd frontend && npm run test -- ContextPriorityConfig.spec.ts
   ```

## Rollback Plan

If issues arise during deployment:

### Immediate Rollback (< 5 minutes)
1. Revert commit with `git revert <commit-hash>`
2. Redeploy previous version
3. User settings automatically fallback to "optional" (safe default)

### Partial Rollback (keep backend, disable frontend)
1. Hide 4-option dropdown in UI (show old binary toggle)
2. Backend continues working with "optional" default
3. Fix frontend issues in next release

### Data Migration (if users already configured)
- No migration needed - new values are additive
- Existing "none"/"light"/"moderate"/"heavy" map to new system:
  - "none" → "optional"
  - "light" → "light" (same)
  - "moderate" → "medium"
  - "heavy" → "full"

## Token Impact Analysis

### Before (2-level system)
| Mode | Tokens | User Complaints |
|------|--------|-----------------|
| Pointer-only | ~200 | "Orchestrator skips vision" |
| Full-inline | ~30K | "Too many tokens wasted" |

### After (4-level system)
| Level | Tokens | User Benefit |
|-------|--------|--------------|
| Optional | ~200 | Trust orchestrator |
| Light | ~10-12K | Quick context |
| Medium | ~20-24K | Balanced detail |
| Full | ~200 + fetch | Guaranteed compliance |

**Savings**:
- Light users: 68% reduction (30K → 10K)
- Medium users: 30% reduction (30K → 20K)
- Full users: 95% upfront + deferred fetch (user controls cost)

## Definition of Done

### Code Complete
- [ ] All 6 backend TDD tests written AND passing
- [ ] All 3 frontend unit tests written AND passing
- [ ] Backend implementation in `MissionPlanner` complete
- [ ] Frontend dropdown updated with 4 options
- [ ] API validation updated for new values

### Quality Gates
- [ ] Test coverage >80% for new code
- [ ] No regressions in existing tests
- [ ] Manual testing: Select each depth level, verify YAML output
- [ ] Token counts verified (±10% tolerance acceptable)

### Documentation
- [ ] CLAUDE.md updated with 4-level system
- [ ] Inline code comments explaining depth logic
- [ ] User-facing help text in UI tooltips

### Deployment Ready
- [ ] Git commit with descriptive message (ref: Handover 0347e)
- [ ] CHANGELOG.md entry added
- [ ] Handover marked complete with completion summary
- [ ] Knowledge transfer: Orchestrator agent updated with new depth options

## Lessons Learned (Post-Implementation)

*To be filled after handover completion*

### What Went Well
- TBD

### What Could Improve
- TBD

### Future Enhancements
- Replace placeholder truncation with AI-powered summarization
- Add user feedback loop: "Was this depth level helpful?"
- Track orchestrator fetch behavior: Do they actually read Full mode?
- A/B test: Does Full mode improve mission quality?

---

**Last Updated**: 2025-12-14
**Assigned To**: TDD Implementor Agent
**Estimated Completion**: 3 hours
**Dependencies**: ✅ 0347b (MissionPlanner YAML restructuring)

---

## Related Handovers

- **0347**: Mission Response YAML Restructuring (parent)
- **0347a**: JSON Core Migration (completed)
- **0347b**: MissionPlanner JSON Upgrade (dependency)
- **0347c**: Settings Endpoint Alignment (parallel)
- **0347d**: Frontend JSON Display (parallel)
- **0347e**: Vision Document 4-Level Depth (this handover)
